# Enterprise Payroll Deduction Automation Suite

Standalone End-to-End Enterprise Automation Tool for Japanese Payroll Deduction Adjustments  
Dedicated High-Performance Web & Desktop Application

---

## 1. Executive Overview

In the operational process mining analysis of desktop telemetry, **`payroll_deduction_adjustment`** was established as the primary operational bottleneck:
- **Baseline Manual Execution Duration:** 182 seconds per case under manual verification.
- **Statutory Risk Profile:** Commuter tax-exempt threshold breaches and contractually prohibited housing subsidies for outsourcing arrangements frequently evade detection during manual cross-checks.
- **Operational Solution:** This standalone application replaces manual clerical verification with a **deterministic, sub-millisecond statutory decision engine**, an **AI Labor Policy Copilot**, **Human-in-the-Loop Exception Triage**, **Pre-flight HRIS/ERP Staging**, and an **Immutable SHA-256 Cryptographic Audit Ledger**.

---

## 2. Architecture & Statutory Compliance Rules

The platform enforces the statutory framework of Japanese Labor and Tax Law deterministically without probabilistic arithmetic:

| Rule Code | Statutory / Policy Authority | Automated Enforcement Logic |
| :--- | :--- | :--- |
| **TAX_CAP_COMMUTE** | Income Tax Act Article 21 (所得税法第21条) | Capped at **¥150,000 / month** statutory tax-exempt ceiling. Any exceeding claim is routed to supervisor exception review. |
| **TELEWORK_CEILING** | Telework Guidelines Section 3 | Benchmarked at **¥250 / day** up to a monthly maximum of **¥5,000**. Variances trigger supervisor review. |
| **HOUSING_RESTRICTION** | Gyomu Itaku Kyuuyo Kitei Art. 4 (業務委託給与規程第4条) | Housing subsidies are **strictly prohibited** for `outsourcing` (業務委託) contracts. Any non-zero claim is immediately rejected. |
| **DEDUCTION_LIMIT** | Labor Standards Act Article 24 (労働基準法第24条) | Custom voluntary deductions may not exceed **20% of gross additions** without formal Article 24 statutory labor agreement authorization. |
| **SOCIAL_INSURANCE** | Health & Employees' Pension Insurance Acts | Deductions are verified against standard monthly remuneration grades (標準報酬月額). |
| **RESIDENT_TAX** | Special Collection Notification (特別徴収税額通知書) | Verified against municipal schedules to prevent unauthorized variance. |

---

## 3. Functional Capabilities

1. **Automated Batch Processing Center (`/view-batch`)**:
   - Ingests CSV and Excel spreadsheets with automated column header detection across Japanese (通勤手当, テレワーク手当, etc.) and English schemas.
   - Evaluates multi-case batches in sub-millisecond execution time (<5ms total).
   - Real-time operational telemetry: Straight-Through Processing (STP) rate, Net Payroll Sum, and Clerical Hours Reclaimed.

2. **Human-in-the-Loop Exception Review Desk (`/view-exceptions`)**:
   - Filter and inspect flagged claims requiring discretionary review.
   - Interactive review interface with comparative mathematical breakdowns.
   - Digital supervisor override authorization with operator identification, digital signature code, and mandatory compliance justification.

3. **Pre-flight HRIS & ERP Commit Hub (`/view-staging`)**:
   - Pre-commit buffer for SAP, Oracle, Workday, and Freee API pipelines.
   - Guarantees that only legally verified payloads are transmitted to downstream ledgers.

4. **Cryptographic SHA-256 Audit Ledger (`/view-audit`)**:
   - Each transaction, automatic decision, and supervisor override is cryptographically sealed into an append-only JSONL ledger.
   - Integrated hash verification for external labor inspector audits.

5. **AI Labor Policy Copilot**:
   - Grounded conversational assistant informed by statutory Japanese labor law and internal compensation rules.
   - Provides on-demand case reasoning and legal citations.

---

## 4. Execution & Deployment Guide

### Option 1: Standalone Desktop Executable (.exe)
Launch the fully compiled, self-contained Windows desktop application (requires no web browser, runs independently with native window container):
```cmd
apps\payroll_automation\launch_desktop_app.bat
```
*(Or execute `apps\payroll_automation\dist\PayrollAutomationSuite\PayrollAutomationSuite.exe` directly)*

### Option 2: Standalone Desktop Container (Python)
Launch the native Windows desktop window via Python with embedded ASGI engine:
```bash
python apps/payroll_automation/desktop_app.py
```

### Option 3: Web Server & Browser Runner
Launch the dedicated backend server and automatically open the interface in the default browser:
```bash
python apps/payroll_automation/run_app.py
```

The application interface is served at:
```
http://localhost:8500/
```

### Option 3: Direct ASGI Server Launch
```bash
uvicorn apps.payroll_automation.backend.main:app --host 127.0.0.1 --port 8500 --reload
```

---

## 5. API Endpoints Specification

| HTTP Method | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/api/status` | Engine status, policy version metadata, and active case counts |
| `GET` | `/api/cases` | Retrieve evaluated claims with optional status filtering |
| `POST` | `/api/evaluate_case` | Sub-millisecond evaluation of an individual claim |
| `POST` | `/api/evaluate_batch` | Batch evaluation of multiple claims |
| `POST` | `/api/upload_csv` | Multipart CSV / Excel file upload with automated schema normalization |
| `POST` | `/api/supervisor_override` | Digital authorization of flagged claims with signature audit logging |
| `GET` | `/api/hris/staged` | Retrieve staged payloads ready for ERP transmission |
| `POST` | `/api/hris/commit` | Transmit staged records to downstream enterprise systems |
| `GET` | `/api/audit_ledger` | Retrieve tamper-evident cryptographic audit ledger |
| `GET` | `/api/export_erp` | Export validated claims in ERP-compliant CSV format |
| `POST` | `/api/copilot/explain` | AI Copilot statutory justification for a specific case ID |
| `POST` | `/api/copilot/query` | Interactive labor policy and regulatory Q&A |

---

## 6. Sample Datasets (170+ Production & Audit Records)

The application includes enterprise production test datasets located in `sample_data/`:
- `monthly_claims_batch_01.csv`: 120 production multi-contract claims (`EMP-9401` to `EMP-9520`) with 87.5% straight-through auto-approval rate, 7.5% commute/deduction review flags, and 5.0% policy violation rejections.
- `edge_cases_batch_02.csv`: 50 stress-testing compliance edge cases including borderline statutory tax thresholds, housing subsidies for non-regular arrangements, and deduction limits under Labor Standards Act Article 24.
- `seed_cases_120.json`: 120 pre-evaluated claims with full audit trail breakdowns for offline local verification.
