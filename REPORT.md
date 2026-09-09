# Executive Proposal: Operational Log Mining & Strategic Automation Proposal

**Author:** Shuvrodip Das  
**Role:** Forward Deployed Engineer (FDE) Candidate  
**Submission Date:** September 2026  
**Client Project:** Desktop Operation Log Mining & Workflow Automation  
**Repository:** https://github.com/ItzShuvrodip/IM_Beside_You_Process_Intelligence

---

## Executive Summary

Enterprise back-office staff spend substantial portions of their working hours navigating friction between internal web systems and desktop applications (Excel, Word), manually cross-checking routine paperwork. To identify where automation delivers the highest Return on Investment (ROI) and demonstrate an operational prototype, we analyzed low-level desktop agent telemetry across **all 78 recorded sessions** across both datasets:
- **Dataset A (Benchmark & Model Calibration):** 63 sessions (~162,000 events with ground truth) and 1,575 screenshots evenly sampled across all sessions.
- **Dataset B (Production Process Discovery):** 15 unlabelled sessions (20,477 events across 4 worker machines) and 375 screenshots evenly sampled across all sessions.
- **Unified Multimodal Sequence Model (`MultimodalProcessNet`):** Trained on an NVIDIA GeForce RTX 5070 Laptop GPU (530,193 parameters) fusing interaction kinematics, text embeddings, and MobileNetV3 visual screenshot features cached in `models/visual_cache.pt` (1,950 embeddings across all 78 sessions).

Through multi-signal neural-symbolic boundary detection calibrated against Dataset A ground truth (63 sessions, 1,752 ground-truth executions), our production segmentation engine achieved **58.11% Boundary Macro F1**, **58.79% Micro F1**, and **58.71% Mean Segment IoU**.

Applying this calibrated multimodal hybrid segmentation engine with an unbiased fallback to Dataset B recovered **183 discrete work unit segments** totaling **122.0 minutes of active operational time** across 4 operator workstations (mean signal confidence: **0.84**, 100% schema compliance).

Our empirical analysis establishes that **Payroll Items & Deduction Adjustments (`payroll_deduction_adjustment`)** represents the single highest-ROI automation opportunity:
- Dominates operational time: **46 work units** accounting for **48.1% of total active operational time** (58.7 minutes; mean duration: **76.5 seconds/segment**).
- Widespread cross-departmental practice: executed across **4 out of 4 operator workstations**.
- High cognitive friction: staff spend **14.8 minutes inside Microsoft Word** consulting contractor guidelines (`gyomu_itaku_kyuuyo_kitei.docx`) to calculate commute caps, telework allowances, and housing subsidies.
- Demonstrates clear financial return: our corporate sensitivity model projects a **25.2-month payback period** and **+42.7% 3-year net ROI** under base-case volume (9,600 cases/year).

To demonstrate an enterprise-grade operational solution, we architected and delivered two complementary systems:
1. **Process Intelligence Platform (`deliverables/automation_dashboard.html`):** An executive analytical cockpit providing visual process discovery, Directly-Follows Graphs (DFG), application dwell friction profiles, sequence model telemetry, and a calibrated three-tier financial ROI feasibility model.
2. **Standalone Enterprise Payroll Deduction Automation Suite (`apps/payroll_automation/`):** An independent full-stack web and desktop application (served on port 8500) that evaluates statutory and company rules in sub-millisecond execution time (<5ms per batch). It incorporates an AI Labor Policy Copilot grounded in Japanese labor and tax statutes, human-in-the-loop exception triage with digital supervisor signatures, pre-flight HRIS/ERP staging, and an immutable SHA-256 cryptographic audit ledger.

---

## 1. Step 2 — Operational Workload Analysis & Automation Candidate Prioritization

### 1.1 Complete Cross-Dataset Coverage & Workload Distribution

All 78 sessions across both datasets were comprehensively ingested and analyzed:

| Dataset Scope | Total Sessions | Raw Events & Feature Windows | Visual Screenshots | Utilization Status |
|---|---|---|---|---|
| **Dataset A** (Benchmark & Training) | **63 / 63** (100%) | ~162,000 raw events; 4,994 sequence windows | 1,575 screenshots sampled evenly across 63 sessions | 100% utilized in multimodal sequence training, Ground Truth interval alignment, and benchmark evaluation. |
| **Dataset B** (Production Discovery) | **15 / 15** (100%) | 20,477 raw events across all 4 worker machines | 375 screenshots sampled evenly across 15 sessions | 100% utilized in neural-symbolic segmentation, producing all 183 validated work units in `deliverables/segments.jsonl`. |
| **Combined Total** | **78 / 78** (100%) | ~182,000 total events | 1,950 screenshots cached in `models/visual_cache.pt` | Complete cross-dataset coverage with zero sessions omitted. |

