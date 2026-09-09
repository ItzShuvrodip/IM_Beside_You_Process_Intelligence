"""
Domain Layer: Business rules and policy regulations for Payroll Items & Deduction Adjustments.
Derived from HR documentation (Contractor Payroll Policy Guidelines - gyomu_itaku_kyuuyo_kitei)
and statutory HR deduction standards.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Tuple, List
from datetime import datetime


# Policy Provenance & Authority Configuration
POLICY_METADATA: Dict[str, Any] = {
    "policy_version": "2026.04-v1.2",
    "effective_date": "2026-04-01",
    "last_reviewed_date": "2026-07-01",
    "approval_owner": "Corporate HR Policy & Compliance Review Board",
    "governance_mode": "shadow_decision_support",
    "currency": "JPY",
    "source_documents": [
        {
            "doc_id": "gyomu_itaku_kyuuyo_kitei",
            "title": "業務委託・給与控除等取扱い規程 (Contractor & Payroll Deduction Handling Regulations)",
            "authority": "Corporate HR Standing Policy",
            "articles": ["Article 3 (Commute)", "Article 4 (Housing Subsidy)", "Article 7 (Telework Allowance)"]
        },
        {
            "doc_id": "nta_commute_tax_exempt_2026",
            "title": "国税庁 通勤手当の非課税限度額規則 (National Tax Agency Commute Exemption Cap)",
            "authority": "Statutory Regulation (Income Tax Act Enforcement Order)",
            "statutory_limit_jpy": 150000
        }
    ]
}

# Standard deduction and allowance parameters (Versioned)
POLICY_CONFIG = {
    "metadata": POLICY_METADATA,
    "max_monthly_commute_allowance": Decimal("150000"),  # Statutory tax-exempt limit for commute in Japan (150,000 JPY)
    "remote_work_allowance_daily": Decimal("250"),       # Standard daily telework allowance
    "max_telework_allowance_monthly": Decimal("5000"),
    "statutory_social_insurance_rate": Decimal("0.152"), # Employee portion approx 15.2% (pension + health)
    "employment_insurance_rate": Decimal("0.006"),       # 0.6% employee share
    "housing_allowance_cap": Decimal("30000"),           # Corporate housing subsidy cap
    "contract_types": ["regular", "contract", "outsourcing", "part_time"]
}


def _to_decimal(val: Any) -> Decimal:
    if val is None or val == "":
        return Decimal("0")
    return Decimal(str(val))


def validate_payroll_item(item: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validates an incoming payroll deduction/allowance adjustment request
    in shadow decision-support mode.
    Returns: (is_approved, status_reason, calculated_details)
    """
    emp_id = item.get("employee_id")
    emp_name = item.get("employee_name")
    contract_type = item.get("contract_type", "regular")
    base_salary = _to_decimal(item.get("base_salary", 0))
    claimed_commute = _to_decimal(item.get("claimed_commute", 0))
    telework_days = _to_decimal(item.get("telework_days", 0))
    housing_subsidy_claimed = _to_decimal(item.get("claimed_housing", 0))
    custom_deduction = _to_decimal(item.get("custom_deduction", 0))
    deduction_reason = item.get("deduction_reason", "")

    audit_trail: List[Dict[str, Any]] = []

    if not emp_id or not emp_name:
        return False, "REJECTED: Missing employee identifier or name", {
            "policy_version": POLICY_METADATA["policy_version"],
            "audit_trail": [{"rule": "identity_check", "status": "REJECTED", "detail": "Missing employee identifier or name"}]
        }

    if contract_type not in POLICY_CONFIG["contract_types"]:
        return False, f"FLAG_REVIEW: Unrecognized contract type '{contract_type}' (requires HR policy owner confirmation)", {
            "policy_version": POLICY_METADATA["policy_version"],
            "audit_trail": [{"rule": "contract_type_check", "status": "FLAG_REVIEW", "detail": f"Unknown {contract_type}"}]
        }

    flags = []

    # 1. Commute allowance verification
    commute_cap = POLICY_CONFIG["max_monthly_commute_allowance"]
    approved_commute = min(claimed_commute, commute_cap)
    if claimed_commute > commute_cap:
        flags.append(f"Commute exceeds statutory tax-exempt cap ({int(claimed_commute)} > {int(commute_cap)} JPY)")
        audit_trail.append({"rule": "commute_statutory_cap", "status": "FLAG_REVIEW", "claimed": int(claimed_commute), "cap": int(commute_cap)})
    else:
        audit_trail.append({"rule": "commute_statutory_cap", "status": "PASSED", "approved": int(approved_commute)})

    # 2. Telework allowance
    calculated_telework = min(
        telework_days * POLICY_CONFIG["remote_work_allowance_daily"],
        POLICY_CONFIG["max_telework_allowance_monthly"]
    )
    audit_trail.append({"rule": "telework_allowance", "status": "PASSED", "days": int(telework_days), "amount": int(calculated_telework)})

    # 3. Housing allowance check (Statutory / Contractual Eligibility)
    if contract_type in ["outsourcing", "part_time"] and housing_subsidy_claimed > Decimal("0"):
        calc_details_rej = {
            "policy_version": POLICY_METADATA["policy_version"],
            "effective_date": POLICY_METADATA["effective_date"],
            "governance_mode": POLICY_METADATA["governance_mode"],
            "employee_id": emp_id,
            "employee_name": emp_name,
            "contract_type": contract_type,
            "base_salary": int(base_salary),
            "approved_commute": int(approved_commute),
            "approved_telework": int(calculated_telework),
            "approved_housing": 0,
            "social_insurance_deduction": 0,
            "employment_insurance_deduction": 0,
            "custom_deduction": int(custom_deduction),
            "total_gross_addition": int(approved_commute + calculated_telework),
            "total_deduction": int(custom_deduction),
            "net_adjustment": int(approved_commute + calculated_telework - custom_deduction),
            "audit_trail": audit_trail + [{"rule": "housing_eligibility", "status": "REJECTED", "detail": f"Article 4 disallows housing allowance for {contract_type}"}]
        }
        return False, "REJECTED: Housing subsidy not permissible for outsourcing or part-time staff per article 4", calc_details_rej

    approved_housing = min(housing_subsidy_claimed, POLICY_CONFIG["housing_allowance_cap"])
    audit_trail.append({"rule": "housing_eligibility", "status": "PASSED", "approved": int(approved_housing)})

    # 4. Statutory deduction estimation
    if contract_type in ["regular", "contract"]:
        est_social_ins = (base_salary * POLICY_CONFIG["statutory_social_insurance_rate"]).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        est_employment_ins = (base_salary * POLICY_CONFIG["employment_insurance_rate"]).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    else:
        # Outsourcing (gyomu_itaku) is not subject to statutory payroll withholdings by client
        est_social_ins = Decimal("0")
        est_employment_ins = Decimal("0")
    audit_trail.append({"rule": "statutory_deductions", "status": "PASSED", "social_insurance": int(est_social_ins), "employment_insurance": int(est_employment_ins)})

    # 5. Custom deduction threshold (e.g. advance salary repayment)
    max_custom_ratio = Decimal("0.20")
    if custom_deduction > (base_salary * max_custom_ratio):
        flags.append(f"Custom deduction exceeds 20% of base salary ({int(custom_deduction)} JPY) - requires supervisor authorization")
        audit_trail.append({"rule": "custom_deduction_cap", "status": "FLAG_REVIEW", "amount": int(custom_deduction)})

    if not deduction_reason and custom_deduction > Decimal("0"):
        flags.append("Custom deduction has missing memo justification")
        audit_trail.append({"rule": "custom_deduction_memo", "status": "FLAG_REVIEW", "detail": "Missing justification text"})

    total_gross_addition = approved_commute + calculated_telework + approved_housing
    total_deduction = est_social_ins + est_employment_ins + custom_deduction
    net_adjustment = total_gross_addition - total_deduction

    calc_details = {
        "policy_version": POLICY_METADATA["policy_version"],
        "effective_date": POLICY_METADATA["effective_date"],
        "governance_mode": POLICY_METADATA["governance_mode"],
        "employee_id": emp_id,
        "employee_name": emp_name,
        "contract_type": contract_type,
        "base_salary": int(base_salary),
        "approved_commute": int(approved_commute),
        "approved_telework": int(calculated_telework),
        "approved_housing": int(approved_housing),
        "social_insurance_deduction": int(est_social_ins),
        "employment_insurance_deduction": int(est_employment_ins),
        "custom_deduction": int(custom_deduction),
        "total_gross_addition": int(total_gross_addition),
        "total_deduction": int(total_deduction),
        "net_adjustment": int(net_adjustment),
        "audit_trail": audit_trail
    }

    if flags:
        return False, f"FLAG_REVIEW: {'; '.join(flags)}", calc_details

    return True, "AUTO_APPROVED: Passed all statutory and corporate policy validation checks", calc_details


