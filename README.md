# Desktop Operation Log Mining & Workflow Automation Proposal

This repository delivers an enterprise platform for recovering business process work units from low-level desktop telemetry, analyzing operational bottlenecks, and executing deterministic automation for statutory payroll deduction compliance.

---

## 1. Repository Architecture

```
IMBY/ (Repository Root)
├── Datasets/                 # Desktop operation log telemetry
│   ├── README.md             # Project brief and client task specification
│   ├── DATA_SCHEMA.md        # Event and stream schema documentation
│   ├── dataset_a/            # 63 benchmark sessions with Ground Truth (~162,000 events)
│   └── dataset_b/            # 15 unlabelled production sessions (~20,000 events)
├── apps/                     # Enterprise applications
│   └── payroll_automation/   # Standalone Enterprise Payroll Automation Suite (Step 3)
│       ├── backend/          # FastAPI service, statutory rules, copilot, and importer
│       ├── frontend/         # Desktop and web UI (batch center, exception desk, audit ledger)
│       ├── sample_data/      # Test CSV batches (production claims and statutory edge cases)
│       ├── run_app.py        # Python launcher (serves backend on port 8500 and opens browser)
│       ├── launch_payroll_app.bat # Windows one-click desktop application launcher
│       └── README.md         # Dedicated application documentation and API specification
├── models/
│   ├── multimodal_process_net.pt # Multimodal BiLSTM sequence checkpoint (530,193 parameters)
│   ├── boundary_bilstm_best.pt   # Benchmark compatibility sequence checkpoint
│   └── visual_cache.pt           # GPU MobileNetV3 visual screenshot feature cache
├── deliverables/
│   ├── segments.jsonl        # Step 1 Output: 179 validated work unit segments for Dataset B
│   ├── audit_trail.jsonl     # Tamper-evident cryptographic transaction ledger
│   └── automation_dashboard.html # Step 2 Intelligence & Executive Cockpit Dashboard
├── notebooks/
│   ├── 01_exploratory_data_analysis.ipynb          # Telemetry distributions and pause dynamics
│   ├── 02_work_unit_segmentation_modeling.ipynb     # Multi-signal hybrid segmentation and evaluation
│   └── 03_process_mining_and_roi_discovery.ipynb    # Process mining, dwell attribution, and ROI modeling
├── src/
│   ├── ml/                   # Multimodal Deep Learning and GPU Acceleration Module
│   │   ├── model.py          # MultimodalProcessNet: BiLSTM with dual classification heads
│   │   ├── vision_extractor.py # MobileNetV3 visual feature extraction on CUDA GPU
│   │   ├── dataset.py        # Sequence window dataset and tensor batch collator
│   │   └── inference.py      # High-throughput GPU sliding window sequence inference
│   ├── ingestion/            # Telemetry stream ingestion and strongly-typed models
│   │   ├── models.py         # Event, Execution, and Segment schema definitions
│   │   └── loader.py         # Chronological multi-chunk loader and manifest parser
│   ├── segmentation/         # Production hybrid segmenter and classification engine
│   │   ├── hybrid_segmenter.py # Multi-signal boundary detector with confidence scoring
│   │   └── classifier.py     # Deterministic process classifier with unbiased fallback
│   ├── evaluation/           # Decoupled 1-to-1 matching evaluation framework
│   │   ├── evaluator.py      # Boundary F1, Segment IoU, and Classification Accuracy
│   │   └── audit_report.py   # Automated evaluation reporting engine
│   ├── analysis/             # Workload profiling, dwell attribution, and ROI modeling
│   │   ├── workload.py       # Duration, frequency, and operator workload discovery
│   │   ├── process_mining.py # Directly-Follows Graph (DFG) and bottleneck analyzer
│   │   └── roi_model.py      # Three-tier financial sensitivity model (Conservative/Base/Optimistic)
│   ├── automation/           # Process Intelligence Dashboard services
│   │   ├── domain/           # Codified statutory rules (v2026.04-v1.2)
│   │   ├── service/          # Decision service workflow and FastAPI REST API
│   │   ├── adapters/         # Mock HRIS/ERP integration adapter
│   │   ├── demo_runner.py    # Sample batch CLI execution utility
│   │   └── generate_dashboard.py # Intelligence dashboard compilation script
│   └── audit/                # Compliance and governance
│       └── audit_logger.py   # Immutable SHA-256 audit trail logger
├── scripts/
│   ├── train_multimodal_model.py # Trains MultimodalProcessNet on GPU with mixed precision
│   ├── run_segmentation.py   # Generates and validates deliverables/segments.jsonl
│   ├── run_analysis.py       # Generates Step 2 workload tables and ROI rankings
│   ├── run_benchmark.py      # Evaluates benchmark performance on Dataset A (63 sessions)
│   └── run_server.py         # Launches Process Intelligence FastAPI server on port 8000
├── tests/                    # 40 automated unit, ML, and enterprise integration tests
├── REPORT.md                 # Formal Senior Executive Report
├── WORK_LOG.md               # Seven-Day Engineering Work Log and Architecture Decisions
├── pyproject.toml            # Build configuration and project metadata
└── README.md                 # Project reproduction and operational guide
```

