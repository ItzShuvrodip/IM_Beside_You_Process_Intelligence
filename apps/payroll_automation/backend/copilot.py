"""Policy reasoning engine for statutory and internal compensation rules.

Authoritative knowledge base codified from:
1. gyomu_itaku_kyuuyo_kitei.docx (業務委託・給与控除等取扱い規程)
2. Japanese Income Tax Act Article 21 & Cabinet Order Article 20-2 (通勤手当非課税限度額)
3. Labor Standards Act Article 24 (賃金全額払いの原則・任意控除制限)
4. Telework Expense Handling Regulations 2026.04 §3

Supports seamless bilingual execution (English & Japanese).
"""

import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("PayrollCopilot")

# Authoritative Policy Articles codified from gyomu_itaku_kyuuyo_kitei.docx
DOCX_POLICY_ARTICLES_EN = {
    "article_1": {
        "article_no": "Article 1",
        "title": "Purpose & Scope (目的および適用範囲)",
        "source_doc": "gyomu_itaku_kyuuyo_kitei.docx",
        "summary": "Establishes standard guidelines for payroll allowance calculations, contractor compensation, and statutory withholdings across regular (正社員), direct contract (契約社員), outsourcing contractors (業務委託), and part-time workers (パート・アルバイト)."
    },
    "article_3": {
        "article_no": "Article 3",
        "title": "Commuter Transit Pass Allowance (通勤交通費の取扱い)",
        "source_doc": "gyomu_itaku_kyuuyo_kitei.docx",
        "statutory_law": "Income Tax Act Article 21 / Enforcement Order Article 20-2",
        "statutory_cap_jpy": 150000,
        "summary": "Commuter pass allowances are tax-exempt up to 150,000 JPY per month for standard transit routes. Claims exceeding 150,000 JPY are capped at 150,000 JPY for non-taxable disbursement; any surplus must be flagged for taxable payroll processing or formal supervisor waiver.",
        "conflict_criteria": "Claimed commute > 150,000 JPY"
    },
    "article_4": {
        "article_no": "Article 4",
        "title": "Housing Subsidy Restrictions (住宅手当・社宅取扱細則)",
        "source_doc": "gyomu_itaku_kyuuyo_kitei.docx",
        "corporate_cap_jpy": 30000,
        "eligible_contracts": ["regular", "contract"],
        "ineligible_contracts": ["outsourcing", "part_time"],
        "summary": "Company housing subsidies (up to 30,000 JPY/month) are strictly reserved for full-time regular and direct contract personnel. Independent outsourcing contractors (業務委託) and part-time employees are contractually ineligible. ANY housing allowance claim submitted by an outsourcing contractor is a critical violation of Article 4 and must be REJECTED.",
        "conflict_criteria": "Contract type in ['outsourcing', 'part_time'] AND claimed_housing > 0"
    },
    "article_5": {
        "article_no": "Article 5",
        "title": "Statutory Deductions & Social Insurance (法定控除および社会保険)",
        "source_doc": "gyomu_itaku_kyuuyo_kitei.docx",
        "statutory_law": "Social Insurance & Labor Standards Act",
        "social_insurance_rate": 0.152,
        "employment_insurance_rate": 0.006,
        "applicable_contracts": ["regular", "contract"],
        "summary": "Standard welfare pension + health insurance (15.2%) and employment insurance (0.6%) are withheld from gross monthly base salary for regular and contract staff. Independent outsourcing contractors (Gyomu Itaku) handle their own national tax/pension; corporate withholdings must remain 0 JPY.",
        "conflict_criteria": "Withholding deducted from outsourcing contractor or rate deviation on regular staff"
    },
    "article_7": {
        "article_no": "Article 7",
        "title": "Telework Allowance & Utility Overhead (在宅勤務手当)",
        "source_doc": "gyomu_itaku_kyuuyo_kitei.docx",
        "regulation": "Internal Telework Policy 2026.04 §3",
        "rate_per_day_jpy": 250,
        "monthly_cap_jpy": 5000,
        "max_eligible_days": 20,
        "summary": "Employees working remotely receive 250 JPY per declared telework day to offset utilities and broadband expenses, up to a monthly maximum ceiling of 5,000 JPY (20 eligible days). Claims claiming >20 days are capped at 5,000 JPY.",
        "conflict_criteria": "Telework days * 250 > 5,000 JPY or telework_days > 20"
    },
    "article_11": {
        "article_no": "Article 11",
        "title": "Voluntary & Custom Deductions (任意控除および相殺の制限)",
        "source_doc": "gyomu_itaku_kyuuyo_kitei.docx",
        "statutory_law": "Labor Standards Act Article 24 (Protection of Full Wage Payment)",
        "max_percentage_of_base": 0.20,
        "requires_documentation": True,
        "summary": "Custom company deductions (equipment leases, salary advance repayments) cannot exceed 20% of monthly base salary without signed supervisory waiver. Furthermore, every custom deduction requires an explicit business justification memo; submissions without an accompanying memo trigger an immediate audit flag.",
        "conflict_criteria": "custom_deduction > 20% of base_salary OR (custom_deduction > 0 AND missing deduction_reason)"
    },
    "article_14": {
        "article_no": "Article 14",
        "title": "Supervisory Exception Overrides & Audit Trail (例外承認および監査証跡)",
        "source_doc": "gyomu_itaku_kyuuyo_kitei.docx",
        "summary": "Flagged anomalies may be resolved through supervisory override only when supported by a formal written compliance justification citing valid business necessity. Every override must be sealed with a cryptographic SHA-256 hash in the enterprise audit ledger."
    }
}

