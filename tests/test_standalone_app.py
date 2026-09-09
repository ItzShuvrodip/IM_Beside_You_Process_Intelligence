"""Tests for the Standalone Payroll Automation Suite backend.

Verifies the FastAPI endpoints, deterministic rule evaluation, supervisor overrides,
cryptographic audit logging, and Policy Copilot reasoning.
"""

from __future__ import annotations

import io
from fastapi.testclient import TestClient

from apps.payroll_automation.backend.main import app


client = TestClient(app)


def test_status_endpoint() -> None:
    """Ensure the system status endpoint reports healthy metrics."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert data["port"] == 8500
    assert "summary" in data
    assert data["total_active_cases"] >= 5


def test_cases_listing_and_filtering() -> None:
    """Test retrieving claims and filtering by status."""
    response = client.get("/api/cases?status=ALL")
    assert response.status_code == 200
    res_data = response.json()
    assert "records" in res_data
    cases = res_data["records"]
    assert isinstance(cases, list)
    assert len(cases) >= 5

    # Filter by AUTO_APPROVED
    res_approved = client.get("/api/cases?status=AUTO_APPROVED")
    assert res_approved.status_code == 200
    approved_cases = res_approved.json()["records"]
    assert all("APPROVED" in c["status"] for c in approved_cases)


def test_single_case_evaluation_regular() -> None:
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
    response = client.post("/api/evaluate_case", json=claim)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["decision"] == "AUTO_APPROVED"
    assert data["result"]["calculated_details"]["net_adjustment"] == -13060
    assert data["result"]["calculated_details"]["approved_commute"] == 15000
    assert data["result"]["calculated_details"]["approved_telework"] == 2500  # 10 * 250


def test_single_case_evaluation_outsourcing_housing_violation() -> None:
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
    response = client.post("/api/evaluate_case", json=claim)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "FLAG_REVIEW" in data["decision"] or "REJECTED" in data["decision"]
    assert "housing" in data["result"]["decision_notes"].lower()


def test_batch_evaluation() -> None:
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
    response = client.post("/api/evaluate_batch", json=batch)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["evaluated_count"] == 2
    records = data["results"]
    assert records[0]["status"] == "AUTO_APPROVED"
    assert records[1]["status"] == "FLAGGED_FOR_REVIEW"


def test_csv_upload() -> None:
    """Test uploading a CSV file and automated ingestion."""
    csv_data = (
        "employee_id,employee_name,contract_type,base_salary,claimed_commute,telework_days,claimed_housing,custom_deduction,deduction_reason\n"
        "EMP-9503,Upload Tester,contract,280000,10000,5,0,0,\n"
    )
    file_bytes = io.BytesIO(csv_data.encode("utf-8"))
    files = {"file": ("test_claims.csv", file_bytes, "text/csv")}
    response = client.post("/api/upload_csv", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["rows_ingested"] == 1
    assert data["evaluated_records"][0]["input_data"]["employee_id"] == "EMP-9503"


def test_supervisor_override_and_audit_ledger() -> None:
    """Test human-in-the-loop supervisor override and verify audit trail."""
    # First, retrieve all cases
    res_cases = client.get("/api/cases?status=ALL")
    cases = res_cases.json()["records"]
    assert len(cases) > 0
    target_case = cases[0]
    target_case_id = target_case["case_id"]

    override_payload = {
        "case_id": target_case_id,
        "decision": "APPROVED_BY_SUPERVISOR",
        "supervisor_memo": "Verified exceptional executive permit under Article 21 §2.",
        "supervisor_id": "SUPV-UNIT-TEST"
    }
    res_override = client.post("/api/supervisor_override", json=override_payload)
    assert res_override.status_code == 200
    override_data = res_override.json()
    assert override_data["status"] == "success"
    assert override_data["updated_record"]["status"] == "APPROVED_BY_SUPERVISOR"
    assert "supervisor_override" in override_data["updated_record"]

    # Verify audit ledger
    res_ledger = client.get("/api/audit_ledger")
    assert res_ledger.status_code == 200
    ledger_data = res_ledger.json()
    assert ledger_data["tamper_evident_algorithm"] == "SHA-256"
    assert isinstance(ledger_data["entries"], list)


def test_staging_hub_and_erp_export() -> None:
    """Test ERP staging hub and payload export."""
    res_staging = client.get("/api/hris/staged")
    assert res_staging.status_code == 200
    staging_data = res_staging.json()
    assert "records" in staging_data
    assert "staged_count" in staging_data

    res_commit = client.post("/api/hris/commit")
    assert res_commit.status_code == 200
    assert res_commit.json()["status"] == "committed"

    res_export = client.get("/api/export_erp")
    assert res_export.status_code == 200
    assert "text/csv" in res_export.headers.get("content-type", "")
    assert "case_id,employee_id" in res_export.text


def test_copilot_endpoints() -> None:
    """Test AI Policy Copilot reasoning and Q&A."""
    # Test query
    res_query = client.post("/api/copilot/query", json={"query": "What is the commuting allowance cap?"})
    assert res_query.status_code == 200
    ans = res_query.json()
    assert "matches" in ans
    assert any(m.get("statutory_cap_jpy") == 150000 for m in ans["matches"])

    # Test explanation for a specific case
    res_cases = client.get("/api/cases?status=ALL")
    first_case_id = res_cases.json()["records"][0]["case_id"]
    res_explain = client.post("/api/copilot/explain", json={"case_id": first_case_id})
    assert res_explain.status_code == 200
    explanation = res_explain.json()
    assert "case_id" in explanation
    assert "copilot_recommendation" in explanation
    assert "findings" in explanation


def test_erp_preflight_and_preview_endpoints() -> None:
    """Test Multi-ERP preflight validation and payload preview across connectors."""
    # Pre-flight validation
    res_preflight = client.post("/api/erp/preflight")
    assert res_preflight.status_code == 200
    preflight_data = res_preflight.json()
    assert preflight_data["preflight_status"] == "READY_FOR_SYNC"
    assert preflight_data["active_roster_count"] == 120

    # SAP preview
    res_sap = client.get("/api/erp/preview/sap")
    assert res_sap.status_code == 200
    sap_data = res_sap.json()
    assert sap_data["target_system"] == "SAP S/4HANA Cloud (OData v4)"
    assert "d" in sap_data["preview"]

    # Workday preview
    res_wd = client.get("/api/erp/preview/workday")
    assert res_wd.status_code == 200
    wd_data = res_wd.json()
    assert wd_data["target_system"] == "Workday HCM (Inbound EIB)"
    assert "Payroll_Input_Data" in wd_data["preview"] or "Header" in str(wd_data["preview"])

    # Freee preview
    res_freee = client.get("/api/erp/preview/freee")
    assert res_freee.status_code == 200
    freee_data = res_freee.json()
    assert freee_data["target_system"] == "Freee HR Cloud (Japan CSV)"
    assert "csv_content" in freee_data


def test_erp_commit_and_export_endpoints() -> None:
    """Test ERP batch commit with idempotency token generation and multi-format download."""
    # Commit staged records with idempotency token
    res_commit = client.post("/api/erp/commit", json={"connector": "sap"})
    assert res_commit.status_code == 200
    commit_data = res_commit.json()
    assert commit_data["status"] == "COMMITTED"
    assert commit_data["idempotency_token"].startswith("IDEM-")
    assert commit_data["connector"] == "sap"

    # Export SAP JSON
    res_exp_sap = client.get("/api/erp/export/sap")
    assert res_exp_sap.status_code == 200
    assert "application/json" in res_exp_sap.headers.get("content-type", "")

    # Export Freee CSV
    res_exp_freee = client.get("/api/erp/export/freee")
    assert res_exp_freee.status_code == 200
    assert "text/csv" in res_exp_freee.headers.get("content-type", "")


def test_policy_governance_studio_endpoints() -> None:
    """Test Policy Governance Studio parameter configuration and cohort simulation."""
    # Read active config
    res_cfg = client.get("/api/policy/config")
    assert res_cfg.status_code == 200
    cfg = res_cfg.json()
    assert cfg["policy_version"] == "2026.04-v1.2"
    assert cfg["commute_tax_free_cap"] == 150000

    # Simulate scenario: higher telework rate, housing allowed for contract workers
    sim_payload = {
        "commute_tax_free_cap": 200000,
        "telework_daily_rate": 500,
        "telework_monthly_cap": 10000,
        "custom_deduction_rate_limit": 0.25,
        "allow_contract_housing": True,
        "allow_outsourcing_housing": False
    }
    res_sim = client.post("/api/policy/simulate", json=sim_payload)
    assert res_sim.status_code == 200
    sim_data = res_sim.json()
    assert "simulated_auto_approval_rate" in sim_data
    assert "net_monthly_payroll_delta" in sim_data
    assert "affected_claims_count" in sim_data
    assert sim_data["total_claims_simulated"] >= 1

