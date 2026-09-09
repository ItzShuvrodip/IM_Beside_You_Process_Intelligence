import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from src.analysis.roi_model import rank_automation_opportunities, calculate_process_metrics
from src.analysis.process_mining import DirectlyFollowsGraphMiner


class TestProcessMiningAndROI(unittest.TestCase):
    def setUp(self):
        self.sample_segments = [
            {"session_id": "s1", "start": "2026-07-01T10:00:00Z", "end": "2026-07-01T10:03:00Z", "label": "payroll_deduction_adjustment"},
            {"session_id": "s1", "start": "2026-07-01T10:05:00Z", "end": "2026-07-01T10:08:00Z", "label": "payroll_deduction_adjustment"},
            {"session_id": "s1", "start": "2026-07-01T10:10:00Z", "end": "2026-07-01T10:12:00Z", "label": "leave_application_processing"},
            {"session_id": "s2", "start": "2026-07-01T11:00:00Z", "end": "2026-07-01T11:05:00Z", "label": "onboarding_verification"},
        ]

    def test_roi_ranking_prioritizes_payroll(self):
        ranked = rank_automation_opportunities(self.sample_segments)
        self.assertGreater(len(ranked), 0)
        top_process = ranked[0]["process"]
        self.assertEqual(top_process, "payroll_deduction_adjustment")
        self.assertIn("roi_score", ranked[0])
        self.assertGreater(ranked[0]["roi_score"], 0)

    def test_metrics_calculation(self):
        metrics = calculate_process_metrics(self.sample_segments)
        self.assertIn("payroll_deduction_adjustment", metrics)
        p_stats = metrics["payroll_deduction_adjustment"]
        self.assertEqual(p_stats["count"], 2)
        self.assertEqual(p_stats["total_duration_sec"], 360.0) # 180 + 180
        self.assertEqual(p_stats["mean_duration_sec"], 180.0)

    def test_monte_carlo_simulation(self):
        from src.analysis.roi_model import ROIPrioritizationModel
        model = ROIPrioritizationModel()
        mc = model.simulate_monte_carlo(iterations=1000)
        self.assertEqual(mc["simulation_metadata"]["iterations"], 1000)
        self.assertIn("percentiles", mc)
        pct = mc["percentiles"]
        self.assertIn("annual_net_savings_jpy", pct)
        self.assertIn("payback_period_months", pct)
        self.assertGreater(pct["payback_period_months"]["p90"], pct["payback_period_months"]["p10"])
        self.assertGreater(mc["risk_probabilities"]["prob_payback_under_36_months_pct"], 70.0)


if __name__ == "__main__":
    unittest.main()
