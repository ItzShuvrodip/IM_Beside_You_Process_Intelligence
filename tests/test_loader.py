import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.loader import SessionDataLoader


class TestSessionDataLoader(unittest.TestCase):
    def setUp(self):
        self.data_dir = Path("d:/IMBY/Datasets")
        self.a_dir = self.data_dir / "dataset_a"
        self.b_dir = self.data_dir / "dataset_b"

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


if __name__ == "__main__":
    unittest.main()
