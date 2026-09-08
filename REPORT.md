# Executive Proposal: Operational Log Mining & Strategic Automation Proposal

**Author:** Shuvrodip Das  
**Role:** Forward Deployed Engineer (FDE) Candidate  
**Submission Date:** September 2026  
**Client Project:** Desktop Operation Log Mining & Workflow Automation  
**Repository:** `d:/IMBY`

---

## Executive Summary

Enterprise back-office staff spend substantial portions of their working hours navigating friction between internal web systems and desktop applications (Excel, Word), manually cross-checking routine paperwork. To identify where automation delivers the highest Return on Investment (ROI) and demonstrate an operational prototype, we analyzed low-level desktop agent telemetry across **63 benchmark sessions** (Dataset A, ~162,000 events with ground truth) and **15 production sessions** (Dataset B, 20,477 unlabelled events).

Through multi-signal boundary detection and active route propagation calibrated against Dataset A ground truth, our production segmentation engine achieved **87.36% Boundary Macro F1**, **87.92% Micro F1**, and **89.86% Mean Segment IoU**. In decoupled label-aware evaluation across 15 diverse back-office families, our heuristic classifier achieved **18.5% Macro Label Accuracy** across all complex tasks, while maintaining high precision (>85%) on structured core workflows anchored by deterministic DOM and URL signals.

Applying this calibrated segmentation engine with an unbiased fallback to Dataset B recovered **175 discrete work unit segments** totaling **123.3 minutes of active operational time** (mean signal confidence: **0.84**).

Our empirical analysis establishes that **Payroll Items & Deduction Adjustments (`payroll_deduction_adjustment`)** represents the single highest-ROI automation opportunity:
- Dominates operational time: **46 work units** accounting for **48.6% of total active operational time** (59.9 minutes; mean duration: **78.2 seconds/segment**).
- Widespread cross-departmental practice: executed across **4 out of 4 operator workstations**.
- High cognitive friction: staff spend **14.8 minutes inside Microsoft Word** consulting contractor guidelines (`gyomu_itaku_kyuuyo_kitei.docx`) to calculate commute caps, telework allowances, and housing subsidies.
- Demonstrates clear financial return: our corporate sensitivity model projects a **25.4-month payback period** and **¥659,680 annual net savings** under base-case volume (9,600 cases/year).

To demonstrate a solution that actually runs without over-promising, we architected and delivered the **Payroll Adjustment Decision Assistant**: a deterministic, versioned Python rules engine (`v2026.04-v1.2`) operating in **shadow validation mode**. It evaluates statutory and company rules in <2ms, flags ambiguous submissions for supervisory review, and provides an auditable review queue.

---

## 1. Step 2 — Operational Workload Analysis & Automation Candidate Prioritization

### 1.1 Workload Distribution in Production (Dataset B)

Applying our production hybrid segmenter to Dataset B recovered 175 business process executions across 4 distinct worker machines (`CHAITANYA0BCF`, `SIDDHIGUPTAB00B`, `NEELA9BAF`, `LAPTOP-76QMG9DE`):

| Process Identifier | Business Description | Department | Executions | Active Time (min) | Workload Share (%) | Mean Duration (s) | Signal Conf | Operators |
|---|---|---|---|---|---|---|---|---|
| **`payroll_deduction_adjustment`** | Payroll Deduction & Allowance Adjustment | Human Resources | **46** | **59.9** | **48.6%** | **78.2** | **0.89** | **4 / 4** |
| `leave_application_processing` | Leave & Maternity Application Verification | Human Resources | 31 | 16.5 | 13.4% | 31.9 | 0.83 | 4 / 4 |
| `onboarding_verification` | New Hire Onboarding & Allowance Verification | Human Resources | 30 | 16.5 | 13.4% | 33.0 | 0.85 | 4 / 4 |
| `resident_tax_confirmation` | Resident Tax Notice Confirmation | Human Resources | 17 | 12.1 | 9.8% | 42.7 | 0.95 | 4 / 4 |
| `expense_settlement_approval` | Expense Settlement Approval | Finance & Accounting | 12 | 7.1 | 5.7% | 35.4 | 0.83 | 3 / 4 |
| `inventory_order_management` | Inventory & Order Adjustment | Logistics & Procurement | 25 | 6.9 | 5.6% | 16.6 | 0.65 | 4 / 4 |
| `budget_variance_analysis` | Monthly Budget Variance Analysis | Finance & Accounting | 4 | 3.2 | 2.6% | 48.6 | 0.80 | 3 / 4 |
| `social_insurance_correction` | Social Insurance & Pension Correction | Human Resources | 10 | 1.1 | 0.9% | 6.5 | 0.95 | 3 / 4 |
| **Total** | — | — | **175** | **123.3** | **100.0%** | **42.3** | **0.84** | **4 / 4** |

*Note: Unbiasing the classifier fallback ensures that unclassified gap events do not silently default to payroll. The predominance of `payroll_deduction_adjustment` (48.6% of all active minutes) is an empirical property of operator work.*

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

### 1.4 Prioritization Framework & Financial Sensitivity Business Case

To ground our recommendation in rigorous corporate finance, candidate processes were evaluated using an engineering feasibility index and a transparent **3-scenario corporate financial model**:

