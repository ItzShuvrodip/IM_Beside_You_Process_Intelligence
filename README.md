# Desktop Operation Log Mining & Workflow Automation Proposal

This repository delivers an enterprise-grade solution for recovering business process units of work from raw client telemetry, uncovering operational bottlenecks, and providing a shadow-mode decision-support assistant for payroll adjustment compliance.

---

## 📁 Repository Structure

```
d:/IMBY/
├── Datasets/                 # Operation log datasets
│   ├── README.md             # Original task specification
│   ├── DATA_SCHEMA.md        # Event schema documentation
│   ├── dataset_a/            # 63 benchmark sessions with Ground Truth (~162k events)
│   └── dataset_b/            # 15 unlabelled production sessions (~20k events)
├── deliverables/
│   ├── segments.jsonl        # Step 1 Output: 175 validated segments for Dataset B
│   └── automation_dashboard.html # Interactive executive visual audit dashboard
├── notebooks/
│   ├── 01_exploratory_data_analysis.ipynb          # Telemetry distributions & pause dynamics
│   ├── 02_work_unit_segmentation_modeling.ipynb     # Multi-signal hybrid segmentation & evaluation
│   └── 03_process_mining_and_roi_discovery.ipynb    # Process mining, dwell attribution & shadow engine
├── src/
│   ├── ingestion/            # Raw event stream ingestion & strongly-typed models
│   │   ├── models.py         # Event, Execution, and Segment data models with confidence
│   │   └── loader.py         # Chronological multi-chunk and manifest loader
│   ├── segmentation/         # Production hybrid segmenter & classification rules
│   │   ├── hybrid_segmenter.py # Anchor boundary detector & signal confidence engine
│   │   └── classifier.py     # Deterministic process classifier & unbiased fallback
│   ├── evaluation/           # Decoupled 1-to-1 matching evaluation
│   │   ├── evaluator.py      # Boundary F1, Segment IoU, Label Accuracy & Strict F1
│   │   └── audit_report.py   # Automated audit report generator
│   ├── analysis/             # Workload profiling, dwell attribution & ROI sensitivity
│   │   ├── workload.py       # Duration, frequency, and operator workload discovery
│   │   ├── process_mining.py # Directly-Follows Graph (DFG) & bottleneck analyzer
│   │   └── roi_model.py      # 3-tier financial scenario model (Conservative/Base/Optimistic)
│   ├── automation/           # Shadow-mode payroll decision support
│   │   ├── domain/           # Statutory payroll policy rules (v2026.04-v1.2, Decimal)
│   │   ├── service/          # Decision service workflow & FastAPI REST API
│   │   ├── adapters/         # Mock HR-system staging interface
│   │   ├── demo_runner.py    # Sample batch CLI demonstrator
│   │   └── generate_dashboard.py # Single-page visual HTML dashboard generator
│   └── audit/                # Compliance & governance
│       └── audit_logger.py   # Immutable JSONL audit trail & override logger
├── scripts/
│   ├── run_segmentation.py   # Generates & verifies deliverables/segments.jsonl
│   ├── run_analysis.py       # Computes Step 2 workload tables & ROI ranking
│   ├── run_benchmark.py      # Runs decoupled benchmark evaluation on Dataset A (63 sessions)
│   └── run_server.py         # Launches FastAPI server & serves interactive dashboard
├── tests/                    # 29 passing unit & evidence integrity tests
├── REPORT.md                 # Senior Executive Report (Strategy, Shadow Mode, Financial Model)
├── WORK_LOG.md               # Engineering Work Log & Design Decisions
└── README.md                 # Project reproduction and operational guide
```

---

## 🚀 Quickstart & Reproduction Guide

### 1. Run Automated Test Suite (29/29 Passing)
```bash
python -m pytest tests/ -v
```
*Validates data loaders, hybrid segmentation, 1-to-1 decoupled evaluation, dwell attribution, financial ROI modeling, versioned payroll policy checks, and FastAPI server endpoints (100% pass rate).*

### 2. Run Step 1 Production Segmentation (Dataset B)
```bash
python scripts/run_segmentation.py
```
*Processes all 15 production sessions in Dataset B, outputs 175 validated work unit segments to `deliverables/segments.jsonl` (mean confidence: 0.84), and validates schema compliance.*

### 3. Run Step 2 Operational Workload & Financial ROI Analysis
```bash
python scripts/run_analysis.py
```
*Extracts process execution statistics, calculates segment-joined application dwell friction, and evaluates candidate processes against 3-tier financial sensitivity scenarios.*

### 4. Benchmark Segmentation on Dataset A (63 Sessions)
```bash
python scripts/run_benchmark.py
```
*Computes decoupled 1-to-1 metrics across 63 ground-truth sessions: Boundary Macro F1 (58.1%), Segment IoU (58.7%), and Process Label Accuracy (18.5%).*

### 5. Launch the Interactive Enterprise Decision Platform
```bash
python scripts/run_server.py
```
*Launches the Uvicorn ASGI server on `http://127.0.0.1:8000/`, exposes live REST APIs (`/api/overview`, `/api/cases`, `/api/process_case`, `/api/supervisor_override`, `/api/export_erp_csv`), and opens the visual dashboard.*

### 6. Explore Jupyter Notebooks
Open `notebooks/` in your Jupyter environment:
- `01_exploratory_data_analysis.ipynb` (Telemetry volume, pause distributions, and GT taxonomy)
- `02_work_unit_segmentation_modeling.ipynb` (Hybrid boundary detection, confidence scores, and Dataset A/B segmentation)
- `03_process_mining_and_roi_discovery.ipynb` (DFG graphs, dwell-time attribution, financial ROI models, and shadow-mode payroll demo)

---

## 📊 Summary of Operational Findings

- **Selected Candidate:** `payroll_deduction_adjustment` (Payroll Items & Deduction Adjustments)
- **Workload Share:** **48.6%** of total active operational time in Dataset B (59.9 minutes across 46 work units; mean signal confidence: **0.89**).
- **Dwell Attribution:** Segment-joined analysis isolates **14.8 minutes** of active Word dwell reading `gyomu_itaku_kyuuyo_kitei.docx` (contractor compensation guidelines) inside payroll intervals, separating it from pooled desktop background activity.
- **Financial Business Case (Base Scenario):** With loaded labor at ¥3,500/hr, build cost of ¥1.4M, and annual maintenance of ¥140K/yr, automating payroll verification yields **25.4 months payback** and **+41.4% net 3-year ROI** at 9,600 cases/year.
- **System Architecture:** Deployed as a **Shadow-Mode Decision Assistant** that recommends, explains statutory basis, logs immutable audit records, and routes non-standard exceptions to human supervisors.

For the comprehensive executive proposal and roadmap, see **[REPORT.md](REPORT.md)**.  
For the daily engineering decisions and empirical logs, see **[WORK_LOG.md](WORK_LOG.md)**.
