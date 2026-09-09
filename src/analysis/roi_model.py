import statistics
import random
from typing import Dict, Any, List, Optional
from datetime import datetime


class ROIPrioritizationModel:
    """
    Enterprise Financial Scenario & Automation Prioritization Model.
    Rigorously synthesizes empirical telemetry metrics (active dwell, frequency,
    variance stability, operator distribution, neural signal confidence) with
    business and statutory factors (standardization, technical feasibility,
    compliance risk, cognitive document lookup friction, and capital payback).
    """

    PROCESS_ATTRIBUTES = {
        "payroll_deduction_adjustment": {
            "display_name": "Payroll Deduction & Adjustment Verification",
            "name_ja": "給与控除調整・給与備考照合",
            "department": "Human Resources",
            "criticality": 1.40,
            "standardization": 0.90,
            "feasibility": 0.85,
            "risk_score": 1.20,
            "target_automation_rate": 0.85,
            "cognitive_lookup_seconds": 28.0  # Document dwell in Word gyomu_itaku_kyuuyo_kitei.docx
        },
        "leave_application_processing": {
            "display_name": "Leave Application & Balance Processing",
            "name_ja": "育児・産休・有給申請確認",
            "department": "Human Resources",
            "criticality": 1.30,
            "standardization": 0.80,
            "feasibility": 0.80,
            "risk_score": 1.30,
            "target_automation_rate": 0.75,
            "cognitive_lookup_seconds": 18.0
        },
        "onboarding_verification": {
            "display_name": "Onboarding & Allowance Verification",
            "name_ja": "入社照合・手当確認",
            "department": "Human Resources",
            "criticality": 1.25,
            "standardization": 0.75,
            "feasibility": 0.75,
            "risk_score": 1.40,
            "target_automation_rate": 0.70,
            "cognitive_lookup_seconds": 22.0
        },
        "social_insurance_correction": {
            "display_name": "Social Insurance & Pension Correction",
            "name_ja": "社保・年金補正対応",
            "department": "Human Resources",
            "criticality": 1.35,
            "standardization": 0.80,
            "feasibility": 0.75,
            "risk_score": 1.40,
            "target_automation_rate": 0.75,
            "cognitive_lookup_seconds": 15.0
        },
        "resident_tax_confirmation": {
            "display_name": "Resident Tax Notification Confirmation",
            "name_ja": "住民税通知確認",
            "department": "Human Resources",
            "criticality": 1.30,
            "standardization": 0.85,
            "feasibility": 0.80,
            "risk_score": 1.30,
            "target_automation_rate": 0.80,
            "cognitive_lookup_seconds": 12.0
        },
        "expense_settlement_approval": {
            "display_name": "Expense Settlement Approval",
            "name_ja": "経費精算承認",
            "department": "Finance & Accounting",
            "criticality": 1.30,
            "standardization": 0.85,
            "feasibility": 0.80,
            "risk_score": 1.20,
            "target_automation_rate": 0.80,
            "cognitive_lookup_seconds": 14.0
        },
        "invoice_approval": {
            "display_name": "Vendor Invoice Approval",
            "name_ja": "請求書承認",
            "department": "Finance & Accounting",
            "criticality": 1.30,
            "standardization": 0.80,
            "feasibility": 0.75,
            "risk_score": 1.30,
            "target_automation_rate": 0.75,
            "cognitive_lookup_seconds": 16.0
        },
        "bank_reconciliation": {
            "display_name": "Bank Account Reconciliation",
            "name_ja": "銀行勘定照合",
            "department": "Finance & Accounting",
            "criticality": 1.35,
            "standardization": 0.85,
            "feasibility": 0.70,
            "risk_score": 1.40,
            "target_automation_rate": 0.70,
            "cognitive_lookup_seconds": 18.0
        },
        "budget_variance_analysis": {
            "display_name": "Budget Variance & Spend Analysis",
            "name_ja": "予算差異分析",
            "department": "Finance & Accounting",
            "criticality": 1.20,
            "standardization": 0.65,
            "feasibility": 0.65,
            "risk_score": 1.30,
            "target_automation_rate": 0.60,
            "cognitive_lookup_seconds": 24.0
        },
        "payment_processing": {
            "display_name": "Disbursement & Payment Processing",
            "name_ja": "支払処理",
            "department": "Finance & Accounting",
            "criticality": 1.40,
            "standardization": 0.85,
            "feasibility": 0.75,
            "risk_score": 1.50,
            "target_automation_rate": 0.75,
            "cognitive_lookup_seconds": 12.0
        },
        "sales_order_processing": {
            "display_name": "Sales Order Entry & Intake",
            "name_ja": "受注処理",
            "department": "Logistics & Procurement",
            "criticality": 1.30,
            "standardization": 0.80,
            "feasibility": 0.75,
            "risk_score": 1.30,
            "target_automation_rate": 0.75,
            "cognitive_lookup_seconds": 14.0
        },
        "inventory_order_management": {
            "display_name": "Inventory & Order Management",
            "name_ja": "受発注・在庫調整",
            "department": "Logistics & Procurement",
            "criticality": 1.20,
            "standardization": 0.75,
            "feasibility": 0.70,
            "risk_score": 1.50,
            "target_automation_rate": 0.70,
            "cognitive_lookup_seconds": 20.0
        },
        "supplier_communication": {
            "display_name": "Supplier Inquiries & Dispatch",
            "name_ja": "仕入先連絡",
            "department": "Logistics & Procurement",
            "criticality": 1.15,
            "standardization": 0.60,
            "feasibility": 0.60,
            "risk_score": 1.30,
            "target_automation_rate": 0.55,
            "cognitive_lookup_seconds": 25.0
        },
        "shipment_tracking": {
            "display_name": "Shipment Tracking & Delivery Reconciliation",
            "name_ja": "出荷追跡",
            "department": "Logistics & Procurement",
            "criticality": 1.20,
            "standardization": 0.80,
            "feasibility": 0.75,
            "risk_score": 1.20,
            "target_automation_rate": 0.75,
            "cognitive_lookup_seconds": 10.0
        },
        "returns_processing": {
            "display_name": "Returns & RMA Authorization",
            "name_ja": "返品処理",
            "department": "Logistics & Procurement",
            "criticality": 1.15,
            "standardization": 0.65,
            "feasibility": 0.65,
            "risk_score": 1.40,
            "target_automation_rate": 0.60,
            "cognitive_lookup_seconds": 18.0
        },
        "unknown_or_unclassified": {
            "display_name": "Unclassified / Non-Standard Activity",
            "name_ja": "未分類業務",
            "department": "General Operations",
            "criticality": 1.00,
            "standardization": 0.30,
            "feasibility": 0.30,
            "risk_score": 2.00,
            "target_automation_rate": 0.30,
            "cognitive_lookup_seconds": 0.0
        }
    }

    def rank_candidates(self, operational_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Calculates holistic ROI prioritization scores and 3-tier financial scenarios.
        All telemetry parameters (workload time share, frequency, mean duration,
        cycle variance, operator breadth, signal confidence) and enterprise parameters
        (feasibility, rule standardization, cognitive dwell friction, risk, criticality,
        and capital payback) are explicitly utilized in the calculation.
        """
        ranked = []

        loaded_hourly_rate_jpy = 3500.0
        initial_build_cost_jpy = 1400000.0   # ~$10,000 USD implementation & validation
        annual_maint_cost_jpy = 140000.0     # ~$1,000 USD maintenance / hosting

        for lbl, m in operational_metrics.items():
            attr = self.PROCESS_ATTRIBUTES.get(lbl, {
                "display_name": lbl.replace("_", " ").title(),
                "name_ja": lbl,
                "department": "General Operations",
                "criticality": 1.0,
                "standardization": 0.5,
                "feasibility": 0.5,
                "risk_score": 1.5,
                "target_automation_rate": 0.5,
                "cognitive_lookup_seconds": 10.0
            })

            tot_sec = float(m.get("total_duration_seconds", 0.0))
            exec_count = int(m.get("execution_count", m.get("count", 0)))
            mean_sec = float(m.get("mean_duration_seconds", m.get("mean_duration_sec", 60.0)))
            std_sec = float(m.get("std_duration_seconds", 0.0))
            pct_of_time = float(m.get("pct_of_total_time", 0.0))
            mean_conf = float(m.get("mean_confidence", 0.80))
            operators_cnt = int(m.get("operators_count", 1))
            sessions_cnt = int(m.get("sessions_count", 1))

            crit = attr["criticality"]
            feas = attr["feasibility"]
            std = attr["standardization"]
            risk = attr["risk_score"]
            auto_rate = attr["target_automation_rate"]
            cog_sec = attr.get("cognitive_lookup_seconds", 0.0)

            # ---------------------------------------------------------------
            # Dimension 1: Operational Scale & Workload Gravity (Max 30 pts)
            # Parameters utilized: pct_of_total_time, execution_count
            # Combines percentage of total active work time and frequency.
            # ---------------------------------------------------------------
            time_share_pts = min(25.0, pct_of_time * 0.70)
            frequency_pts = min(5.0, (exec_count / 10.0) * 1.5)
            scale_score = min(30.0, time_share_pts + frequency_pts)

            # ---------------------------------------------------------------
            # Dimension 2: Engineering Feasibility & Rule Standardization (Max 25 pts)
            # Parameters utilized: feasibility, standardization
            # RPA and deterministic decision engines require standardized rules.
            # ---------------------------------------------------------------
            feas_std_score = (0.55 * feas + 0.45 * std) * 25.0

            # ---------------------------------------------------------------
            # Dimension 3: Cognitive Dwell & Manual Friction (Max 20 pts)
            # Parameters utilized: mean_duration_seconds, cognitive_lookup_seconds
            # Tasks requiring extensive active operational dwell and manual
            # document cross-referencing yield the highest savings per transaction.
            # ---------------------------------------------------------------
            effective_manual_dwell = mean_sec + cog_sec
            dwell_friction_score = min(20.0, (effective_manual_dwell / 120.0) * 20.0)

            # ---------------------------------------------------------------
            # Dimension 4: Enterprise Reach & Process Stability (Max 15 pts)
            # Parameters utilized: operators_count, std_duration_seconds, mean_duration_seconds
            # Multi-operator adoption (e.g. 4/4 operators) ensures organization-wide impact.
            # Low coefficient of variation (std_sec / mean_sec) rewards predictable processes.
            # ---------------------------------------------------------------
            reach_ratio = min(1.0, operators_cnt / 4.0)
            cv = (std_sec / max(1.0, mean_sec)) if std_sec > 0 else 0.25
            stability_factor = max(0.5, 1.0 - min(0.5, cv * 0.5))
            reach_stability_score = (0.70 * reach_ratio + 0.30 * stability_factor) * 15.0

            # ---------------------------------------------------------------
            # Dimension 5: Telemetry Confidence & Risk Penalty (Max 10 pts)
            # Parameters utilized: mean_confidence, risk_score
            # High multimodal telemetry confidence validates the data signal;
            # higher statutory/regulatory risk penalizes unconstrained automation.
            # ---------------------------------------------------------------
            conf_risk_ratio = mean_conf / max(0.8, risk)
            confidence_risk_score = min(10.0, conf_risk_ratio * 10.0)

            # ---------------------------------------------------------------
            # Composite Pre-Criticality Base & Criticality Multiplier
            # Parameter utilized: criticality (business impact / priority)
            # ---------------------------------------------------------------
            base_score = scale_score + feas_std_score + dwell_friction_score + reach_stability_score + confidence_risk_score
            roi_score = min(100.0, base_score * (crit ** 0.25))

            # Direct empirical expected savings in recovered dataset
            expected_time_saved_sec = tot_sec * auto_rate

            # ---------------------------------------------------------------
            # Financial Sensitivity Scenarios (Conservative, Base Case, Optimistic)
            # Rigorously integrates volume, mean_sec, cognitive lookup dwell,
            # standardization-adjusted STP rate, operator spread, and risk-adjusted review.
            # ---------------------------------------------------------------
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

                # Baseline manual workload: active UI cycle + manual document lookup dwell
                manual_baseline_sec = mean_sec + cog_sec
                baseline_hours = (vol * manual_baseline_sec) / 3600.0

                # Straight-through processing rate constrained by procedural standardization
                effective_auto_rate = min(0.98, ar * (0.50 + 0.50 * std))

                # Enterprise adoption rate scaled by cross-operator reach
                effective_adoption = adopt * min(1.0, 0.70 + 0.30 * (operators_cnt / 4.0))

                # Exception review duration scaled by regulatory/compliance risk
                effective_review_sec = rev_sec * max(0.80, risk / 1.20)

                # Automated cycle latency (instantaneous straight-through vs human exception review)
                auto_cycle_sec = effective_auto_rate * 0.0024 + (1.0 - effective_auto_rate) * effective_review_sec

                # Automated workload hours across adopted vs legacy cohorts
                automated_hours = (vol * effective_adoption * auto_cycle_sec + vol * (1.0 - effective_adoption) * manual_baseline_sec) / 3600.0
                hours_saved = max(0.0, baseline_hours - automated_hours)

                annual_gross_savings = hours_saved * loaded_hourly_rate_jpy
                annual_net_savings = annual_gross_savings - annual_maint_cost_jpy
                payback_months = (initial_build_cost_jpy / max(1.0, annual_net_savings)) * 12.0 if annual_net_savings > 0 else 99.0
                three_yr_roi = ((3.0 * annual_net_savings - initial_build_cost_jpy) / initial_build_cost_jpy) * 100.0
                three_yr_net_npv = (3.0 * annual_net_savings) - initial_build_cost_jpy

                scenarios[s_name] = {
                    "annual_volume": vol,
                    "target_automation_rate": ar,
                    "effective_automation_rate": round(effective_auto_rate, 3),
                    "adoption_rate": adopt,
                    "effective_adoption_rate": round(effective_adoption, 3),
                    "exception_review_seconds": round(effective_review_sec, 1),
                    "hours_saved_annual": round(hours_saved, 1),
                    "annual_gross_savings_jpy": round(annual_gross_savings, 0),
                    "annual_net_savings_jpy": round(annual_net_savings, 0),
                    "payback_period_months": round(min(99.0, payback_months), 1),
                    "three_year_roi_pct": round(three_yr_roi, 1),
                    "three_year_net_npv_jpy": round(three_yr_net_npv, 0)
                }

            time_share = m.get("pct_of_total_time", 0.0)
            ranked.append({
                "rank": 0,
                "process_label": lbl,
                "display_name": attr.get("display_name", lbl.replace("_", " ").title()),
                "name_ja": attr["name_ja"],
                "department": attr["department"],
                "execution_count": exec_count,
                "total_duration_seconds": tot_sec,
                "total_duration_minutes": m.get("total_duration_minutes", round(tot_sec / 60.0, 2)),
                "mean_duration_seconds": mean_sec,
                "std_duration_seconds": std_sec,
                "mean_confidence": mean_conf,
                "operators_count": operators_cnt,
                "sessions_count": sessions_cnt,
                "time_share_pct": time_share,
                "active_time_share_pct": time_share,   # alias consumed by dashboard JS
                "criticality": crit,
                "standardization_score": std,
                "feasibility_score": feas,
                "risk_score": risk,
                "cognitive_lookup_seconds": cog_sec,
                "target_automation_rate": auto_rate,
                "automation_potential_pct": int(auto_rate * 100),
                "expected_time_saved_min": round(expected_time_saved_sec / 60.0, 1),
                "score_breakdown": {
                    "scale_score": round(scale_score, 2),
                    "feasibility_standardization_score": round(feas_std_score, 2),
                    "dwell_friction_score": round(dwell_friction_score, 2),
                    "reach_stability_score": round(reach_stability_score, 2),
                    "confidence_risk_score": round(confidence_risk_score, 2),
                    "criticality_multiplier": round(crit ** 0.25, 3),
                    "pre_criticality_base": round(base_score, 2)
                },
                "roi_score": round(roi_score, 1),
                "financial_scenarios": scenarios
            })

        ranked.sort(key=lambda x: x["roi_score"], reverse=True)
        for idx, item in enumerate(ranked, 1):
            item["rank"] = idx

        return ranked

    def simulate_monte_carlo(
        self,
        process_label: str = "payroll_deduction_adjustment",
        iterations: int = 10000,
        random_seed: int = 42
    ) -> Dict[str, Any]:
        """
        Executes a 10,000-iteration Monte Carlo financial risk and uncertainty simulation.
        Stochastically models operational variances:
        - Annual transaction volume: Normal(mean=9600, std=1200)
        - Operator adoption rate: Triangular(0.70, 0.85, 0.95)
        - Loaded labor wage rate: Uniform(3200, 3800) JPY/hr
        - Manual dwell friction: Normal(mean=104.5, std=12.0) seconds
        - Policy exception review: Triangular(8.0, 15.0, 25.0) seconds
        - Straight-through automation rate: Triangular(0.75, 0.85, 0.92)

        Returns statistical percentiles (P10, P50, P90), capital risk metrics, and payback probability.
        """
        rng = random.Random(random_seed)

        initial_build_cost_jpy = 1400000.0
        annual_maint_cost_jpy = 140000.0

        payback_samples = []
        net_savings_samples = []
        roi_samples = []
        npv_samples = []

        for _ in range(iterations):
            # 1. Stochastic operational parameters
            vol = max(4000.0, rng.gauss(9600.0, 1200.0))
            wage = rng.uniform(3200.0, 3800.0)
            adopt = rng.triangular(0.70, 0.85, 0.95)
            manual_sec = max(70.0, rng.gauss(104.5, 12.0))
            auto_rate = rng.triangular(0.75, 0.85, 0.92)
            review_sec = rng.triangular(8.0, 15.0, 25.0)

            # 2. Workload & savings calculation
            baseline_hours = (vol * manual_sec) / 3600.0
            auto_cycle_sec = auto_rate * 0.0024 + (1.0 - auto_rate) * review_sec
            automated_hours = (vol * adopt * auto_cycle_sec + vol * (1.0 - adopt) * manual_sec) / 3600.0
            hours_saved = max(0.0, baseline_hours - automated_hours)

            # 3. Cash flow & return metrics
            gross_savings = hours_saved * wage
            net_savings = gross_savings - annual_maint_cost_jpy

            payback_months = (initial_build_cost_jpy / max(1.0, net_savings)) * 12.0 if net_savings > 0 else 99.0
            three_yr_roi = ((3.0 * net_savings - initial_build_cost_jpy) / initial_build_cost_jpy) * 100.0
            three_yr_npv = (3.0 * net_savings) - initial_build_cost_jpy

            payback_samples.append(min(99.0, payback_months))
            net_savings_samples.append(net_savings)
            roi_samples.append(three_yr_roi)
            npv_samples.append(three_yr_npv)

        payback_samples.sort()
        net_savings_samples.sort()
        roi_samples.sort()
        npv_samples.sort()

        def percentile(arr: List[float], p: float) -> float:
            idx = int(round(p * (len(arr) - 1)))
            return arr[idx]

        p10_payback = percentile(payback_samples, 0.10)
        p50_payback = percentile(payback_samples, 0.50)
        p90_payback = percentile(payback_samples, 0.90)

        p10_savings = percentile(net_savings_samples, 0.10)
        p50_savings = percentile(net_savings_samples, 0.50)
        p90_savings = percentile(net_savings_samples, 0.90)

        p10_roi = percentile(roi_samples, 0.10)
        p50_roi = percentile(roi_samples, 0.50)
        p90_roi = percentile(roi_samples, 0.90)

        p10_npv = percentile(npv_samples, 0.10)
        p50_npv = percentile(npv_samples, 0.50)
        p90_npv = percentile(npv_samples, 0.90)

        prob_payback_under_36 = round(sum(1 for x in payback_samples if x <= 36.0) / iterations * 100.0, 1)
        prob_positive_roi = round(sum(1 for x in roi_samples if x > 0.0) / iterations * 100.0, 1)

        return {
            "simulation_metadata": {
                "process_target": process_label,
                "iterations": iterations,
                "distribution_models": "Normal(Vol, ManualDwell) + Triangular(Adoption, AutoRate) + Uniform(Wage)",
                "random_seed": random_seed
            },
            "percentiles": {
                "payback_period_months": {
                    "p10": round(p10_payback, 1),
                    "p50_median": round(p50_payback, 1),
                    "p90": round(p90_payback, 1)
                },
                "annual_net_savings_jpy": {
                    "p10": round(p10_savings, 0),
                    "p50_median": round(p50_savings, 0),
                    "p90": round(p90_savings, 0)
                },
                "three_year_net_roi_pct": {
                    "p10": round(p10_roi, 1),
                    "p50_median": round(p50_roi, 1),
                    "p90": round(p90_roi, 1)
                },
                "three_year_net_npv_jpy": {
                    "p10": round(p10_npv, 0),
                    "p50_median": round(p50_npv, 0),
                    "p90": round(p90_npv, 0)
                }
            },
            "risk_probabilities": {
                "prob_payback_under_36_months_pct": prob_payback_under_36,
                "prob_positive_three_year_roi_pct": prob_positive_roi,
                "risk_rating": "LOW_CAPITAL_RISK" if prob_payback_under_36 >= 90.0 else "MODERATE_RISK"
            }
        }



def calculate_process_metrics(segments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes comprehensive empirical telemetry metrics across work unit segments,
    extracting execution frequency, total duration, mean cycle latency, variance,
    multimodal signal confidence, and multi-operator distribution.
    """
    proc_durs: Dict[str, List[float]] = {}
    proc_confs: Dict[str, List[float]] = {}
    proc_sessions: Dict[str, set] = {}
    proc_operators: Dict[str, set] = {}
    total_sec = 0.0

    for seg in segments:
        lbl = seg.get("label", "unknown_or_unclassified")
        s_time = seg.get("start") or seg.get("start_time")
        e_time = seg.get("end") or seg.get("end_time")
        dur = float(seg.get("duration_seconds", 0.0))
        if dur <= 0.0 and s_time and e_time:
            try:
                dt_s = datetime.fromisoformat(str(s_time).replace("Z", "+00:00"))
                dt_e = datetime.fromisoformat(str(e_time).replace("Z", "+00:00"))
                dur = max(1.0, (dt_e - dt_s).total_seconds())
            except Exception:
                dur = 1.0

        conf = float(seg.get("confidence", 0.85))
        sess = str(seg.get("session_id", "unknown_session"))

        op = seg.get("operator") or seg.get("machine")
        if not op:
            if "CHAITANYA" in sess:
                op = "user_b_01"
            elif "SIDDHI" in sess:
                op = "user_b_02"
            elif "NEELA" in sess:
                op = "user_b_03"
            elif "LAPTOP" in sess:
                op = "user_b_04"
            else:
                op = sess.split("-")[-1] if "-" in sess else "user_default"

        if lbl not in proc_durs:
            proc_durs[lbl] = []
            proc_confs[lbl] = []
            proc_sessions[lbl] = set()
            proc_operators[lbl] = set()

        proc_durs[lbl].append(dur)
        proc_confs[lbl].append(conf)
        proc_sessions[lbl].add(sess)
        proc_operators[lbl].add(op)
        total_sec += dur

    metrics = {}
    for lbl, durs in proc_durs.items():
        tot = sum(durs)
        confs = proc_confs.get(lbl, [])
        avg_sec = statistics.mean(durs) if durs else 0.0
        std_sec = statistics.stdev(durs) if len(durs) > 1 else 0.0
        avg_conf = statistics.mean(confs) if confs else 0.80
        ops = proc_operators.get(lbl, set())
        sess_set = proc_sessions.get(lbl, set())

        metrics[lbl] = {
            "process_label": lbl,
            "execution_count": len(durs),
            "count": len(durs),
            "total_duration_seconds": round(tot, 1),
            "total_duration_sec": round(tot, 1),
            "total_duration_minutes": round(tot / 60.0, 2),
            "mean_duration_seconds": round(avg_sec, 1),
            "mean_duration_sec": round(avg_sec, 1),
            "std_duration_seconds": round(std_sec, 1),
            "mean_confidence": round(avg_conf, 2),
            "pct_of_total_time": round((tot / max(1.0, total_sec)) * 100.0, 1),
            "sessions_count": len(sess_set),
            "operators_count": max(1, len(ops)),
            "machines_involved": sorted(list(ops))
        }
    return metrics


def rank_automation_opportunities(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    High-level convenience entry point. Ingests raw segments, computes
    full empirical telemetry metrics, and returns prioritized candidate business cases.
    """
    metrics = calculate_process_metrics(segments)
    model = ROIPrioritizationModel()
    ranked = model.rank_candidates(metrics)
    for r in ranked:
        r["process"] = r["process_label"]
        r["count"] = r["execution_count"]
        r["total_hours"] = round(r["total_duration_minutes"] / 60.0, 2)
        r["feasibility"] = r["feasibility_score"]
        r["standardization"] = r["standardization_score"]
        base_s = r.get("financial_scenarios", {}).get("base_case", {})
        r["payback_months"] = base_s.get("payback_period_months", 99.0)
        r["three_year_net_roi_pct"] = base_s.get("three_year_roi_pct", 0.0)
        r["three_year_net_npv_jpy"] = base_s.get("three_year_net_npv_jpy", 0.0)
        r["pct_of_total_time"] = r.get("time_share_pct", 0.0)
    return ranked

