import statistics
from typing import Dict, Any, List
from datetime import datetime


class ROIPrioritizationModel:
    """
    Financial Scenario & Automation Prioritization Model.
    Replaces qualitative scoring with an enterprise business case model
    featuring sensitivity analysis (Conservative, Base Case, Optimistic).
    """

    PROCESS_ATTRIBUTES = {
        "payroll_deduction_adjustment": {
            "display_name": "Payroll Deduction Adjustment",
            "name_ja": "給与控除調整",
            "department": "Human Resources",
            "criticality": 1.4,
            "standardization": 0.90,
            "feasibility": 0.85,
            "risk_score": 1.2,
            "target_automation_rate": 0.85
        },
        "leave_application_processing": {
            "display_name": "Leave Application Processing",
            "name_ja": "育児・産休・有給申請確認",
            "department": "Human Resources",
            "criticality": 1.3,
            "standardization": 0.80,
            "feasibility": 0.80,
            "risk_score": 1.3,
            "target_automation_rate": 0.75
        },
        "onboarding_verification": {
            "display_name": "Onboarding & Allowance Verification",
            "name_ja": "入社照合・手当確認",
            "department": "Human Resources",
            "criticality": 1.25,
            "standardization": 0.75,
            "feasibility": 0.75,
            "risk_score": 1.4,
            "target_automation_rate": 0.70
        },
        "social_insurance_correction": {
            "display_name": "Social Insurance & Pension Correction",
            "name_ja": "社保・年金補正対応",
            "department": "Human Resources",
            "criticality": 1.35,
            "standardization": 0.80,
            "feasibility": 0.75,
            "risk_score": 1.4,
            "target_automation_rate": 0.75
        },
        "resident_tax_confirmation": {
            "display_name": "Resident Tax Confirmation",
            "name_ja": "住民税通知確認",
            "department": "Human Resources",
            "criticality": 1.3,
            "standardization": 0.85,
            "feasibility": 0.80,
            "risk_score": 1.3,
            "target_automation_rate": 0.80
        },
        "expense_settlement_approval": {
            "display_name": "Expense Settlement Approval",
            "name_ja": "経費精算承認",
            "department": "Finance & Accounting",
            "criticality": 1.3,
            "standardization": 0.85,
            "feasibility": 0.80,
            "risk_score": 1.2,
            "target_automation_rate": 0.80
        },
        "inventory_order_management": {
            "display_name": "Inventory & Order Management",
            "name_ja": "受発注・在庫調整",
            "department": "Logistics & Procurement",
            "criticality": 1.2,
            "standardization": 0.75,
            "feasibility": 0.70,
            "risk_score": 1.5,
            "target_automation_rate": 0.70
        },
        "unknown_or_unclassified": {
            "display_name": "Unclassified / Non-Standard",
            "name_ja": "未分類業務",
            "department": "General",
            "criticality": 1.0,
            "standardization": 0.30,
            "feasibility": 0.30,
            "risk_score": 2.0,
            "target_automation_rate": 0.30
        }
    }

    def rank_candidates(self, operational_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        ranked = []

        loaded_hourly_rate_jpy = 3500.0
        initial_build_cost_jpy = 1400000.0   # ~$10,000 USD implementation & validation (1 FDE sprint)
        annual_maint_cost_jpy = 140000.0     # ~$1,000 USD maintenance / hosting

        for lbl, m in operational_metrics.items():
            attr = self.PROCESS_ATTRIBUTES.get(lbl, {
                "name_ja": lbl,
                "department": "General",
                "criticality": 1.0,
                "standardization": 0.5,
                "feasibility": 0.5,
                "risk_score": 1.5,
                "target_automation_rate": 0.5
            })

            tot_sec = m.get("total_duration_seconds", 0.0)
            exec_count = m.get("execution_count", 0)
            mean_sec = m.get("mean_duration_seconds", 60.0)
            pct_of_time = m.get("pct_of_total_time", 0.0)
            auto_rate = attr["target_automation_rate"]
            crit = attr["criticality"]
            feas = attr["feasibility"]
            risk = attr["risk_score"]

            # ---------------------------------------------------------------
            # Composite ROI Score (0-100 basis, four balanced dimensions)
            # ---------------------------------------------------------------
            # D1: Workload share - how much operational time does this consume? (max 40 pts)
            #     Scaled so 50% share -> 40 pts; avoids raw-seconds volume domination.
            volume_score = min(40.0, pct_of_time * 0.80)

            # D2: Engineering feasibility (max 30 pts)
            feas_score = feas * 30.0

            # D3: Risk-inverse - lower risk processes score higher (max 20 pts)
            risk_score_dim = (1.0 / max(0.5, risk)) * 20.0

            # D4: Mean duration bonus - longer per-case tasks yield more savings per automation (max 10 pts)
            duration_bonus = min(10.0, (mean_sec / 120.0) * 10.0)

            # Combine; criticality acts as a modest multiplier (1.0-1.4 range), cap at 100
            roi_score = min(100.0, (volume_score + feas_score + risk_score_dim + duration_bonus) * (crit ** 0.3))

            expected_time_saved_sec = tot_sec * auto_rate

            scenarios = {}
            for s_name, s_params in [
                ("conservative", {"volume": 6000, "auto_rate": max(0.40, auto_rate - 0.20), "review_sec": 35.0, "adoption": 0.70}),
                ("base_case",    {"volume": 9600, "auto_rate": auto_rate,                     "review_sec": 15.0, "adoption": 0.85}),
                ("optimistic",   {"volume": 14400, "auto_rate": min(0.95, auto_rate + 0.10), "review_sec": 8.0,  "adoption": 0.95})
            ]:
                vol = s_params["volume"]
                ar = s_params["auto_rate"]
                adopt = s_params["adoption"]
                rev_sec = s_params["review_sec"]

                baseline_hours = (vol * mean_sec) / 3600.0
                auto_cycle_sec = ar * 2.0 + (1.0 - ar) * rev_sec
                automated_hours = (vol * adopt * auto_cycle_sec + vol * (1.0 - adopt) * mean_sec) / 3600.0
                hours_saved = max(0.0, baseline_hours - automated_hours)

                annual_gross_savings = hours_saved * loaded_hourly_rate_jpy
                annual_net_savings = annual_gross_savings - annual_maint_cost_jpy
                payback_months = (initial_build_cost_jpy / max(1.0, annual_net_savings)) * 12.0 if annual_net_savings > 0 else 99.0
                three_yr_roi = ((3.0 * annual_net_savings - initial_build_cost_jpy) / initial_build_cost_jpy) * 100.0

                scenarios[s_name] = {
                    "annual_volume": vol,
                    "target_automation_rate": ar,
                    "adoption_rate": adopt,
                    "exception_review_seconds": rev_sec,
                    "hours_saved_annual": round(hours_saved, 1),
                    "annual_gross_savings_jpy": round(annual_gross_savings, 0),
                    "annual_net_savings_jpy": round(annual_net_savings, 0),
                    "payback_period_months": round(min(99.0, payback_months), 1),
                    "three_year_roi_pct": round(three_yr_roi, 1)
                }

            time_share = m.get("pct_of_total_time", 0.0)
            ranked.append({
                "rank": 0,
                "process_label": lbl,
                "name_ja": attr["name_ja"],
                "department": attr["department"],
                "execution_count": exec_count,
                "total_duration_minutes": m.get("total_duration_minutes", round(tot_sec / 60.0, 2)),
                "mean_duration_seconds": mean_sec,
                "operators_count": m.get("operators_count", 1),
                "time_share_pct": time_share,
                "active_time_share_pct": time_share,   # alias consumed by dashboard JS
                "automation_potential_pct": int(auto_rate * 100),
                "expected_time_saved_min": round(expected_time_saved_sec / 60.0, 1),
                "feasibility_score": feas,
                "risk_score": risk,
                "roi_score": round(roi_score, 1),
                "financial_scenarios": scenarios
            })

        ranked.sort(key=lambda x: x["roi_score"], reverse=True)
        for idx, item in enumerate(ranked, 1):
            item["rank"] = idx

        return ranked


def calculate_process_metrics(segments: List[Dict[str, Any]]) -> Dict[str, Any]:
    proc_data = {}
    total_sec = 0.0
    for seg in segments:
        lbl = seg.get("label", "unknown_or_unclassified")
        s_time = seg.get("start") or seg.get("start_time")
        e_time = seg.get("end") or seg.get("end_time")
        dur = float(seg.get("duration_seconds", 0.0))
        if dur <= 0.0 and s_time and e_time:
            dt_s = datetime.fromisoformat(s_time.replace("Z", "+00:00"))
            dt_e = datetime.fromisoformat(e_time.replace("Z", "+00:00"))
            dur = max(1.0, (dt_e - dt_s).total_seconds())

        if lbl not in proc_data:
            proc_data[lbl] = []
        proc_data[lbl].append(dur)
        total_sec += dur

    metrics = {}
    for lbl, durs in proc_data.items():
        tot = sum(durs)
        metrics[lbl] = {
            "process_label": lbl,
            "execution_count": len(durs),
            "count": len(durs),
            "total_duration_seconds": round(tot, 1),
            "total_duration_sec": round(tot, 1),
            "total_duration_minutes": round(tot / 60.0, 2),
            "mean_duration_seconds": round(statistics.mean(durs), 1) if durs else 0.0,
            "mean_duration_sec": round(statistics.mean(durs), 1) if durs else 0.0,
            "pct_of_total_time": round((tot / max(1.0, total_sec)) * 100.0, 1),
            "operators_count": 1
        }
    return metrics


def rank_automation_opportunities(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    metrics = calculate_process_metrics(segments)
    model = ROIPrioritizationModel()
    ranked = model.rank_candidates(metrics)
    for r in ranked:
        r["process"] = r["process_label"]
        r["count"] = r["execution_count"]
        r["total_hours"] = round(r["total_duration_minutes"] / 60.0, 2)
        r["feasibility"] = r["feasibility_score"]
        base_s = r.get("financial_scenarios", {}).get("base_case", {})
        r["payback_months"] = base_s.get("payback_period_months", 99.0)
        r["three_year_net_roi_pct"] = base_s.get("three_year_roi_pct", 0.0)
        r["pct_of_total_time"] = r.get("time_share_pct", 0.0)
    return ranked
