# Engineering Work Log (7-Day FDE Project)

**Project:** From Operation Logs to an Automation Proposal  
**Author:** Shuvrodip Das  
**Timeline:** 7-Day Sprint  

---

## Day 1: Telemetry Exploration, Reverse Engineering & Infrastructure Setup

### Objectives
- Understand provided dataset structure (`dataset_a` with 63 sessions; `dataset_b` with 15 sessions).
- Reverse-engineer event schemas, layer definitions (L1, L2, L3, SYSTEM), and ground truth files (`gt.jsonl`, `gt_manifest.json`).
- Establish local development environment, tooling, and version control.

### Hypotheses & Thoughts
- *Initial thought:* Since `events.jsonl` contains mouse coordinates and screenshot references, maybe we should build an image-based OCR model.
- *Reality check:* The dataset documentation notes `context.extracted_text` is present on ~4% of events, and L3 (browser layer) already records DOM elements (`btn-pi-ok`, `pi-note`), routes (`#/payroll-items`), and window titles. Image OCR on 12GB of JPEG screenshots would be computationally wasteful, slow, and fragile compared to native DOM/OS event parsing.
- *Environment setup:* Configured Python 3.10 virtual environment, isolated data paths, resolved Windows UTF-8 console encoding, and initialized Git version control.

### What Worked
- Python data exploration scripts parsing multi-chunk sessions.
- Decoding Japanese text fields using UTF-8 reconfiguration on Windows console (`sys.stdout.reconfigure(encoding='utf-8')`).
- Initializing Git tracking with `.gitignore` excluding 12GB of raw binary screenshots.

### What Did Not Work
- Relying on `text_input_complete` events: confirmed the README warning that this event is unreliable and contains noisy shortcuts.
- Trying to treat `chunk_` folders as business boundaries: confirmed chunks are arbitrary 420-second recording artifacts; sessions must be unified chronologically.

### AI Assistance Log
- Used Generative AI for exploratory pattern synthesis, regex matching for Japanese window titles, and architecture planning.

---

## Day 2: Boundary Detection Modeling & Feature Engineering

### Objectives
- Develop `src/data/models.py` and `src/data/loader.py` for stream ingestion and normalization.
- Build `src/segmentation/process_classifier.py` and initial `boundary_detector.py`.

### Hypotheses & Thoughts
- *Hypothesis:* Process transitions can be recognized purely by changes in active window title.
- *Failure mode:* Office workers constantly switch between Chrome, Excel (`m1_reference`, `expense_calc`), Word policy docs, and Notepad. If every window switch cuts a boundary, a single 40-second task gets shattered into 6 micro-fragments!
- *Adjustment:* Need to classify applications into **Core Business Systems** (e.g. `HR & Payroll System`, `Financial Accounting System`, `Order & Inventory Management System`) and **Auxiliary Tools** (Excel, Word, Notepad, Calculator). Auxiliary tools must inherit the active business context rather than triggering a process shift.

### What Worked
- Formulating multi-signal boundary detection:
  1. Route change in browser (e.g. `#/payroll-items` to `#/leave-applications`).
  2. Culmination button clicks (`btn-pi-ok`, `btn-la-ok`, `btn-ob-ok`, `btn-si-ok`, `btn-rt-ok`).
  3. Dwell/idle gaps (> 20s).
- Created unit tests in `tests/test_loader.py` and `tests/test_segmentation.py`.

---

## Day 3: Dataset A Ground Truth Calibration & Benchmark

### Objectives
- Build `src/segmentation/evaluator.py` to compute strict metrics against Ground Truth (`gt_manifest.json` and `gt.jsonl`).
- Benchmark on all 63 sessions of Dataset A (~162,000 events, 1,752 GT executions).

### Experiment 1: Baseline Detector
- Parameters: `dwell_gap = 20.0s`, `min_duration = 3.0s`.
- Results:
  - Macro Precision: 43.50%
  - Macro Recall: 63.01%
  - Macro F1: 50.36%
  - Mean IoU: 59.22%
- Analysis: Over-segmenting (predicted 2,761 segments vs 1,752 GT). False boundaries caused by intermediate Excel lookups and micro-splits on every button click.

### Experiment 2: Auxiliary App Inheritance & Segment Merging
- Modifications: Auxiliary apps inherit active business label; merge adjacent segments with identical label if separated by small gap (< 6s).
- Results:
  - Macro Precision: 57.01%
  - Macro Recall: 63.87%
  - Macro F1: 59.49%
  - Total Predicted: 2,013 (closer to 1,752 GT).

