import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from src.automation.service.decision_service import PayrollDecisionService as PayrollAdjustmentAutomationEngine
from src.automation.domain.payroll_rules import validate_payroll_item, POLICY_CONFIG


class TestPayrollAutomationEngine(unittest.TestCase):
    def setUp(self):
        self.engine = PayrollAdjustmentAutomationEngine()

    def test_regular_employee_auto_approval(self):
        valid_item = {
            "case_id": "TEST-01",
            "employee_id": "E101",
            "employee_name": "Employee 01",
            "contract_type": "regular",
            "base_salary": 300000,
            "claimed_commute": 15000,
            "telework_days": 10,
            "claimed_housing": 20000,
            "custom_deduction": 0,
            "deduction_reason": ""
        }
        res = self.engine.process_item(valid_item)
        self.assertEqual(res["status"], "AUTO_APPROVED")
        details = res["calculated_details"]
        self.assertEqual(details["approved_commute"], 15000)
        self.assertEqual(details["approved_telework"], 2500) # 10 * 250
        self.assertEqual(details["approved_housing"], 20000)
        self.assertGreater(details["social_insurance_deduction"], 0)

    def test_outsourcing_housing_rejection(self):
        # Outsourcing staff cannot claim housing subsidy
        ineligible_item = {
            "case_id": "TEST-02",
            "employee_id": "E102",
            "employee_name": "Employee 02",
            "contract_type": "outsourcing",
            "base_salary": 400000,
            "claimed_commute": 10000,
            "telework_days": 5,
            "claimed_housing": 20000,
            "custom_deduction": 0,
            "deduction_reason": ""
        }
        res = self.engine.process_item(ineligible_item)
        self.assertEqual(res["status"], "REJECTED")

    def test_high_deduction_flagged_for_review(self):
        # Deduction exceeding 20% of base salary must be flagged
        flagged_item = {
            "case_id": "TEST-03",
            "employee_id": "E103",
            "employee_name": "Employee 03",
            "contract_type": "regular",
            "base_salary": 200000,
            "claimed_commute": 10000,
            "telework_days": 0,
            "claimed_housing": 10000,
            "custom_deduction": 50000, # 25% > 20%
            "deduction_reason": "Damage Compensation Share"
        }

        res = self.engine.process_item(flagged_item)
        self.assertEqual(res["status"], "FLAGGED_FOR_REVIEW")

    def test_batch_summary_statistics(self):
        batch = [
            {"employee_id": "E1", "employee_name": "Employee 01", "contract_type": "regular", "base_salary": 300000},
            {"employee_id": "E2", "employee_name": "Employee 02", "contract_type": "outsourcing", "base_salary": 400000, "claimed_housing": 10000},
            {"employee_id": "E3", "employee_name": "Employee 03", "contract_type": "regular", "base_salary": 200000, "custom_deduction": 60000}
        ]
        results = self.engine.process_batch(batch)
        self.assertEqual(len(results), 3)
        summary = self.engine.get_summary_report()
        self.assertEqual(summary["total_processed"], 3)
        self.assertEqual(summary["auto_approved"], 1)
        self.assertEqual(summary["rejected"], 1)
        self.assertEqual(summary["flagged_for_review"], 1)

    def test_supervisor_override_stats_synchronization(self):
        item = {
            "case_id": "TEST-OVR-01",
            "employee_id": "E103",
            "employee_name": "Employee 03",
            "contract_type": "regular",
            "base_salary": 200000,
            "custom_deduction": 50000,
            "deduction_reason": "Advance repayment"
        }
        rec = self.engine.process_item(item)
        self.assertEqual(rec["status"], "FLAGGED_FOR_REVIEW")
        rep_before = self.engine.get_summary_report()
        flagged_before = rep_before["flagged_for_review"]
        approved_before = rep_before["auto_approved"]

        # Apply override
        ovr = self.engine.record_supervisor_override(
            case_id="TEST-OVR-01",
            decision="SUPERVISOR_APPROVED",
            reason="Signed repayment authorization verified"
        )
        self.assertIsNotNone(ovr)
        self.assertEqual(ovr["status"], "SUPERVISOR_APPROVED")

        rep_after = self.engine.get_summary_report()
        self.assertEqual(rep_after["flagged_for_review"], flagged_before - 1)
        self.assertEqual(rep_after["auto_approved"], approved_before + 1)

    def test_audit_logger_disk_hydration(self):
        import tempfile
        from src.audit.audit_logger import AuditLogger
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tf:
            temp_p = Path(tf.name)

        try:
            logger1 = AuditLogger(temp_p)
            logger1.log_evaluation(
                case_id="TEMP-01",
                input_data={"test": 1},
                status="AUTO_APPROVED",
                policy_version="1.0",
                decision_notes="Approved",
                calculated_details={},
                audit_trail=[]
            )
            self.assertEqual(len(logger1.records), 1)

            # Re-instantiate logger on same file to test hydration
            logger2 = AuditLogger(temp_p)
            self.assertEqual(len(logger2.records), 1)
            self.assertEqual(logger2.records[0]["case_id"], "TEMP-01")
            self.assertEqual(logger2.records_count, 1)
            self.assertEqual(logger2.last_hash, logger1.last_hash)
        finally:
            if temp_p.exists():
                temp_p.unlink()


if __name__ == "__main__":
    unittest.main()
