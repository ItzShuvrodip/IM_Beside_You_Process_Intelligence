import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Immutable, structured audit logging system for shadow-mode decision assistance.
    Captures policy provenance, evaluated rule trails, input parameters,
    and human supervisor overrides.
    """
    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = Path(log_path) if log_path else (Path("d:/IMBY/deliverables/audit_trail.jsonl"))
        self.records: List[Dict[str, Any]] = []

    def log_evaluation(
        self,
        case_id: str,
        input_data: Dict[str, Any],
        status: str,
        policy_version: str,
        decision_notes: str,
        calculated_details: Dict[str, Any],
        audit_trail: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        record = {
            "audit_id": f"AUD-{len(self.records) + 1:05d}",
            "case_id": case_id,
            "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "policy_version": policy_version,
            "governance_mode": "shadow_decision_support",
            "status": status,
            "decision_notes": decision_notes,
            "input_data": input_data,
            "calculated_details": calculated_details,
            "rule_audit_trail": audit_trail,
            "supervisor_override": None
        }
        self.records.append(record)
        self._append_to_disk(record)
        return record

    def log_override(
        self,
        case_id: str,
        original_status: str,
        override_decision: str,
        reason: str,
        reviewer_id: str = "HR_SUPERVISOR_01"
    ) -> Optional[Dict[str, Any]]:
        for rec in reversed(self.records):
            if rec["case_id"] == case_id:
                rec["supervisor_override"] = {
                    "overridden_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "reviewer_id": reviewer_id,
                    "original_status": original_status,
                    "override_decision": override_decision,
                    "justification": reason
                }
                self._append_to_disk(rec)
                return rec
        return None

    def get_history(self, case_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if case_id:
            return [r for r in self.records if r["case_id"] == case_id]
        return list(self.records)

    def _append_to_disk(self, record: Dict[str, Any]):
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Could not persist audit record to disk: {e}")
