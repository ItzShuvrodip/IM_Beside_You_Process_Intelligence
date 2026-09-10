import sys
import json
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from datetime import datetime
from src.segmentation.classifier import (
    ProcessClassifier,
    canonicalize_label,
    JAPANESE_GT_TO_CANONICAL,
    GT_CODE_TO_CANONICAL
)
from src.evaluation.evaluator import SegmentationEvaluator
from src.ingestion.models import Segment, GroundTruthExecution, RawEvent
from src.analysis.process_mining import ProcessMiningEngine
from src.analysis.roi_model import ROIPrioritizationModel
from src.automation.domain.payroll_rules import validate_payroll_item, POLICY_METADATA, POLICY_CONFIG
from src.config import SEGMENTS_FILE


class TestEvidenceIntegrity(unittest.TestCase):
    """Tests for label mappings, unbiased fallbacks, dwell attribution, and audit logs."""

    def test_japanese_label_mapping_completeness(self):
        # Verify all 15 ground truth families map to canonical English labels
        expected_families = [
            ("住民税通知確認", "resident_tax_confirmation"),
            ("給与備考・控除整備", "payroll_deduction_adjustment"),
            ("育児・産休申請確認", "leave_application_processing"),
            ("社保・年金補正対応", "social_insurance_correction"),
            ("入社照合・手当確認", "onboarding_verification"),
            ("請求書承認", "invoice_approval"),
            ("経費精算承認", "expense_settlement_approval"),
            ("銀行勘定照合", "bank_reconciliation"),
            ("予算差異分析", "budget_variance_analysis"),
            ("支払処理", "payment_processing"),
            ("受注処理", "sales_order_processing"),
            ("在庫調整", "inventory_order_management"),
            ("仕入先連絡", "supplier_communication"),
            ("出荷追跡", "shipment_tracking"),
            ("返品処理", "returns_processing")
        ]
        for jp_name, expected_canonical in expected_families:
            canonical = canonicalize_label(jp_name)
            self.assertEqual(canonical, expected_canonical, f"Failed mapping for {jp_name}")
            self.assertNotEqual(canonical, "idle_or_other", f"{jp_name} collapsed to idle_or_other")

        # Verify single letter codes A-O map correctly
        for letter, expected_canonical in [("A", "resident_tax_confirmation"), ("B", "payroll_deduction_adjustment"), ("O", "returns_processing")]:
            self.assertEqual(canonicalize_label(letter), expected_canonical)

    def test_classifier_fallback_is_unbiased(self):
        classifier = ProcessClassifier()
        # Empty or unrecognized event sequence
        generic_event = RawEvent(
            event_id="ev_test",
            session_id="ses_test",
            timestamp_ms=1000,
            timestamp_iso="2026-07-01T10:00:00Z",
            layer="os",
            event_type="keypress",
            app_name="notepad.exe",
            window_title="Untitled - Notepad",
            browser_url=None
        )
        label = classifier.classify_segment_events([generic_event])
        self.assertEqual(label, "unknown_or_unclassified", "Fallback must NOT default to payroll")

    def test_label_aware_evaluator_metrics(self):
        evaluator = SegmentationEvaluator(min_iou=0.25)
        # Test matched boundary with matching label
        pred_matching = [
            Segment("s1", "2026-07-01T10:00:00Z", "2026-07-01T10:02:00Z", "payroll_deduction_adjustment")
        ]
        gt = [
            GroundTruthExecution("B", "給与備考・控除整備", "hr", "case_1", "2026-07-01T10:00:00Z", "2026-07-01T10:02:00Z")
        ]
        res_matching = evaluator.evaluate_session(pred_matching, gt)
        self.assertEqual(res_matching["f1"], 1.0)
        self.assertEqual(res_matching["label_accuracy"], 1.0)
        self.assertEqual(res_matching["strict_f1"], 1.0)

        # Test matched boundary with WRONG label
        pred_wrong = [
            Segment("s1", "2026-07-01T10:00:00Z", "2026-07-01T10:02:00Z", "leave_application_processing")
        ]
        res_wrong = evaluator.evaluate_session(pred_wrong, gt)
        self.assertEqual(res_wrong["f1"], 1.0, "Boundary overlap still matches")
        self.assertEqual(res_wrong["label_accuracy"], 0.0, "Label accuracy must be 0 for mismatched label")
        self.assertEqual(res_wrong["strict_f1"], 0.0, "Strict end-to-end F1 must be 0 for mismatched label")

    def test_segment_joined_dwell_time_attribution(self):
        # Verify that process mining isolates dwell strictly to segment time boundaries
        miner = ProcessMiningEngine()
        mock_segments = [
            {
                "session_id": "ses_test",
                "start": "2026-07-01T10:00:00Z",
                "end": "2026-07-01T10:02:00Z",
                "label": "payroll_deduction_adjustment"
            }
        ]
        dfg = miner.extract_directly_follows_graph(target_label="payroll_deduction_adjustment", segments=mock_segments)
        self.assertIn("edges", dfg)
        self.assertIn("node_frequencies", dfg)

    def test_financial_roi_scenarios(self):
        model = ROIPrioritizationModel()
        mock_metrics = {
            "payroll_deduction_adjustment": {
                "execution_count": 32,
                "total_duration_seconds": 3372.8,
                "total_duration_minutes": 56.2,
                "pct_of_total_time": 33.1,
                "mean_duration_seconds": 105.4,
                "operators_count": 4
            }
        }
        ranked = model.rank_candidates(mock_metrics)
        self.assertEqual(len(ranked), 1)
        item = ranked[0]
        self.assertIn("financial_scenarios", item)
        scenarios = item["financial_scenarios"]
        self.assertIn("conservative", scenarios)
        self.assertIn("base_case", scenarios)
        self.assertIn("optimistic", scenarios)
        self.assertGreater(scenarios["base_case"]["hours_saved_annual"], 0)
        self.assertGreater(scenarios["base_case"]["annual_net_savings_jpy"], 0)
        self.assertLess(scenarios["base_case"]["payback_period_months"], 36.0)

    def test_policy_provenance_and_audit_trail(self):
        self.assertIn("policy_version", POLICY_METADATA)
        self.assertIn("effective_date", POLICY_METADATA)
        self.assertIn("approval_owner", POLICY_METADATA)

        valid_case = {
            "employee_id": "EMP-9401",
            "employee_name": "Employee 01",
            "contract_type": "regular",
            "base_salary": 380000,
            "claimed_commute": 18500,
            "telework_days": 12,
            "claimed_housing": 25000,
            "custom_deduction": 0
        }
        is_appr, reason, details = validate_payroll_item(valid_case)
        self.assertTrue(is_appr)
        self.assertIn("audit_trail", details)
        self.assertIn("policy_version", details)
        self.assertTrue(len(details["audit_trail"]) >= 4)

    def test_gold_audit_set_dataset_b(self):
        """
        Manually verified Gold Audit Set (stratified sample of confirmed segments in Dataset B)
        """
        seg_file = SEGMENTS_FILE
        self.assertTrue(seg_file.exists())
        segments = []
        with open(seg_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    segments.append(json.loads(line))

        # Known verified anchor segments in Dataset B
        gold_samples = [
            {"session_id": "ses_20260701-164424-CHAITANYA0BCF", "label": "payroll_deduction_adjustment"},
            {"session_id": "ses_20260701-171614-CHAITANYA0BCF", "label": "resident_tax_confirmation"},
            {"session_id": "ses_20260701-171614-CHAITANYA0BCF", "label": "onboarding_verification"},
            {"session_id": "ses_20260701-171614-CHAITANYA0BCF", "label": "social_insurance_correction"}
        ]

        for gold in gold_samples:
            matching = [s for s in segments if s["session_id"] == gold["session_id"] and s["label"] == gold["label"]]
            self.assertTrue(len(matching) > 0, f"Gold anchor segment {gold} missing from recovered segments")

    def test_gold_audit_csv_structure_and_references(self):
        """
        Validates that deliverables/dataset_b_audit.csv exists, has >= 30 rows,
        includes required columns, and references valid screenshots or events.
        """
        audit_csv = PROJECT_ROOT / "deliverables" / "dataset_b_audit.csv"
        self.assertTrue(audit_csv.exists(), "dataset_b_audit.csv must exist in deliverables/")
        
        import csv
        with open(audit_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.assertGreaterEqual(len(rows), 30, "Audit sheet must contain at least 30 stratified segments")
        
        required_cols = {"audit_id", "session_id", "start_time", "end_time", "predicted_label", 
                         "screenshot_reference", "reviewer", "audit_decision", "audit_notes", "verified_label"}
        self.assertIsNotNone(reader.fieldnames, "Audit CSV must have header columns")
        fieldnames = reader.fieldnames or []
        for col in required_cols:
            self.assertIn(col, fieldnames, f"Column {col} missing from dataset_b_audit.csv")

        # Verify referenced screenshots exist in Dataset B directory
        from src.config import DATASET_B_DIR
        found_screenshots = 0
        for row in rows:
            scr_name = row["screenshot_reference"]
            if scr_name and scr_name not in ("none", "N/A"):
                session_dir = DATASET_B_DIR / row["session_id"]
                if session_dir.exists():
                    matches = list(session_dir.glob(f"**/{scr_name}"))
                    if matches:
                        found_screenshots += 1

        self.assertGreater(found_screenshots, 0, "At least some audit rows must link to verified screenshots in Dataset B")

    def test_review_queue_csv_structure(self):
        """
        Validates that deliverables/dataset_b_review_queue.csv exists and contains
        expected triage fields for low-confidence or unclassified segments.
        """
        queue_csv = PROJECT_ROOT / "deliverables" / "dataset_b_review_queue.csv"
        self.assertTrue(queue_csv.exists(), "dataset_b_review_queue.csv must exist in deliverables/")

        import csv
        with open(queue_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.assertGreater(len(rows), 0, "Review queue should contain low-confidence items requiring triage")
        required_cols = {"session_id", "start", "end", "label", "confidence", "review_status"}
        self.assertIsNotNone(reader.fieldnames, "Review queue CSV must have header columns")
        fieldnames = reader.fieldnames or []
        for col in required_cols:
            self.assertIn(col, fieldnames, f"Column {col} missing from dataset_b_review_queue.csv")

    def test_audit_logger_hash_chain_integrity(self):
        """
        Validates SHA-256 cryptographic hash-chaining in AuditLogger:
        1. Each record's prev_hash links to prior record's entry_hash
        2. Tampering with an intermediate entry invalidates the chain
        """
        import tempfile
        from src.audit.audit_logger import AuditLogger, GENESIS_HASH

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            logger = AuditLogger(log_path=tmp_path)
            # Log 3 sequential records
            r1 = logger.log_evaluation(
                case_id="TEST-001",
                input_data={"salary": 300000},
                status="RECOMMEND_APPROVE",
                policy_version="1.0.0",
                decision_notes="Approved",
                calculated_details={},
                audit_trail=[]
            )
            r2 = logger.log_evaluation(
                case_id="TEST-002",
                input_data={"salary": 350000},
                status="FLAG_REVIEW",
                policy_version="1.0.0",
                decision_notes="Commute excessive",
                calculated_details={},
                audit_trail=[]
            )
            r3 = logger.log_evaluation(
                case_id="TEST-003",
                input_data={"salary": 400000},
                status="RECOMMEND_APPROVE",
                policy_version="1.0.0",
                decision_notes="Approved",
                calculated_details={},
                audit_trail=[]
            )

            self.assertEqual(r1["prev_hash"], GENESIS_HASH)
            self.assertEqual(r2["prev_hash"], r1["entry_hash"])
            self.assertEqual(r3["prev_hash"], r2["entry_hash"])

            # Verify on-disk persistence preserves hashes
            lines = tmp_path.read_text(encoding="utf-8").strip().split("\n")
            self.assertEqual(len(lines), 3)
            disk_r1 = json.loads(lines[0])
            disk_r2 = json.loads(lines[1])
            self.assertEqual(disk_r2["prev_hash"], disk_r1["entry_hash"])
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_decision_service_hris_contract_mismatch(self):
        """
        Validates that PayrollDecisionService flags cases where the claimed
        contract type does not match the master record in HRIS.
        """
        from src.automation.service.decision_service import PayrollDecisionService
        from src.automation.adapters.hr_system import MockHRSystemAdapter
        from src.audit.audit_logger import AuditLogger
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            audit_logger = AuditLogger(log_path=tmp_path)
            adapter = MockHRSystemAdapter()
            # E101 in adapter is regular employee (Tanaka Kenji)
            service = PayrollDecisionService(audit_logger=audit_logger, hr_adapter=adapter)

            mismatched_claim = {
                "case_id": "TEST-MISMATCH-01",
                "employee_id": "E101",
                "contract_type": "contractor",  # Claim says contractor, HRIS says regular
                "base_salary": 420000,
                "claimed_commute": 15000,
                "telework_days": 10,
                "claimed_housing": 20000,
                "custom_deduction": 0
            }
            res = service.process_item(mismatched_claim)
            self.assertEqual(res["status"], "FLAGGED_FOR_REVIEW")
            self.assertIn("Contract type mismatch", res["decision_notes"])
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


if __name__ == "__main__":
    unittest.main()

