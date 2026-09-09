import sys
import unittest
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from src.automation.service.api import app, engine


class TestAutomationServerAPI(unittest.TestCase):
    """
    Test suite for the Enterprise FastAPI Automation & Shadow Decision Server.
    Verifies all telemetry, decision engine, process mining, and CSV export endpoints.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_dashboard_root_html(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("ORBITAL AUTOMATION ENGINE", response.text)
        self.assertIn("text/html", response.headers["content-type"])

    def test_get_overview(self):
        response = self.client.get("/api/overview")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ONLINE")
        self.assertIn("kpis", data)
        self.assertIn("governance", data)
        self.assertIn("hardware", data)
        self.assertEqual(data["governance"]["mode"], "shadow_decision_support")
        self.assertIn("v2026", data["governance"]["policy_version"])

    def test_get_metrics(self):
        response = self.client.get("/api/metrics")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("total_processed", data["metrics"])

    def test_get_cases_filtering(self):
        # All cases
        resp_all = self.client.get("/api/cases")
        self.assertEqual(resp_all.status_code, 200)
        all_data = resp_all.json()
        self.assertGreater(all_data["count"], 0)

        # Filter by AUTO_APPROVED
        resp_app = self.client.get("/api/cases?status=AUTO_APPROVED")
        self.assertEqual(resp_app.status_code, 200)
        app_data = resp_app.json()
        for r in app_data["records"]:
            self.assertEqual(r["status"], "AUTO_APPROVED")

    def test_process_single_case_auto_approval(self):
        claim = {
            "case_id": "TEST-CLAIM-001",
            "employee_id": "EMP-8801",
            "employee_name": "Test Employee One",
            "contract_type": "regular",
            "base_salary": 320000,
            "claimed_commute": 12000,
            "telework_days": 8,
            "claimed_housing": 20000,
            "custom_deduction": 0,
            "deduction_reason": ""
        }
        response = self.client.post("/api/process_case", json=claim)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        res = data["result"]
        self.assertEqual(res["status"], "AUTO_APPROVED")
        self.assertEqual(res["calculated_details"]["approved_commute"], 12000)
        self.assertEqual(res["calculated_details"]["approved_telework"], 2000)
        self.assertEqual(res["calculated_details"]["approved_housing"], 20000)

    def test_process_single_case_flagged_for_review(self):
        # Custom deduction without required reason triggers FLAGGED_FOR_REVIEW
        claim = {
            "case_id": "TEST-CLAIM-002",
            "employee_id": "EMP-8802",
            "employee_name": "Test Employee Two",
            "contract_type": "contract",
            "base_salary": 280000,
            "claimed_commute": 12000,
            "telework_days": 5,
            "claimed_housing": 0,
            "custom_deduction": 8000,
            "deduction_reason": ""
        }
        response = self.client.post("/api/process_case", json=claim)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        res = data["result"]
        self.assertEqual(res["status"], "FLAGGED_FOR_REVIEW")
        self.assertIn("FLAG_REVIEW", res["decision_notes"])

    def test_supervisor_override(self):
        # Submit a flagged case first
        claim = {
            "case_id": "TEST-OVERRIDE-003",
            "employee_id": "EMP-8803",
            "employee_name": "Test Employee Three",
            "contract_type": "contract",
            "base_salary": 300000,
            "claimed_commute": 18000,
            "telework_days": 0,
            "claimed_housing": 0,
            "custom_deduction": 5000,
            "deduction_reason": ""  # missing reason triggers flag
        }
        self.client.post("/api/process_case", json=claim)

        # Now apply supervisor override
        override_payload = {
            "case_id": "TEST-OVERRIDE-003",
            "decision": "APPROVED_BY_SUPERVISOR",
            "supervisor_memo": "Approved per Department Head confirmation"
        }
        response = self.client.post("/api/supervisor_override", json=override_payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["updated_record"]["status"], "APPROVED_BY_SUPERVISOR")
        self.assertIn("SUPERVISOR OVERRIDE", data["updated_record"]["decision_notes"])

    def test_get_segments(self):
        response = self.client.get("/api/segments?limit=10")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertLessEqual(len(data["segments"]), 10)
        if data["segments"]:
            seg = data["segments"][0]
            self.assertIn("session_id", seg)
            self.assertIn("label", seg)
            self.assertIn("start", seg)
            self.assertIn("end", seg)

    def test_process_mining_endpoints(self):
        # DFG endpoint
        dfg_resp = self.client.get("/api/mining/dfg")
        self.assertEqual(dfg_resp.status_code, 200)
        dfg_data = dfg_resp.json()
        self.assertIn("dfg", dfg_data)
        self.assertIn("node_frequencies", dfg_data["dfg"])

        # Bottlenecks endpoint
        bn_resp = self.client.get("/api/mining/bottlenecks")
        self.assertEqual(bn_resp.status_code, 200)
        bn_data = bn_resp.json()
        self.assertIn("bottlenecks", bn_data)

    def test_roi_ranking(self):
        response = self.client.get("/api/roi")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("candidates", data)
        self.assertGreater(len(data["candidates"]), 0)

    def test_hardware_telemetry(self):
        response = self.client.get("/api/hardware")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("hardware", data)
        self.assertIn("model", data)

    def test_export_erp_csv(self):
        response = self.client.get("/api/export_erp_csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "text/csv; charset=utf-8")
        self.assertIn("attachment; filename=approved_payroll_adjustments.csv", response.headers["content-disposition"])
        lines = response.text.strip().split("\r\n" if "\r\n" in response.text else "\n")
        self.assertGreaterEqual(len(lines), 2)
        self.assertIn("case_id,employee_id,employee_name", lines[0])


if __name__ == "__main__":
    unittest.main()
