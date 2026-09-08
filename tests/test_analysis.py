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


if __name__ == "__main__":
    unittest.main()
