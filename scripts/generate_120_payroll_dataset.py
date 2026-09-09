"""
Generates 120 realistic enterprise payroll cases adhering strictly to:
- Income Tax Act Art. 21 (Commute <= 150,000 JPY)
- Telework Policy (250 JPY/day up to 5,000 JPY/mo)
- Gyomu Itaku Kyuuyo Kitei Art. 4 (Housing subsidy prohibited for outsourcing/part-time)
- Labor Standards Act Art. 24 (Custom deductions capped at 20% of base salary)
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.automation.service.decision_service import PayrollDecisionService

SERVICE = PayrollDecisionService()

raw_cases = []
for i in range(1, 121):
    case_id = f"PI-PROD-2026-{i:03d}"
    emp_id = f"EMP-{9400 + i:04d}"
    emp_name = f"Employee {i:02d}"

    if i in (5, 17, 32, 58, 83, 109):
        # Specific outsourcing housing violation test cases (REJECTED)
        contract = "outsourcing"
        base_salary = 380000 + (i % 7) * 20000
        commute = 12000 + (i % 15) * 1500
        telework = (i % 12) + 2
        housing = 25000  # Prohibited for outsourcing!
        custom_ded = 0
        ded_reason = ""
    elif i in (3, 27, 51, 76, 99):
        # Commute tax cap overage test cases (FLAGGED_FOR_REVIEW)
        contract = "regular"
        base_salary = 420000 + (i % 5) * 25000
        commute = 155000 + (i % 4) * 10000  # Exceeds 150,000 JPY
        telework = (i % 8) + 1
        housing = 20000
        custom_ded = 0
        ded_reason = ""
    elif i in (4, 38, 67, 114):
        # High custom deduction > 20% test cases (FLAGGED_FOR_REVIEW)
        contract = "contract" if i % 2 == 0 else "regular"
        base_salary = 300000
        commute = 15000
        telework = 5
        housing = 15000
        custom_ded = 75000  # 25% > 20%
        ded_reason = "Advance emergency salary repayment"
    else:
        # Standard Clean Enterprise Cases (AUTO_APPROVED)
        contracts = ["regular", "regular", "regular", "contract", "outsourcing"]
        contract = contracts[i % len(contracts)]
        base_salary = 320000 + (i * 3500) % 380000
        commute = 8000 + (i * 1200) % 32000
        telework = (i * 3) % 18
        if contract in ("outsourcing", "part_time"):
            housing = 0
        else:
            housing = 15000 if i % 3 == 0 else (25000 if i % 2 == 0 else 0)
        
        if i % 5 == 0 and contract == "outsourcing":
            custom_ded = 5000
            ded_reason = "Monthly IT workstation lease deduction"
        elif i % 6 == 0 and contract == "regular":
            custom_ded = 8000
            ded_reason = "Company Housing Maintenance Fee"
        else:
            custom_ded = 0
            ded_reason = ""

    raw_cases.append({
        "case_id": case_id,
        "employee_id": emp_id,
        "employee_name": emp_name,
        "contract_type": contract,
        "base_salary": base_salary,
        "claimed_commute": commute,
        "telework_days": telework,
        "claimed_housing": housing,
        "custom_deduction": custom_ded,
        "deduction_reason": ded_reason
    })

csv_path = ROOT / "apps" / "payroll_automation" / "sample_data" / "monthly_claims_batch_01.csv"
fieldnames = [
    "case_id", "employee_id", "employee_name", "contract_type",
    "base_salary", "claimed_commute", "telework_days", "claimed_housing",
    "custom_deduction", "deduction_reason"
]

with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for row in raw_cases:
        writer.writerow(row)

print(f"[OK] Successfully wrote {len(raw_cases)} cases to {csv_path}")

evaluated_results = SERVICE.process_batch(raw_cases)

status_counts = {}
for r in evaluated_results:
    st = r["status"]
    status_counts[st] = status_counts.get(st, 0) + 1

print(f"[OK] Evaluation Breakdown across {len(evaluated_results)} cases:")
for st, cnt in sorted(status_counts.items()):
    pct = (cnt / len(evaluated_results)) * 100
    print(f"     - {st}: {cnt} ({pct:.1f}%)")

json_out = ROOT / "apps" / "payroll_automation" / "sample_data" / "seed_cases_120.json"
with open(json_out, "w", encoding="utf-8") as f:
    json.dump(evaluated_results, f, indent=2, ensure_ascii=False)

print(f"[OK] Successfully exported evaluated seed cases to {json_out}")