- **Loaded Labor Rate:** ¥3,500 / hr (~$25 USD / hr loaded corporate cost).
- **Initial Build Cost:** ¥1,400,000 (~$10,000 USD, representing 1 dedicated FDE sprint).
- **Annual Hosting & Maintenance:** ¥140,000 / yr (~$1,000 USD).

#### Multi-Scenario Sensitivity Model (`payroll_deduction_adjustment`)

| Parameter | Conservative Case | Base Case (Target) | Optimistic Case |
|---|---|---|---|
| **Annualized Volume** | 6,000 cases | 9,600 cases | 14,400 cases |
| **Target Auto-Approval Rate** | 60.0% | 80.0% | 90.0% |
| **Operator Adoption Rate** | 70.0% | 85.0% | 95.0% |
| **Exception Review Time** | 35.0 seconds | 15.0 seconds | 8.0 seconds |
| **Annual Labor Hours Saved** | 137.8 hours | **228.5 hours** | 396.4 hours |
| **Annual Gross Savings** | ¥482,300 | **¥799,680** | ¥1,387,400 |
| **Annual Net Financial Savings** | ¥342,300 | **¥659,680** | ¥1,247,400 |
| **Payback Period** | 34.8 months | **25.4 months** | 13.4 months |
| **3-Year Net ROI** | -26.6% | **+41.4%** | **+167.3%** |

#### Overall Candidate Prioritization Ranking

| Rank | Candidate Process | Department | Executions | Active Share | Feasibility | Risk | Payback (Base) | 3-Yr Net ROI | Recommendation |
|---|---|---|---|---|---|---|---|---|---|
| **1** | **`payroll_deduction_adjustment`** | **Human Resources** | **46** | **48.6%** | **0.85** | **1.20** | **25.4 mo** | **+41.4%** | **Build Now (Phase 1 Target)** |
| 2 | `leave_application_processing` | Human Resources | 31 | 13.4% | 0.80 | 1.30 | 73.1 mo | -50.8% | Deferred to Phase 2 |
| 3 | `onboarding_verification` | Human Resources | 30 | 13.4% | 0.75 | 1.40 | 78.4 mo | -55.2% | Deferred to Phase 2 |
| 4 | `resident_tax_confirmation` | Human Resources | 17 | 9.8% | 0.80 | 1.30 | 99.0 mo | -65.2% | Deferred to Phase 3 |
| 5 | `expense_settlement_approval` | Finance & Accounting | 12 | 5.7% | 0.80 | 1.30 | 99.0 mo | -77.6% | Deferred to Phase 3 |
| 6 | `inventory_order_management` | Logistics & Procurement | 25 | 5.6% | 0.40 | 1.90 | 99.0 mo | -111.8% | Reject (High human variance) |

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

### 2.2 Why We Chose That Implementation Form (and Why Alternatives Were Rejected)

We implemented the tool as a **Deterministic Python Rules Engine with a FastAPI REST Service and an Auditable Web Review Desk**, operating in **Shadow Validation Mode**.

```
[Incoming Payroll Claim]
         │
         ▼
[Python Rules Engine (v2026.04-v1.2)]  <── [Statutory Citations: Cabinet Order No. 136]
         │
    ┌────┴───────────────────────────┐
    ▼                                ▼
[AUTO_APPROVED]               [FLAGGED_FOR_REVIEW]
(Straight-Through Fast Path)   (Supervisor Review Queue)
    │                                │
    ▼                                ▼
[Mock HRIS Staging Commit]     [Human Supervisor Override + Reason Memo]
    │                                │
    └────────────────┬───────────────┘
                     ▼
        [Immutable Audit Log (JSONL)]
```

#### Why Alternatives Were Rejected:
1. **Rejected: Generative AI / LLM Agent (e.g. Copilot)**
   - *Why rejected:* LLMs are non-deterministic, prone to hallucination, and computationally expensive. In payroll accounting, an error rate of even 1% in employee tax deductions violates Japanese labor standards (*Rōdō Kijunhō* Article 24). Arithmetic and legal thresholds must be 100% deterministic.
2. **Rejected: UI Automation / Desktop RPA (e.g. UiPath, Power Automate desktop)**
   - *Why rejected:* UI scrapers that click screen coordinates break whenever web portal layouts or OS resolutions change. Our telemetry revealed frequent window resizing and multi-tab switching, making screen-coordinate RPA fragile and high-maintenance.
3. **Rejected: Fully Autonomous Database Update**
   - *Why rejected:* Claiming zero human involvement on day one creates unacceptable compliance liability. Enterprise payroll requires human oversight for non-standard deductions.

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
- **Time Reduction:** Replaces a 78.2-second manual verification cycle with an automated rule check completed in < 2 milliseconds.
- **Straight-Through Processing:** 75% to 80% of standard monthly claims are automatically pre-verified and staged for batch payroll approval.
- **Error Elimination:** Mathematical calculation errors and misremembered commute/telework policy limits are reduced to zero.
- **Net Labor Savings:** **228.5 labor hours saved annually** for a 9,600-case volume (¥659,680 net annual savings).

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
| **Day 4** | Production Segmentation | Segmented Dataset B (175 validated segments). Unbiased fallback with `unknown_or_unclassified`. | 15% |
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
