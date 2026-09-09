import io
import os
import csv
import json
import platform
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Body, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from src.automation.service.decision_service import PayrollDecisionService
from src.automation.domain.payroll_rules import SAMPLE_BATCH, POLICY_CONFIG, POLICY_METADATA
from src.analysis.process_mining import ProcessMiningEngine
from src.analysis.roi_model import rank_automation_opportunities
from src.config import PROJECT_ROOT

app = FastAPI(
    title="Enterprise Process Automation & Decision Platform",
    description="Disciplined shadow-mode decision-support API for operational telemetry, process mining, and versioned policy rules.",
    version="2.5.0"
)

engine = PayrollDecisionService()
engine.process_batch(SAMPLE_BATCH)

_CACHED_SEGMENTS: Optional[List[Dict[str, Any]]] = None


def get_cached_segments() -> List[Dict[str, Any]]:
    global _CACHED_SEGMENTS
    if _CACHED_SEGMENTS is None:
        seg_file = PROJECT_ROOT / "deliverables" / "segments.jsonl"
        segs = []
        if seg_file.exists():
            with open(seg_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        s_str = item.get("start") or item.get("start_time", "")
                        e_str = item.get("end") or item.get("end_time", "")
                        dur = float(item.get("duration_seconds", 0.0))
                        if dur <= 0.0 and s_str and e_str:
                            try:
                                dt_s = datetime.fromisoformat(str(s_str).replace("Z", "+00:00"))
                                dt_e = datetime.fromisoformat(str(e_str).replace("Z", "+00:00"))
                                dur = max(1.0, (dt_e - dt_s).total_seconds())
                            except Exception:
                                dur = 1.0
                        item["start"] = s_str
                        item["end"] = e_str
                        item["start_time"] = s_str
                        item["end_time"] = e_str
                        item["duration_seconds"] = round(dur, 1)

                        sess = str(item.get("session_id", ""))
                        if "CHAITANYA" in sess:
                            operator = "user_b_01"
                            machine = "CHAITANYA0BCF"
                        elif "SIDDHI" in sess:
                            operator = "user_b_02"
                            machine = "SIDDHIGUPTAB00B"
                        elif "NEELA" in sess:
                            operator = "user_b_03"
                            machine = "NEELA9BAF"
                        elif "LAPTOP" in sess:
                            operator = "user_b_04"
                            machine = "LAPTOP-76QMG9DE"
                        else:
                            operator = "user_b_01"
                            machine = "CHAITANYA0BCF"
                        item["operator"] = operator
                        item["machine"] = machine

                        segs.append(item)
        _CACHED_SEGMENTS = segs
    return _CACHED_SEGMENTS


class PayrollClaimInput(BaseModel):
    case_id: Optional[str] = None
    employee_id: str = Field(..., json_schema_extra={"example": "EMP-9501"})
    employee_name: str = Field(..., json_schema_extra={"example": "Kenji Takahashi"})
    contract_type: str = Field(..., json_schema_extra={"example": "regular"})
    base_salary: int = Field(..., json_schema_extra={"example": 350000})
    claimed_commute: int = Field(0, json_schema_extra={"example": 16000})
    telework_days: int = Field(0, json_schema_extra={"example": 10})
    claimed_housing: int = Field(0, json_schema_extra={"example": 20000})
    custom_deduction: int = Field(0, json_schema_extra={"example": 0})
    deduction_reason: str = Field("", json_schema_extra={"example": ""})


class SupervisorOverrideInput(BaseModel):
    case_id: str
    decision: str
    supervisor_memo: str


@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    """Serves the interactive enterprise dashboard Single Page Application."""
    html_path = PROJECT_ROOT / "deliverables" / "automation_dashboard.html"
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(
                content=f.read(),
                headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}
            )
    except Exception as e:
        return HTMLResponse(content=f"<h1>Dashboard loading error: {str(e)}</h1>", status_code=500)


@app.get("/api/overview")
def get_system_overview():
    summary = engine.get_summary_report()
    return {
        "status": "ONLINE",
        "service": "Enterprise Decision Assistant (Shadow Mode)",
        "version": "2.5.0",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kpis": summary,
        "governance": {
            "policy_version": POLICY_METADATA.get("version", "v2026.04-v1.2"),
            "mode": "shadow_decision_support",
            "approval_owner": POLICY_METADATA.get("owner", "Corporate HR Policy Review Board")
        },
        "engine": {
            "name": "Production Hybrid Segmenter + Shadow Decision Engine",
            "architecture": "Deterministic Japanese Statutory Rules Engine",
            "statutory_basis": "Heisei 28 Cabinet Order No. 136; Shakai Hoken Standard Table 2026"
        },
        "hardware": {
            "platform": platform.platform(),
            "cpu_count": os.cpu_count() or 4,
            "architecture": platform.machine()
        }
    }


@app.get("/api/metrics")
def get_metrics():
    summary = engine.get_summary_report()
    return {
        "status": "success",
        "metrics": summary
    }