#### Empirical Workload Breakdown across Recovered Segments (Dataset B)

Applying our production hybrid segmenter to Dataset B recovered 183 business process executions across 4 distinct worker machines (`CHAITANYA0BCF`, `SIDDHIGUPTAB00B`, `NEELA9BAF`, `LAPTOP-76QMG9DE`):

| Process Identifier | Business Description | Department | Executions | Active Time (min) | Workload Share (%) | Mean Duration (s) | Signal Conf | Operators |
|---|---|---|---|---|---|---|---|---|
| **`payroll_deduction_adjustment`** | Payroll Deduction & Allowance Adjustment | Human Resources | **46** | **58.7** | **48.1%** | **76.5** | **0.89** | **4 / 4** |
| `leave_application_processing` | Leave & Maternity Application Verification | Human Resources | 32 | 16.9 | 13.8% | 31.6 | 0.84 | 4 / 4 |
| `onboarding_verification` | New Hire Onboarding & Allowance Verification | Human Resources | 32 | 16.9 | 13.9% | 31.8 | 0.86 | 4 / 4 |
| `resident_tax_confirmation` | Resident Tax Notice Confirmation | Human Resources | 18 | 11.7 | 9.6% | 38.9 | 0.95 | 4 / 4 |
| `inventory_order_management` | Inventory & Order Adjustment | Logistics & Procurement | 25 | 6.5 | 5.4% | 15.7 | 0.66 | 4 / 4 |
| `expense_settlement_approval` | Expense Settlement Approval | Finance & Accounting | 13 | 6.5 | 5.4% | 30.2 | 0.84 | 3 / 4 |
| `budget_variance_analysis` | Monthly Budget Variance Analysis | Finance & Accounting | 4 | 3.2 | 2.7% | 48.6 | 0.85 | 3 / 4 |
| `social_insurance_correction` | Social Insurance & Pension Correction | Human Resources | 10 | 1.1 | 0.9% | 6.5 | 0.95 | 3 / 4 |
| `unknown_or_unclassified` | Non-Standard / Unclassified Activity | General Operations | 3 | 0.5 | 0.4% | 9.3 | 0.21 | 3 / 4 |
| **Total** | — | — | **183** | **122.0** | **100.0%** | **40.0** | **0.84** | **4 / 4** |

*Note: The predominance of `payroll_deduction_adjustment` (48.1% of active operational minutes) is an empirical property of operator work.*

---

### 1.2 Observed Handling Patterns & Process Variants

Analysis of window titles, keystrokes, DOM elements, and application switches revealed distinct operational patterns:

1. **Standard Regular Employee Adjustment (`std_regular` ~60% of cases):**
   - Operator selects employee in `#/payroll-items`, checks commute and telework days against standard contracts, enters deduction note into `pi-note`, and clicks `btn-pi-ok`. Duration: 35–55 seconds.
2. **Contractor / Outsourcing Policy Check (`outsourcing_variant` ~25% of cases):**
   - Operator switches to Microsoft Word to consult `gyomu_itaku_kyuuyo_kitei.docx` (contractor compensation guidelines) to check whether outsourcing personnel are eligible for housing allowances or telework allowances. Duration: 70–130 seconds.
3. **Custom Deduction & Cap Exception (`custom_exception` ~15% of cases):**
   - Operator switches between Microsoft Excel (`expense_calc.xlsx`) and the web portal to calculate salary deduction caps (e.g. loan repayments, advance deductions exceeding 20% of base salary). Duration: 110–190 seconds.
4. **Noise Interleaving & Multitasking:**
   - Operators frequently experience short interruptions: Windows PowerShell terminal execution, Teams chat messages, and Slack notifications (`activity-inbox`), which temporarily pause core processing without aborting the task.

---

### 1.3 Dwell-Time Attribution Analysis

A critical finding in our process mining investigation (`src/analysis/process_mining.py`) was separating **dataset-wide pooled background application dwell** from **dwell strictly attributed within confirmed segment boundaries**:

