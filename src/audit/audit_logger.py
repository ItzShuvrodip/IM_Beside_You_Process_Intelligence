import json
import hashlib
import logging
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

GENESIS_HASH = "0" * 64


class AuditLogger:
    """Append-only audit logger with SHA-256 hash chaining and thread-safe locking."""
    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = Path(log_path) if log_path else (Path(__file__).resolve().parent.parent.parent / "deliverables" / "audit_trail.jsonl")
        self.records: List[Dict[str, Any]] = []
        self.records_count = 0
        self.last_hash = GENESIS_HASH
        self._lock = threading.RLock()
        self._initialize_from_disk()

    def _initialize_from_disk(self) -> None:
        """Loads existing ledger tail and historical records to resume monotonic numbering and hash chain."""
        if not self.log_path.exists():
            return
        try:
            count = 0
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        count += 1
                        try:
                            data = json.loads(line)
                            if "entry_hash" in data:
                                self.last_hash = data["entry_hash"]
                            self.records.append(data)
                        except Exception:
                            pass
            self.records_count = count
        except Exception as e:
            logger.warning(f"Could not read existing audit trail for hash chain: {e}")
            self.records_count = 0

    def _compute_hash(self, payload: Dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        hasher = hashlib.sha256()
        hasher.update(self.last_hash.encode("utf-8"))
        hasher.update(serialized.encode("utf-8"))
        return hasher.hexdigest()

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
        with self._lock:
            self.records_count += 1
            audit_num = self.records_count
            record = {
                "audit_id": f"AUD-{audit_num:05d}",
                "case_id": case_id,
                "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "policy_version": policy_version,
                "governance_mode": "shadow_decision_support",
                "status": status,
                "decision_notes": decision_notes,
                "input_data": input_data,
                "calculated_details": calculated_details,
                "rule_audit_trail": audit_trail,
                "supervisor_override": None,
                "prev_hash": self.last_hash
            }
            entry_hash = self._compute_hash(record)
            record["entry_hash"] = entry_hash
            self.last_hash = entry_hash

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
        with self._lock:
            for rec in reversed(self.records):
                if rec.get("case_id") == case_id and rec.get("record_type") != "SUPERVISOR_OVERRIDE":
                    override_data = {
                        "overridden_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "reviewer_id": reviewer_id,
                        "original_status": original_status,
                        "override_decision": override_decision,
                        "justification": reason
                    }
                    rec["supervisor_override"] = override_data
                    delta = {
                        "audit_id": rec.get("audit_id"),
                        "case_id": case_id,
                        "record_type": "SUPERVISOR_OVERRIDE",
                        "supervisor_override": override_data,
                        "prev_hash": self.last_hash
                    }
                    entry_hash = self._compute_hash(delta)
                    delta["entry_hash"] = entry_hash
                    self.last_hash = entry_hash

                    self.records.append(delta)
                    self._append_to_disk(delta)
                    return rec
            return None

    def get_history(self, case_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            if case_id:
                return [r for r in self.records if r.get("case_id") == case_id]
            return list(self.records)

    def _append_to_disk(self, record: Dict[str, Any]):
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Could not persist audit record to disk: {e}")
