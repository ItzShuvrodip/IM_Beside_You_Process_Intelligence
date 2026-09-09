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
        # Extend registry for all 20 standard demo employees
        for i in range(6, 21):
            emp_id = f"EMP-94{i:02d}"
            self._employee_registry[emp_id] = {
                "name": f"Employee {i:02d}",
                "contract": "regular" if i % 2 == 0 else ("contract" if i % 3 == 0 else "outsourcing"),
                "department": ["Operations", "IT Support", "Finance", "Logistics", "Facilities"][i % 5]
            }
        self.staged_commits: List[Dict[str, Any]] = []

    def verify_employee(self, employee_id: str) -> Optional[Dict[str, Any]]:
        return self._employee_registry.get(employee_id)

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