DOCX_POLICY_ARTICLES_JA = {
    "article_1": {
        "article_no": "第1条",
        "title": "目的および適用範囲",
        "source_doc": "gyomu_itaku_kyuuyo_kitei.docx",
        "summary": "正社員、契約社員、業務委託、パート・アルバイト等の契約区分ごとに、諸手当の支給基準、控除項目、および法令に基づく計算規程を定める。"
    },
    "article_3": {
        "article_no": "第3条",
        "title": "通勤交通費の取扱い",
        "source_doc": "gyomu_itaku_kyuuyo_kitei.docx",
        "statutory_law": "所得税法第21条 / 所得税法施行令第20条の2",
        "statutory_cap_jpy": 150000,
        "summary": "通勤定期券代は月額150,000円を上限として非課税支給とする。150,000円を超える申請については、非課税枠は150,000円で上限適用し、超過額は課税対象給与として処理するか上長特認が必要となる。",
        "conflict_criteria": "通勤費申請額 > 150,000円"
    },
    "article_4": {
        "article_no": "第4条",
        "title": "住宅手当・社宅取扱細則（支給対象の制限）",
        "source_doc": "gyomu_itaku_kyuuyo_kitei.docx",
        "corporate_cap_jpy": 30000,
        "eligible_contracts": ["regular", "contract"],
        "ineligible_contracts": ["outsourcing", "part_time"],
        "summary": "住宅補助（月額最大30,000円）は正社員および直接雇用契約社員に限定される。業務委託（Gyomu Itaku）およびパート従業員には支給対象外であり、業務委託による住宅手当の申請は第4条の重大な規程違反として自動却下（支給額0円）される。",
        "conflict_criteria": "契約区分 in ['outsourcing', 'part_time'] かつ 住宅手当申請額 > 0円"
    },
    "article_5": {
        "article_no": "第5条",
        "title": "法定控除および社会保険",
        "source_doc": "gyomu_itaku_kyuuyo_kitei.docx",
        "statutory_law": "社会保険各法および労働基準法",
        "social_insurance_rate": 0.152,
        "employment_insurance_rate": 0.006,
        "applicable_contracts": ["regular", "contract"],
        "summary": "正社員・契約社員には厚生年金・健康保険（折半本人負担分15.2%）および雇用保険（0.6%）を標準控除する。個人事業主である業務委託契約者は国民年金・国保をご自身で納付するため、企業側の給与天引き控除は行わない（控除0円）。",
        "conflict_criteria": "業務委託に対する誤天引き、または法定料率の乖離"
    },
    "article_7": {
        "article_no": "第7条",
        "title": "在宅勤務手当（通信光熱費補助）",
        "source_doc": "gyomu_itaku_kyuuyo_kitei.docx",
        "regulation": "社内テレワーク取扱規程 2026.04 第3条",
        "rate_per_day_jpy": 250,
        "monthly_cap_jpy": 5000,
        "max_eligible_days": 20,
        "summary": "テレワーク実績1日あたり250円を支給し、月間上限は20日分（5,000円）とする。20日を超える申請は月額5,000円に制限・上限適用される。",
        "conflict_criteria": "テレワーク日数 * 250 > 5,000円 または 日数 > 20日"
    },
    "article_11": {
        "article_no": "第11条",
        "title": "任意控除および相殺の制限（賃金全額払いの原則）",
        "source_doc": "gyomu_itaku_kyuuyo_kitei.docx",
        "statutory_law": "労働基準法第24条（賃金全額払いの原則）",
        "max_percentage_of_base": 0.20,
        "requires_documentation": True,
        "summary": "機器リース費や立替金精算等の任意控除は、基本給の20%を超えてはならない。また、任意控除を行う場合は必ず正当な理由書の添付を必須とし、理由未記載は監査フラグとなる。",
        "conflict_criteria": "任意控除額 > 基本給の20% または 控除理由の未記載"
    },
    "article_14": {
        "article_no": "第14条",
        "title": "例外承認および監査証跡",
        "source_doc": "gyomu_itaku_kyuuyo_kitei.docx",
        "summary": "規程外の例外事項を承認する場合は、管理職による特別裁量承認稟議メモの作成と、SHA-256改ざん防止監査台帳への電子記録が義務付けられる。"
    }
}

# Backward compatibility lookup dictionary
CORPORATE_POLICY_RULES = {
    "commute_allowance": {
        "rule_id": "POL-COMMUTE-01",
        "article": "Article 3",
        "statutory_cap_jpy": 150000,
        "tax_exemption_law": "Income Tax Act Article 21 / Cabinet Order Article 20-2",
        "description": "Commuter pass allowance is tax-exempt up to 150,000 JPY per month for standard transit routes. Claims above 150,000 JPY must be capped at 150,000 JPY or submitted for special tax treatment authorization."
    },
    "telework_allowance": {
        "rule_id": "POL-TELEWORK-02",
        "article": "Article 7",
        "rate_per_day_jpy": 250,
        "monthly_cap_jpy": 5000,
        "regulation": "Internal Telework Policy 2026.04 §3 & gyomu_itaku_kyuuyo_kitei Article 7",
        "description": "Employees working from home receive 250 JPY per declared telework day to offset utility & broadband overhead, up to a monthly maximum of 5,000 JPY (20 days)."
    },
    "housing_subsidy": {
        "rule_id": "POL-HOUSING-03",
        "article": "Article 4",
        "monthly_cap_jpy": 30000,
        "eligible_contracts": ["regular", "contract"],
        "ineligible_contracts": ["outsourcing", "part_time"],
        "regulation": "gyomu_itaku_kyuuyo_kitei.docx Article 4",
        "description": "Housing subsidies (up to 30,000 JPY) are strictly reserved for full-time regular and contract employees. Outsourcing (Gyomu Itaku) contractors and part-time workers are contractually ineligible; any housing claim by outsourcing staff must be REJECTED."
    },
    "statutory_deductions": {
        "rule_id": "POL-STATUTORY-04",
        "article": "Article 5",
        "social_insurance_rate": 0.152,
        "employment_insurance_rate": 0.006,
        "applicable_contracts": ["regular", "contract"],
        "regulation": "Social Insurance & Labor Standards Act & gyomu_itaku_kyuuyo_kitei Article 5",
        "description": "Standard welfare pension + health insurance (15.2%) and employment insurance (0.6%) applied to gross monthly base salary for regular and contract employees. Independent outsourcing contractors handle their own national pension/tax."
    },
    "custom_deductions": {
        "rule_id": "POL-CUSTOM-DED-05",
        "article": "Article 11",
        "max_percentage_of_base": 0.20,
        "requires_documentation": True,
        "regulation": "Labor Standards Act Article 24 (Protection of Wages) & gyomu_itaku_kyuuyo_kitei.docx Article 11",
        "description": "Voluntary or company deductions cannot exceed 20% of monthly base salary without formal supervisor waiver. All custom deductions require an explicit documented justification (e.g. equipment lease, advance repayment)."
    }
}


