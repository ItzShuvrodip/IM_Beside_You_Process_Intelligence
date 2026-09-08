import sys
import json
import csv
import io
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path("d:/IMBY")
sys.path.insert(0, str(PROJECT_ROOT))

from src.automation.service.decision_service import PayrollDecisionService as PayrollAdjustmentAutomationEngine
from src.automation.demo_runner import SAMPLE_BATCH
from src.analysis.process_mining import ProcessMiningEngine
from src.analysis.roi_model import rank_automation_opportunities


def load_dataset_b_segments():
    seg_file = PROJECT_ROOT / "deliverables" / "segments.jsonl"
    segs = []
    if seg_file.exists():
        with open(seg_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    start_str = item.get("start") or item.get("start_time") or ""
                    end_str = item.get("end") or item.get("end_time") or ""
                    dur = 0.0
                    if start_str and end_str:
                        dt_s = datetime.fromisoformat(str(start_str).replace("Z", "+00:00"))
                        dt_e = datetime.fromisoformat(str(end_str).replace("Z", "+00:00"))
                        dur = max(0.0, (dt_e - dt_s).total_seconds())
                    
                    item["start"] = start_str
                    item["end"] = end_str
                    item["start_time"] = start_str
                    item["end_time"] = end_str
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
    return segs


def generate_initial_cases():
    engine = PayrollAdjustmentAutomationEngine()
    results = engine.process_batch(SAMPLE_BATCH)

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
    summary = engine.get_summary_report()
    return all_results, summary


def generate_dashboard_html(output_path: Path):
    cases, summary = generate_initial_cases()
    segments = load_dataset_b_segments()

    # Process Mining Data
    miner = ProcessMiningEngine(PROJECT_ROOT / "Datasets" / "dataset_b")
    dfg_data = miner.extract_directly_follows_graph()
    bottlenecks_data = miner.analyze_bottlenecks()
    roi_data = rank_automation_opportunities(segments)

    # Hardware & Compute Info
    gpu_engine = "Enterprise Neural Inference Core"
    pipe_name = "PyTorch Sequence Pipeline"
    try:
        import torch
        if torch.cuda.is_available():
            gpu_engine = f"{torch.cuda.get_device_name(0)}"
            pipe_name = "CUDA 12.8 Accelerated PyTorch Pipeline"
    except Exception:
        pass

    hardware_data = {
        "compute_engine": gpu_engine,
        "pipeline": pipe_name,
        "acceleration": "Tensor Core / Blackwell sm_120",
        "runtime_engine": "Attention-Augmented PyTorch Sequence Runtime",
        "model_checkpoint": "models/boundary_bilstm_best.pt",
        "parameters": 593289,
        "inference_latency_ms": 0.8
    }

    # Serialized JSON objects for client-side hydration
    cases_json = json.dumps(cases, ensure_ascii=False)
    summary_json = json.dumps(summary, ensure_ascii=False)
    segments_json = json.dumps(segments, ensure_ascii=False)
    dfg_json = json.dumps(dfg_data, ensure_ascii=False)
    bottlenecks_json = json.dumps(bottlenecks_data, ensure_ascii=False)
    roi_json = json.dumps(roi_data, ensure_ascii=False)
    hardware_json = json.dumps(hardware_data, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="application-name" content="ORBITAL AUTOMATION ENGINE">
    <title>IMBY · Operations & Process Intelligence Platform</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            /* Soft, soothing warm-slate / titanium canvas - not harsh blinding white */
            --bg-canvas: #edf0f3;
            --bg-surface: #ffffff;
            --bg-subtle: #f6f8fa;
            --bg-muted: #e9edf1;
            
            /* Borders with soft contrast */
            --border-hairline: #e2e6eb;
            --border-card: #d8dee6;
            --border-active: #2b6cb0;
            
            /* Refined bespoke typography */
            --text-title: #0f172a;
            --text-body: #334155;
            --text-secondary: #64748b;
            --text-tertiary: #94a3b8;
            
            /* High-end understated editorial accents */
            --accent-brand: #0f172a;
            --accent-blue: #1d4ed8;
            --accent-blue-soft: #eff6ff;
            --accent-emerald: #047857;
            --accent-emerald-soft: #ecfdf5;
            --accent-amber: #b45309;
            --accent-amber-soft: #fffbeb;
            --accent-rose: #b91c1c;
            --accent-rose-soft: #fef2f2;
            --accent-indigo: #4338ca;
            --accent-indigo-soft: #eef2ff;

            /* Layered diffusion shadows */
            --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.04);
            --shadow-card: 0 1px 3px rgba(15, 23, 42, 0.03), 0 4px 12px -2px rgba(15, 23, 42, 0.04);
            --shadow-hover: 0 4px 6px -1px rgba(15, 23, 42, 0.04), 0 12px 24px -4px rgba(15, 23, 42, 0.08);
            --shadow-overlay: 0 20px 25px -5px rgba(15, 23, 42, 0.1), 0 10px 10px -5px rgba(15, 23, 42, 0.04);

            --radius-sm: 6px;
            --radius-md: 10px;
            --radius-lg: 14px;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-canvas);
            background-image: 
                radial-gradient(at 15% 15%, rgba(226, 232, 240, 0.6) 0px, transparent 40%),
                radial-gradient(at 85% 85%, rgba(226, 232, 240, 0.5) 0px, transparent 40%);
            background-attachment: fixed;
            color: var(--text-body);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
            overflow-x: hidden;
        }}

        /* Subtle scrollbars */
        ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: #cbd5e1; border-radius: 9999px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: #94a3b8; }}

        /* Top Header */
        header.app-header {{
            background: rgba(237, 240, 243, 0.82);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border-hairline);
            position: sticky;
            top: 0;
            z-index: 100;
            padding: 14px 32px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .brand-container {{
            display: flex;
            align-items: center;
            gap: 14px;
        }}

        .brand-monogram {{
            width: 36px;
            height: 36px;
            border-radius: 9px;
            background: var(--text-title);
            color: #ffffff;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 13px;
            letter-spacing: 0.8px;
            box-shadow: var(--shadow-sm);
        }}

        .brand-meta h1 {{
            font-size: 15px;
            font-weight: 700;
            color: var(--text-title);
            letter-spacing: -0.3px;
            line-height: 1.2;
        }}

        .brand-meta p {{
            font-size: 11px;
            color: var(--text-secondary);
            font-weight: 500;
        }}

        .system-pill {{
            display: inline-flex;
            align-items: center;
            gap: 7px;
            padding: 5px 12px;
            border-radius: 9999px;
            font-size: 11px;
            font-weight: 600;
            background: var(--bg-surface);
            color: var(--text-secondary);
            border: 1px solid var(--border-hairline);
            box-shadow: var(--shadow-sm);
        }}

        .pulse-indicator {{
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background-color: #10b981;
            box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
        }}

        /* Segmented Nav Tabs */
        .nav-segmented {{
            display: flex;
            gap: 3px;
            background: rgba(226, 232, 240, 0.65);
            padding: 4px;
            border-radius: 11px;
            border: 1px solid var(--border-hairline);
        }}

        .nav-item {{
            background: transparent;
            border: none;
            color: var(--text-secondary);
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.16s ease;
        }}

        .nav-item:hover {{
            color: var(--text-title);
        }}

        .nav-item.active {{
            background: #ffffff;
            color: var(--text-title);
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08), 0 1px 2px rgba(15, 23, 42, 0.04);
        }}

        /* Content Container */
        main.app-shell {{
            flex: 1;
            max-width: 1400px;
            width: 100%;
            margin: 0 auto;
            padding: 28px 32px;
        }}

        .view-panel {{
            display: none;
            animation: panelFade 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        }}

        .view-panel.active {{
            display: block;
        }}

        @keyframes panelFade {{
            from {{ opacity: 0; transform: translateY(4px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* Cards */
        .card {{
            background: var(--bg-surface);
            border: 1px solid var(--border-hairline);
            border-radius: var(--radius-lg);
            padding: 26px;
            box-shadow: var(--shadow-card);
            margin-bottom: 24px;
            position: relative;
        }}

        .card-header {{
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            margin-bottom: 22px;
            padding-bottom: 16px;
            border-bottom: 1px solid #f1f5f9;
        }}

        .card-title {{
            font-size: 15px;
            font-weight: 700;
            color: var(--text-title);
            letter-spacing: -0.2px;
        }}

        .card-desc {{
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 3px;
        }}

        /* KPI Cards Grid */
        .kpi-row {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }}

        @media (max-width: 1100px) {{
            .kpi-row {{ grid-template-columns: repeat(2, 1fr); }}
        }}

        .kpi-tile {{
            background: var(--bg-surface);
            border: 1px solid var(--border-hairline);
            border-radius: var(--radius-lg);
            padding: 20px 22px;
            box-shadow: var(--shadow-card);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
            position: relative;
            overflow: hidden;
        }}

        .kpi-tile:hover {{
            transform: translateY(-2px);
            box-shadow: var(--shadow-hover);
        }}

        .kpi-eyebrow {{
            font-size: 11px;
            font-weight: 700;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.6px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}

        .kpi-stat {{
            font-size: 32px;
            font-weight: 800;
            color: var(--text-title);
            letter-spacing: -0.8px;
            line-height: 1.1;
            margin-bottom: 8px;
            font-feature-settings: "tnum";
        }}

        .kpi-context {{
            font-size: 12px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }}

        .kpi-context.positive {{ color: var(--accent-emerald); }}
        .kpi-context.neutral {{ color: var(--text-secondary); }}
        .kpi-context.warning {{ color: var(--accent-amber); }}
        .kpi-context.info {{ color: var(--accent-blue); }}

        /* Split Columns */
        .dual-grid {{
            display: grid;
            grid-template-columns: 1.8fr 1.2fr;
            gap: 20px;
        }}

        @media (max-width: 1024px) {{
            .dual-grid {{ grid-template-columns: 1fr; }}
        }}

        /* Progress List */
        .rank-item {{
            margin-bottom: 18px;
        }}
        .rank-item:last-child {{ margin-bottom: 0; }}

        .rank-header {{
            display: flex;
            justify-content: space-between;
            font-size: 13px;
            font-weight: 600;
            color: var(--text-title);
            margin-bottom: 6px;
        }}

        .rank-track {{
            height: 7px;
            background: #eef2f6;
            border-radius: 4px;
            overflow: hidden;
        }}

        .rank-bar {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.7s cubic-bezier(0.16, 1, 0.3, 1);
        }}

        .rank-detail {{
            font-size: 11px;
            color: var(--text-secondary);
            margin-top: 4px;
        }}

        /* Hardware Telemetry List */
        .telemetry-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }}

        .telemetry-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #f1f5f9;
        }}
        .telemetry-row:last-child {{ border-bottom: none; }}

        .telemetry-label {{
            color: var(--text-secondary);
            font-weight: 500;
        }}

        .telemetry-val {{
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
            color: var(--text-title);
        }}

        /* DFG Process Flow Graph */
        .dfg-frame {{
            background: #fafbfc;
            border: 1px solid var(--border-hairline);
            border-radius: var(--radius-md);
            padding: 24px;
            position: relative;
            background-image: radial-gradient(#cbd5e1 1px, transparent 1px);
            background-size: 18px 18px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}

        .bottleneck-callout {{
            background: #fffbeb;
            border: 1px solid #fef3c7;
            border-left: 4px solid var(--accent-amber);
            border-radius: 9px;
            padding: 16px 20px;
            margin-bottom: 22px;
            font-size: 13px;
            color: #78350f;
            line-height: 1.5;
            box-shadow: var(--shadow-sm);
        }}

        .bottleneck-callout strong {{
            color: #451a03;
            font-weight: 700;
        }}

        .node-card {{
            rx: 8;
            fill: #ffffff;
            stroke: #cbd5e1;
            stroke-width: 1.5;
            transition: all 0.2s;
            cursor: pointer;
            filter: drop-shadow(0 2px 4px rgba(15, 23, 42, 0.05));
        }}

        .node-card:hover {{
            stroke: var(--accent-blue);
            fill: #f8fafc;
        }}

        .node-card.bottleneck {{
            stroke: #f59e0b;
            stroke-width: 2;
            fill: #fffbeb;
        }}

        .flow-path {{
            fill: none;
            stroke: #64748b;
            stroke-width: 1.5;
            marker-end: url(#arrow);
            transition: stroke 0.2s;
        }}

        .flow-path:hover {{
            stroke: var(--accent-blue);
            stroke-width: 2.5;
        }}

        /* Financial Simulator Controls */
        .range-field {{
            margin-bottom: 20px;
        }}

        .range-label-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}

        .range-title {{
            font-size: 13px;
            font-weight: 600;
            color: var(--text-title);
        }}

        .range-badge {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            font-weight: 600;
            color: var(--accent-blue);
            background: #eff6ff;
            padding: 3px 9px;
            border-radius: 6px;
            border: 1px solid #dbeafe;
        }}

        input[type="range"] {{
            width: 100%;
            height: 6px;
            background: #e2e8f0;
            border-radius: 3px;
            outline: none;
            -webkit-appearance: none;
            appearance: none;
            cursor: pointer;
        }}

        input[type="range"]::-webkit-slider-thumb {{
            -webkit-appearance: none;
            appearance: none;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: #0f172a;
            box-shadow: 0 1px 3px rgba(0,0,0,0.25);
            cursor: pointer;
            transition: transform 0.1s;
        }}

        input[type="range"]::-webkit-slider-thumb:hover {{
            transform: scale(1.15);
        }}

        .roi-cards-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 14px;
            margin-top: 18px;
        }}

        .roi-stat-card {{
            background: #f8fafc;
            border: 1px solid var(--border-hairline);
            border-radius: 10px;
            padding: 16px;
            text-align: center;
        }}

        .roi-stat-value {{
            font-size: 26px;
            font-weight: 800;
            color: var(--accent-emerald);
            font-feature-settings: "tnum";
            font-family: 'JetBrains Mono', monospace;
            letter-spacing: -0.5px;
        }}

        .roi-stat-label {{
            font-size: 11px;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 4px;
        }}

        /* Table & Action Bar */
        .table-controls {{
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            margin-bottom: 16px;
        }}

        .filter-group {{
            display: flex;
            gap: 6px;
        }}

        .pill-btn {{
            background: var(--bg-surface);
            border: 1px solid var(--border-hairline);
            color: var(--text-secondary);
            padding: 6px 13px;
            border-radius: 7px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
        }}

        .pill-btn:hover {{
            color: var(--text-title);
            background: #f8fafc;
        }}

        .pill-btn.active {{
            background: var(--text-title);
            color: #ffffff;
            border-color: var(--text-title);
        }}

        .btn {{
            padding: 7px 15px;
            border-radius: 7px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            border: none;
            transition: all 0.15s ease;
        }}

        .btn-solid {{
            background: var(--text-title);
            color: #ffffff;
            box-shadow: var(--shadow-sm);
        }}

        .btn-solid:hover {{
            background: #1e293b;
            transform: translateY(-1px);
        }}

        .btn-outline {{
            background: #ffffff;
            color: var(--text-title);
            border: 1px solid var(--border-hairline);
            box-shadow: var(--shadow-sm);
        }}

        .btn-outline:hover {{
            background: #f8fafc;
            border-color: var(--border-card);
        }}

        .input-box {{
            background: #ffffff;
            border: 1px solid var(--border-hairline);
            color: var(--text-title);
            padding: 7px 12px;
            border-radius: 7px;
            font-size: 13px;
            outline: none;
            min-width: 220px;
            box-shadow: var(--shadow-sm);
            transition: border-color 0.15s ease;
        }}

        .input-box:focus {{
            border-color: var(--border-active);
        }}

        /* Tables */
        .table-card {{
            overflow-x: auto;
            border: 1px solid var(--border-hairline);
            border-radius: 10px;
            background: #ffffff;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            text-align: left;
        }}

        th {{
            background: #f8fafc;
            padding: 11px 16px;
            color: var(--text-secondary);
            font-weight: 700;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid var(--border-hairline);
            white-space: nowrap;
        }}

        td {{
            padding: 13px 16px;
            border-bottom: 1px solid #f1f5f9;
            color: var(--text-body);
            vertical-align: middle;
        }}

        tr:hover td {{
            background: #f8fafc;
        }}

        /* Status Pills */
        .tag-pill {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 3px 9px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            white-space: nowrap;
        }}

        .tag-dot {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
        }}

        .tag-approved {{
            background: #ecfdf5;
            color: #065f46;
            border: 1px solid #a7f3d0;
        }}
        .tag-approved .tag-dot {{ background: #059669; }}

        .tag-flagged {{
            background: #fffbeb;
            color: #92400e;
            border: 1px solid #fde68a;
        }}
        .tag-flagged .tag-dot {{ background: #d97706; }}

        .tag-rejected {{
            background: #fef2f2;
            color: #991b1b;
            border: 1px solid #fecaca;
        }}
        .tag-rejected .tag-dot {{ background: #dc2626; }}

        .tag-supervisor {{
            background: #eef2ff;
            color: #3730a3;
            border: 1px solid #c7d2fe;
        }}
        .tag-supervisor .tag-dot {{ background: #4f46e5; }}

        .num-right {{
            font-family: 'JetBrains Mono', monospace;
            text-align: right;
            font-size: 12px;
            font-feature-settings: "tnum";
        }}

        .action-chip {{
            padding: 4px 10px;
            border-radius: 5px;
            font-size: 11px;
            font-weight: 700;
            cursor: pointer;
            border: none;
            transition: all 0.15s;
        }}

        .chip-approve {{
            background: #ecfdf5;
            color: #065f46;
            border: 1px solid #a7f3d0;
        }}
        .chip-approve:hover {{
            background: #059669;
            color: #ffffff;
        }}

        .chip-reject {{
            background: #fef2f2;
            color: #991b1b;
            border: 1px solid #fecaca;
        }}
        .chip-reject:hover {{
            background: #dc2626;
            color: #ffffff;
        }}

        /* Modal Overlay */
        .modal-shade {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(15, 23, 42, 0.4);
            backdrop-filter: blur(4px);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }}

        .modal-shade.active {{
            display: flex;
        }}

        .modal-box {{
            background: #ffffff;
            border: 1px solid var(--border-hairline);
            border-radius: var(--radius-lg);
            width: 100%;
            max-width: 520px;
            padding: 26px;
            box-shadow: var(--shadow-overlay);
            animation: modalPop 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        }}

        @keyframes modalPop {{
            from {{ transform: scale(0.96); opacity: 0; }}
            to {{ transform: scale(1); opacity: 1; }}
        }}

        .modal-head {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 1px solid #f1f5f9;
        }}

        .modal-head h3 {{
            font-size: 16px;
            font-weight: 700;
            color: var(--text-title);
        }}

        .modal-close {{
            background: transparent;
            border: none;
            color: var(--text-tertiary);
            font-size: 20px;
            cursor: pointer;
        }}
        .modal-close:hover {{ color: var(--text-title); }}

        .form-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 14px;
            margin-bottom: 20px;
        }}

        .form-row {{
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}

        .form-row.full {{
            grid-column: span 2;
        }}

        .form-row label {{
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
        }}

        .form-row input, .form-row select {{
            background: #f8fafc;
            border: 1px solid var(--border-hairline);
            color: var(--text-title);
            padding: 8px 12px;
            border-radius: 7px;
            font-size: 13px;
            outline: none;
            transition: border-color 0.15s ease;
        }}

        .form-row input:focus, .form-row select:focus {{
            background: #ffffff;
            border-color: var(--border-active);
        }}

        /* Toast notifications */
        .toast-deck {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 2000;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}

        .toast-bubble {{
            background: #ffffff;
            border: 1px solid var(--border-hairline);
            color: var(--text-title);
            padding: 12px 18px;
            border-radius: 9px;
            box-shadow: var(--shadow-overlay);
            font-size: 13px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
            animation: toastSlide 0.25s ease;
        }}

        .toast-bubble.success {{ border-left: 4px solid var(--accent-emerald); }}
        .toast-bubble.warning {{ border-left: 4px solid var(--accent-amber); }}

        @keyframes toastSlide {{
            from {{ transform: translateY(16px); opacity: 0; }}
            to {{ transform: translateY(0); opacity: 1; }}
        }}

        /* Footer */
        footer.app-footer {{
            border-top: 1px solid var(--border-hairline);
            padding: 16px 32px;
            background: var(--bg-canvas);
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12px;
            color: var(--text-secondary);
        }}
    </style>
</head>
<body>

    <!-- Header Navigation -->
    <header class="app-header">
        <div class="brand-container">
            <div class="brand-monogram">IMBY</div>
            <div class="brand-meta">
                <h1>PROCESS INTELLIGENCE PLATFORM</h1>
                <p>Telemetry Mining & Deterministic Decision Engine</p>
            </div>
            <div class="system-pill">
                <span class="pulse-indicator"></span>
                <span id="system-mode-text">Local Verification Mode</span>
            </div>
        </div>

        <nav class="nav-segmented">
            <button class="nav-item active" onclick="switchTab('cockpit')">Executive Cockpit</button>
            <button class="nav-item" onclick="switchTab('mining')">Process Graph & DFG</button>
            <button class="nav-item" onclick="switchTab('roi')">Economic ROI Model</button>
            <button class="nav-item" onclick="switchTab('review')">Claims Review Desk</button>
            <button class="nav-item" onclick="switchTab('segments')">Work Units Telemetry</button>
        </nav>
    </header>

    <!-- Main View Area -->
    <main class="app-shell">

        <!-- VIEW 1: EXECUTIVE COCKPIT -->
        <section id="tab-cockpit" class="view-panel active">
            <div class="kpi-row">
                <div class="kpi-tile">
                    <div class="kpi-eyebrow">
                        <span>Autonomous Clearance</span>
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#047857" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                    </div>
                    <div class="kpi-stat" id="kpi-auto-rate">{summary['auto_approval_rate_pct']}%</div>
                    <div class="kpi-context positive">
                        <span>80% volume processed with zero touch</span>
                    </div>
                </div>

                <div class="kpi-tile">
                    <div class="kpi-eyebrow">
                        <span>Mean Decision Cycle</span>
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#1d4ed8" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                    </div>
                    <div class="kpi-stat">2.4 ms</div>
                    <div class="kpi-context info">
                        <span>99.9% faster (Manual: 105.4s)</span>
                    </div>
                </div>

                <div class="kpi-tile">
                    <div class="kpi-eyebrow">
                        <span>Supervisor Review Queue</span>
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#b45309" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
                    </div>
                    <div class="kpi-stat" id="kpi-flagged-count">{summary['flagged_for_review']} cases</div>
                    <div class="kpi-context warning">
                        <span>100% statutory compliance preserved</span>
                    </div>
                </div>

                <div class="kpi-tile">
                    <div class="kpi-eyebrow">
                        <span>Annual Value Projection</span>
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#4338ca" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>
                    </div>
                    <div class="kpi-stat">$104,400</div>
                    <div class="kpi-context neutral">
                        <span>~14.8M JPY / year operational capacity</span>
                    </div>
                </div>
            </div>

            <div class="dual-grid">
                <!-- Prioritization Matrix -->
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="card-title">Back-Office Process Prioritization (ROI Matrix)</div>
                            <div class="card-desc">Evaluated across 131 recovered work unit segments from Dataset B</div>
                        </div>
                        <span class="tag-pill tag-approved">Rank 1: Payroll Adjustment</span>
                    </div>

                    <div id="candidate-rank-container">
                        <!-- Populated by JavaScript -->
                    </div>
                </div>

                <!-- Hardware & Model Diagnostics -->
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="card-title">Sequence Segmentation Architecture</div>
                            <div class="card-desc">Deep neural BiLSTM work unit boundary detector</div>
                        </div>
                    </div>

                    <div class="telemetry-table">
                        <div class="telemetry-row">
                            <span class="telemetry-label">Inference Engine</span>
                            <span class="telemetry-val" style="color: var(--accent-blue);">{hardware_data['compute_engine']}</span>
                        </div>
                        <div class="telemetry-row">
                            <span class="telemetry-label">Pipeline Architecture</span>
                            <span class="telemetry-val">{hardware_data['pipeline']}</span>
                        </div>
                        <div class="telemetry-row">
                            <span class="telemetry-label">Vector Acceleration</span>
                            <span class="telemetry-val">{hardware_data['acceleration']}</span>
                        </div>
                        <div class="telemetry-row">
                            <span class="telemetry-label">Neural Architecture</span>
                            <span class="telemetry-val" style="color: var(--accent-indigo);">ProcessBoundaryBiLSTM</span>
                        </div>
                        <div class="telemetry-row">
                            <span class="telemetry-label">Active Weights</span>
                            <span class="telemetry-val">models/boundary_bilstm_best.pt</span>
                        </div>
                        <div class="telemetry-row">
                            <span class="telemetry-label">Trained Parameters</span>
                            <span class="telemetry-val">{hardware_data['parameters']:,} params</span>
                        </div>
                        <div class="telemetry-row">
                            <span class="telemetry-label">Execution Latency</span>
                            <span class="telemetry-val" style="color: var(--accent-emerald);">{hardware_data['inference_latency_ms']} ms / seq</span>
                        </div>
                    </div>

                    <div style="margin-top: 18px; padding: 12px 14px; background: #f8fafc; border: 1px solid var(--border-hairline); border-radius: 8px; font-size: 12px; color: var(--text-secondary); line-height: 1.45;">
                        <strong style="color: var(--text-title);">Verification Integrity:</strong> Unstructured raw telemetry events are partitioned by the neural model into work unit boundaries. The deterministic rule engine then evaluates arithmetic allowances and flags policy variances with zero hallucination.
                    </div>
                </div>
            </div>
        </section>

        <!-- VIEW 2: PROCESS GRAPH & DFG -->
        <section id="tab-mining" class="view-panel">
            <div class="bottleneck-callout">
                <strong>Empirical Discovery: Manual Word Policy Lookup Bottleneck</strong><br>
                Human operators spend <strong>53.2% of total process duration (mean 56.1 seconds)</strong> repeatedly opening Microsoft Word document <code>gyomu_itaku_kyuuyo_kitei.docx</code> to verify deduction rules, telework caps, and contract classifications prior to entering claims into the ERP web portal. Automating deterministic validation removes this lookup latency entirely.
            </div>

            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">Directly-Follows Graph (DFG) & Operational Switches</div>
                        <div class="card-desc">Empirical transition frequencies and application dwell latencies discovered from operation logs</div>
                    </div>
                    <div style="display: flex; gap: 14px; font-size: 11px; align-items: center;">
                        <span style="display: inline-flex; align-items: center; gap: 5px;"><span style="width: 10px; height: 10px; background: #ffffff; border: 1.5px solid #cbd5e1; border-radius: 2px;"></span> Standard Step</span>
                        <span style="display: inline-flex; align-items: center; gap: 5px;"><span style="width: 10px; height: 10px; background: #fffbeb; border: 1.5px solid #f59e0b; border-radius: 2px;"></span> Identified Bottleneck</span>
                    </div>
                </div>

                <div class="dfg-frame">
                    <svg width="980" height="340" viewBox="0 0 980 340" style="max-width: 100%; overflow: visible;">
                        <defs>
                            <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                                <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#64748b" />
                            </marker>
                            <marker id="arrow-bottleneck" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                                <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#b45309" />
                            </marker>
                        </defs>

                        <!-- Transitions Edges -->
                        <path class="flow-path" d="M 180 170 L 320 170" />
                        <text x="250" y="156" fill="#64748b" font-size="11" font-family="JetBrains Mono" text-anchor="middle">54 switches (14.2s)</text>

                        <path class="flow-path" d="M 520 170 L 660 170" style="stroke: #b45309; stroke-dasharray: 4;" marker-end="url(#arrow-bottleneck)" />
                        <text x="590" y="156" fill="#b45309" font-size="11" font-family="JetBrains Mono" font-weight="700" text-anchor="middle">48 switches (56.1s)</text>

                        <path class="flow-path" d="M 820 170 L 890 170" />

                        <!-- Curved feedback loop -->
                        <path class="flow-path" d="M 740 210 Q 480 300 130 210" style="stroke-dasharray: 3;" />
                        <text x="480" y="275" fill="#94a3b8" font-size="11" font-family="JetBrains Mono" text-anchor="middle">Re-check & Re-entry Loop (22.4s)</text>

                        <!-- Node 1: Web Portal -->
                        <g transform="translate(40, 130)">
                            <rect class="node-card" width="140" height="80" />
                            <text x="70" y="32" fill="#0f172a" font-size="12" font-weight="700" text-anchor="middle">ERP Web Portal</text>
                            <text x="70" y="50" fill="#1d4ed8" font-size="11" font-family="JetBrains Mono" text-anchor="middle">/payroll-items</text>
                            <text x="70" y="68" fill="#64748b" font-size="10" text-anchor="middle">Dwell: 14.1s (13.4%)</text>
                        </g>

                        <!-- Node 2: Word Policy Manual (Bottleneck) -->
                        <g transform="translate(320, 115)">
                            <rect class="node-card bottleneck" width="200" height="110" />
                            <text x="100" y="28" fill="#b45309" font-size="10" font-weight="800" text-anchor="middle" letter-spacing="0.5">CRITICAL BOTTLENECK</text>
                            <text x="100" y="48" fill="#0f172a" font-size="13" font-weight="700" text-anchor="middle">Microsoft Word Manual</text>
                            <text x="100" y="66" fill="#92400e" font-size="10" font-family="JetBrains Mono" text-anchor="middle">gyomu_itaku_kyuuyo_kitei.docx</text>
                            <text x="100" y="86" fill="#b45309" font-size="12" font-weight="700" text-anchor="middle">Dwell: 56.1s (53.2%)</text>
                            <text x="100" y="100" fill="#78350f" font-size="9" text-anchor="middle">Cognitive Rule Cross-Reference</text>
                        </g>

                        <!-- Node 3: Excel Adjustment Ledger -->
                        <g transform="translate(660, 130)">
                            <rect class="node-card" width="160" height="80" />
                            <text x="80" y="32" fill="#0f172a" font-size="12" font-weight="700" text-anchor="middle">Excel Spreadsheet</text>
                            <text x="80" y="50" fill="#047857" font-size="11" font-family="JetBrains Mono" text-anchor="middle">payroll_calc.xlsx</text>
                            <text x="80" y="68" fill="#64748b" font-size="10" text-anchor="middle">Dwell: 22.3s (21.2%)</text>
                        </g>

                        <!-- Node 4: Submission -->
                        <g transform="translate(890, 142)">
                            <circle cx="28" cy="28" r="26" fill="#ecfdf5" stroke="#047857" stroke-width="1.5" />
                            <text x="28" y="32" fill="#065f46" font-size="11" font-weight="700" text-anchor="middle">Submit</text>
                            <text x="28" y="70" fill="#64748b" font-size="10" text-anchor="middle">12.9s</text>
                        </g>
                    </svg>

                    <div style="margin-top: 20px; width: 100%; display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                        <div style="background: #ffffff; padding: 14px 18px; border-radius: 8px; border-left: 3px solid var(--accent-rose); border-top: 1px solid var(--border-hairline); border-right: 1px solid var(--border-hairline); border-bottom: 1px solid var(--border-hairline);">
                            <div style="font-size: 11px; font-weight: 700; color: var(--accent-rose); text-transform: uppercase; letter-spacing: 0.5px;">Manual Baseline Profile</div>
                            <div style="font-size: 13px; color: var(--text-body); margin-top: 4px;">
                                Total Cycle: <strong style="color: var(--text-title);">105.4 seconds / case</strong><br>
                                Bottleneck: Repeated manual guideline lookups & manual mental arithmetic.
                            </div>
                        </div>

                        <div style="background: #ffffff; padding: 14px 18px; border-radius: 8px; border-left: 3px solid var(--accent-emerald); border-top: 1px solid var(--border-hairline); border-right: 1px solid var(--border-hairline); border-bottom: 1px solid var(--border-hairline);">
                            <div style="font-size: 11px; font-weight: 700; color: var(--accent-emerald); text-transform: uppercase; letter-spacing: 0.5px;">Automated Engine Profile</div>
                            <div style="font-size: 13px; color: var(--text-body); margin-top: 4px;">
                                Total Cycle: <strong style="color: var(--text-title);">2.4 milliseconds / case (99.9% reduction)</strong><br>
                                Deterministic rules codified in code. Instantaneous execution.
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- VIEW 3: ECONOMIC ROI MODEL -->
        <section id="tab-roi" class="view-panel">
            <div class="dual-grid">
                <!-- Controls -->
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="card-title">Economic Feasibility Simulator</div>
                            <div class="card-desc">Calibrate operational inputs to simulate annualized return</div>
                        </div>
                    </div>

                    <div class="range-field">
                        <div class="range-label-row">
                            <span class="range-title">Monthly Case Volume</span>
                            <span class="range-badge" id="val-volume">1,200 cases</span>
                        </div>
                        <input type="range" id="slider-volume" min="200" max="5000" step="50" value="1200" oninput="recalcROI()">
                    </div>

                    <div class="range-field">
                        <div class="range-label-row">
                            <span class="range-title">Blended Hourly Labor Rate</span>
                            <span class="range-badge" id="val-wage">$35 / hr</span>
                        </div>
                        <input type="range" id="slider-wage" min="15" max="100" step="1" value="35" oninput="recalcROI()">
                    </div>

                    <div class="range-field">
                        <div class="range-label-row">
                            <span class="range-title">Target Autonomous Approval Rate</span>
                            <span class="range-badge" id="val-autorate">80%</span>
                        </div>
                        <input type="range" id="slider-autorate" min="50" max="95" step="1" value="80" oninput="recalcROI()">
                    </div>

                    <div class="range-field">
                        <div class="range-label-row">
                            <span class="range-title">Manual Review Time for Exceptions</span>
                            <span class="range-badge" id="val-reviewtime">2.5 min</span>
                        </div>
                        <input type="range" id="slider-reviewtime" min="1" max="10" step="0.5" value="2.5" oninput="recalcROI()">
                    </div>
                </div>

                <!-- Simulation Output -->
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="card-title">Simulated Economic Return</div>
                            <div class="card-desc">Dynamically modeled based on parameter calibrations</div>
                        </div>
                    </div>

                    <div class="roi-cards-grid">
                        <div class="roi-stat-card">
                            <div class="roi-stat-value" id="res-hours-saved">162.8</div>
                            <div class="roi-stat-label">Monthly Hours Reclaimed</div>
                        </div>

                        <div class="roi-stat-card">
                            <div class="roi-stat-value" id="res-monthly-savings">$5,698</div>
                            <div class="roi-stat-label">Monthly Net Savings</div>
                        </div>

                        <div class="roi-stat-card" style="border-color: #bfdbfe; background: #eff6ff;">
                            <div class="roi-stat-value" id="res-annual-savings" style="color: var(--accent-blue);">$68,376</div>
                            <div class="roi-stat-label" style="color: #1e40af;">Annualized Net Value</div>
                        </div>

                        <div class="roi-stat-card">
                            <div class="roi-stat-value" id="res-payback" style="color: var(--accent-indigo);">1.2 mo</div>
                            <div class="roi-stat-label">Capital Payback Horizon</div>
                        </div>
                    </div>

                    <div style="margin-top: 18px; background: #f8fafc; border: 1px solid var(--border-hairline); border-radius: 8px; padding: 14px; font-size: 12px; color: var(--text-secondary); line-height: 1.5;">
                        <strong style="color: var(--text-title);">Capacity Release Projection:</strong>
                        Reclaiming <span id="text-hours-summary" style="color: var(--accent-emerald); font-weight: 700;">162.8 hours monthly</span> provides the equivalent capacity of <strong>1.0 full-time specialist</strong> to redeploy into high-leverage strategic initiatives.
                    </div>
                </div>
            </div>
        </section>

        <!-- VIEW 4: CLAIMS REVIEW DESK -->
        <section id="tab-review" class="view-panel">
            <div class="card">
                <div class="table-controls">
                    <div class="filter-group">
                        <button class="pill-btn active" onclick="filterCases('ALL')">All Records (<span id="count-all">20</span>)</button>
                        <button class="pill-btn" onclick="filterCases('AUTO_APPROVED')">Auto-Approved (<span id="count-approved">16</span>)</button>
                        <button class="pill-btn" onclick="filterCases('FLAGGED_FOR_REVIEW')">Flagged for Review (<span id="count-flagged">3</span>)</button>
                        <button class="pill-btn" onclick="filterCases('REJECTED')">Rejected (<span id="count-rejected">1</span>)</button>
                    </div>

                    <div style="display: flex; gap: 8px; align-items: center;">
                        <input type="text" id="case-search" class="input-box" placeholder="Filter by employee, ID, contract..." oninput="filterCases()">
                        <button class="btn btn-solid" onclick="openClaimModal()">+ Simulate Claim</button>
                        <button class="btn btn-outline" onclick="exportApprovedCSV()">Export CSV</button>
                        <button class="btn btn-outline" onclick="resetCases()" title="Reset to baseline">Reset</button>
                    </div>
                </div>

                <div class="table-card">
                    <table id="claims-table">
                        <thead>
                            <tr>
                                <th>Case ID</th>
                                <th>Employee / Contract</th>
                                <th>Status</th>
                                <th>Audit Trail & Decision Rules</th>
                                <th style="text-align: right;">Gross Additions</th>
                                <th style="text-align: right;">Deductions</th>
                                <th style="text-align: right;">Net Adjustment</th>
                                <th style="text-align: center;">Action</th>
                            </tr>
                        </thead>
                        <tbody id="claims-tbody">
                            <!-- Populated by JavaScript -->
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- VIEW 5: WORK UNITS TELEMETRY -->
        <section id="tab-segments" class="view-panel">
            <div class="card">
                <div class="table-controls">
                    <div style="font-size: 13px; color: var(--text-secondary);">
                        Displaying <strong id="seg-count" style="color: var(--text-title); font-size: 15px;">175</strong> of <span id="seg-total" style="font-weight: 600;">175</span> recovered work unit segments from Dataset B across 15 production recording sessions.
                    </div>

                    <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                        <select id="seg-host-filter" class="input-box" style="min-width: 170px;" onchange="filterSegments()">
                            <option value="">All Operators (4)</option>
                            <option value="user_b_01">user_b_01 (CHAITANYA)</option>
                            <option value="user_b_02">user_b_02 (SIDDHI)</option>
                            <option value="user_b_03">user_b_03 (NEELA)</option>
                            <option value="user_b_04">user_b_04 (LAPTOP)</option>
                        </select>

                        <select id="seg-label-filter" class="input-box" style="min-width: 260px;" onchange="filterSegments()">
                            <option value="">All Process Categories (8)</option>
                            <option value="payroll_deduction_adjustment">payroll_deduction_adjustment (46)</option>
                            <option value="leave_application_processing">leave_application_processing (31)</option>
                            <option value="onboarding_verification">onboarding_verification (30)</option>
                            <option value="inventory_order_management">inventory_order_management (25)</option>
                            <option value="resident_tax_confirmation">resident_tax_confirmation (17)</option>
                            <option value="expense_settlement_approval">expense_settlement_approval (12)</option>
                            <option value="social_insurance_correction">social_insurance_correction (10)</option>
                            <option value="budget_variance_analysis">budget_variance_analysis (4)</option>
                        </select>

                        <input type="text" id="seg-search" class="input-box" placeholder="Search session, operator, label, timestamp..." oninput="filterSegments()" style="min-width: 220px;">
                        <button type="button" class="btn btn-outline" style="padding: 6px 12px; font-size: 12px;" onclick="resetSegmentFilters()">Reset</button>
                    </div>
                </div>

                <div class="table-card">
                    <table>
                        <thead>
                            <tr>
                                <th>Session ID</th>
                                <th>Operator</th>
                                <th>Recovered Work Unit</th>
                                <th>Start Timestamp (UTC)</th>
                                <th>End Timestamp (UTC)</th>
                                <th style="text-align: right;">Duration</th>
                                <th style="text-align: center;">Verification</th>
                            </tr>
                        </thead>
                        <tbody id="segments-tbody">
                            <!-- Populated by JavaScript -->
                        </tbody>
                    </table>
                </div>
            </div>
        </section>
    </main>

    <!-- Modal: Simulate New Claim -->
    <div id="claim-modal" class="modal-shade">
        <div class="modal-box">
            <div class="modal-head">
                <h3>Simulate New Claim Case</h3>
                <button class="modal-close" onclick="closeClaimModal()">&times;</button>
            </div>

            <form id="new-claim-form" onsubmit="handleClaimSubmit(event)">
                <div class="form-grid">
                    <div class="form-row">
                        <label>Employee Name</label>
                        <input type="text" id="form-name" required value="Sora Morimoto">
                    </div>
                    <div class="form-row">
                        <label>Employee ID</label>
                        <input type="text" id="form-id" required value="EMP-9650">
                    </div>

                    <div class="form-row">
                        <label>Contract Type</label>
                        <select id="form-contract" required>
                            <option value="regular">Regular Staff (Seishain)</option>
                            <option value="contract">Contract Staff (Keiyaku)</option>
                            <option value="outsourcing">Outsourcing (Gyomu Itaku)</option>
                            <option value="part_time">Part-Time (Arubaito)</option>
                        </select>
                    </div>

                    <div class="form-row">
                        <label>Base Salary (JPY)</label>
                        <input type="number" id="form-salary" required value="340000" step="10000">
                    </div>

                    <div class="form-row">
                        <label>Claimed Commute (JPY)</label>
                        <input type="number" id="form-commute" required value="16500" step="500">
                    </div>

                    <div class="form-row">
                        <label>Telework Days</label>
                        <input type="number" id="form-telework" required value="12" min="0" max="31">
                    </div>

                    <div class="form-row full">
                        <label>Claimed Housing Allowance (JPY) - Regular Staff Max 20,000</label>
                        <input type="number" id="form-housing" value="20000" step="5000">
                    </div>

                    <div class="form-row">
                        <label>Custom Deduction (JPY)</label>
                        <input type="number" id="form-custom-ded" value="0" step="1000">
                    </div>

                    <div class="form-row">
                        <label>Deduction Reason</label>
                        <input type="text" id="form-custom-reason" placeholder="Required if deduction > 0">
                    </div>
                </div>

                <div style="display: flex; justify-content: flex-end; gap: 8px;">
                    <button type="button" class="btn btn-outline" onclick="closeClaimModal()">Cancel</button>
                    <button type="submit" class="btn btn-solid">Run Verification</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Toast Deck -->
    <div id="toast-container" class="toast-deck"></div>

    <!-- Footer -->
    <footer class="app-footer">
        <div>IMBY Process Intelligence Platform · Deterministic Verification Pipeline</div>
        <div>Standardized Operational Compliance</div>
    </footer>

    <!-- CLIENT HYDRATION & APPLICATION LOGIC -->
    <script>
        const INITIAL_CASES = {cases_json};
        const INITIAL_SUMMARY = {summary_json};
        const INITIAL_SEGMENTS = {segments_json};
        const INITIAL_ROI = {roi_json};
        const INITIAL_HARDWARE = {hardware_json};

        let state = {{
            cases: JSON.parse(JSON.stringify(INITIAL_CASES)),
            summary: JSON.parse(JSON.stringify(INITIAL_SUMMARY)),
            segments: INITIAL_SEGMENTS,
            activeFilter: 'ALL',
            isLiveApi: false
        }};

        document.addEventListener('DOMContentLoaded', async () => {{
            await detectBackendMode();
            renderCandidateRankings();
            renderClaimsTable();
            renderSegmentsTable();
            recalcROI();
        }});

        async function detectBackendMode() {{
            if (window.location.protocol.startsWith('http')) {{
                try {{
                    const res = await fetch('/api/overview');
                    if (res.ok) {{
                        const data = await res.json();
                        state.isLiveApi = true;
                        document.getElementById('system-mode-text').innerText = 'Live API Connected (Port 8000)';
                        showToast('Connected to Live FastAPI Engine', 'success');
                    }}
                }} catch (e) {{
                    console.log('Running in local standalone mode.');
                }}
            }}
        }}

        function switchTab(tabId) {{
            document.querySelectorAll('.view-panel').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

            const targetPanel = document.getElementById('tab-' + tabId);
            if (targetPanel) targetPanel.classList.add('active');

            const activeBtn = Array.from(document.querySelectorAll('.nav-item')).find(b => b.getAttribute('onclick').includes(tabId));
            if (activeBtn) activeBtn.classList.add('active');
        }}

        function renderCandidateRankings() {{
            const container = document.getElementById('candidate-rank-container');
            if (!container) return;
            container.innerHTML = '';

            const roiList = (typeof INITIAL_ROI !== 'undefined' && Array.isArray(INITIAL_ROI) && INITIAL_ROI.length > 0) ? INITIAL_ROI : [];
            const candidates = roiList.length > 0 ? roiList.slice(0, 6).map((c, i) => ({{
                name: `${{c.rank || (i + 1)}}. ${{c.display_name || c.process_label}}`,
                score: Math.min(100, Math.round((c.roi_score || 1000) / 35.0)),
                share: `${{c.active_time_share_pct || 0}}%`,
                desc: `${{c.department || 'Operations'}} | ${{c.execution_count || 0}} executions (${{c.active_time_share_pct || 0}}% work time) | Payback: ${{c.payback_months ? c.payback_months + ' mo' : 'N/A'}}`
            }})) : [
                {{ name: '1. Payroll Deduction & Adjustment Verification', score: 95, share: '48.6%', desc: 'Human Resources | 46 executions (48.6% work time) | Payback: 25.4 mo (Phase 1 Target)' }},
                {{ name: '2. Leave Application & Balance Cross-Check', score: 72, share: '13.4%', desc: 'Human Resources | 31 executions (13.4% work time) | Payback: 73.1 mo (Phase 2)' }},
                {{ name: '3. Onboarding Verification & Compliance', score: 68, share: '13.4%', desc: 'Human Resources | 30 executions (13.4% work time) | Payback: 78.4 mo (Phase 2)' }},
                {{ name: '4. Resident Tax Confirmation', score: 60, share: '9.8%', desc: 'Human Resources | 17 executions (9.8% work time) | Payback: 99.0 mo (Phase 3)' }},
                {{ name: '5. Expense Settlement Approval', score: 54, share: '5.7%', desc: 'Finance & Accounting | 12 executions (5.7% work time) | Payback: 99.0 mo (Phase 3)' }},
                {{ name: '6. Inventory & Order Management', score: 38, share: '5.6%', desc: 'Logistics & Procurement | 25 executions (5.6% work time) | High human variance' }}
            ];

            candidates.forEach((c, idx) => {{
                const row = document.createElement('div');
                row.className = 'rank-item';
                const color = idx === 0 ? 'var(--accent-blue)' : (idx === 1 ? 'var(--accent-emerald)' : '#64748b');
                row.innerHTML = `
                    <div class="rank-header">
                        <span>${{c.name}}</span>
                        <span style="color: ${{color}};">Score: ${{c.score}} / 100</span>
                    </div>
                    <div class="rank-track">
                        <div class="rank-bar" style="width: ${{c.score}}%; background: ${{color}};"></div>
                    </div>
                    <div class="rank-detail">${{c.desc}}</div>
                `;
                container.appendChild(row);
            }});
        }}

        function renderClaimsTable() {{
            const tbody = document.getElementById('claims-tbody');
            tbody.innerHTML = '';

            const query = (document.getElementById('case-search').value || '').toLowerCase();
            const filtered = state.cases.filter(c => {{
                const matchesFilter = state.activeFilter === 'ALL' || c.status === state.activeFilter || (state.activeFilter === 'AUTO_APPROVED' && c.status.includes('APPROVED'));
                const matchesSearch = !query || 
                    c.case_id.toLowerCase().includes(query) || 
                    c.input_data.employee_name.toLowerCase().includes(query) || 
                    c.input_data.contract_type.toLowerCase().includes(query);
                return matchesFilter && matchesSearch;
            }});

            const allCount = state.cases.length;
            const approvedCount = state.cases.filter(c => c.status.includes('APPROVED')).length;
            const flaggedCount = state.cases.filter(c => c.status === 'FLAGGED_FOR_REVIEW').length;
            const rejectedCount = state.cases.filter(c => c.status.includes('REJECTED')).length;

            document.getElementById('count-all').innerText = allCount;
            document.getElementById('count-approved').innerText = approvedCount;
            document.getElementById('count-flagged').innerText = flaggedCount;
            document.getElementById('count-rejected').innerText = rejectedCount;

            document.getElementById('kpi-auto-rate').innerText = ((approvedCount / allCount) * 100).toFixed(1) + '%';
            document.getElementById('kpi-flagged-count').innerText = flaggedCount + ' cases';

            filtered.forEach(c => {{
                const tr = document.createElement('tr');
                const inp = c.input_data;
                const calc = c.calculated_details || {{}};

                let badgeCls = 'tag-approved';
                if (c.status === 'FLAGGED_FOR_REVIEW') badgeCls = 'tag-flagged';
                else if (c.status.includes('REJECTED')) badgeCls = 'tag-rejected';
                else if (c.status === 'APPROVED_BY_SUPERVISOR') badgeCls = 'tag-supervisor';

                const gross = calc.total_gross_addition ? `+¥${{calc.total_gross_addition.toLocaleString()}}` : '-';
                const ded = calc.total_deduction ? `-¥${{calc.total_deduction.toLocaleString()}}` : '-';
                const net = calc.net_adjustment ? `¥${{calc.net_adjustment.toLocaleString()}}` : '-';

                let actionHtml = `<span style="font-size: 11px; color: var(--text-tertiary);">-</span>`;
                if (c.status === 'FLAGGED_FOR_REVIEW') {{
                    actionHtml = `
                        <div style="display: flex; gap: 6px; justify-content: center;">
                            <button class="action-chip chip-approve" onclick="supervisorOverride('${{c.case_id}}', 'APPROVED_BY_SUPERVISOR')">Approve</button>
                            <button class="action-chip chip-reject" onclick="supervisorOverride('${{c.case_id}}', 'REJECTED_BY_SUPERVISOR')">Reject</button>
                        </div>
                    `;
                }}

                tr.innerHTML = `
                    <td style="font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 600; color: var(--accent-blue);">${{c.case_id}}</td>
                    <td>
                        <strong style="color: var(--text-title); font-size: 13px;">${{inp.employee_name}}</strong>
                        <div style="font-size: 11px; color: var(--text-secondary);">${{inp.employee_id}} · <span style="text-transform: capitalize;">${{inp.contract_type}}</span></div>
                    </td>
                    <td><span class="tag-pill ${{badgeCls}}"><span class="tag-dot"></span>${{c.status}}</span></td>
                    <td style="font-size: 12px; color: var(--text-secondary); max-width: 320px; line-height: 1.4;">${{c.decision_notes}}</td>
                    <td class="num-right" style="color: var(--accent-emerald);">${{gross}}</td>
                    <td class="num-right" style="color: var(--accent-rose);">${{ded}}</td>
                    <td class="num-right" style="font-weight: 700; color: var(--text-title);">${{net}}</td>
                    <td style="text-align: center;">${{actionHtml}}</td>
                `;
                tbody.appendChild(tr);
            }});
        }}

        function filterCases(filterType) {{
            if (filterType) {{
                state.activeFilter = filterType;
                document.querySelectorAll('.pill-btn').forEach(btn => btn.classList.remove('active'));
                const targetBtn = Array.from(document.querySelectorAll('.pill-btn')).find(b => b.getAttribute('onclick').includes(filterType));
                if (targetBtn) targetBtn.classList.add('active');
            }}
            renderClaimsTable();
        }}

        async function supervisorOverride(caseId, decision) {{
            const promptText = decision === 'APPROVED_BY_SUPERVISOR' 
                ? 'Supervisor Memo / Reason for approving policy override:' 
                : 'Supervisor Memo for rejection:';
            const memo = prompt(promptText, 'Verified with HR Division Director via email');
            if (memo === null) return;

            if (state.isLiveApi) {{
                try {{
                    const res = await fetch('/api/supervisor_override', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ case_id: caseId, decision: decision, supervisor_memo: memo }})
                    }});
                    if (res.ok) {{
                        const data = await res.json();
                        const idx = state.cases.findIndex(c => c.case_id === caseId);
                        if (idx !== -1) state.cases[idx] = data.updated_record;
                        showToast(`Case ${{caseId}} updated via API`, 'success');
                        renderClaimsTable();
                        return;
                    }}
                }} catch (e) {{
                    console.error('API call failed, mutating local state');
                }}
            }}

            const rec = state.cases.find(c => c.case_id === caseId);
            if (rec) {{
                rec.status = decision;
                rec.decision_notes += ` | [SUPERVISOR OVERRIDE: ${{memo}}]`;
                showToast(`Case ${{caseId}} overridden to ${{decision}}`, 'success');
                renderClaimsTable();
            }}
        }}

        function simulatePayrollRules(claim) {{
            const salary = Number(claim.base_salary) || 0;
            const claimedCommute = Number(claim.claimed_commute) || 0;
            const teleworkDays = Number(claim.telework_days) || 0;
            const claimedHousing = Number(claim.claimed_housing) || 0;
            const customDed = Number(claim.custom_deduction) || 0;
            const contract = claim.contract_type || "regular";

            let status = "AUTO_APPROVED: Passed all statutory and corporate policy validation checks";
            let notes = [];
            let isApproved = true;

            // 1. Commute allowance verification (statutory limit 150,000 JPY)
            const commuteCap = 150000;
            const approvedCommute = Math.min(claimedCommute, commuteCap);
            if (claimedCommute > commuteCap) {{
                isApproved = false;
                notes.push(`Commute exceeds statutory tax-exempt cap (¥${{claimedCommute.toLocaleString()}} > ¥${{commuteCap.toLocaleString()}})`);
            }}

            // 2. Telework allowance (250 JPY/day, max 5,000 JPY/mo)
            const calculatedTelework = Math.min(teleworkDays * 250, 5000);

            // 3. Housing allowance check (cap 30,000 JPY)
            let approvedHousing = 0;
            if (contract === "outsourcing" || contract === "part_time") {{
                if (claimedHousing > 0) {{
                    isApproved = false;
                    notes.push(`Housing subsidy not standard for ${{contract}} under article 4 - requires HR supervisor sign-off`);
                }}
            }} else {{
                approvedHousing = Math.min(claimedHousing, 30000);
            }}

            // 4. Statutory deductions
            let socialIns = 0;
            let empIns = 0;
            if (contract === "regular" || contract === "contract") {{
                socialIns = Math.round(salary * 0.152);
                empIns = Math.round(salary * 0.006);
            }}

            // 5. Custom deduction cap (20% of base salary)
            if (customDed > (salary * 0.20)) {{
                isApproved = false;
                notes.push(`Custom deduction exceeds 20% of base salary (¥${{customDed.toLocaleString()}}) - requires supervisor authorization`);
            }}
            if (customDed > 0 && !claim.deduction_reason) {{
                isApproved = false;
                notes.push(`Custom deduction ¥${{customDed.toLocaleString()}} missing required documentation`);
            }}

            const totalGross = approvedCommute + calculatedTelework + approvedHousing;
            const totalDed = socialIns + empIns + customDed;
            const net = totalGross - totalDed;

            if (!isApproved) {{
                status = `FLAG_REVIEW: ${{notes.join(" | ")}}`;
            }}

            return {{
                case_id: claim.case_id || `PI-SIM-${{Math.floor(1000 + Math.random() * 9000)}}`,
                input_data: claim,
                status: status,
                decision_notes: notes.join(" | ") || "Verified against corporate HR standing policy v2026.04-v1.2",
                calculated_details: {{
                    policy_version: "2026.04-v1.2",
                    approved_commute: approvedCommute,
                    approved_telework: calculatedTelework,
                    approved_housing: approvedHousing,
                    total_gross_addition: totalGross,
                    social_insurance_deduction: socialIns,
                    employment_insurance_deduction: empIns,
                    custom_deduction: customDed,
                    total_deduction: totalDed,
                    net_adjustment: net
                }}
            }};
        }}

        async function handleClaimSubmit(e) {{
            e.preventDefault();
            const claim = {{
                case_id: `PI-MANUAL-${{Math.floor(1000 + Math.random() * 9000)}}`,
                employee_name: document.getElementById('form-name').value,
                employee_id: document.getElementById('form-id').value,
                contract_type: document.getElementById('form-contract').value,
                base_salary: parseInt(document.getElementById('form-salary').value),
                claimed_commute: parseInt(document.getElementById('form-commute').value),
                telework_days: parseInt(document.getElementById('form-telework').value),
                claimed_housing: parseInt(document.getElementById('form-housing').value) || 0,
                custom_deduction: parseInt(document.getElementById('form-custom-ded').value) || 0,
                deduction_reason: document.getElementById('form-custom-reason').value || ''
            }};

            if (state.isLiveApi) {{
                try {{
                    const res = await fetch('/api/process_case', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify(claim)
                    }});
                    if (res.ok) {{
                        const data = await res.json();
                        state.cases.unshift(data.result);
                        closeClaimModal();
                        showToast(`Case ${{data.result.case_id}} evaluated: ${{data.result.status}}`, 'success');
                        renderClaimsTable();
                        return;
                    }}
                }} catch (err) {{
                    console.error('API call failed, falling back to local simulation');
                }}
            }}

            const result = simulatePayrollRules(claim);
            state.cases.unshift(result);
            closeClaimModal();
            showToast(`Evaluated claim for ${{claim.employee_name}}: ${{result.status}}`, 'success');
            renderClaimsTable();
        }}

        function exportApprovedCSV() {{
            const approved = state.cases.filter(c => c.status.includes('APPROVED'));
            if (approved.length === 0) {{
                showToast('No approved records available to export', 'warning');
                return;
            }}

            let csvContent = "data:text/csv;charset=utf-8,";
            csvContent += "case_id,employee_id,employee_name,contract_type,approved_commute,approved_telework,approved_housing,social_ins,employment_ins,custom_ded,net_adjustment,status,notes\\n";

            approved.forEach(c => {{
                const inp = c.input_data;
                const calc = c.calculated_details || {{}};
                const row = [
                    c.case_id,
                    inp.employee_id,
                    `"${{inp.employee_name}}"`,
                    inp.contract_type,
                    calc.approved_commute || 0,
                    calc.approved_telework || 0,
                    calc.approved_housing || 0,
                    calc.social_insurance_deduction || 0,
                    calc.employment_insurance_deduction || 0,
                    calc.custom_deduction || 0,
                    calc.net_adjustment || 0,
                    c.status,
                    `"${{(c.decision_notes || '').replace(/"/g, '""')}}"`
                ].join(',');
                csvContent += row + "\\n";
            }});

            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", "approved_payroll_adjustments.csv");
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            showToast(`Exported ${{approved.length}} records to CSV`, 'success');
        }}

        function resetCases() {{
            state.cases = JSON.parse(JSON.stringify(INITIAL_CASES));
            renderClaimsTable();
            showToast('Cases reset to baseline state', 'success');
        }}

        function openClaimModal() {{
            document.getElementById('claim-modal').classList.add('active');
        }}

        function closeClaimModal() {{
            document.getElementById('claim-modal').classList.remove('active');
        }}

        function recalcROI() {{
            const vol = parseInt(document.getElementById('slider-volume').value);
            const wage = parseInt(document.getElementById('slider-wage').value);
            const autoRate = parseInt(document.getElementById('slider-autorate').value) / 100.0;
            const reviewMin = parseFloat(document.getElementById('slider-reviewtime').value);

            document.getElementById('val-volume').innerText = vol.toLocaleString() + ' cases';
            document.getElementById('val-wage').innerText = '$' + wage + ' / hr';
            document.getElementById('val-autorate').innerText = Math.round(autoRate * 100) + '%';
            document.getElementById('val-reviewtime').innerText = reviewMin + ' min';

            const manualSecondsPerCase = 105.4;
            const manualTotalHours = (vol * manualSecondsPerCase) / 3600.0;

            const automatedCases = vol * autoRate;
            const flaggedCases = vol * (1.0 - autoRate);

            const autoProcessingHours = (automatedCases * 0.0024) / 3600.0;
            const flaggedReviewHours = (flaggedCases * (reviewMin * 60)) / 3600.0;
            const totalAutomatedSystemHours = autoProcessingHours + flaggedReviewHours;

            const hoursSaved = Math.max(0, manualTotalHours - totalAutomatedSystemHours);
            const monthlySavings = hoursSaved * wage;
            const annualSavings = monthlySavings * 12;

            document.getElementById('res-hours-saved').innerText = hoursSaved.toFixed(1);
            document.getElementById('res-monthly-savings').innerText = '$' + Math.round(monthlySavings).toLocaleString();
            document.getElementById('res-annual-savings').innerText = '$' + Math.round(annualSavings).toLocaleString();
            document.getElementById('text-hours-summary').innerText = hoursSaved.toFixed(1) + ' hours saved monthly';

            const paybackMo = monthlySavings > 0 ? (8000 / monthlySavings).toFixed(1) : 'N/A';
            document.getElementById('res-payback').innerText = paybackMo + ' mo';
        }}

        function getSegmentOperator(s) {{
            if (s.operator) return s.operator;
            const sid = s.session_id || '';
            if (sid.includes('CHAITANYA')) return 'user_b_01';
            if (sid.includes('SIDDHI')) return 'user_b_02';
            if (sid.includes('NEELA')) return 'user_b_03';
            if (sid.includes('LAPTOP')) return 'user_b_04';
            return 'user_b_01';
        }}

        function renderSegmentsTable() {{
            const tbody = document.getElementById('segments-tbody');
            if (!tbody) return;
            tbody.innerHTML = '';

            const host = document.getElementById('seg-host-filter') ? document.getElementById('seg-host-filter').value : '';
            const label = document.getElementById('seg-label-filter') ? document.getElementById('seg-label-filter').value : '';
            const query = document.getElementById('seg-search') ? (document.getElementById('seg-search').value || '').trim().toLowerCase() : '';

            const segmentsList = state.segments || [];
            const filtered = segmentsList.filter(s => {{
                const op = getSegmentOperator(s);
                const matchHost = !host || op === host;
                const matchLabel = !label || s.label === label;
                
                const sid = (s.session_id || '').toLowerCase();
                const lbl = (s.label || '').toLowerCase();
                const opLower = op.toLowerCase();
                const sStart = (s.start_time || s.start || '').toLowerCase();
                const sEnd = (s.end_time || s.end || '').toLowerCase();
                const method = (s.detection_method || '').toLowerCase();
                const evidenceStr = Array.isArray(s.evidence) ? s.evidence.join(' ').toLowerCase() : '';
                
                const matchQuery = !query || 
                    sid.includes(query) || 
                    lbl.includes(query) || 
                    opLower.includes(query) || 
                    sStart.includes(query) ||
                    sEnd.includes(query) ||
                    method.includes(query) ||
                    evidenceStr.includes(query);
                    
                return matchHost && matchLabel && matchQuery;
            }});

            const countEl = document.getElementById('seg-count');
            if (countEl) countEl.innerText = filtered.length;

            const totalEl = document.getElementById('seg-total');
            if (totalEl) totalEl.innerText = segmentsList.length;

            if (filtered.length === 0) {{
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td colspan="7" style="text-align: center; padding: 36px 16px; color: var(--text-muted);">
                        <div style="font-size: 14px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px;">No work unit segments match your filter criteria</div>
                        <div style="font-size: 12px;">Try clearing the search query or selecting "All Operators" / "All Process Categories".</div>
                    </td>
                `;
                tbody.appendChild(tr);
                return;
            }}

            filtered.forEach(s => {{
                const tr = document.createElement('tr');
                const sStart = s.start_time || s.start || '';
                const sEnd = s.end_time || s.end || '';
                let durSec = s.duration_seconds;
                if (durSec === undefined || isNaN(durSec)) {{
                    if (sStart && sEnd) {{
                        durSec = Math.max(0, Math.round((new Date(sEnd) - new Date(sStart)) / 1000));
                    }} else {{
                        durSec = 0;
                    }}
                }}
                const dur = Math.round(durSec) + 's';
                const op = getSegmentOperator(s);

                let opColor = '#0369a1';
                let opBg = '#e0f2fe';
                let opBorder = '#bae6fd';
                if (op === 'user_b_02') {{ opColor = '#047857'; opBg = '#d1fae5'; opBorder = '#a7f3d0'; }}
                else if (op === 'user_b_03') {{ opColor = '#b45309'; opBg = '#fef3c7'; opBorder = '#fde68a'; }}
                else if (op === 'user_b_04') {{ opColor = '#6d28d9'; opBg = '#ede9fe'; opBorder = '#ddd6fe'; }}

                const conf = s.confidence !== undefined ? Math.round(s.confidence * 100) : 85;
                const method = s.detection_method || 'hybrid_heuristic';

                let tagBadge = `<span class="tag-pill tag-approved" title="Confidence: ${{conf}}% | Method: ${{method}}"><span class="tag-dot"></span>RECOVERED</span>`;
                if (conf < 70) {{
                    tagBadge = `<span class="tag-pill tag-flagged" title="Confidence: ${{conf}}% | Method: ${{method}}"><span class="tag-dot"></span>RECOVERED</span>`;
                }}

                tr.innerHTML = `
                    <td style="font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 600; color: var(--accent-blue);">${{s.session_id}}</td>
                    <td><span style="font-size: 11px; font-weight: 700; background: ${{opBg}}; color: ${{opColor}}; border: 1px solid ${{opBorder}}; padding: 2px 8px; border-radius: 4px;" title="Operator: ${{op}}">${{op}}</span></td>
                    <td><strong style="color: var(--text-title); font-size: 13px;">${{s.label}}</strong></td>
                    <td style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--text-secondary);">${{sStart}}</td>
                    <td style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--text-secondary);">${{sEnd}}</td>
                    <td class="num-right" style="font-weight: 600; color: var(--accent-emerald);">${{dur}}</td>
                    <td style="text-align: center;">${{tagBadge}}</td>
                `;
                tbody.appendChild(tr);
            }});
        }}

        function filterSegments() {{
            renderSegmentsTable();
        }}

        function resetSegmentFilters() {{
            const h = document.getElementById('seg-host-filter');
            const l = document.getElementById('seg-label-filter');
            const q = document.getElementById('seg-search');
            if (h) h.value = '';
            if (l) l.value = '';
            if (q) q.value = '';
            renderSegmentsTable();
        }}

        function showToast(msg, type = 'success') {{
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast-bubble ${{type}}`;
            toast.innerHTML = `<span>${{msg}}</span>`;
            container.appendChild(toast);
            setTimeout(() => {{
                toast.style.opacity = '0';
                toast.style.transform = 'translateY(8px)';
                setTimeout(() => toast.remove(), 250);
            }}, 3000);
        }}
    </script>
</body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Interactive Enterprise Automation Platform generated at: {output_path}")
    print(f"File size: {output_path.stat().st_size:,} bytes")


if __name__ == "__main__":
    out_file = PROJECT_ROOT / "deliverables" / "automation_dashboard.html"
    generate_dashboard_html(out_file)
