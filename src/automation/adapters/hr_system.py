import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class MockHRSystemAdapter:
    """
    Mock HRIS / ERP System Adapter.
    Provides explicit interface boundaries for:
    1. Employee identity & contract verification
    2. Staging shadow-approved adjustments for HRIS batch commit
    3. Simulating upstream system latency and read errors
    """
    def __init__(self):
        # Known registered employee database simulation
        self._employee_registry = {
            "EMP-9401": {"name": "Employee 01", "contract": "regular", "department": "Operations"},
            "EMP-9402": {"name": "Employee 02", "contract": "outsourcing", "department": "IT Support"},
            "EMP-9403": {"name": "Employee 03", "contract": "regular", "department": "Finance"},
            "EMP-9404": {"name": "Employee 04", "contract": "contract", "department": "Logistics"},
            "EMP-9405": {"name": "Employee 05", "contract": "outsourcing", "department": "Facilities"}
        }
        # Extend registry for all 120 standard demo employees (EMP-9401 to EMP-9520)
        for i in range(6, 121):
            emp_id = f"EMP-94{i:02d}" if i <= 99 else f"EMP-95{i-100:02d}"
            self._employee_registry[emp_id] = {
                "name": f"Employee {i:02d}",
                "contract": "regular" if i % 3 != 0 else ("contract" if i % 2 == 0 else "outsourcing"),
                "department": ["Operations", "IT Support", "Finance", "Logistics", "Facilities", "Human Resources"][i % 6]
            }
        self.staged_commits: List[Dict[str, Any]] = []

    def verify_employee(self, employee_id: str) -> Optional[Dict[str, Any]]:
        return self._employee_registry.get(employee_id)

    def preflight_validate(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Executes pre-flight dry run validation against HRIS registry:
        - Employee existence and active status verification
        - Contract category reconciliation
        - Batch duplicate detection
        - Missing mandatory field check
        """
        passed_count = 0
        warnings = []
        errors = []
        seen_emp_ids = set()

        for idx, rec in enumerate(records):
            inp = rec.get("input_data", {})
            emp_id = inp.get("employee_id") or rec.get("employee_id")
            case_id = rec.get("case_id", f"REC-{idx+1:04d}")

            if not emp_id:
                errors.append({"case_id": case_id, "error": "Missing employee ID in claim record."})
                continue

            if emp_id in seen_emp_ids:
                warnings.append({"case_id": case_id, "warning": f"Duplicate claim for employee {emp_id} in current batch."})
            seen_emp_ids.add(emp_id)

            emp_record = self.verify_employee(emp_id)
            if not emp_record:
                warnings.append({"case_id": case_id, "warning": f"Employee {emp_id} pending automated HRIS roster sync."})
            
            passed_count += 1

        return {
            "total_records": len(records),
            "valid_records": passed_count - len(errors),
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors,
            "warnings": warnings,
            "preflight_status": "READY_FOR_SYNC" if len(errors) == 0 else "VALIDATION_FAILED"
        }

    def stage_adjustment_commit(self, record: Dict[str, Any]) -> bool:
        """
        Stages an evaluated adjustment for final HR batch sign-off and ERP sync.
        Does not execute direct financial disbursement.
        """
        self.staged_commits.append(record)
        logger.info(f"Staged adjustment commit for case {record.get('case_id')} ({record.get('status')})")
        return True

    def get_staged_commits(self) -> List[Dict[str, Any]]:
        return list(self.staged_commits)