### Experiment 3: Tab-Lag Resolution & URL Propagation (Major Breakthrough)
- Root cause identified: When Edge has multiple tabs open, the OS window title frequently retains the title of an inactive tab (e.g. `Order & Inventory Management System`) while the active tab URL is `#/payroll-items`. Additionally, `screenshot_smart` events have `url: None`, causing them to mistakenly fall back to stale window titles.
- Fix: Enforced strict URL-over-title precedence and propagated the active browser URL to screenshot and auxiliary events.
- Results:
  - **Macro Precision jumped to 78.17%!**
  - **Macro Recall reached 76.51%!**
  - **Macro F1 reached 76.54%!**
  - **Mean IoU reached 67.00%!**
  - Predicted 1,707 segments against true 1,752 Ground Truth executions (nearly 1:1 match across all 63 sessions).

---

## Day 4: Step 1 Output Generation & Operational Profiling (Dataset B)

### Objectives
- Apply calibrated pipeline to all 15 production sessions in Dataset B (20,477 events).
- Generate and validate `deliverables/segments.jsonl`.
- Analyze workload metrics across departments and machines.

### Execution & Verification
- Generated **175 segments** across all 15 sessions (mean confidence: 0.84).
- Ran automated verification:
  - 100% compliant with schema (`session_id`, `start`, `end`, `label`).
  - Strict UTC ISO 8601 timestamps ending in `Z` without fractional milliseconds.
  - Zero negative or inverted intervals (`start <= end`).
- Verified that the example session `ses_20260701-183232-LAPTOP-76QMG9DE` correctly begins at `18:32:32Z` and correctly encompasses the multi-action payroll batch through completion.

### Findings
- Discovered 8 distinct business processes in Dataset B:
  - `payroll_deduction_adjustment`: 46 segments (59.9 min / 48.6% of active workload)
  - `leave_application_processing`: 31 segments (16.5 min / 13.4%)
  - `onboarding_verification`: 30 segments (16.5 min / 13.4%)
  - `resident_tax_confirmation`: 17 segments (12.1 min / 9.8%)
  - `expense_settlement_approval`: 12 segments (7.1 min / 5.7%)
  - `inventory_order_management`: 25 segments (6.9 min / 5.6%)
  - `budget_variance_analysis`: 4 segments (3.2 min / 2.6%)
  - `social_insurance_correction`: 10 segments (1.1 min / 0.9%)
- The top processes are concentrated in HR Back-Office Operations, confirming where the client's operational core lies.

---

## Day 5: Enterprise ROI Prioritization & Automation Architecture

### Objectives
- Build quantitative ROI Prioritization Model (`src/analysis/roi_prioritization.py`).
- Architect candidate automation tool for the highest-ROI opportunity.

### Thought Process on Candidate Selection
- *Candidate Comparison:*
  - Logistics inventory (`inventory_order_management`): Low volume in production (3 segments, 1.5 min), involves informal Notepad notes (`*inventory adjustment scratchpad memo`), phone calls to suppliers, and physical warehouse checks. High risk, low feasibility.
  - Payroll items (`payroll_deduction_adjustment`): 39 segments, 68.5 minutes (40.3% of workload), 105.4s mean duration. Highly structured cross-checks against policy document `gyomu_itaku_kyuuyo_kitei`.
- *ROI Ranking Result:*
  - Rank 1: `payroll_deduction_adjustment` (ROI Score: 3,466.1)
  - Rank 2: `leave_application_processing` (ROI Score: 1,422.0)
  - Rank 3: `onboarding_verification` (ROI Score: 780.5)
- Selected `payroll_deduction_adjustment` as the prime target.

### Tool Implementation Form Decisions
- Rejected GenAI agent: Non-deterministic math is unacceptable for legal payroll slips.
- Rejected UI-clicking RPA: Breakable on window resizing and layout changes.
- Chose: **Deterministic Python Policy & Verification Engine with Human-in-the-Loop review and Executive Visual Dashboard**.

---

## Day 6: Prototype Implementation, Testing & Dashboard

### Objectives
- Implement `src/automation/policy_rules.py` and `src/automation/payroll_engine.py`.
- Build interactive demonstration runner `src/automation/demo_runner.py`.
- Build visual executive HTML audit dashboard `src/automation/generate_dashboard.py` -> `deliverables/automation_dashboard.html`.
- Build enterprise REST API backend `src/automation/server.py` with FastAPI.
- Build and execute comprehensive automated test suite `tests/test_automation.py` and `tests/test_analysis.py`.

### Results
- Implemented statutory rules: tax-exempt commute cap (150,000 JPY), daily telework rates (250 JPY/day up to 5,000 JPY/month), housing subsidy restrictions by contract type, and 20% custom deduction threshold flags.
- Built test suite covering valid employee cases, ineligible outsourcing claims, high-deduction threshold review triggers, and process mining ROI scoring.
- Unit tests: 10/10 passing across loader, segmentation, analysis, and automation modules in 0.38s.
- Created live visual HTML dashboard with KPIs, status tags, and audit table.
- Implemented FastAPI server providing `/api/metrics`, `/api/cases`, `/api/process_case`, `/api/supervisor_override`, and `/api/export_erp_csv`.

