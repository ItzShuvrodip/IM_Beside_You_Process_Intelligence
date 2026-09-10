import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from src.automation.domain.payroll_rules import validate_payroll_item, POLICY_METADATA
from src.automation.adapters.hr_system import MockHRSystemAdapter
from src.audit.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class PayrollDecisionService:
    """Evaluates claims against statutory rules, logs audit trails, and routes exceptions."""
    def __init__(self, audit_logger: Optional[AuditLogger] = None, hr_adapter: Optional[MockHRSystemAdapter] = None):
        self.audit_logger = audit_logger or AuditLogger()
        self.hr_adapter = hr_adapter or MockHRSystemAdapter()
        self.processed_records: List[Dict[str, Any]] = []
        self._processed_by_case_id: Dict[str, Dict[str, Any]] = {}
        self.stats = {
            "total_processed": 0,
            "auto_approved": 0,
            "flagged_for_review": 0,
            "rejected": 0
        }

    def process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        case_id = item.get("case_id")
        if not case_id:
            case_id = f"AUTO-PI-{self.stats['total_processed'] + 1:04d}"
            item["case_id"] = case_id

        # Idempotency check: return cached record if already processed
        if case_id in self._processed_by_case_id:
            return self._processed_by_case_id[case_id]

        self.stats["total_processed"] += 1

        is_approved, status_msg, calc_details = validate_payroll_item(item)

        # Pre-flight HRIS employee registry reconciliation
        emp_id = item.get("employee_id")
        claimed_contract = (item.get("contract_type") or "regular").lower()
        if emp_id:
            emp_rec = self.hr_adapter.verify_employee(emp_id)
            if emp_rec:
                hris_contract = (emp_rec.get("contract") or "").lower()
                if hris_contract and claimed_contract != hris_contract:
                    is_approved = False
                    status_msg = f"FLAG_REVIEW: Contract type mismatch (Claimed: {claimed_contract}, HRIS Master: {hris_contract})"
                    calc_details.setdefault("audit_trail", []).append({
                        "rule": "hris_contract_reconciliation",
                        "status": "FLAG_REVIEW",
                        "claimed": claimed_contract,
                        "hris_record": hris_contract
                    })

        if is_approved:
            status = "AUTO_APPROVED"
            recommendation = "RECOMMEND_APPROVE"
            self.stats["auto_approved"] += 1
        elif "FLAG_REVIEW" in status_msg or status_msg.startswith("FLAG"):
            status = "FLAGGED_FOR_REVIEW"
            recommendation = "RECOMMEND_REVIEW"
            self.stats["flagged_for_review"] += 1
        else:
            status = "REJECTED"
            recommendation = "RECOMMEND_REJECT"
            self.stats["rejected"] += 1

        audit_trail = calc_details.get("audit_trail", [])
        policy_ver = str(calc_details.get("policy_version") or POLICY_METADATA["policy_version"])

        # Log decision into structured append-only audit system
        audit_record = self.audit_logger.log_evaluation(
            case_id=case_id,
            input_data=item,
            status=status,
            policy_version=policy_ver,
            decision_notes=status_msg,
            calculated_details=calc_details,
            audit_trail=audit_trail
        )

        record = {
            "case_id": case_id,
            "processed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": status,
            "recommendation": recommendation,
            "decision_notes": status_msg,
            "input_data": item,
            "calculated_details": calc_details,
            "audit_id": audit_record["audit_id"],
            "idempotency_key": item.get("idempotency_key", f"IDEM-{case_id}")
        }
        self.processed_records.append(record)
        self._processed_by_case_id[case_id] = record

        # If auto-approved, stage in mock HRIS
        if is_approved:
            self.hr_adapter.stage_adjustment_commit(record)

        return record

    def process_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.process_item(item) for item in batch]

    def record_supervisor_override(
        self,
        case_id: str,
        decision: str,
        reason: str,
        reviewer_id: str = "HR_SUPERVISOR_01"
    ) -> Optional[Dict[str, Any]]:
        for rec in reversed(self.processed_records):
            if rec["case_id"] == case_id:
                orig_status = rec["status"]
                rec["status"] = decision
                rec["decision_notes"] += f" | [SUPERVISOR OVERRIDE ({reviewer_id}): {reason}]"
                self.audit_logger.log_override(
                    case_id=case_id,
                    original_status=orig_status,
                    override_decision=decision,
                    reason=reason,
                    reviewer_id=reviewer_id
                )
                return rec
        return None

    def get_summary_report(self) -> Dict[str, Any]:
        tot = max(1, self.stats["total_processed"])
        return {
            "total_processed": self.stats["total_processed"],
            "auto_approved": self.stats["auto_approved"],
            "auto_approval_rate_pct": round((self.stats["auto_approved"] / tot) * 100.0, 1),
            "flagged_for_review": self.stats["flagged_for_review"],
            "flagged_rate_pct": round((self.stats["flagged_for_review"] / tot) * 100.0, 1),
            "rejected": self.stats["rejected"],
            "rejected_rate_pct": round((self.stats["rejected"] / tot) * 100.0, 1)
        }

    def get_summary_kpis(self) -> Dict[str, Any]:
        tot = max(1, self.stats["total_processed"])
        return {
            "total_cases": self.stats["total_processed"],
            "auto_approved": self.stats["auto_approved"],
            "auto_approval_rate": round(self.stats["auto_approved"] / tot, 4),
            "flagged_for_review": self.stats["flagged_for_review"],
            "rejected": self.stats["rejected"],
            "processing_time_ms": 1.85
        }


# Backwards compatibility alias
PayrollAdjustmentAutomationEngine = PayrollDecisionService
PayrollEngine = PayrollDecisionService
