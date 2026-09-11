"""Tests for the Standalone Payroll Automation Suite backend.

Verifies the FastAPI endpoints, deterministic rule evaluation, supervisor overrides,
cryptographic audit logging, and Policy Copilot reasoning.
"""

from __future__ import annotations

import io
import unittest
from fastapi.testclient import TestClient

from apps.payroll_automation.backend.main import app
import apps.payroll_automation.backend.main as backend_module


class TestStandalonePayrollApp(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        if len(backend_module._CURRENT_CASES) < 5:
            backend_module.initialize_app_data(force=True)

    def test_status_endpoint(self) -> None:
        """Ensure the system status endpoint reports healthy metrics."""
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ONLINE")
        self.assertEqual(data["port"], 8500)
        self.assertIn("summary", data)
        self.assertGreaterEqual(data["total_active_cases"], 5)

    def test_cases_listing_and_filtering(self) -> None:
        """Test retrieving claims and filtering by status."""
        response = self.client.get("/api/cases?status=ALL")
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertIn("records", res_data)
        cases = res_data["records"]
        self.assertIsInstance(cases, list)
        self.assertGreaterEqual(len(cases), 5)

        # Filter by AUTO_APPROVED
        res_approved = self.client.get("/api/cases?status=AUTO_APPROVED")
        self.assertEqual(res_approved.status_code, 200)
        approved_cases = res_approved.json()["records"]
        self.assertTrue(all("APPROVED" in c["status"] for c in approved_cases))

    def test_single_case_evaluation_regular(self) -> None:
        """Test deterministic evaluation for a clean regular staff claim."""
        claim = {
            "employee_id": "EMP-9499",
            "employee_name": "Test Employee Regular",
            "contract_type": "regular",
            "base_salary": 320000,
            "claimed_commute": 15000,
            "telework_days": 10,
            "claimed_housing": 20000,
            "custom_deduction": 0,
            "deduction_reason": ""
        }
        response = self.client.post("/api/evaluate_case", json=claim)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["decision"], "AUTO_APPROVED")
        self.assertEqual(data["result"]["calculated_details"]["net_adjustment"], -13060)
        self.assertEqual(data["result"]["calculated_details"]["approved_commute"], 15000)
        self.assertEqual(data["result"]["calculated_details"]["approved_telework"], 2500)

    def test_single_case_evaluation_outsourcing_housing_violation(self) -> None:
        """Test deterministic rejection of housing subsidy for outsourcing contracts."""
        claim = {
            "employee_id": "EMP-9500",
            "employee_name": "Test Outsourcing Contractor",
            "contract_type": "outsourcing",
            "base_salary": 400000,
            "claimed_commute": 8000,
            "telework_days": 5,
            "claimed_housing": 25000,  # Disallowed under Art. 4
            "custom_deduction": 0,
            "deduction_reason": ""
        }
        response = self.client.post("/api/evaluate_case", json=claim)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertTrue("FLAG_REVIEW" in data["decision"] or "REJECTED" in data["decision"])
        self.assertIn("housing", data["result"]["decision_notes"].lower())

    def test_batch_evaluation(self) -> None:
        """Test batch evaluation of multiple claims."""
        batch = [
            {
                "employee_id": "EMP-9501",
                "employee_name": "Batch Worker 1",
                "contract_type": "regular",
                "base_salary": 300000,
                "claimed_commute": 12000,
                "telework_days": 8,
                "claimed_housing": 15000,
                "custom_deduction": 0,
                "deduction_reason": ""
            },
            {
                "employee_id": "EMP-9502",
                "employee_name": "Batch Worker 2",
                "contract_type": "regular",
                "base_salary": 300000,
                "claimed_commute": 160000,  # Cap breach > 150k
                "telework_days": 4,
                "claimed_housing": 15000,
                "custom_deduction": 0,
                "deduction_reason": ""
            }
        ]
        response = self.client.post("/api/evaluate_batch", json=batch)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["evaluated_count"], 2)
        records = data["results"]
        self.assertEqual(records[0]["status"], "AUTO_APPROVED")
        self.assertEqual(records[1]["status"], "FLAGGED_FOR_REVIEW")

    def test_csv_upload(self) -> None:
        """Test uploading a CSV file and automated ingestion."""
        csv_data = (
            "employee_id,employee_name,contract_type,base_salary,claimed_commute,telework_days,claimed_housing,custom_deduction,deduction_reason\n"
            "EMP-9503,Upload Tester,contract,280000,10000,5,0,0,\n"
        )
        file_bytes = io.BytesIO(csv_data.encode("utf-8"))
        files = {"file": ("test_claims.csv", file_bytes, "text/csv")}
        response = self.client.post("/api/upload_csv", files=files)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["rows_ingested"], 1)
        self.assertEqual(data["evaluated_records"][0]["input_data"]["employee_id"], "EMP-9503")

    def test_csv_upload_with_case_id_no_collision(self) -> None:
        """Ensure case_id and employee_id do not collide during batch CSV ingestion."""
        csv_data = (
            "case_id,employee_id,employee_name,contract_type,base_salary,claimed_commute,telework_days,claimed_housing,custom_deduction,deduction_reason\n"
            "CASE-UNIQUE-99,EMP-REAL-01,Yamada Taro,regular,340000,12000,4,15000,0,\n"
        )
        file_bytes = io.BytesIO(csv_data.encode("utf-8"))
        files = {"file": ("test_claims_both_ids.csv", file_bytes, "text/csv")}
        response = self.client.post("/api/upload_csv", files=files)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["rows_ingested"], 1)
        record = data["evaluated_records"][0]
        self.assertEqual(record["case_id"], "CASE-UNIQUE-99")
        self.assertEqual(record["input_data"]["employee_id"], "EMP-REAL-01")
        self.assertEqual(record["input_data"]["employee_name"], "Yamada Taro")

    def test_csv_upload_japanese_headers(self) -> None:
        """Ensure Japanese canonical CSV headers parse and normalize accurately."""
        csv_data = (
            "申請番号,社員番号,氏名,契約形態,基本給,通勤手当,在宅日数,住宅手当,任意控除,控除事由\n"
            "JP-APP-001,E-JP-101,田中 一郎,正社員,350000,10000,8,20000,0,\n"
        )
        file_bytes = io.BytesIO(csv_data.encode("utf-8"))
        files = {"file": ("test_japanese_claims.csv", file_bytes, "text/csv")}
        response = self.client.post("/api/upload_csv", files=files)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["rows_ingested"], 1)
        record = data["evaluated_records"][0]
        self.assertEqual(record["case_id"], "JP-APP-001")
        self.assertEqual(record["input_data"]["employee_id"], "E-JP-101")
        self.assertEqual(record["input_data"]["employee_name"], "田中 一郎")
        self.assertEqual(record["input_data"]["contract_type"], "regular")

    def test_supervisor_override_and_audit_ledger(self) -> None:
        """Test human-in-the-loop supervisor override and verify audit trail."""
        res_cases = self.client.get("/api/cases?status=ALL")
        cases = res_cases.json()["records"]
        self.assertGreater(len(cases), 0)
        target_case = cases[0]
        target_case_id = target_case["case_id"]

        override_payload = {
            "case_id": target_case_id,
            "decision": "APPROVED_BY_SUPERVISOR",
            "supervisor_memo": "Verified exceptional executive permit under Article 21 §2.",
            "supervisor_id": "SUPV-UNIT-TEST"
        }
        res_override = self.client.post("/api/supervisor_override", json=override_payload)
        self.assertEqual(res_override.status_code, 200)
        override_data = res_override.json()
        self.assertEqual(override_data["status"], "success")
        self.assertEqual(override_data["updated_record"]["status"], "APPROVED_BY_SUPERVISOR")
        self.assertIn("supervisor_override", override_data["updated_record"])

        # Verify audit ledger
        res_ledger = self.client.get("/api/audit_ledger")
        self.assertEqual(res_ledger.status_code, 200)
        ledger_data = res_ledger.json()
        self.assertEqual(ledger_data["tamper_evident_algorithm"], "SHA-256")
        self.assertIsInstance(ledger_data["entries"], list)

    def test_staging_hub_and_erp_export(self) -> None:
        """Test ERP staging hub and payload export."""
        res_staging = self.client.get("/api/hris/staged")
        self.assertEqual(res_staging.status_code, 200)
        staging_data = res_staging.json()
        self.assertIn("records", staging_data)
        self.assertIn("staged_count", staging_data)

        res_commit = self.client.post("/api/hris/commit")
        self.assertEqual(res_commit.status_code, 200)
        self.assertEqual(res_commit.json()["status"], "committed")

        res_export = self.client.get("/api/export_erp")
        self.assertEqual(res_export.status_code, 200)
        self.assertIn("text/csv", res_export.headers.get("content-type", ""))
        self.assertIn("case_id,employee_id", res_export.text)

    def test_copilot_endpoints(self) -> None:
        """Test AI Policy Copilot reasoning and Q&A."""
        res_query = self.client.post("/api/copilot/query", json={"query": "What is the commuting allowance cap?"})
        self.assertEqual(res_query.status_code, 200)
        ans = res_query.json()
        self.assertIn("matches", ans)
        self.assertTrue(any(m.get("statutory_cap_jpy") == 150000 for m in ans["matches"]))

        res_cases = self.client.get("/api/cases?status=ALL")
        first_case_id = res_cases.json()["records"][0]["case_id"]
        res_explain = self.client.post("/api/copilot/explain", json={"case_id": first_case_id})
        self.assertEqual(res_explain.status_code, 200)
        explanation = res_explain.json()
        self.assertIn("case_id", explanation)
        self.assertIn("copilot_recommendation", explanation)
        self.assertIn("findings", explanation)

    def test_copilot_audit_and_docx_features(self) -> None:
        """Test batch payment conflict auditing and docx inspection."""
        res_audit = self.client.post("/api/copilot/audit_conflicts")
        self.assertEqual(res_audit.status_code, 200)
        audit = res_audit.json()
        self.assertIn("total_cases_audited", audit)
        self.assertIn("financial_exposure", audit)
        self.assertIn("conflicting_cases", audit)
        self.assertEqual(audit["policy_document"], "gyomu_itaku_kyuuyo_kitei.docx")

        res_doc = self.client.get("/api/copilot/policy_doc")
        self.assertEqual(res_doc.status_code, 200)
        doc = res_doc.json()
        self.assertEqual(doc["filename"], "gyomu_itaku_kyuuyo_kitei.docx")
        self.assertGreaterEqual(len(doc["articles"]), 5)

        res_docx_query = self.client.post("/api/copilot/query", json={"query": "Check problems and conflicts in payments seeing the docx"})
        self.assertEqual(res_docx_query.status_code, 200)
        data = res_docx_query.json()
        self.assertIn("audit_summary", data)
        self.assertIn("response_markdown", data)

    def test_copilot_zero_base_salary_resilience(self) -> None:
        """Verify copilot does not raise ZeroDivisionError when base salary is 0."""
        from apps.payroll_automation.backend.copilot import PolicyCopilot
        test_copilot = PolicyCopilot()
        zero_salary_case = {
            "case_id": "TEST-ZERO-SAL",
            "status": "FLAGGED_FOR_REVIEW",
            "input_data": {
                "employee_id": "EMP-INTERN-01",
                "contract_type": "regular",
                "base_salary": 0,
                "claimed_commute": 5000,
                "claimed_housing": 0,
                "custom_deduction": 2000,
                "deduction_reason": "Equipment fee"
            },
            "calculated_details": {},
            "decision_notes": "Custom deduction check"
        }
        explanation = test_copilot.explain_case(zero_salary_case)
        self.assertIn("findings", explanation)
        self.assertEqual(explanation["status"], "FLAGGED_FOR_REVIEW")

    def test_erp_preflight_and_preview_endpoints(self) -> None:
        """Test Multi-ERP preflight validation and payload preview across connectors."""
        res_preflight = self.client.post("/api/erp/preflight")
        self.assertEqual(res_preflight.status_code, 200)
        preflight_data = res_preflight.json()
        self.assertEqual(preflight_data["preflight_status"], "READY_FOR_SYNC")
        self.assertGreaterEqual(preflight_data["active_roster_count"], 120)

        # SAP preview
        res_sap = self.client.get("/api/erp/preview/sap")
        self.assertEqual(res_sap.status_code, 200)
        sap_data = res_sap.json()
        self.assertEqual(sap_data["target_system"], "SAP S/4HANA Cloud (OData v4)")
        self.assertIn("d", sap_data["preview"])

        # Workday preview
        res_wd = self.client.get("/api/erp/preview/workday")
        self.assertEqual(res_wd.status_code, 200)
        wd_data = res_wd.json()
        self.assertEqual(wd_data["target_system"], "Workday HCM (Inbound EIB)")

        # Freee preview
        res_freee = self.client.get("/api/erp/preview/freee")
        self.assertEqual(res_freee.status_code, 200)
        freee_data = res_freee.json()
        self.assertEqual(freee_data["target_system"], "Freee HR Cloud (Japan CSV)")
        self.assertIn("csv_content", freee_data)

    def test_erp_commit_and_export_endpoints(self) -> None:
        """Test ERP batch commit with idempotency token generation and multi-format download."""
        res_commit = self.client.post("/api/erp/commit", json={"connector": "sap"})
        self.assertEqual(res_commit.status_code, 200)
        commit_data = res_commit.json()
        self.assertEqual(commit_data["status"], "COMMITTED")
        self.assertTrue(commit_data["idempotency_token"].startswith("IDEM-"))
        self.assertEqual(commit_data["connector"], "sap")

        # Export SAP JSON
        res_exp_sap = self.client.get("/api/erp/export/sap")
        self.assertEqual(res_exp_sap.status_code, 200)
        self.assertIn("application/json", res_exp_sap.headers.get("content-type", ""))

        # Export Freee CSV
        res_exp_freee = self.client.get("/api/erp/export/freee")
        self.assertEqual(res_exp_freee.status_code, 200)
        self.assertIn("text/csv", res_exp_freee.headers.get("content-type", ""))

    def test_policy_governance_studio_endpoints(self) -> None:
        """Test Policy Governance Studio parameter configuration and cohort simulation."""
        res_cfg = self.client.get("/api/policy/config")
        self.assertEqual(res_cfg.status_code, 200)
        cfg = res_cfg.json()
        self.assertEqual(cfg["policy_version"], "2026.04-v1.2")
        self.assertEqual(cfg["commute_tax_free_cap"], 150000)

        sim_payload = {
            "commute_tax_free_cap": 200000,
            "telework_daily_rate": 500,
            "telework_monthly_cap": 10000,
            "custom_deduction_rate_limit": 0.25,
            "allow_contract_housing": True,
            "allow_outsourcing_housing": False
        }
        res_sim = self.client.post("/api/policy/simulate", json=sim_payload)
        self.assertEqual(res_sim.status_code, 200)
        sim_data = res_sim.json()
        self.assertIn("simulated_auto_approval_rate", sim_data)
        self.assertIn("net_monthly_payroll_delta", sim_data)
        self.assertIn("affected_claims_count", sim_data)
        self.assertGreaterEqual(sim_data["total_claims_simulated"], 1)

    def test_copilot_bilingual_conversation_and_japanese_switch(self) -> None:
        """Verify Copilot switches conversation language to natural Japanese when lang='ja'."""
        # 1. Greeting in Japanese
        res_greet_ja = self.client.post("/api/copilot/query", json={"query": "こんにちは", "lang": "ja"})
        self.assertEqual(res_greet_ja.status_code, 200)
        data_ja = res_greet_ja.json()
        self.assertEqual(data_ja["lang"], "ja")
        self.assertIn("AIコパイロット（日本語対話モード）", data_ja["response_markdown"])
        self.assertIn("gyomu_itaku_kyuuyo_kitei.docx", data_ja["response_markdown"])

        # 2. English query asked while lang='ja' switches talking language to Japanese
        res_en_in_ja = self.client.post("/api/copilot/query", json={"query": "What are the rules for commute allowance?", "lang": "ja"})
        self.assertEqual(res_en_in_ja.status_code, 200)
        data_commute_ja = res_en_in_ja.json()
        self.assertEqual(data_commute_ja["lang"], "ja")
        self.assertIn("第3条（通勤交通費）", data_commute_ja["response_markdown"])
        self.assertIn("150,000円", data_commute_ja["response_markdown"])

        # 3. Japanese conflict audit endpoint
        res_audit_ja = self.client.post("/api/copilot/audit_conflicts?lang=ja")
        self.assertEqual(res_audit_ja.status_code, 200)
        audit_ja = res_audit_ja.json()
        self.assertEqual(audit_ja["lang"], "ja")
        self.assertIn("不支給対象・住宅手当違反額（第4条）", audit_ja["financial_exposure"]["exposure_headline_ja"])

        # 4. Supervisor override draft in Japanese
        res_cases = self.client.get("/api/cases?status=ALL")
        first_case_id = res_cases.json()["records"][0]["case_id"]
        res_memo_ja = self.client.post(f"/api/copilot/draft_override?case_id={first_case_id}&supervisor_name=給与審査責任者&lang=ja")
        self.assertEqual(res_memo_ja.status_code, 200)
        memo_data = res_memo_ja.json()
        self.assertEqual(memo_data["lang"], "ja")
        self.assertIn("【特別承認決裁書（業務委託・給与控除等取扱い規程 第14条）】", memo_data["draft_memo"])

        # 5. Verify translate_decision_notes helper
        from apps.payroll_automation.backend.copilot import PolicyCopilot
        copilot_inst = PolicyCopilot()
        raw_note = "REJECTED: Housing subsidy not permissible for outsourcing or part-time staff per article 4"
        translated = copilot_inst.translate_decision_notes(raw_note, lang="ja")
        self.assertIn("規程第4条に基づき業務委託・パートへの住宅手当は支給不可", translated)


if __name__ == "__main__":
    unittest.main()