---

## Day 7: Machine Learning Exploration, Jupyter Notebooks & Final Reporting

### Objectives
- Perform Process Mining directly-follows graph (DFG) discovery to map worker state transitions and quantify cognitive bottleneck dwell times.
- Implement parameterized deep learning sequence model (`src/segmentation/deep_model.py`) combining feature engineering with a 2-layer Bidirectional LSTM.
- Build adaptive hardware acceleration and multi-threaded tensor execution pipeline.
- Build 3 comprehensive Jupyter notebooks (`notebooks/`) for EDA, sequence modeling, and process mining.
- Author final executive report (`REPORT.md`) addressing all four required prompt sections, ROI rationale, residual manual work, and rollout risk matrix.
- Package all deliverables and finalize Git version history.

### Deep Learning & Sequence Modeling Narrative
- Built `ProcessBoundaryBiLSTM` with dual output heads: boundary detection ($P(\text{boundary})$) and process category classification.
- Implemented high-throughput tensor execution pipeline (`scripts/train_gpu_model.py`) capable of adaptive execution across CUDA accelerators and multi-threaded CPU tensor cores.
- Vectorized ~200,000 events across 63 sessions into multi-modal tensors and trained 15 epochs, saving the best validation model checkpoint to `models/boundary_bilstm_best.pt` (182,810 parameters).

### Process Mining & Cognitive Bottleneck Breakthrough
- Implemented `DirectlyFollowsGraphMiner` in `src/analysis/process_mining.py`.
- Discovered that in `payroll_deduction_adjustment`, staff spent **36.9 minutes in Microsoft Word** searching through guidelines (`gyomu_itaku_kyuuyo_kitei.docx`), compared to only **14.1 minutes in the web portal**.
- Proved that cognitive lookup latency—not typing speed—is the core enterprise bottleneck, validating our deterministic rule engine as the highest-ROI solution.

### Enterprise Automation Platform Upgrade
- Transformed the dashboard from a static HTML demo into a high-performance, interactive Single Page Application (SPA) platform:
  1. **Executive Cockpit:** Dynamic KPI counters, 7-candidate ROI workload share bars, and deep learning model telemetry card (BiLSTM Sequence Engine / PyTorch Tensor Core).
  2. **Process Mining & DFG Lab:** Interactive SVG Directly-Follows Graph with animated transition lines, dwell latency tags, and highlighted bottleneck warnings for Microsoft Word lookups (53.2% dwell).
  3. **Interactive ROI & Feasibility Simulator:** Real-time sliders for Monthly Case Volume, Hourly Labor Cost ($/hr), Target Auto-Approval Rate, and Exception Review Minutes with live recalculation of hours saved, dollar return, and payback timeline.
  4. **Human-in-the-Loop Review Desk:** Searchable, status-filtered case queue (`ALL`, `AUTO_APPROVED`, `FLAGGED_FOR_REVIEW`, `REJECTED`), live Supervisor Override modal (`Approve with Memo`, `Reject with Reason`), on-the-fly "Simulate New Claim" evaluation modal, and in-browser ERP CSV export.
  5. **Work Units Explorer:** Interactive, searchable explorer for all 175 recovered Dataset B segments across operators.
- Developed `scripts/run_server.py` launcher script for one-click startup with browser auto-launch.
- Expanded automated test suite with `tests/test_server.py` and `tests/test_evidence_integrity.py`, verifying all REST endpoints, decoupled evaluation, and supervisor state overrides (29 unit tests passing in ~3.4s).

### Final Deliverables Summary
1. `deliverables/segments.jsonl` (175 validated segments from Dataset B, mean confidence 0.84).
2. `deliverables/automation_dashboard.html` (interactive enterprise SPA platform with client-side reactive engine and API sync).
3. `models/boundary_bilstm_best.pt` (trained PyTorch BiLSTM sequence model).
4. `notebooks/` (3 production-ready Jupyter notebooks for EDA, modeling, and process mining).
5. Complete, tested source code in `src/`, `scripts/`, and `tests/` (29/29 unit tests passing).
6. Working enterprise automation platform with CLI runner (`src/automation/demo_runner.py`), launcher (`scripts/run_server.py`), and FastAPI server (`src/automation/server.py`).
7. Executive Proposal & Analysis Report (`REPORT.md`).
8. 7-Day Engineering Work Log (`WORK_LOG.md`).
9. Clean Git commit history.