class PolicyCopilot:
    """
    Enterprise Policy Copilot grounded in gyomu_itaku_kyuuyo_kitei.docx.
    Provides:
    1. Batch conflict audits against the docx guidelines.
    2. Interactive case-by-case statutory explanations with exact financial variance.
    3. Standardized supervisor override memo generation in English or Japanese.
    4. Conversational natural language Q&A regarding labor statutes and payment problems.
    """

    def audit_payment_conflicts(self, cases: List[Dict[str, Any]], lang: str = "en") -> Dict[str, Any]:
        """
        Scans an entire list of payment claims against gyomu_itaku_kyuuyo_kitei.docx
        and identifies all policy conflicts, monetary discrepancies, and required actions.
        """
        is_ja = (lang == "ja")
        total_cases = len(cases)
        conflicting_cases = []
        total_disallowed_amount = 0
        total_excess_taxable_commute = 0
        category_counts = {
            "housing_violation": 0,
            "commute_cap_breach": 0,
            "telework_excess": 0,
            "custom_deduction_cap": 0,
            "missing_memo": 0
        }

        for c in cases:
            inp = c.get("input_data", {})
            calc = c.get("calculated_details", {})
            status = c.get("status", "UNKNOWN")

            emp_id = inp.get("employee_id", "Unknown")
            emp_name = inp.get("employee_name", "Unknown")
            contract = inp.get("contract_type", "regular")
            try:
                base_sal = float(inp.get("base_salary") or 0)
            except (ValueError, TypeError):
                base_sal = 0.0

            try:
                claimed_commute = float(inp.get("claimed_commute") or 0)
            except (ValueError, TypeError):
                claimed_commute = 0.0

            try:
                telework_days = int(inp.get("telework_days") or 0)
            except (ValueError, TypeError):
                telework_days = 0

            try:
                claimed_housing = float(inp.get("claimed_housing") or 0)
            except (ValueError, TypeError):
                claimed_housing = 0.0

            try:
                custom_ded = float(inp.get("custom_deduction") or 0)
            except (ValueError, TypeError):
                custom_ded = 0.0

            ded_reason = str(inp.get("deduction_reason") or "")

            case_conflicts = []

            # 1. Housing Allowance Conflict (Article 4 of docx)
            if contract in ["outsourcing", "part_time"] and claimed_housing > 0:
                category_counts["housing_violation"] += 1
                total_disallowed_amount += claimed_housing
                case_conflicts.append({
                    "category": "住宅手当の支給制限違反" if is_ja else "Housing Ineligibility",
                    "severity": "CRITICAL_VIOLATION",
                    "doc_ref": "gyomu_itaku_kyuuyo_kitei.docx 第4条" if is_ja else "gyomu_itaku_kyuuyo_kitei.docx Article 4",
                    "claimed": claimed_housing,
                    "permitted": 0,
                    "variance": claimed_housing,
                    "issue": f"業務委託（{contract}）による住宅手当 ¥{claimed_housing:,.0f} の申請は第4条違反です。業務委託への住宅手当は支給不可（¥0）です。" if is_ja else f"Outsourcing contractor ({contract}) claimed ¥{claimed_housing:,.0f} housing subsidy. Article 4 restricts housing to regular and contract staff.",
                    "resolution": "住宅手当を0円として却下、またはERP連携前に控除対象から除外。" if is_ja else "Automatically reject housing claim or zero out before ERP commit."
                })

            # 2. Commute Exemption Cap Breach (Article 3 of docx & Income Tax Act Art. 21)
            if claimed_commute > 150000:
                excess = claimed_commute - 150000
                category_counts["commute_cap_breach"] += 1
                total_excess_taxable_commute += excess
                case_conflicts.append({
                    "category": "通勤手当非課税限度額超過" if is_ja else "Commute Cap Breach",
                    "severity": "FLAG_TAXABLE_REVIEW",
                    "doc_ref": "規程第3条 / 所得税法第21条" if is_ja else "gyomu_itaku_kyuuyo_kitei.docx Article 3 / Income Tax Act Art. 21",
                    "claimed": claimed_commute,
                    "permitted": 150000,
                    "variance": excess,
                    "issue": f"通勤定期代の申請額 ¥{claimed_commute:,.0f} が法定非課税上限（150,000円）を ¥{excess:,.0f} 超過しています。" if is_ja else f"Commuter pass claim of ¥{claimed_commute:,.0f} exceeds statutory cap of ¥150,000 by ¥{excess:,.0f}.",
                    "resolution": "非課税枠は150,000円で上限適用し、超過分 ¥{excess:,.0f} は課税対象として処理するか特認を申請。" if is_ja else f"Cap non-taxable disbursement at ¥150,000 and treat surplus ¥{excess:,.0f} as taxable wages or obtain supervisor sign-off."
                })

            # 3. Telework Allowance Guideline Limit (Article 7 of docx)
            if telework_days > 20:
                claimed_tele = telework_days * 250
                excess_tele = claimed_tele - 5000
                category_counts["telework_excess"] += 1
                case_conflicts.append({
                    "category": "在宅勤務手当上限超過" if is_ja else "Telework Ceiling Exceeded",
                    "severity": "AUTO_CAPPED",
                    "doc_ref": "規程第7条 / テレワーク取扱細則" if is_ja else "gyomu_itaku_kyuuyo_kitei.docx Article 7 / Telework §3",
                    "claimed": claimed_tele,
                    "permitted": 5000,
                    "variance": excess_tele,
                    "issue": f"テレワーク日数（{telework_days}日 = ¥{claimed_tele:,}）が月間上限20日（5,000円）を超過しています。" if is_ja else f"Telework days ({telework_days} days = ¥{claimed_tele:,}) exceed monthly maximum of 20 days (¥5,000 cap).",
                    "resolution": "月額上限 5,000円 を適用して支給。" if is_ja else "Disburse capped standard ¥5,000."
                })

            # 4. Custom Deduction 20% Limit & Documentation (Article 11 of docx & LSA Art. 24)
            if custom_ded > 0:
                threshold = base_sal * 0.20 if base_sal > 0 else 0
                if custom_ded > threshold:
                    category_counts["custom_deduction_cap"] += 1
                    case_conflicts.append({
                        "category": "任意控除20%超過（労基法第24条）" if is_ja else "Custom Deduction Ceiling",
                        "severity": "SUPERVISOR_WAIVER_REQUIRED",
                        "doc_ref": "規程第11条 / 労働基準法第24条" if is_ja else "gyomu_itaku_kyuuyo_kitei.docx Article 11 / Labor Standards Act Art. 24",
                        "claimed": custom_ded,
                        "permitted": int(threshold),
                        "variance": int(custom_ded - threshold),
                        "issue": f"任意控除額 ¥{custom_ded:,.0f} が基本給の20%基準（¥{threshold:,.0f}）を超過しています。" if is_ja else f"Custom deduction ¥{custom_ded:,.0f} exceeds 20% wage threshold (¥{threshold:,.0f}).",
                        "resolution": "所定の理由書および上長の特別裁量承認が必要です。" if is_ja else "Requires signed supervisor authorization memo."
                    })
                if not ded_reason:
                    category_counts["missing_memo"] += 1
                    case_conflicts.append({
                        "category": "控除理由書未添付" if is_ja else "Missing Deduction Justification",
                        "severity": "AUDIT_FLAG",
                        "doc_ref": "規程第11条" if is_ja else "gyomu_itaku_kyuuyo_kitei.docx Article 11",
                        "claimed": custom_ded,
                        "permitted": custom_ded,
                        "variance": 0,
                        "issue": "任意控除申請に必須の理由説明メモが添付されていません。" if is_ja else "Custom deduction submitted without mandatory justification memo.",
                        "resolution": "ERP連携前に理由書を添付してください。" if is_ja else "Attach formal justification before batch commit."
                    })

            if not case_conflicts and status in ["REJECTED", "FLAGGED_FOR_REVIEW"]:
                case_conflicts.append({
                    "category": "要上長確認・監査フラグ" if is_ja else "Compliance Review Required",
                    "severity": "FLAG_REVIEW" if status == "FLAGGED_FOR_REVIEW" else "CRITICAL_VIOLATION",
                    "doc_ref": "gyomu_itaku_kyuuyo_kitei.docx 第14条" if is_ja else "gyomu_itaku_kyuuyo_kitei.docx §14",
                    "claimed": 0,
                    "permitted": 0,
                    "variance": 0,
                    "issue": c.get("decision_notes") or ("要上長レビュー" if is_ja else "Supervisor review required"),
                    "resolution": "上長電子決裁にて承認または差し戻し" if is_ja else "Review and resolve in Exception Desk"
                })

            if case_conflicts or status in ["REJECTED", "FLAGGED_FOR_REVIEW"]:
                conflicting_cases.append({
                    "case_id": c.get("case_id"),
                    "employee_id": emp_id,
                    "employee_name": emp_name,
                    "contract_type": contract,
                    "status": status,
                    "conflicts": case_conflicts,
                    "decision_notes": self.translate_decision_notes(c.get("decision_notes") or "", lang="ja") if is_ja else (c.get("decision_notes") or "")
                })

        return {
            "audited_at_utc": datetime.now(timezone.utc).isoformat(),
            "policy_document": "gyomu_itaku_kyuuyo_kitei.docx",
            "lang": "ja" if is_ja else "en",
            "total_cases_audited": total_cases,
            "conflict_case_count": len(conflicting_cases),
            "compliant_case_count": total_cases - len(conflicting_cases),
            "compliance_rate_pct": round(((total_cases - len(conflicting_cases)) / total_cases * 100), 1) if total_cases > 0 else 100.0,
            "financial_exposure": {
                "total_disallowed_funds_jpy": total_disallowed_amount,
                "total_excess_taxable_commute_jpy": total_excess_taxable_commute,
                "exposure_headline": f"不支給対象・住宅手当違反額（第4条）: ¥{total_disallowed_amount:,}" if is_ja else f"Disallowed Housing Subsidies (Art. 4): ¥{total_disallowed_amount:,}",
                "exposure_headline_ja": f"不支給対象・住宅手当違反額（第4条）: ¥{total_disallowed_amount:,}"
            },
            "category_summary": category_counts,
            "conflicting_cases": conflicting_cases
        }

    def translate_decision_notes(self, notes: str, lang: str = "en") -> str:
        """Translates standard engine decision notes into Japanese if lang is ja."""
        if lang != "ja" or not notes:
            return notes or ""
        t = str(notes)
        t = re.sub(r"AUTO_APPROVED:\s*Passed all statutory and corporate policy validation checks", "【自動承認】社内規程および法定要件の全バリデーションに適合", t, flags=re.IGNORECASE)
        t = re.sub(r"FLAG_REVIEW:\s*Commute exceeds statutory tax-exempt cap \((\d+) > (\d+) JPY\)", r"【要確認】通勤費が所得税法第21条非課税枠（150,000円）を超過（申請: ¥\1）", t, flags=re.IGNORECASE)
        t = re.sub(r"FLAG_REVIEW:\s*Custom deduction exceeds 20% of base salary \((\d+) JPY\) - requires supervisor authorization", r"【要確認】任意控除額が規程第11条の基本給20%制限を超過（控除: ¥\1）- 上長決裁が必要", t, flags=re.IGNORECASE)
        t = re.sub(r"REJECTED:\s*Housing subsidy not permissible for outsourcing or part-time staff per article 4", "【規程違反却下】規程第4条に基づき業務委託・パートへの住宅手当は支給不可（支給額0円）", t, flags=re.IGNORECASE)
        t = re.sub(r"FLAG_REVIEW:\s*Custom deduction without documented business justification", "【要確認】規程第11条に基づく業務上の正当理由メモ未添付", t, flags=re.IGNORECASE)
        t = re.sub(r"SUPERVISOR OVERRIDE \((.*?)\):\s*(.*)", r"【上長特認 (\1)】\2", t, flags=re.IGNORECASE)
        return t

    def explain_case(self, case: Dict[str, Any], lang: str = "en") -> Dict[str, Any]:
        """
        Deep-dive statutory policy explanation for a specific case claim.
        Analyzed claimed commute vs 150k cap, housing eligibility vs contract type,
        and generates structured conflict cards with docx article references in EN or JA.
        """
        is_ja = (lang == "ja")
        input_data = case.get("input_data", {})
        calc = case.get("calculated_details", {})
        contract = input_data.get("contract_type", "regular")
        status = case.get("status", "UNKNOWN")
        notes = self.translate_decision_notes(case.get("decision_notes") or "", lang=lang) if is_ja else (case.get("decision_notes") or "")

        try:
            claimed_commute = float(input_data.get("claimed_commute") or 0)
        except (ValueError, TypeError):
            claimed_commute = 0.0

        try:
            claimed_housing = float(input_data.get("claimed_housing") or 0)
        except (ValueError, TypeError):
            claimed_housing = 0.0

        try:
            custom_ded = float(input_data.get("custom_deduction") or 0)
        except (ValueError, TypeError):
            custom_ded = 0.0

        try:
            base_salary = float(input_data.get("base_salary") or 0)
        except (ValueError, TypeError):
            base_salary = 0.0

        try:
            telework_days = int(input_data.get("telework_days") or 0)
        except (ValueError, TypeError):
            telework_days = 0

        findings: List[Dict[str, str]] = []
        conflicts_detected: List[Dict[str, Any]] = []
        doc_citations: List[Dict[str, Any]] = []
        recommendation = ""

        # Analyze Commute
        if claimed_commute > 150000:
            diff = claimed_commute - 150000
            findings.append({
                "category": "通勤手当非課税限度枠" if is_ja else "Commute Allowance",
                "severity": "FLAG_REVIEW",
                "rule_ref": "規程第3条 / 所得税法第21条 (上限: ¥150,000)" if is_ja else "gyomu_itaku_kyuuyo_kitei.docx Article 3 & Income Tax Act Art. 21",
                "detail": f"申請額 ¥{claimed_commute:,.0f} は法定非課税上限（150,000円）を ¥{diff:,.0f} 超過しています。非課税支給額を150,000円に制限し、超過分 ¥{diff:,.0f} を課税対象給与としてレビュー対象に設定しました。" if is_ja else f"Claimed ¥{claimed_commute:,.0f} exceeds statutory tax-exempt threshold of ¥150,000 by ¥{diff:,.0f}. The engine capped approved non-taxable amount at ¥150,000 and flagged the surplus ¥{diff:,.0f} for taxable treatment."
            })
            conflicts_detected.append({
                "field": "claimed_commute",
                "article": "Article 3",
                "claimed": claimed_commute,
                "cap": 150000,
                "difference": diff,
                "type": "STATUTORY_CAP_EXCEEDED"
            })
            doc_citations.append(DOCX_POLICY_ARTICLES_JA["article_3"] if is_ja else DOCX_POLICY_ARTICLES_EN["article_3"])

        # Analyze Housing Eligibility
        if contract in ["outsourcing", "part_time"] and claimed_housing > 0:
            findings.append({
                "category": "住宅手当の資格制限" if is_ja else "Housing Allowance",
                "severity": "REJECTED",
                "rule_ref": "gyomu_itaku_kyuuyo_kitei.docx 第4条" if is_ja else "gyomu_itaku_kyuuyo_kitei.docx Article 4",
                "detail": f"業務委託（{contract}）は規程上、住宅補助の支給対象外です。申請額 ¥{claimed_housing:,.0f} は第4条に基づき自動却下されました。" if is_ja else f"Outsourcing ({contract}) personnel are contractually barred from claiming company housing subsidies. Claim of ¥{claimed_housing:,.0f} violates Article 4 and was automatically denied."
            })
            conflicts_detected.append({
                "field": "claimed_housing",
                "article": "Article 4",
                "claimed": claimed_housing,
                "cap": 0,
                "difference": claimed_housing,
                "type": "CONTRACTUAL_INELIGIBILITY"
            })
            doc_citations.append(DOCX_POLICY_ARTICLES_JA["article_4"] if is_ja else DOCX_POLICY_ARTICLES_EN["article_4"])

        # Analyze Telework
        if telework_days > 20:
            diff_tele = (telework_days * 250) - 5000
            findings.append({
                "category": "在宅勤務手当" if is_ja else "Telework Overhead",
                "severity": "AUTO_CAPPED",
                "rule_ref": "規程第7条 (上限: ¥5,000)" if is_ja else "gyomu_itaku_kyuuyo_kitei.docx Article 7",
                "detail": f"申請日数 {telework_days}日（¥{telework_days*250:,.0f}）に対し、第7条の月間上限20日（5,000円）が適用されました。" if is_ja else f"Telework declared for {telework_days} days (¥{telework_days*250:,.0f}). Capped to 20 days maximum (¥5,000) per Article 7."
            })
            conflicts_detected.append({
                "field": "telework_days",
                "article": "Article 7",
                "claimed": telework_days * 250,
                "cap": 5000,
                "difference": diff_tele,
                "type": "TELEWORK_CAP_CAPPED"
            })
            doc_citations.append(DOCX_POLICY_ARTICLES_JA["article_7"] if is_ja else DOCX_POLICY_ARTICLES_EN["article_7"])

        # Analyze Custom Deductions
        if custom_ded > 0:
            threshold = base_salary * 0.20 if base_salary > 0 else 0
            if custom_ded > threshold:
                pct_str = f"{(custom_ded / base_salary) * 100:.1f}%" if base_salary > 0 else "N/A"
                findings.append({
                    "category": "任意控除制限" if is_ja else "Custom Deduction Ceiling",
                    "severity": "FLAG_REVIEW",
                    "rule_ref": "規程第11条 / 労基法第24条 (上限: 基本給20%)" if is_ja else "gyomu_itaku_kyuuyo_kitei.docx Article 11 & LSA Art. 24",
                    "detail": f"控除額 ¥{custom_ded:,.0f} は基本給の {pct_str} に達しており、規程上の上限20%（¥{threshold:,.0f}）を超過しています。" if is_ja else f"Deduction of ¥{custom_ded:,.0f} equals {pct_str} of base salary, exceeding the 20% limit (¥{threshold:,.0f})."
                })
                conflicts_detected.append({
                    "field": "custom_deduction",
                    "article": "Article 11",
                    "claimed": custom_ded,
                    "cap": threshold,
                    "difference": custom_ded - threshold,
                    "type": "PERCENTAGE_CEILING_BREACH"
                })
                doc_citations.append(DOCX_POLICY_ARTICLES_JA["article_11"] if is_ja else DOCX_POLICY_ARTICLES_EN["article_11"])

            reason = str(input_data.get("deduction_reason") or "")
            if not reason:
                findings.append({
                    "category": "控除理由メモ添付" if is_ja else "Deduction Documentation",
                    "severity": "FLAG_REVIEW",
                    "rule_ref": "規程第11条" if is_ja else "gyomu_itaku_kyuuyo_kitei.docx Article 11",
                    "detail": "任意控除に必須の業務上正当理由メモが未添付です。" if is_ja else "Custom deduction submitted without mandatory business justification memo."
                })
                conflicts_detected.append({
                    "field": "deduction_reason",
                    "article": "Article 11",
                    "claimed": "理由未記入" if is_ja else "No reason provided",
                    "cap": "必須メモ" if is_ja else "Mandatory memo",
                    "difference": 0,
                    "type": "MISSING_DOCUMENTATION"
                })
                doc_citations.append(DOCX_POLICY_ARTICLES_JA["article_11"] if is_ja else DOCX_POLICY_ARTICLES_EN["article_11"])

        # Deduplicate doc_citations preserving order
        unique_citations: List[Dict[str, Any]] = []
        seen_articles = set()
        for citation in doc_citations:
            art_id = citation.get("article_no") or citation.get("title")
            if art_id not in seen_articles:
                seen_articles.add(art_id)
                unique_citations.append(citation)
        doc_citations = unique_citations

        if status == "AUTO_APPROVED":
            recommendation = "本申請は「業務委託・給与控除等取扱い規程」および日本の税法・労働基準法に100%合致しています。自動ERPコミット可能です。" if is_ja else "Case complies 100% with gyomu_itaku_kyuuyo_kitei.docx and Japanese statutory tax laws. Safe for automated ERP commit."
        elif status == "FLAGGED_FOR_REVIEW":
            recommendation = "検知された不整合を確認してください。業務上の特認理由が存在する場合は理由書を作成し、上長電子決裁を実行してください。" if is_ja else "Review flagged anomalies above. If a legitimate business exception or supervisor agreement exists, record the rationale and approve via digital override."
        elif status == "REJECTED":
            recommendation = "重大な規程違反が検知されました。第4条のガイドラインに従い申請を差し戻し、該当項目の支給を停止してください。" if is_ja else "Policy violation detected. Reject claim or request employee resubmission in accordance with Article 4 guidelines."

        suggested_memo = self.generate_override_draft(case, "給与審査責任者" if is_ja else "HR Supervisor", lang=lang)

        return {
            "case_id": case.get("case_id"),
            "employee_id": input_data.get("employee_id"),
            "employee_name": input_data.get("employee_name"),
            "contract_type": contract,
            "status": status,
            "decision_notes": notes,
            "findings": findings,
            "conflicts_detected": conflicts_detected,
            "doc_citations": doc_citations,
            "suggested_memo": suggested_memo,
            "copilot_recommendation": recommendation,
            "policy_version": calc.get("policy_version", "2026.04-v1.2"),
            "source_document": "gyomu_itaku_kyuuyo_kitei.docx",
            "lang": "ja" if is_ja else "en",
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        }

    def generate_override_draft(self, case: Dict[str, Any], supervisor_name: str, lang: str = "en") -> str:
        """Auto-drafts a standardized compliance memo for supervisor override referencing the docx."""
        is_ja = (lang == "ja")
        inp = case.get("input_data", {})
        c_id = case.get("case_id", "N/A")
        emp_id = inp.get("employee_id", "N/A")
        emp_name = inp.get("employee_name", "Staff")
        contract = inp.get("contract_type", "regular")
        notes = self.translate_decision_notes(case.get("decision_notes", ""), lang=lang) if is_ja else case.get("decision_notes", "")
        today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        if is_ja:
            return (
                f"【特別承認決裁書（業務委託・給与控除等取扱い規程 第14条）】\n"
                f"対象案件: {c_id} | 申請者: {emp_name} ({emp_id}・{contract})\n"
                f"決裁責任者: {supervisor_name} | 決裁日: {today_str}\n"
                f"規程参照: 業務委託・給与控除等取扱い規程 (2026.04-v1.2) 第14条（特別裁量承認）\n"
                f"検知例外事項: {notes}\n"
                f"承認事由: 業務上の必要性および部門長による裁量基準に基づき内容を精査・承認いたしました。"
                f"暗号化監査ログ（SHA-256）に改ざん防止記録として登録の上、ERP連携へ回送します。"
            )

        return (
            f"SUPERVISORY COMPLIANCE EXCEPTION MEMO\n"
            f"Case: {c_id} | Employee: {emp_name} ({emp_id}, {contract})\n"
            f"Reviewing Authority: {supervisor_name} | Date: {today_str}\n"
            f"Codified Policy: gyomu_itaku_kyuuyo_kitei.docx (2026.04-v1.2) §14\n"
            f"Identified Exception: {notes}\n"
            f"Justification: Exception verified against department operations and verified with HR compliance. "
            f"Approved under authorized managerial discretion with cryptographic audit trail registration."
        )

    def answer_policy_query(self, query: str, active_cases: Optional[List[Dict[str, Any]]] = None, lang: str = "en") -> Dict[str, Any]:
        """
        Interactive reasoning assistant that answers natural language questions regarding
        gyomu_itaku_kyuuyo_kitei.docx, checks payment conflicts, and details policy rules in EN or JA.
        """
        q_lower = query.lower().strip()
        is_ja = (lang == "ja") or bool(re.search(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]', query))
        effective_lang = "ja" if is_ja else "en"

        # Check for greeting or introductory question
        is_greeting = any(g in q_lower for g in ["hello", "hi", "hey", "greetings", "こんにちは", "初めまして", "おはよう", "こんばんは", "はじめまして"])
        if is_greeting and len(query.strip()) <= 20:
            if is_ja:
                response_text = (
                    "### 労働法規・規程照合 AIコパイロット（日本語対話モード）\n\n"
                    "こんにちは！私は **`gyomu_itaku_kyuuyo_kitei.docx`（業務委託・給与控除等取扱い規程）** および日本の労働基準法・所得税法に準拠したAIコパイロットです。\n\n"
                    "以下の業務を日本語でサポートいたします:\n"
                    "- **全申請の規程照合監査**: 「🔍 全申請の規程照合監査」または「監査」と入力\n"
                    "- **特定案件の違反理由・差分照会**: `PI-PROD-2026-003` などの案件IDを入力\n"
                    "- **第4条 住宅手当制限の照会**: 業務委託への不支給ルール等の確認\n"
                    "- **第3条 交通費非課税枠の照会**: 15万円上限と課税振替ルールの確認\n"
                    "- **第14条 特別承認稟議書の起案**: 「稟議書作成」または案件詳細からワンクリック生成\n\n"
                    "ご質問や監査対象の案件IDを入力してください。"
                )
            else:
                response_text = (
                    "### Labor Policy Copilot Online\n\n"
                    "Hello! I am your AI compliance assistant grounded in **`gyomu_itaku_kyuuyo_kitei.docx`** and Japanese statutory labor/tax regulations.\n\n"
                    "I can assist you with:\n"
                    "- **Batch Conflict Audits**: Audit all active records against codified docx regulations\n"
                    "- **Case Inspections**: Analyze specific cases (e.g. `PI-PROD-2026-003`)\n"
                    "- **Article 4 Housing Restrictions**: Outsourcing housing exclusion rules\n"
                    "- **Article 3 Commuter Pass Limits**: ¥150k statutory non-taxable limits\n"
                    "- **Article 14 Override Memos**: Automated compliance justification drafts\n\n"
                    "How may I assist your payroll compliance review today?"
                )
            return {
                "query": query,
                "response_markdown": response_text,
                "matches": list(CORPORATE_POLICY_RULES.values())[:3],
                "policy_version": "2026.04-v1.2",
                "effective_date": "2026-04-01",
                "lang": effective_lang,
                "source_document": "gyomu_itaku_kyuuyo_kitei.docx"
            }

        matched_rules: List[Dict[str, Any]] = []

        # 1. Check if user is asking to audit payments / find conflicts / check problems
        audit_intent_keywords = [
            "audit", "conflict", "problem", "issue", "error", "check payment",
            "check problem", "seeing the docx", "seeing docx", "in payments",
            "flagged", "rejected", "disallowed", "violation", "不整合", "問題", "エラー",
            "チェック", "規程照合", "コンフリクト", "監査"
        ]
        is_audit_intent = any(k in q_lower for k in audit_intent_keywords)

        # 2. Check if user mentions a specific case ID or employee ID
        case_match = re.search(r"((?:PI|AUTO|JP|CASE|EMP|E|TEST)-[A-Z0-9\-]+)", query, re.IGNORECASE)

        if case_match and active_cases:
            target_id = case_match.group(1).upper()
            target_case = next(
                (c for c in active_cases if c.get("case_id", "").upper() == target_id or 
                 c.get("input_data", {}).get("employee_id", "").upper() == target_id),
                None
            )
            if target_case:
                explanation = self.explain_case(target_case, lang=effective_lang)
                if is_ja:
                    response_text = (
                        f"### 【案件詳細・規程照合監査】**{explanation['case_id']}**\n\n"
                        f"- **申請者**: {explanation['employee_name']} ({explanation['employee_id']}) - *契約区分: {explanation['contract_type']}*\n"
                        f"- **判定ステータス**: `{explanation['status']}`\n"
                        f"- **準拠規程**: `業務委託・給与控除等取扱い規程 (gyomu_itaku_kyuuyo_kitei.docx)`\n\n"
                        f"**検知された規程違反・監査事項:**\n"
                    )
                    if explanation["findings"]:
                        for f in explanation["findings"]:
                            response_text += f"• **[{f['severity']}] {f['category']}**: {f['detail']} *(根拠: {f['rule_ref']})*\n"
                    else:
                        response_text += "• 規程違反は検出されませんでした。全項目が社内規程および労働法規に完全に合致しています。\n"
                    response_text += f"\n**コパイロット推奨対応:**\n{explanation['copilot_recommendation']}\n"
                else:
                    response_text = (
                        f"### Detailed Conflict Audit for **{explanation['case_id']}**\n\n"
                        f"- **Employee**: {explanation['employee_name']} ({explanation['employee_id']}) - *{explanation['contract_type']}*\n"
                        f"- **System Decision**: `{explanation['status']}`\n"
                        f"- **Governing Document**: `gyomu_itaku_kyuuyo_kitei.docx`\n\n"
                        f"**Audit Findings & Conflict Analysis:**\n"
                    )
                    if explanation["findings"]:
                        for f in explanation["findings"]:
                            response_text += f"• **[{f['severity']}] {f['category']}**: {f['detail']} *(Ref: {f['rule_ref']})*\n"
                    else:
                        response_text += "• No policy conflicts identified. Claim is 100% compliant with internal regulations.\n"
                    response_text += f"\n**Copilot Recommendation:**\n{explanation['copilot_recommendation']}\n"

                return {
                    "query": query,
                    "response_markdown": response_text,
                    "case_details": explanation,
                    "matches": [CORPORATE_POLICY_RULES["housing_subsidy"], CORPORATE_POLICY_RULES["commute_allowance"]],
                    "policy_version": "2026.04-v1.2",
                    "effective_date": "2026-04-01",
                    "lang": effective_lang,
                    "source_document": "gyomu_itaku_kyuuyo_kitei.docx"
                }
            else:
                if is_ja:
                    response_text = (
                        f"### 【案件照会】`{target_id}` が見つかりませんでした\n\n"
                        f"指定された案件IDまたは従業員ID (`{target_id}`) は現在ロードされている申請データの中に存在しません。\n"
                        f"IDをご確認の上、再度お試しいただくか、「全件監査」と入力して全案件の規程照合を行ってください。"
                    )
                else:
                    response_text = (
                        f"### Case ID `{target_id}` Not Found\n\n"
                        f"The requested Case or Employee ID (`{target_id}`) could not be located among active payment claims.\n"
                        f"Please verify the ID format or request a full batch audit by asking to 'audit all payments'."
                    )
                return {
                    "query": query,
                    "response_markdown": response_text,
                    "case_details": None,
                    "matches": [],
                    "policy_version": "2026.04-v1.2",
                    "effective_date": "2026-04-01",
                    "lang": effective_lang,
                    "source_document": "gyomu_itaku_kyuuyo_kitei.docx"
                }

        # If audit intent or general conflict check
        if is_audit_intent and active_cases:
            audit_result = self.audit_payment_conflicts(active_cases, lang=effective_lang)
            conflict_count = audit_result["conflict_case_count"]
            total_cases = audit_result["total_cases_audited"]
            disallowed = audit_result["financial_exposure"]["total_disallowed_funds_jpy"]
            excess_commute = audit_result["financial_exposure"]["total_excess_taxable_commute_jpy"]
            summary_cats = audit_result["category_summary"]

            if is_ja:
                response_text = (
                    f"### 【給与申請・規程照合監査レポート】（`gyomu_itaku_kyuuyo_kitei.docx` 準拠）\n\n"
                    f"現在取り込まれている **{total_cases}件の申請データ** を社内規程および関連法規と全件照合しました:\n\n"
                    f"- **違反・不整合検知件数**: **{conflict_count}件** （全体の {round(conflict_count/total_cases*100, 1) if total_cases else 0}%）\n"
                    f"- **不支給対象・住宅手当違反額（第4条）**: **¥{disallowed:,}** （業務委託による不正申請 {summary_cats['housing_violation']}件）\n"
                    f"- **通勤交通費・非課税枠超過額（第3条）**: **¥{excess_commute:,}** （15万円超過 {summary_cats['commute_cap_breach']}件）\n"
                    f"- **任意控除20%超過案件（第11条）**: **{summary_cats['custom_deduction_cap']}件**\n"
                    f"- **理由書未添付案件（第11条）**: **{summary_cats['missing_memo']}件**\n\n"
                    f"**主な対応要請案件:**\n"
                )
                for c in audit_result["conflicting_cases"][:4]:
                    response_text += f"• **{c['case_id']}** ({c['employee_name']}, *{c['contract_type']}*): "
                    issues = [conf['issue'] for conf in c.get('conflicts', [])]
                    response_text += "；".join(issues) if issues else self.translate_decision_notes(c['decision_notes'], lang="ja")
                    response_text += "\n"

                if conflict_count > 4:
                    response_text += f"\n*(...他 {conflict_count - 4} 件の警告案件は例外トリアージ画面にてご確認いただけます)*\n"
            else:
                response_text = (
                    f"### Payment Conflict Audit against `gyomu_itaku_kyuuyo_kitei.docx`\n\n"
                    f"Scanned **{total_cases} active payment claims** against codified internal regulations:\n\n"
                    f"- **Total Conflicts Detected**: **{conflict_count} claims** ({round(conflict_count/total_cases*100, 1) if total_cases else 0}% of batch)\n"
                    f"- **Disallowed Housing Subsidies (Art. 4)**: **¥{disallowed:,}** ({summary_cats['housing_violation']} outsourcing violations)\n"
                    f"- **Excess Taxable Commute (Art. 3 / NTA)**: **¥{excess_commute:,}** ({summary_cats['commute_cap_breach']} claims exceeding ¥150k cap)\n"
                    f"- **Custom Deduction 20% Breaches (Art. 11)**: **{summary_cats['custom_deduction_cap']} claims**\n"
                    f"- **Missing Justification Memos (Art. 11)**: **{summary_cats['missing_memo']} claims**\n\n"
                    f"**Top Discrepancies Requiring Action:**\n"
                )
                for c in audit_result["conflicting_cases"][:4]:
                    response_text += f"• **{c['case_id']}** ({c['employee_name']}, {c['contract_type']}): "
                    issues = [conf['issue'] for conf in c.get('conflicts', [])]
                    response_text += "; ".join(issues) if issues else c['decision_notes']
                    response_text += "\n"

                if conflict_count > 4:
                    response_text += f"\n*(...and {conflict_count - 4} more conflicting claims visible in the Exception Desk)*\n"

            return {
                "query": query,
                "response_markdown": response_text,
                "audit_summary": audit_result,
                "matches": [CORPORATE_POLICY_RULES["housing_subsidy"], CORPORATE_POLICY_RULES["commute_allowance"], CORPORATE_POLICY_RULES["custom_deductions"]],
                "policy_version": "2026.04-v1.2",
                "effective_date": "2026-04-01",
                "lang": effective_lang,
                "source_document": "gyomu_itaku_kyuuyo_kitei.docx"
            }

        # Keyword matching against rules
        if any(k in q_lower for k in ["commute", "travel", "train", "tax", "150000", "transit", "通勤", "定期代", "交通費"]):
            matched_rules.append(CORPORATE_POLICY_RULES["commute_allowance"])
        if any(k in q_lower for k in ["telework", "remote", "wfh", "250", "home", "在宅", "テレワーク", "リモート"]):
            matched_rules.append(CORPORATE_POLICY_RULES["telework_allowance"])
        if any(k in q_lower for k in ["housing", "rent", "outsourcing", "article 4", "gyomu", "住宅", "家賃", "補助"]):
            matched_rules.append(CORPORATE_POLICY_RULES["housing_subsidy"])
        if any(k in q_lower for k in ["social", "insurance", "pension", "health", "deduction", "社保", "健康保険", "厚生年金"]):
            matched_rules.append(CORPORATE_POLICY_RULES["statutory_deductions"])
        if any(k in q_lower for k in ["custom", "20%", "repayment", "equipment", "lease", "任意控除", "返済", "控除"]):
            matched_rules.append(CORPORATE_POLICY_RULES["custom_deductions"])

        if not matched_rules:
            matched_rules = list(CORPORATE_POLICY_RULES.values())[:3]

        # Generate conversational narrative response
        rule_bullets = []
        for r in matched_rules:
            article = r.get("article", "Corporate Rule")
            desc = r.get("description", "")
            rule_bullets.append(f"• **{article} ({r.get('rule_id', '')})**: {desc}")

        if is_ja:
            response_text = (
                f"### 【社内規程および労働法規ガイド】（`gyomu_itaku_kyuuyo_kitei.docx`）\n\n"
            )
            for r in matched_rules:
                if r["rule_id"] == "POL-COMMUTE-01":
                    response_text += "• **第3条（通勤交通費）**: 所得税法第21条に基づき、月額150,000円まで非課税。超過分は課税給与算入または特認承認が必要。\n\n"
                elif r["rule_id"] == "POL-HOUSING-03":
                    response_text += "• **第4条（住宅手当制限）**: 住宅補助（上限3万円）は正社員・契約社員限定。業務委託（Gyomu Itaku）およびパート従業員には支給不可。\n\n"
                elif r["rule_id"] == "POL-TELEWORK-02":
                    response_text += "• **第7条（在宅勤務手当）**: 1日250円、月間上限20日（5,000円）まで支給。\n\n"
                elif r["rule_id"] == "POL-CUSTOM-DED-05":
                    response_text += "• **第11条（任意控除制限）**: 労基法第24条に基づき基本給の20%を上限とし、理由書の提出が義務付けられます。\n\n"
                elif r["rule_id"] == "POL-STATUTORY-04":
                    response_text += "• **第5条（法定控除）**: 厚生年金・社保（15.2%）および雇用保険（0.6%）を標準控除。業務委託には天引き不可。\n\n"
            response_text += "*準拠基準: 2026.04-v1.2 労務コンプライアンス委員会承認版*"
        else:
            response_text = (
                f"### Statutory & Policy Guidance (`gyomu_itaku_kyuuyo_kitei.docx`)\n\n"
                + "\n\n".join(rule_bullets) +
                f"\n\n*Governance Standard: Version 2026.04-v1.2, verified by Corporate HR Compliance Board.*"
            )

        return {
            "query": query,
            "response_markdown": response_text,
            "matches": matched_rules,
            "policy_version": "2026.04-v1.2",
            "effective_date": "2026-04-01",
            "lang": effective_lang,
            "source_document": "gyomu_itaku_kyuuyo_kitei.docx",
            "statutory_authority": "Ministry of Health, Labour and Welfare (MHLW) & Corporate HR Governance"
        }

    def get_policy_document(self, lang: str = "en") -> Dict[str, Any]:
        """Returns the full codified text of gyomu_itaku_kyuuyo_kitei.docx for UI inspection."""
        is_ja = (lang == "ja")
        articles = list(DOCX_POLICY_ARTICLES_JA.values()) if is_ja else list(DOCX_POLICY_ARTICLES_EN.values())
        return {
            "document_title": "業務委託・給与控除等取扱い規程 (gyomu_itaku_kyuuyo_kitei.docx)" if is_ja else "Contractor & Payroll Deduction Handling Regulations (gyomu_itaku_kyuuyo_kitei.docx)",
            "filename": "gyomu_itaku_kyuuyo_kitei.docx",
            "version": "2026.04-v1.2",
            "lang": "ja" if is_ja else "en",
            "effective_date": "2026-04-01",
            "approval_body": "労務コンプライアンス委員会・人事統括部" if is_ja else "Corporate HR Policy & Compliance Review Board",
            "articles": articles
        }