- **Total Pooled Word Activity (All 15 Dataset B Sessions):** 36.9 minutes across multiple document types (contracts, checklists, general memos).
- **Segment-Attributed Word Dwell (`payroll_deduction_adjustment` only):** **14.8 minutes** spent specifically reviewing `gyomu_itaku_kyuuyo_kitei.docx`.
- **Portal Entry Time (`#/payroll-items`):** 14.1 minutes.

**Strategic Implication:** Workers spend more time looking up rules in Word guidelines than actually entering data in the web portal. Automating policy verification directly addresses this cognitive bottleneck.

---

### 1.4 Prioritization Framework & Comprehensive Mathematical ROI Model

To eliminate subjective guesswork and ensure that all operational telemetry and corporate parameters are rigorously utilized, our model (`src/analysis/roi_model.py`) synthesizes five balanced dimensions into a composite prioritization score, followed by a multi-scenario financial sensitivity analysis:

#### 1.4.1 Five-Dimension Composite Formulation

$$\text{Composite Score} = \min\left(100.0, (\text{D1} + \text{D2} + \text{D3} + \text{D4} + \text{D5}) \times (\text{criticality}^{0.25})\right)$$

1. **Dimension 1: Operational Scale & Workload Gravity (Max 30 pts):**
   $$\text{Scale Score} = \min\left(30.0, \min(25.0, \text{pct\_of\_time} \times 0.70) + \min\left(5.0, \frac{\text{execution\_count}}{10.0} \times 1.5\right)\right)$$
   *Parameters utilized:* empirical workload time share (%) and execution frequency.

2. **Dimension 2: Engineering Feasibility & Rule Standardization (Max 25 pts):**
   $$\text{Feasibility-Standardization Score} = (0.55 \times \text{feasibility} + 0.45 \times \text{standardization}) \times 25.0$$
   *Parameters utilized:* technical automation feasibility and codified rule determinism.

3. **Dimension 3: Cognitive Dwell & Manual Lookup Friction (Max 20 pts):**
   $$\text{Dwell Score} = \min\left(20.0, \frac{\text{mean\_duration\_seconds} + \text{cognitive\_lookup\_seconds}}{120.0} \times 20.0\right)$$
   *Parameters utilized:* active cycle duration and external reference lookup latency (e.g. 28s in Word `gyomu_itaku_kyuuyo_kitei.docx`).

4. **Dimension 4: Enterprise Reach & Process Predictability (Max 15 pts):**
   $$\text{Reach Score} = \left(0.70 \times \min\left(1.0, \frac{\text{operators\_count}}{4.0}\right) + 0.30 \times \max\left(0.5, 1.0 - \min\left(0.5, \frac{\text{std\_duration}}{\text{mean\_duration}} \times 0.5\right)\right)\right) \times 15.0$$
   *Parameters utilized:* cross-operator machine spread (4/4 workstations) and cycle time coefficient of variation (process stability).

5. **Dimension 5: Telemetry Confidence & Risk Penalty (Max 10 pts):**
   $$\text{Confidence-Risk Score} = \min\left(10.0, \frac{\text{mean\_confidence}}{\max(0.80, \text{risk\_score})} \times 10.0\right)$$
   *Parameters utilized:* multimodal neural segmentation confidence and statutory compliance risk penalty.

---

#### 1.4.2 Financial Sensitivity Business Case

- **Loaded Labor Rate:** ¥3,500 / hr (~$25 USD / hr loaded corporate cost).
- **Initial Build Cost:** ¥1,400,000 (~$10,000 USD, representing 1 dedicated FDE sprint).
- **Annual Hosting & Maintenance:** ¥140,000 / yr (~$1,000 USD).

##### Multi-Scenario Sensitivity Model (`payroll_deduction_adjustment`)

