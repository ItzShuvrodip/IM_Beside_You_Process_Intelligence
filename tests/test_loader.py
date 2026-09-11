import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.loader import SessionDataLoader


from src.config import DATASETS_DIR, DATASET_A_DIR, DATASET_B_DIR


class TestSessionDataLoader(unittest.TestCase):
    def setUp(self):
        self.data_dir = DATASETS_DIR
        self.a_dir = DATASET_A_DIR
        self.b_dir = DATASET_B_DIR

    def test_load_dataset_a_session(self):
        sessions = [d for d in self.a_dir.iterdir() if d.is_dir()]
        self.assertTrue(len(sessions) > 0, "No sessions found in dataset_a")
        loader = SessionDataLoader(sessions[0])
        events = loader.load_events()
        self.assertTrue(len(events) > 0, "No events loaded from session")
        gt = loader.load_ground_truth()
        self.assertTrue(len(gt) > 0, "No ground truth executions loaded")

        # Verify sorted order
        for i in range(len(events) - 1):
            self.assertLessEqual(events[i].timestamp_ms, events[i + 1].timestamp_ms)

    def test_load_dataset_b_session(self):
        sessions = [d for d in self.b_dir.iterdir() if d.is_dir()]
        self.assertTrue(len(sessions) > 0, "No sessions found in dataset_b")
        loader = SessionDataLoader(sessions[0])
        events = loader.load_events()
        self.assertTrue(len(events) > 0, "No events loaded from dataset_b session")

    def test_iter_events_generator(self):
        sessions = [d for d in self.a_dir.iterdir() if d.is_dir()]
        self.assertTrue(len(sessions) > 0)
        loader = SessionDataLoader(sessions[0])
        gen = loader.iter_events()
        first_event = next(gen)
        self.assertIsNotNone(first_event.event_id)
        self.assertGreater(first_event.timestamp_ms, 0)

    def test_invalid_session_path_resilience(self):
        bogus_path = self.a_dir / "non_existent_session_folder_xyz"
        loader = SessionDataLoader(bogus_path)
        self.assertEqual(loader.load_events(), [])
        self.assertEqual(list(loader.iter_events()), [])
        self.assertEqual(loader.load_ground_truth(), [])

    def test_segment_is_valid_property(self):
        from src.ingestion.models import Segment
        valid_seg = Segment("s1", "2026-07-01T10:00:00Z", "2026-07-01T10:05:00Z", "payroll_deduction_adjustment")
        self.assertTrue(valid_seg.is_valid)
        self.assertEqual(valid_seg.duration_seconds, 300.0)

        invalid_seg = Segment("s1", "2026-07-01T10:05:00Z", "2026-07-01T10:00:00Z", "payroll_deduction_adjustment")
        self.assertFalse(invalid_seg.is_valid)


if __name__ == "__main__":
    unittest.main()
