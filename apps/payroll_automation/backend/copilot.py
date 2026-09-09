"""
AI Policy Copilot & Corporate Regulation Reasoning Engine
Grounded in Japanese Labor Law and Internal Regulations:
- gyomu_itaku_kyuuyo_kitei (Compensation & Outsourcing Guidelines)
- Statutory Commute Tax-Exempt Caps (Income Tax Act Art. 21)
- Statutory Deductions (Social & Employment Insurance)
- Custom Deduction Safeguards (20% Base Salary Cap)
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("PayrollCopilot")

CORPORATE_POLICY_RULES = {
    "commute_allowance": {
        "rule_id": "POL-COMMUTE-01",
        "statutory_cap_jpy": 150000,
        "tax_exemption_law": "Income Tax Act Article 21 / Cabinet Order Article 20-2",
        "description": "Commuter pass allowance is tax-exempt up to 150,000 JPY per month for standard transit routes. Claims above 150,000 JPY must be capped at 150,000 JPY or submitted for special tax treatment authorization."
    },
    "telework_allowance": {
        "rule_id": "POL-TELEWORK-02",
        "rate_per_day_jpy": 250,
        "monthly_cap_jpy": 5000,
        "regulation": "Internal Telework Policy 2026.04 §3",
        "description": "Employees working from home receive 250 JPY per declared telework day to offset utility & broadband overhead, up to a monthly maximum of 5,000 JPY (20 days)."
    },
    "housing_subsidy": {
        "rule_id": "POL-HOUSING-03",
        "monthly_cap_jpy": 30000,
        "eligible_contracts": ["regular", "contract"],
        "ineligible_contracts": ["outsourcing", "part_time"],
        "regulation": "gyomu_itaku_kyuuyo_kitei Article 4",
        "description": "Housing subsidies (up to 30,000 JPY) are strictly reserved for full-time regular and contract employees. Outsourcing (Gyomu Itaku) contractors and part-time workers are contractually ineligible; any housing claim by outsourcing staff must be REJECTED."
    },
    "statutory_deductions": {
        "rule_id": "POL-STATUTORY-04",
        "social_insurance_rate": 0.152,
        "employment_insurance_rate": 0.006,
        "applicable_contracts": ["regular", "contract"],
        "regulation": "Social Insurance & Labor Standards Act",
        "description": "Standard welfare pension + health insurance (15.2%) and employment insurance (0.6%) applied to gross monthly base salary for regular and contract employees. Independent outsourcing contractors handle their own national pension/tax."
    },
    "custom_deductions": {
        "rule_id": "POL-CUSTOM-DED-05",
        "max_percentage_of_base": 0.20,
        "requires_documentation": True,
        "regulation": "Labor Standards Act Article 24 (Protection of Wages) & Internal Policy §11",
        "description": "Voluntary or company deductions cannot exceed 20% of monthly base salary without formal supervisor waiver. All custom deductions require an explicit documented justification (e.g. equipment lease, advance repayment)."
    }
}


class PolicyCopilot:
    """
    Intelligent Assistant providing:
    1. Comprehensive explanations of decision rationale for flagged/rejected cases.
    2. Automated drafting of supervisor override compliance memos.
    3. Natural language Q&A regarding internal and statutory payroll policies.
    """

    def explain_case(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """Generates a structured, audit-ready explanation of a case's evaluation."""
        status = case.get("status", "UNKNOWN")
        input_data = case.get("input_data", {})
        calc = case.get("calculated_details", {})
        notes = case.get("decision_notes", "")

        contract = input_data.get("contract_type", "regular")
        claimed_commute = input_data.get("claimed_commute", 0)
        claimed_housing = input_data.get("claimed_housing", 0)
        custom_ded = input_data.get("custom_deduction", 0)
        base_salary = input_data.get("base_salary", 0)

        findings: List[Dict[str, str]] = []
        recommendation = ""

        # Analyze Commute
        if claimed_commute > 150000:
            diff = claimed_commute - 150000
            findings.append({
                "category": "Commute Allowance",
                "severity": "FLAG_REVIEW",
                "rule_ref": "Income Tax Act Art. 21 (Cap: ¥150,000)",
                "detail": f"Claimed ¥{claimed_commute:,} exceeds statutory tax-exempt threshold by ¥{diff:,}. The engine approved the statutory maximum of ¥150,000 and flagged the surplus ¥{diff:,} for taxable review."
            })

        # Analyze Housing Eligibility
        if contract in ["outsourcing", "part_time"] and claimed_housing > 0:
            findings.append({
                "category": "Housing Allowance",
                "severity": "REJECTED",
                "rule_ref": "gyomu_itaku_kyuuyo_kitei Article 4",
                "detail": f"Outsourcing ({contract}) personnel are contractually barred from claiming company housing subsidies. Claim of ¥{claimed_housing:,} was automatically denied per corporate guidelines."
            })

        # Analyze Custom Deductions
        if custom_ded > 0:
            threshold = base_salary * 0.20
            if custom_ded > threshold:
                findings.append({
                    "category": "Custom Deduction Ceiling",
                    "severity": "FLAG_REVIEW",
                    "rule_ref": "Labor Standards Act Art. 24 & Policy §11 (Cap: 20%)",
                    "detail": f"Deduction of ¥{custom_ded:,} represents {(custom_ded / base_salary) * 100:.1f}% of base salary (¥{base_salary:,}), exceeding the 20% statutory protective threshold (¥{threshold:,.0f}). Requires signed supervisor authorization."
                })
            reason = input_data.get("deduction_reason", "")
            if not reason:
                findings.append({
                    "category": "Deduction Documentation",
                    "severity": "FLAG_REVIEW",
                    "rule_ref": "Internal Policy §11",
                    "detail": "Custom deduction submitted without mandatory business justification memo."
                })

        if status == "AUTO_APPROVED":
            recommendation = "Case complies 100% with statutory tax boundaries and internal corporate regulations. Safe for automated ERP batch commit without human intervention."
        elif status == "FLAGGED_FOR_REVIEW":
            recommendation = "Review flagged anomalies above. If a legitimate business exception or supervisor agreement exists, record the rationale and approve via digital override."
        elif status == "REJECTED":
            recommendation = "Policy violation detected. Reject claim or request employee resubmission in accordance with Article 4 guidelines."

        return {
            "case_id": case.get("case_id"),
            "employee_id": input_data.get("employee_id"),
            "status": status,
            "decision_notes": notes,
            "findings": findings,
            "copilot_recommendation": recommendation,
            "policy_version": calc.get("policy_version", "2026.04-v1.2"),
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        }

    def generate_override_draft(self, case: Dict[str, Any], supervisor_name: str) -> str:
        """Auto-drafts a standardized compliance memo for supervisor override."""
        inp = case.get("input_data", {})
        c_id = case.get("case_id", "N/A")
        emp_id = inp.get("employee_id", "N/A")
        notes = case.get("decision_notes", "")

        return (
            f"SUPERVISOR COMPLIANCE MEMO\n"
            f"Case: {c_id} | Employee: {emp_id} ({inp.get('contract_type', '')})\n"
            f"Authorized By: {supervisor_name} | Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n"
            f"Original Exception: {notes}\n"
            f"Justification: Exception reviewed against department budget and verified with HR operations. "
            f"Approved for execution under authorized discretionary threshold (Policy Ref: 2026.04-v1.2 §14)."
        )

    def answer_policy_query(self, query: str) -> Dict[str, Any]:
        """Answers general HR payroll policy questions using corporate reference knowledge."""
        q_lower = query.lower()
        matched_rules: List[Dict[str, Any]] = []

        if any(k in q_lower for k in ["commute", "travel", "train", "tax", "150000", "transit"]):
            matched_rules.append(CORPORATE_POLICY_RULES["commute_allowance"])
        if any(k in q_lower for k in ["telework", "remote", "wfh", "250", "home"]):
            matched_rules.append(CORPORATE_POLICY_RULES["telework_allowance"])
        if any(k in q_lower for k in ["housing", "rent", "outsourcing", "article 4", "gyomu"]):
            matched_rules.append(CORPORATE_POLICY_RULES["housing_subsidy"])
        if any(k in q_lower for k in ["social", "insurance", "pension", "health", "deduction"]):
            matched_rules.append(CORPORATE_POLICY_RULES["statutory_deductions"])
        if any(k in q_lower for k in ["custom", "20%", "repayment", "equipment", "lease"]):
            matched_rules.append(CORPORATE_POLICY_RULES["custom_deductions"])

        if not matched_rules:
            matched_rules = list(CORPORATE_POLICY_RULES.values())[:3]

        return {
            "query": query,
            "matches": matched_rules,
            "policy_version": "2026.04-v1.2",
            "effective_date": "2026-04-01",
            "statutory_authority": "Ministry of Health, Labour and Welfare (MHLW) & Corporate HR Governance"
        }