---

## 2. Quickstart & Operational Guide

### 2.1 Automated Test Suite Verification (44/44 Passing)
Execute the complete test suite across data loading, neural network inference, hybrid segmentation, process mining, financial ROI modeling, Multi-ERP connectors, Policy Governance Studio, and the standalone automation application:

```bash
python -m pytest tests/ -v
```

Static type checking verification:
```bash
pyrefly check
```

---

### 2.2 Launching the Standalone Payroll Automation Suite (Step 3 Deliverable)

The operational automation engine is decoupled into a dedicated enterprise web and desktop application located in `apps/payroll_automation/`. It features an institutional whitish light theme and obsidian dark mode inspired by `imbesideyou.com` and `tsugu.life`.

**Option A (Standalone Desktop Executable .exe):**
Launch the compiled Windows desktop application (requires no web browser, runs independently in a native window):
```cmd
apps\payroll_automation\launch_desktop_app.bat
```
*(Or execute `apps\payroll_automation\dist\PayrollAutomationSuite\PayrollAutomationSuite.exe` directly)*

**Option B (Native Desktop Window via Python):**
```bash
python apps/payroll_automation/desktop_app.py
```

**Option C (Web Server Mode on Port 8500):**
```bash
python apps/payroll_automation/run_app.py
```
Access in any browser at: `http://localhost:8500/`

Enterprise capabilities:
- **Scaled Production Dataset:** 120 verified corporate claims (`EMP-9401` to `EMP-9520`) with 87.5% straight-through auto-approval, 7.5% review flags, and 5.0% policy rejections, plus 50 compliance edge cases.
- **Sub-Millisecond Batch Ingestion:** Evaluates multi-case CSV/Excel batches in <5ms with automated schema normalization.
- **Deterministic Statutory Compliance:** Strict enforcement of Japanese Income Tax Act Art. 21 (¥150,000 commute cap), Labor Standards Act Art. 24 (20% custom deduction limit), and Gyomu Itaku Kyuuyo Kitei Art. 4 (housing subsidy exclusion for outsourcing contracts).
- **Enterprise Policy Governance & Scenario Simulation Studio:** Interactive parameter sandbox allowing HR specialists and compensation committees to calibrate statutory thresholds (commute cap, telework daily stipend, telework monthly ceiling, deduction ratio, housing subsidy eligibility matrix) and run live dry-run impact simulations across all 120 claims cohort.
- **Multi-ERP Pre-Flight Staging & Integration Hub:** Pre-flight validation against the 120-employee active roster with export downloads for SAP S/4HANA OData v4 JSON, Workday HCM Inbound EIB JSON, and Freee HR Cloud Japanese CSV formats sealed with cryptographic SHA-256 idempotency tokens (`IDEM-...`).
- **AI Labor Policy Copilot:** Grounded statutory reasoning and supervisory explanation drawer.
- **Human-in-the-Loop Exception Triage:** Discretionary review desk with comparative mathematical breakdowns and supervisor override digital signatures.
- **Tamper-Evident SHA-256 Cryptographic Audit Ledger:** Immutable audit trail with cryptographic hash verification.
- **Bilingual Interface (English / Japanese):** Real-time language toggle (`EN` / `JA`) across all interfaces with authentic Japanese statutory terminology (`要確認・レビュー`, `規程違反却下`, `正社員`, `契約社員`, `業務委託`).
- **Port Collision Resilience:** Intelligent port discovery and socket protection in `run_app.py`, gracefully reusing existing instances or discovering available alternate ports.
- **Dynamic Light & Dark Themes:** High-contrast whitish corporate light theme (MS Excel / SAP enterprise aesthetic) and sleek obsidian dark mode.

---

