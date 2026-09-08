import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, "d:/IMBY")

from src.ingestion.loader import SessionDataLoader
from src.segmentation.hybrid_segmenter import HybridSegmenter, SegmentationPipeline
from src.evaluation.evaluator import SegmentationEvaluator


def main():
    a_dir = Path("d:/IMBY/Datasets/dataset_a")
    sessions = sorted([d for d in a_dir.iterdir() if d.is_dir()])
    print(f"Benchmarking Segmentation Pipeline on Dataset A ({len(sessions)} sessions)...")

    pipeline = SegmentationPipeline(
        dwell_gap_seconds=20.0,
        min_segment_seconds=3.0,
        min_segment_events=3
    )
    evaluator = SegmentationEvaluator(tolerance_seconds=10.0)

    total_gt = 0
    total_pred = 0
    total_matches = 0
    session_f1s = []
    session_precisions = []
    session_recalls = []
    session_ious = []
    session_label_accs = []
    session_strict_f1s = []
    total_label_matches = 0

    for i, s in enumerate(sessions):
        loader = SessionDataLoader(s)
        gt = loader.load_ground_truth()
        if not gt:
            continue

        predicted = pipeline.process_session(s)
        metrics = evaluator.evaluate_session(predicted, gt)

        total_gt += metrics["gt_count"]
        total_pred += metrics["pred_count"]
        total_matches += metrics["matches"]
        total_label_matches += metrics["label_matches"]
        session_f1s.append(metrics["f1"])
        session_precisions.append(metrics["precision"])
        session_recalls.append(metrics["recall"])
        if metrics["matches"] > 0:
            session_label_accs.append(metrics["label_accuracy"])
        session_strict_f1s.append(metrics["strict_f1"])
        if metrics["avg_iou"] > 0:
            session_ious.append(metrics["avg_iou"])

        if (i + 1) % 15 == 0 or (i + 1) == len(sessions):
            print(f"  Processed {i+1}/{len(sessions)} sessions | Running Boundary F1: {sum(session_f1s)/len(session_f1s):.4f}")

    macro_precision = sum(session_precisions) / len(session_precisions) if session_precisions else 0.0
    macro_recall = sum(session_recalls) / len(session_recalls) if session_recalls else 0.0
    macro_f1 = sum(session_f1s) / len(session_f1s) if session_f1s else 0.0
    macro_iou = sum(session_ious) / max(1, len(session_ious))
    macro_label_acc = sum(session_label_accs) / len(session_label_accs) if session_label_accs else 0.0
    macro_strict_f1 = sum(session_strict_f1s) / len(session_strict_f1s) if session_strict_f1s else 0.0

    micro_precision = total_matches / max(1, total_pred)
    micro_recall = total_matches / max(1, total_gt)
    micro_f1 = 2 * micro_precision * micro_recall / max(1e-6, micro_precision + micro_recall)
    micro_label_acc = total_label_matches / max(1, total_matches)
    micro_strict_prec = total_label_matches / max(1, total_pred)
    micro_strict_rec = total_label_matches / max(1, total_gt)
    micro_strict_f1 = 2 * micro_strict_prec * micro_strict_rec / max(1e-6, micro_strict_prec + micro_strict_rec)

    print("\n================ BENCHMARK RESULTS (DATASET A) ================")
    print(f"Total Ground Truth Executions: {total_gt}")
    print(f"Total Predicted Segments:      {total_pred}")
    print(f"Total Matched Segments:        {total_matches}")
    print(f"Total Label-Correct Matches:   {total_label_matches}")
    print("---------------------------------------------------------------")
    print(f"Boundary Macro Precision:      {macro_precision * 100:.2f}%")
    print(f"Boundary Macro Recall:         {macro_recall * 100:.2f}%")
    print(f"Boundary Macro F1 Score:       {macro_f1 * 100:.2f}%")
    print(f"Boundary Micro F1 Score:       {micro_f1 * 100:.2f}%")
    print(f"Mean Segment IoU (Overlap):    {macro_iou * 100:.2f}%")
    print("---------------------------------------------------------------")
    print(f"Process Label Accuracy:        {macro_label_acc * 100:.2f}% (Macro) | {micro_label_acc * 100:.2f}% (Micro)")
    print(f"Strict End-to-End F1:          {macro_strict_f1 * 100:.2f}% (Macro) | {micro_strict_f1 * 100:.2f}% (Micro)")
    print("===============================================================\n")


if __name__ == "__main__":
    main()