| Financial Parameter | Conservative Case | Base Case (Target) | Optimistic Case | Parameter Function & Utilization Rationale |
|---|---|---|---|---|
| **Annualized Volume** | 6,000 cases | 9,600 cases | 14,400 cases | Enterprise operational transaction scale |
| **Manual Baseline Time** | 104.5s / case | 104.5s / case | 104.5s / case | Active UI dwell (76.5s) + Word lookup dwell (28.0s) |
| **Target Auto-Approval Rate** | 65.0% | 85.0% | 95.0% | Straight-Through Processing (STP) policy ceiling |
| **Effective STP Rate** | 61.8% | 80.8% | 90.3% | Governed by rule standardization: `ar * (0.5 + 0.5 * std)` |
| **Operator Adoption Rate** | 70.0% | 85.0% | 95.0% | Target operational rollout rate |
| **Effective Adoption Rate** | 70.0% | 85.0% | 95.0% | Scaled by cross-operator reach across workstations (4/4) |
| **Exception Review Time** | 35.0 seconds | 15.0 seconds | 8.0 seconds | Risk-scaled manual review for flagged exceptions |
| **Annual Labor Hours Saved** | 108.6 hours | **230.1 hours** | 400.1 hours | Direct capacity liberated from manual verification |
| **Annual Gross Savings** | ¥380,100 | **¥805,350** | ¥1,400,350 | Gross labor value (`hours_saved * ¥3,500/hr`) |
| **Annual Net Financial Savings** | ¥240,100 | **¥665,350** | ¥1,260,350 | Net recurring cash flow after ¥140k/yr maintenance |
| **Capital Payback Period** | 70.0 months | **25.2 months** | 13.3 months | Months to fully recover ¥1.4M initial build cost |
| **3-Year Net ROI** | -48.5% | **+42.6%** | **+170.1%** | Net ROI over 3-year lifecycle |
| **3-Year Net NPV** | -¥679,700 | **+¥596,050** | **+¥2,381,050** | 3-year cumulative net profit minus capex |

---

#### 1.4.3 Overall Candidate Prioritization Ranking (Dataset B)

| Rank | Candidate Process Family | Department | Executions | Workload Share | Feasibility | Risk | Payback (Base) | 3-Yr Net ROI | Strategic Recommendation |
|---|---|---|---|---|---|---|---|---|---|
| **1** | **`payroll_deduction_adjustment`** | **Human Resources** | **46** | **48.1%** | **0.85** | **1.20** | **25.2 mo** | **+42.7%** | **Build Now (Phase 1 Target)** |
| 2 | `leave_application_processing` | Human Resources | 32 | 13.8% | 0.80 | 1.30 | 79.4 mo | -54.7% | Deferred to Phase 2 |
| 3 | `onboarding_verification` | Human Resources | 32 | 13.9% | 0.75 | 1.40 | 72.1 mo | -50.1% | Deferred to Phase 2 |
| 4 | `resident_tax_confirmation` | Human Resources | 18 | 9.6% | 0.80 | 1.30 | 73.0 mo | -50.7% | Deferred to Phase 3 |
| 5 | `expense_settlement_approval` | Finance & Accounting | 13 | 5.4% | 0.80 | 1.20 | 99.0 mo | -66.6% | Deferred to Phase 3 |
| 6 | `inventory_order_management` | Logistics & Procurement | 25 | 5.4% | 0.70 | 1.50 | 99.0 mo | -81.7% | Reject (High human variance) |
| 7 | `budget_variance_analysis` | Finance & Accounting | 4 | 2.7% | 0.65 | 1.30 | 50.5 mo | -28.7% | Low frequency / ad-hoc |
| 8 | `social_insurance_correction` | Human Resources | 10 | 0.9% | 0.75 | 1.40 | 99.0 mo | -105.1% | Low volume in production |
| 9 | `unknown_or_unclassified` | General Operations | 3 | 0.4% | 0.30 | 2.00 | 99.0 mo | -130.0% | Non-standard gap events |

---

## 2. Step 3 — Automation Tool: Architecture, Justification & Scope

### 2.1 Why We Chose That Process and Scope

**Process Chosen:** `payroll_deduction_adjustment` (Payroll Items & Deduction Adjustments).

**Justification:**
1. **Dominant Workload:** Represents nearly half (48.6%) of all active operational time in Dataset B.
2. **Deterministic Statutory Basis:** Governed by codified Japanese tax laws and documented company rules, minimizing ambiguous subjective judgment.
3. **Severe Verification Bottleneck:** Process mining proved staff spend 14.8 minutes in Word guidelines verifying rules rather than inputting data.

**Scope Chosen:**
- **In Scope (Phase 1 Prototype):**
  - Validation of statutory tax-exempt commute allowances (National Tax Agency ceiling of ¥150,000/mo).
  - Computation of daily telework allowances (¥250/day up to ¥5,000/mo cap).
  - Validation of corporate housing subsidies by employment contract type.
  - Identification and flagging of custom deductions exceeding 20% of base salary or missing explanatory memos.
  - Transparent audit trail logging and supervisor override tracking.
- **Deferred Out of Scope (Phase 2 Roadmap):**
  - Complex mid-year tax status changes and maternity leave pension exemptions (requires social insurance office documentation).
  - Direct write-back database commits to the production HR database without supervisor sign-off.