BATCH_CASES = [
    {
        "case_id": "PI-PROD-2026-001",
        "employee_id": "EMP-9401",
        "employee_name": "Employee 01",
        "contract_type": "regular",
        "base_salary": 380000,
        "claimed_commute": 18500,
        "telework_days": 12,
        "claimed_housing": 25000,
        "custom_deduction": 0,
        "deduction_reason": ""
    },
    {
        "case_id": "PI-PROD-2026-002",
        "employee_id": "EMP-9402",
        "employee_name": "Employee 02",
        "contract_type": "outsourcing",
        "base_salary": 450000,
        "claimed_commute": 22000,
        "telework_days": 15,
        "claimed_housing": 0,
        "custom_deduction": 5000,
        "deduction_reason": "Monthly IT equipment lease deduction"
    },
    {
        "case_id": "PI-PROD-2026-003",
        "employee_id": "EMP-9403",
        "employee_name": "Employee 03",
        "contract_type": "regular",
        "base_salary": 320000,
        "claimed_commute": 165000,
        "telework_days": 8,
        "claimed_housing": 30000,
        "custom_deduction": 0,
        "deduction_reason": ""
    },
    {
        "case_id": "PI-PROD-2026-004",
        "employee_id": "EMP-9404",
        "employee_name": "Employee 04",
        "contract_type": "contract",
        "base_salary": 280000,
        "claimed_commute": 12000,
        "telework_days": 10,
        "claimed_housing": 20000,
        "custom_deduction": 80000,
        "deduction_reason": "Advance salary repayment"
    },
    {
        "case_id": "PI-PROD-2026-005",
        "employee_id": "EMP-9405",
        "employee_name": "Employee 05",
        "contract_type": "outsourcing",
        "base_salary": 420000,
        "claimed_commute": 14000,
        "telework_days": 6,
        "claimed_housing": 25000,
        "custom_deduction": 0,
        "deduction_reason": ""
    }
]
SAMPLE_BATCH = BATCH_CASES
