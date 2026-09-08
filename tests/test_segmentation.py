import unittest
from pathlib import Path
from src.ingestion.loader import SessionDataLoader
from src.segmentation.hybrid_segmenter import HybridSegmenter as SegmentationPipeline
from src.evaluation.evaluator import SegmentationEvaluator


class TestSegmentation(unittest.TestCase):
    def setUp(self):
        self.data_dir = Path("d:/IMBY/Datasets")
        self.a_dir = self.data_dir / "dataset_a"
        self.b_dir = self.data_dir / "dataset_b"
        self.pipeline = SegmentationPipeline(dwell_gap_seconds=20.0)

    def test_segmentation_dataset_a(self):
        sessions = [d for d in self.a_dir.iterdir() if d.is_dir()]
        self.assertTrue(len(sessions) > 0)
        s0 = sessions[0]
        segments = self.pipeline.process_session(s0)
        self.assertTrue(len(segments) > 0, "Pipeline produced 0 segments for session in A")

        # Evaluate against GT
        loader = SessionDataLoader(s0)
        gt = loader.load_ground_truth()
        evaluator = SegmentationEvaluator()
        metrics = evaluator.evaluate_session(segments, gt)

        self.assertIn("f1", metrics)
        self.assertIn("precision", metrics)
        self.assertIn("recall", metrics)
        self.assertGreater(metrics["f1"], 0.0)

    def test_segmentation_dataset_b(self):
        sessions = [d for d in self.b_dir.iterdir() if d.is_dir()]
        self.assertTrue(len(sessions) > 0)
        s0 = sessions[0]
        segments = self.pipeline.process_session(s0)
        self.assertTrue(len(segments) > 0, "Pipeline produced 0 segments for session in B")
        # Check segment fields
        for seg in segments:
            d = seg.to_dict()
            self.assertIn("session_id", d)
            self.assertIn("start", d)
            self.assertIn("end", d)
            self.assertIn("label", d)
            self.assertTrue(d["start"].endswith("Z"))
            self.assertTrue(d["end"].endswith("Z"))
            self.assertLessEqual(seg.start_dt, seg.end_dt)


if __name__ == "__main__":
    unittest.main()