@app.get("/api/hardware")
def get_hardware_telemetry():
    hw_info = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "cpu_count": os.cpu_count() or 4,
        "architecture": platform.machine()
    }
    gpu_name = None
    try:
        import torch  # type: ignore
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            hw_info["gpu"] = gpu_name
            hw_info["cuda_available"] = True
            hw_info["vram_gb"] = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
    except Exception:
        pass

    return {
        "status": "success",
        "hardware": hw_info,
        "model": {
            "name": "Multimodal Neural-Symbolic Hybrid Segmenter",
            "type": "Attention-Augmented Multimodal BiLSTM + Deterministic Anchors",
            "checkpoint": "models/multimodal_process_net.pt" if (PROJECT_ROOT / "models" / "multimodal_process_net.pt").exists() else "models/boundary_bilstm_best.pt",
            "parameters": 530193,
            "acceleration": f"CUDA Tensor Core ({gpu_name})" if gpu_name else "Optimized CPU Engine",
            "status": "active"
        }
    }


@app.post("/api/process_case")
def process_single_case(claim: PayrollClaimInput):
    claim_dict = claim.model_dump(exclude_unset=False)
    if not claim_dict.get("case_id"):
        claim_dict["case_id"] = f"PI-API-{int(datetime.now(timezone.utc).timestamp())}"
    res = engine.process_item(claim_dict)
    return {"status": "success", "result": res}


@app.post("/api/supervisor_override")
def supervisor_override(override: SupervisorOverrideInput):
    res = engine.record_supervisor_override(
        case_id=override.case_id,
        decision=override.decision,
        reason=override.supervisor_memo
    )
    if not res:
        raise HTTPException(status_code=404, detail=f"Case {override.case_id} not found in active session queue")
    return {
        "status": "success",
        "updated_record": res,
        "case": res
    }


@app.get("/api/cases")
def get_cases(status: Optional[str] = Query(None)):
    cases = engine.processed_records
    if status and status != "ALL":
        cases = [c for c in cases if c["status"] == status]
    return {
        "status": "success",
        "total": len(cases),
        "count": len(cases),
        "cases": cases,
        "records": cases
    }


@app.get("/api/segments")
def get_segments(limit: int = 500, offset: int = 0):
    segs = get_cached_segments()
    total = len(segs)
    paged = segs[offset: offset + limit]
    return {
        "status": "success",
        "total": total,
        "count": len(paged),
        "limit": limit,
        "offset": offset,
        "segments": paged
    }


@app.get("/api/process_mining")
def get_process_mining():
    miner = ProcessMiningEngine(PROJECT_ROOT / "Datasets" / "dataset_b")
    dfg = miner.extract_directly_follows_graph()
    bottlenecks = miner.analyze_bottlenecks()
    return {"status": "success", "dfg": dfg, "bottlenecks": bottlenecks}


@app.get("/api/mining/dfg")
def get_mining_dfg():
    miner = ProcessMiningEngine(PROJECT_ROOT / "Datasets" / "dataset_b")
    dfg = miner.extract_directly_follows_graph()
    return {"status": "success", "dfg": dfg}


@app.get("/api/mining/bottlenecks")
def get_mining_bottlenecks():
    miner = ProcessMiningEngine(PROJECT_ROOT / "Datasets" / "dataset_b")
    bottlenecks = miner.analyze_bottlenecks()
    return {"status": "success", "bottlenecks": bottlenecks}


@app.get("/api/roi")
def get_roi():
    segs = get_cached_segments()
    candidates = rank_automation_opportunities(segs)
    return {"status": "success", "candidates": candidates, "rankings": candidates}


@app.get("/api/roi_ranking")
def get_roi_ranking():
    return get_roi()


@app.get("/api/export_approved_csv")
def export_approved_csv():
    approved = [c for c in engine.processed_records if c["status"] == "AUTO_APPROVED" or "APPROVED" in c["status"]]
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([
        "case_id", "employee_id", "employee_name", "contract_type",
        "approved_commute", "approved_telework", "approved_housing",
        "social_insurance_deduction", "employment_insurance_deduction",
        "custom_deduction", "net_adjustment", "status", "audit_id"
    ])
    for a in approved:
        inp = a["input_data"]
        calc = a["calculated_details"]
        writer.writerow([
            a["case_id"], inp.get("employee_id"), inp.get("employee_name"), inp.get("contract_type"),
            calc.get("approved_commute", 0), calc.get("approved_telework", 0), calc.get("approved_housing", 0),
            calc.get("social_insurance_deduction", 0), calc.get("employment_insurance_deduction", 0),
            calc.get("custom_deduction", 0), calc.get("net_adjustment", 0), a["status"], a.get("audit_id", "")
        ])
    out.seek(0)
    return StreamingResponse(
        out,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=approved_payroll_adjustments.csv"}
    )


@app.get("/api/export_erp_csv")
def export_erp_csv():
    return export_approved_csv()
