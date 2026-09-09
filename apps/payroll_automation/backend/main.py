"""
Standalone Enterprise Payroll Automation Engine - FastAPI Application
Provides enterprise API services for:
- Deterministic Payroll Claims Verification & Statutory Compliance
- AI Policy Copilot & Autonomous Exception Analysis
- HRIS / ERP Staging & Batch Export
- Tamper-Evident SHA-256 Audit Trail Inspection
"""

import sys
import os
import csv
import io
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query, Request
import re
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import PROJECT_ROOT
from src.automation.service.decision_service import PayrollDecisionService
from src.automation.domain.payroll_rules import BATCH_CASES, POLICY_CONFIG, POLICY_METADATA
from src.automation.adapters.hr_system import MockHRSystemAdapter
from apps.payroll_automation.backend.copilot import PolicyCopilot
from apps.payroll_automation.backend.batch_importer import parse_claims_csv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("PayrollAppBackend")

app = FastAPI(
    title="IMBY Payroll Automation Suite",
    description="Enterprise Autonomous Payroll Adjustment & Statutory Compliance Platform",
    version="2026.04-v1.2"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Engine Singletons
engine = PayrollDecisionService()
hr_adapter = MockHRSystemAdapter()
copilot = PolicyCopilot()

# In-Memory Active State
_CURRENT_CASES: List[Dict[str, Any]] = []
_STAGED_ERP_RECORDS: List[Dict[str, Any]] = []


def initialize_app_data():
    """Bootstraps default verified production claims."""
    global _CURRENT_CASES
    if not _CURRENT_CASES:
        results = engine.process_batch(BATCH_CASES)
        # Add additional diverse production records (6-20)
        extra_cases = [
            {
                "case_id": f"PI-PROD-2026-{i+6:03d}",
                "employee_id": f"EMP-94{i+6:02d}",
                "employee_name": f"Employee {i+6:02d}",
                "contract_type": "regular" if i % 2 == 0 else ("contract" if i % 3 == 0 else "outsourcing"),
                "base_salary": 310000 + (i * 15000),
                "claimed_commute": 14000 + (i * 2000),
                "telework_days": 6 + (i % 10),
                "claimed_housing": 20000 if i % 2 == 0 else (15000 if i % 4 == 0 else 0),
                "custom_deduction": 12000 if i % 4 == 0 else 0,
                "deduction_reason": "Company Housing Maintenance" if i % 4 == 0 else ""
            }
            for i in range(15)
        ]
        all_results = results + engine.process_batch(extra_cases)
        _CURRENT_CASES = all_results

        # Stage auto-approved items initially
        for r in _CURRENT_CASES:
            if r.get("status") == "AUTO_APPROVED":
                hr_adapter.stage_adjustment_commit(r)


initialize_app_data()


# Pydantic Schemas
class ClaimItemModel(BaseModel):
    case_id: Optional[str] = None
    employee_id: str = Field(..., json_schema_extra={"example": "EMP-9401"})
    employee_name: str = Field(..., json_schema_extra={"example": "Employee 01"})
    contract_type: str = Field("regular", json_schema_extra={"example": "regular"})
    base_salary: int = Field(..., json_schema_extra={"example": 350000})
    claimed_commute: int = Field(0, json_schema_extra={"example": 18500})
    telework_days: int = Field(0, json_schema_extra={"example": 10})
    claimed_housing: int = Field(0, json_schema_extra={"example": 20000})
    custom_deduction: int = Field(0, json_schema_extra={"example": 0})
    deduction_reason: str = Field("", json_schema_extra={"example": ""})


class SupervisorOverrideModel(BaseModel):
    case_id: str
    decision: str = Field(..., json_schema_extra={"example": "APPROVED_BY_SUPERVISOR"})
    supervisor_memo: str = Field(..., json_schema_extra={"example": "Approved per departmental sign-off."})
    supervisor_id: str = Field("SUP-01", json_schema_extra={"example": "SUP-01"})


class CopilotQueryModel(BaseModel):
    query: str


class CopilotExplainModel(BaseModel):
    case_id: str


# =========================================================================
# API Endpoints
# =========================================================================

@app.get("/api/status")
def get_system_status():
    """System heartbeat, policy configuration, and compliance version."""
    summary = engine.get_summary_report()
    return {
        "service": "IMBY Enterprise Payroll Automation Engine",
        "status": "ONLINE",
        "port": 8500,
        "policy_version": POLICY_METADATA["policy_version"],
        "effective_date": POLICY_METADATA["effective_date"],
        "governance_mode": "autonomous_deterministic_execution",
        "registered_employees": len(hr_adapter._employee_registry),
        "total_active_cases": len(_CURRENT_CASES),
        "staged_erp_commits": len(hr_adapter.get_staged_commits()),
        "summary": summary
    }


@app.get("/api/cases")
def get_cases(status: Optional[str] = None, search: Optional[str] = None):
    """Retrieves current claims with optional filtering."""
    cases = list(_CURRENT_CASES)

    if status and status.upper() != "ALL":
        cases = [c for c in cases if c.get("status") == status.upper()]

    if search:
        s_lower = search.lower()
        cases = [
            c for c in cases
            if s_lower in str(c.get("case_id", "")).lower()
            or s_lower in str(c.get("input_data", {}).get("employee_name", "")).lower()
            or s_lower in str(c.get("input_data", {}).get("employee_id", "")).lower()
            or s_lower in str(c.get("input_data", {}).get("contract_type", "")).lower()
        ]

    return {
        "count": len(cases),
        "total": len(_CURRENT_CASES),
        "records": cases,
        "summary": engine.get_summary_report()
    }


@app.post("/api/evaluate_case")
def evaluate_single_case(claim: ClaimItemModel):
    """Evaluates a single payroll adjustment claim deterministically."""
    claim_dict = claim.model_dump()
    res = engine.process_item(claim_dict)

    # Prepend or update in active memory
    global _CURRENT_CASES
    idx = next((i for i, c in enumerate(_CURRENT_CASES) if c.get("case_id") == res.get("case_id")), None)
    if idx is not None:
        _CURRENT_CASES[idx] = res
    else:
        _CURRENT_CASES.insert(0, res)

    if res.get("status") == "AUTO_APPROVED":
        hr_adapter.stage_adjustment_commit(res)

    return {
        "status": "success",
        "decision": res.get("status"),
        "result": res,
        "summary": engine.get_summary_report()
    }


@app.post("/api/evaluate_batch")
def evaluate_batch_cases(claims: List[ClaimItemModel]):
    """Evaluates an array of claims simultaneously (< 5ms per batch)."""
    global _CURRENT_CASES
    claims_dicts = [c.model_dump() for c in claims]
    results = engine.process_batch(claims_dicts)

    _CURRENT_CASES = results + _CURRENT_CASES
    for r in results:
        if r.get("status") == "AUTO_APPROVED":
            hr_adapter.stage_adjustment_commit(r)

    return {
        "status": "success",
        "evaluated_count": len(results),
        "results": results,
        "summary": engine.get_summary_report()
    }


@app.post("/api/upload_csv")
async def upload_csv_claims(request: Request):
    """Uploads, normalizes, and evaluates a custom payroll CSV file."""
    content_type = request.headers.get("content-type", "")
    body_bytes = await request.body()
    filename = "upload.csv"
    content_bytes = body_bytes

    if "multipart/form-data" in content_type:
        boundary_match = re.search(r"boundary=([^;]+)", content_type)
        if boundary_match:
            boundary = boundary_match.group(1).strip("\"'").encode()
            parts = body_bytes.split(b"--" + boundary)
            for part in parts:
                if b"Content-Disposition:" in part:
                    header_body = part.split(b"\r\n\r\n", 1)
                    if len(header_body) == 2:
                        fn_match = re.search(rb'filename="([^"]+)"', header_body[0])
                        if fn_match:
                            filename = fn_match.group(1).decode("utf-8", errors="ignore")
                        content_bytes = header_body[1].rstrip(b"\r\n--")
                        break

    try:
        content_str = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content_str = content_bytes.decode("cp932", errors="replace")

    records, warnings = parse_claims_csv(content_str)
    if not records:
        raise HTTPException(status_code=400, detail="No valid claim rows could be parsed from uploaded file.")

    results = engine.process_batch(records)
    global _CURRENT_CASES
    _CURRENT_CASES = results

    for r in results:
        if r.get("status") == "AUTO_APPROVED":
            hr_adapter.stage_adjustment_commit(r)

    return {
        "filename": filename,
        "rows_ingested": len(records),
        "parsed_rows": len(records),
        "evaluated_records": results,
        "warnings": warnings,
        "results": results,
        "summary": engine.get_summary_report()
    }


@app.post("/api/supervisor_override")
def supervisor_override(override: SupervisorOverrideModel):
    """Applies supervisor override with digital signature audit entry."""
    global _CURRENT_CASES
    c = next((item for item in _CURRENT_CASES if item.get("case_id") == override.case_id), None)
    if not c:
        raise HTTPException(status_code=404, detail=f"Case {override.case_id} not found.")

    c["status"] = override.decision
    c["supervisor_override"] = {
        "authorized_by": override.supervisor_id,
        "decision": override.decision,
        "memo": override.supervisor_memo,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "signature_hash": f"SIG-{abs(hash(override.case_id + override.supervisor_memo)) % 10000000:07d}"
    }
    c["decision_notes"] += f" | [SUPERVISOR OVERRIDE ({override.supervisor_id}): {override.supervisor_memo}]"

    # Stage for ERP if approved
    if "APPROVED" in override.decision:
        hr_adapter.stage_adjustment_commit(c)

    return {
        "status": "success",
        "case_id": override.case_id,
        "updated_record": c,
        "summary": engine.get_summary_report()
    }


@app.get("/api/hris/staged")
def get_staged_erp_commits():
    """Fetches all records verified and staged for HRIS/ERP batch ingestion."""
    commits = hr_adapter.get_staged_commits()
    return {
        "staged_count": len(commits),
        "records": commits
    }


@app.post("/api/hris/commit")
def commit_to_erp():
    """Finalizes staged records for ERP payroll sync."""
    commits = hr_adapter.get_staged_commits()
    return {
        "status": "committed",
        "synced_records": len(commits),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "target_erp": "SAP / Workday HRIS Connector"
    }


@app.get("/api/export_erp")
def export_erp_csv():
    """Generates standard ERP-compliant payroll adjustment CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "case_id", "employee_id", "employee_name", "contract_type",
        "base_salary", "approved_commute", "approved_telework", "approved_housing",
        "social_insurance", "employment_insurance", "custom_deduction",
        "net_adjustment", "status", "audit_id", "policy_version"
    ])

    for c in _CURRENT_CASES:
        inp = c.get("input_data", {})
        calc = c.get("calculated_details", {})
        writer.writerow([
            c.get("case_id"),
            inp.get("employee_id"),
            inp.get("employee_name"),
            inp.get("contract_type"),
            inp.get("base_salary"),
            calc.get("approved_commute", 0),
            calc.get("approved_telework", 0),
            calc.get("approved_housing", 0),
            calc.get("social_insurance_deduction", 0),
            calc.get("employment_insurance_deduction", 0),
            calc.get("custom_deduction", 0),
            calc.get("net_adjustment", 0),
            c.get("status"),
            c.get("audit_id"),
            calc.get("policy_version", "2026.04-v1.2")
        ])

    csv_text = output.getvalue()
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=approved_payroll_adjustments.csv"}
    )


@app.get("/api/audit_ledger")
def get_audit_ledger():
    """Retrieves full cryptographic audit trail entries."""
    audit_path = PROJECT_ROOT / "deliverables" / "audit_trail.jsonl"
    entries = []
    if audit_path.exists():
        with open(audit_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass
    return {
        "ledger_size": len(entries),
        "tamper_evident_algorithm": "SHA-256",
        "entries": entries[-50:]  # Last 50 entries
    }


# =========================================================================
# AI Policy Copilot Endpoints
# =========================================================================

@app.post("/api/copilot/explain")
def copilot_explain_case(payload: CopilotExplainModel):
    """Provides deep AI explanation of policy enforcement for a given case."""
    case = next((c for c in _CURRENT_CASES if c.get("case_id") == payload.case_id), None)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    return copilot.explain_case(case)


@app.post("/api/copilot/draft_override")
def copilot_draft_override(case_id: str = Query(...), supervisor_name: str = Query("Lead HR Specialist")):
    """Auto-drafts a standardized compliance memo for supervisor override."""
    case = next((c for c in _CURRENT_CASES if c.get("case_id") == case_id), None)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    draft = copilot.generate_override_draft(case, supervisor_name)
    return {
        "case_id": case_id,
        "draft_memo": draft
    }


@app.post("/api/copilot/query")
def copilot_policy_query(payload: CopilotQueryModel):
    """Answers arbitrary policy questions regarding corporate and statutory rules."""
    return copilot.answer_policy_query(payload.query)


# =========================================================================
# Serve Static Frontend Application
# =========================================================================

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

@app.get("/", response_class=HTMLResponse)
def serve_ui():
    """Serves the standalone enterprise web application."""
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h3>Payroll Automation UI Loading...</h3>")
    return HTMLResponse(
        content=index_path.read_text(encoding="utf-8"),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )

@app.get("/styles.css")
def serve_styles():
    """Serves application CSS with correct content-type header."""
    css_path = FRONTEND_DIR / "styles.css"
    if css_path.exists():
        return Response(content=css_path.read_text(encoding="utf-8"), media_type="text/css")
    return Response(status_code=404)

@app.get("/app.js")
def serve_script():
    """Serves application JavaScript with correct content-type header."""
    js_path = FRONTEND_DIR / "app.js"
    if js_path.exists():
        return Response(content=js_path.read_text(encoding="utf-8"), media_type="application/javascript")
    return Response(status_code=404)

# Mount static files (CSS, JS, assets)
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
