# IMBY Enterprise Payroll Deduction Automation Suite

> **Standalone End-to-End Enterprise Automation Tool for Japanese Payroll Deduction Adjustments**  
> Dedicated High-Performance Web & Desktop Application

---

## 🌟 Executive Overview

In the process mining analysis of the IMBY telemetry dataset, **`payroll_deduction_adjustment`** was identified as the highest-friction operational bottleneck:
- **Baseline Manual Duration:** **182 seconds per case**
- **Clerical Error Rate:** Borderline commute cap breaches and prohibited housing subsidies for outsourcing contracts often go undetected manually.
- **Enterprise Solution:** This standalone automation tool completely replaces manual verification with a **deterministic, sub-millisecond evaluation engine** coupled with an **AI Policy Copilot**, **Human-in-the-Loop Exception Triage**, **Pre-flight HRIS/ERP Staging**, and a **Cryptographic SHA-256 Audit Ledger**.

---

## 🏛️ Architecture & Statutory Compliance Rules

The platform deterministically enforces the full statutory framework of Japanese Labor and Tax Law:

| Rule Code | Statutory / Policy Basis | Automated Enforcement Logic |
| :--- | :--- | :--- |
| **TAX_CAP_COMMUTE** | Income Tax Act Article 21 (所得税法第21条) | Capped at **¥150,000/month** tax-exempt limit. Any excess is flagged for manual supervisor review. |
| **TELEWORK_CEILING** | Telework Guidelines §3 | Benchmarked at **¥250/day** up to a monthly maximum of **¥5,000**. Overages trigger review. |
| **HOUSING_RESTRICTION** | Gyomu Itaku Kyuuyo Kitei Art. 4 (業務委託給与規程第4条) | Housing subsidies are **strictly prohibited** for `outsourcing` (業務委託) contracts. Non-zero values are immediately rejected. |
| **DEDUCTION_LIMIT** | Labor Standards Act Article 24 (労働基準法第24条) | Custom voluntary deductions may not exceed **20% of gross additions** without statutory Article 24 labor agreement authorization. |
| **SOCIAL_INSURANCE** | Health & Employees' Pension Insurance Acts | Deductions are verified against standard monthly remuneration grades (標準報酬月額). |
| **RESIDENT_TAX** | Special Collection Notification (特別徴収税額通知書) | Verified against municipal tax schedules without unauthorized variance. |

---

## 🚀 Key Functional Capabilities

1. **Automated Batch Processing Center (`/view-batch`)**:
   - Ingest CSV and Excel spreadsheets with automated column header detection in both Japanese (通勤手当, テレワーク手当, etc.) and English.
   - Evaluates hundreds of claims in sub-millisecond execution time (<5ms total).
   - Real-time KPI telemetry: Straight-Through Processing (STP) rate, Net Payroll Sum, and Clerical Hours Saved.

2. **Human-in-the-Loop Exception Review Desk (`/view-exceptions`)**:
   - Filter and inspect flagged claims.
   - Interactive review modal with side-by-side mathematical breakdown.
   - Supervisor override signing with operator ID, digital PIN, and mandatory audit justification.

3. **Pre-flight HRIS & ERP Commit Hub (`/view-staging`)**:
   - Pre-commit buffer for SAP, Oracle, Workday, and Freee API integrations.
   - Guarantees zero unverified or rejected payloads ever reach production payroll ledgers.

4. **Cryptographic SHA-256 Audit Ledger (`/view-audit`)**:
   - Every transaction, automatic decision, and supervisor override is cryptographically sealed into a tamper-evident audit ledger.
   - Built-in hash verification for external labor inspector audits.

5. **AI Labor Policy Copilot Drawer**:
   - Interactive conversational assistant grounded in the official rules and Japanese statutory labor precedents.
   - Provides on-demand explanations for any case ID and answers labor questions.

---

## 🏃 Quick Start Guide

### Option 1: Standalone Runner (Recommended)
Launch the application and automatically open it in your default browser:

```bash
# Using project Python environment
python apps/payroll_automation/run_app.py
```

Or on Windows, simply double-click:
```cmd
apps\payroll_automation\launch_payroll_app.bat
```

The application will be live at:
```
http://localhost:8500/
```

### Option 2: Direct Uvicorn Launch
```bash
uvicorn apps.payroll_automation.backend.main:app --host 127.0.0.1 --port 8500 --reload
```

---

## 🔌 API Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/status` | Engine health, operational status, and global metrics |
| `GET` | `/api/cases` | Retrieve all evaluated claims with filtering support |
| `POST` | `/api/evaluate_case` | Sub-millisecond evaluation of a single claim |
| `POST` | `/api/evaluate_batch` | Evaluate an array of claims |
| `POST` | `/api/upload_csv` | Multipart upload of CSV / Excel files with auto-normalization |
| `POST` | `/api/supervisor_override` | Seal supervisor approval/rejection with digital signature |
| `GET` | `/api/staging_hub` | Get staged payloads ready for ERP transmission |
| `POST` | `/api/commit_staging` | Transmit staged payloads to ERP endpoints |
| `GET` | `/api/audit_ledger` | Retrieve tamper-evident cryptographic audit ledger |
| `GET` | `/api/export_erp` | Export validated claims in ERP JSON payload format |
| `POST` | `/api/copilot/explain` | AI Copilot reasoning for a specific claim |
| `POST` | `/api/copilot/query` | Interactive labor policy consultation |

---

## 📂 Sample Datasets

The application includes production-ready sample files for instant testing in `sample_data/`:
- `monthly_claims_batch_01.csv`: Standard multi-contract batch (Regular, Contract, Outsourcing) showcasing Straight-Through Processing.
- `edge_cases_batch_02.csv`: Edge cases containing commute excess breaches, illegal housing subsidies for outsourcing contracts, and extreme deduction limits.