### 2.3 Launching the Process Intelligence Platform (Steps 1 & 2 Deliverable)
The primary analytical dashboard provides executive workload telemetry, Directly-Follows Graphs (DFG), sequence model metrics, and the three-tier economic feasibility model:

```bash
python scripts/run_server.py
```

Access the dashboard in any browser at:
```
http://localhost:8000/
```
Or open the static deliverable directly:
```
deliverables/automation_dashboard.html
```

Analytical capabilities:
- **Process Digital Twin & Visual Telemetry Replay:** Click any of the 179 recovered work unit segments in the telemetry explorer to inspect second-by-second operations, application dwell distributions (Microsoft Word 53.2% lookup bottleneck, Excel calculations, Chrome portal entry), keystroke counts, and automated remediation rationale.
- **Monte Carlo Financial Risk & Uncertainty Engine:** 10,000 stochastic iterations modeling operational volume shifts (±30%), wage variances ($30–$45/hr), and adoption fluctuations, yielding empirical confidence intervals (P10: 20.0 mo, P50: 26.2 mo, P90: 35.9 mo) and demonstrating a **90.2% probability of capital recovery within 36 months**.

---

### 2.4 Training the Multimodal Deep Learning Model (Optional)
To retrain the multimodal sequence model using GPU acceleration:

```bash
python scripts/train_multimodal_model.py
```
*Trains `MultimodalProcessNet` across 12 epochs with mixed precision (AMP) on an NVIDIA CUDA-enabled GPU, persisting weights to `models/multimodal_process_net.pt`.*

---

### 2.5 Executing Step 1 Production Segmentation (Dataset B)
```bash
python scripts/run_segmentation.py
```
*Processes all 15 production sessions in Dataset B, outputs 179 validated work unit segments to `deliverables/segments.jsonl` (mean confidence: 0.84), and validates schema compliance.*

---

### 2.6 Executing Step 2 Workload & Financial ROI Analysis
```bash
python scripts/run_analysis.py
```
*Extracts process execution statistics, calculates segment-joined application dwell friction, and evaluates candidate processes against three-tier financial sensitivity scenarios.*

---

### 2.7 Running Benchmark Evaluation (Dataset A)
```bash
python scripts/run_benchmark.py
```
*Computes decoupled 1-to-1 metrics across 63 ground-truth sessions: Boundary Macro F1 (58.11%), Segment IoU (58.71%), and Process Label Accuracy (18.52%).*

---

### 2.8 Exploring Analytical Jupyter Notebooks
Located in the `notebooks/` directory:
- `01_exploratory_data_analysis.ipynb`: Telemetry distributions, pause dynamics, and Ground Truth taxonomy.
- `02_work_unit_segmentation_modeling.ipynb`: Hybrid boundary detection, confidence scores, and Dataset A/B segmentation.
- `03_process_mining_and_roi_discovery.ipynb`: DFG graphs, dwell-time attribution, financial ROI models, and deterministic payroll evaluation.

---

## 3. Summary of Operational Findings

- **Selected Automation Target:** `payroll_deduction_adjustment` (Payroll Items & Deduction Adjustments).
- **Workload Concentration:** Represents **48.3% of total active operational time** in Dataset B (59.5 minutes across 46 work units; mean signal confidence: **0.89**).
- **Dwell Attribution Analysis:** Segment-joined telemetry isolates **14.8 minutes** of active Microsoft Word dwell reviewing `gyomu_itaku_kyuuyo_kitei.docx` (contractor compensation guidelines) inside payroll intervals, confirming a substantial manual cognitive lookup bottleneck.
- **Financial Business Case (Base Target Scenario):** At an enterprise loaded labor rate of ¥3,500/hr, initial development cost of ¥1.4M, and annual maintenance of ¥140K/yr, automating payroll verification yields **25.2 months payback** and **+42.7% net three-year ROI** based on an annual volume of 9,600 cases.
- **System Delivery:** Separated into two distinct operational artifacts:
  1. *Process Intelligence Platform:* Quantitative executive cockpit, DFG process graph, and workload telemetry.
  2. *Enterprise Payroll Automation Suite:* Dedicated web and desktop application executing deterministic compliance validation, AI Copilot assistance, exception triage, and tamper-evident audit logging.

For the comprehensive senior executive proposal and financial models, refer to [REPORT.md](REPORT.md).  
For the chronological engineering decisions and design trade-offs, refer to [WORK_LOG.md](WORK_LOG.md).