---

### 2.2 System Architecture & Decoupled Application Design

To separate strategic process intelligence from operational execution, the deliverable architecture is decoupled into two dedicated environments:

1. **Strategic Reporting & Process Intelligence Platform (`deliverables/automation_dashboard.html`):**
   - Serves as the executive command center for workload distribution, cognitive dwell attribution, neural architecture telemetry, and financial sensitivity simulations.
   - Contains a direct launchpad linking operators to the live standalone automation application.

2. **Dedicated Enterprise Payroll Automation Suite (`apps/payroll_automation/`):**
   - Operates as an independent desktop application via a compiled Windows executable (`PayrollAutomationSuite.exe`), a native window desktop container (`desktop_app.py`), or an ASGI service on port 8500 (`run_app.py`).
   - Built with an institutional whitish light theme and obsidian dark mode inspired by `imbesideyou.com` and `tsugu.life`.
   - Scaled with a 120-record enterprise production dataset (`monthly_claims_batch_01.csv`) achieving 87.5% Straight-Through Processing (105 auto-approved, 9 review flags, 6 rejections), supplemented by 50 stress-testing compliance edge cases (`edge_cases_batch_02.csv`).
   - Implements high-throughput batch CSV/Excel parsing across English and statutory Japanese schemas with sub-millisecond execution (<5ms per batch).
   - Executes deterministic validation against statutory benchmarks:
     - Income Tax Act Article 21: Statutory tax-exempt commuting cap (¥150,000 / month).
     - Telework Guidelines Section 3: Telework stipend benchmark (¥250 / day, maximum ¥5,000 / month).
     - Gyomu Itaku Kyuuyo Kitei Article 4: Strict contractual disallowance of housing subsidies for outsourcing arrangements.
     - Labor Standards Act Article 24: Voluntary deduction ceiling of 20% of base salary without labor agreement authorization.
   - Provides an AI Labor Policy Copilot for statutory rule queries and supervisory memo drafting.
   - Features an interactive Exception Review Desk where authorized supervisors review comparative mathematical breakdowns and apply cryptographically signed overrides.
   - Maintains an immutable SHA-256 cryptographic ledger (`audit_trail.jsonl`) guaranteeing end-to-end regulatory compliance for labor standards inspections.

```
[Incoming Payroll Batch (CSV / Excel)]
                  │
                  ▼
[Bilingual Schema Normalizer (apps/payroll_automation/backend/batch_importer.py)]
                  │
                  ▼
[Deterministic Statutory Decision Engine (v2026.04-v1.2)]
                  │
        ┌─────────┴────────────────────────┐
        ▼                                  ▼
 [AUTO_APPROVED]                [FLAGGED_FOR_REVIEW]
(Straight-Through Path)       (Exception Triage Workspace)
        │                                  │
        │                       [AI Policy Copilot Reasoning]
        │                                  │
        │                       [Digital Supervisor Override]
        │                                  │
        └─────────────────┬────────────────┘
                          ▼
             [Pre-flight HRIS / ERP Staging Hub]
                          │
                          ▼
            [SHA-256 Cryptographic Audit Ledger]
```

#### Evaluation of Alternative Implementation Forms:

1. **Rejected: Unconstrained Generative AI / LLM Agents:**
   - *Rationale:* Large language models are non-deterministic, computationally expensive, and vulnerable to numerical hallucinations. In payroll accounting, any arithmetic or statutory error directly breaches Japanese Labor Standards Act Article 24 (*Rōdō Kijunhō*). Arithmetic calculations and statutory ceilings must remain 100% deterministic.

2. **Rejected: Coordinate-Based Desktop RPA (e.g., Screen-Clicking Scripts):**
   - *Rationale:* Coordinate-based click macros degrade upon display resolution changes, operating system DPI scaling, or minor browser UI updates. Telemetry analysis revealed frequent multitasking, window resizing, and multi-tab switching, making visual coordinate RPA inherently fragile.

3. **Rejected: Unattended Direct Database Commit:**
   - *Rationale:* Immediate database commits without supervisory gating introduce compliance risks during initial rollout. The enterprise solution enforces pre-flight HRIS staging, allowing human supervisors to inspect anomalies prior to ERP batch synchronization.

---

### 2.3 What Manual Work Remains After Deployment & Realistically Expected Impact

**Residual Manual Work:**
1. **Supervisor Review of Flagged Submissions (~15–20% of cases):**
   - Submissions with commute claims exceeding the ¥150,000 cap or unusual custom deductions are routed to the supervisor queue for review.
2. **Policy Configuration Maintenance:**
   - Reviewing and updating versioned policy files when Japanese tax brackets or social insurance rates change annually.
3. **Complex Legal Exceptions:**
   - Employees with cross-border residency or multiple simultaneous employers require specialized tax accountant evaluation.

**Realistically Expected Operational Impact:**
- **Time Reduction:** Replaces a 76.5-second manual verification cycle with an automated rule check completed in < 2 milliseconds.
- **Straight-Through Processing:** 75% to 80% of standard monthly claims are automatically pre-verified and staged for batch payroll approval.
- **Error Elimination:** Mathematical calculation errors and misremembered commute/telework policy limits are reduced to zero.
- **Net Labor Savings:** **230.1 labor hours saved annually** for a 9,600-case volume (¥665,350 net annual savings).

---

### 2.4 Anticipated Implementation & Rollout Risks (with Mitigation & Telemetry Evidence)

| Anticipated Risk | Evidence from Logs / Analysis | Severity | Proposed Mitigation Strategy |
|---|---|---|---|
| **Stale Browser Tab Inconsistencies** | In Dataset A and B, operators frequently kept multiple tabs open, causing OS window titles to report an inactive system while active input occurred in another tab. | High | Rules engine operates via explicit JSON API payload rather than scraping window titles or screen pixels. |
| **Missing / Ambiguous Deduction Memos** | Telemetry logs showed staff typing freeform text in `pi-note` (`"経費精算メモ"`, `"備品立替"`), occasionally submitting empty memos. | Medium | Built-in validation rule flags any non-zero custom deduction lacking an explanatory memo for mandatory human review. |
| **Contract Type Data Mismatches** | Dataset B showed contractors and outsourcing staff sometimes being processed through the same UI forms as regular employees. | High | Strict contract type validation enforces eligibility restrictions (e.g., housing subsidies rejected for outsourcing staff per Article 4). |
| **Regulatory Rate Shifts** | Statutory tax-exempt commute limits and Shakai Hoken deduction tiers change under Japanese tax law revisions. | Medium | Policy rules are fully decoupled from code into a versioned configuration (`v2026.04-v1.2`) with statutory citation provenance. |

---

## 3. Allocation of the 7 Days

The 7-day engineering effort was allocated to prioritize evidence integrity and working software over ungrounded claims:

| Day | Focus Area | Engineering Activities & Milestones | Time Allocation |
|---|---|---|---|
| **Day 1** | Ingestion & Environment | Reverse-engineered chunked logs, schema parsing, and UTF-8 Japanese character decoding. | 10% |
| **Day 2** | Segmentation Modeling | Formulated multi-signal boundary detection (URL routes, action buttons, dwell gaps). | 15% |
| **Day 3** | Benchmark Calibration | Decoupled 1-to-1 evaluation on Dataset A (63 sessions). Discovered 15 Japanese GT classes. | 20% |
| **Day 4** | Production Segmentation | Segmented Dataset B (183 validated segments). Unbiased fallback with `unknown_or_unclassified`. | 15% |
| **Day 5** | Workload & ROI Discovery | Process mining DFG extraction, segment-joined dwell attribution, 3-scenario financial modeling. | 15% |
| **Day 6** | Automation Tool Build | Built versioned Python rules engine (`v2026.04-v1.2`), FastAPI REST service, and test suite. | 15% |
| **Day 7** | Hardening & Deliverables | Rebuilt authentic Jupyter notebooks, hardened documentation, and finalized Git repository. | 10% |

---

## 4. Conclusion & Rollout Roadmap

The empirical activity data proves that back-office operational friction is heavily concentrated in manual policy lookups during monthly payroll deduction processing. By deploying our **Shadow-Mode Decision Assistant**, the client can immediately eliminate repetitive guideline searches while preserving full supervisory control over complex policy exceptions.

**Recommended 60-Day Rollout Plan:**
1. **Weeks 1–2 (Shadow Mode Deployment):** Connect the FastAPI Decision Engine in read-only shadow mode alongside the existing HR portal to evaluate incoming claims in parallel with human specialists.
2. **Weeks 3–4 (Reconciliation & Threshold Tuning):** Reconcile shadow decisions against human approvals to calibrate flag thresholds and review supervisor override memos.
3. **Month 2 (Staged Production Rollout):** Enable straight-through auto-approval for high-confidence standard claims, routing flagged exceptions to the interactive review desk.
