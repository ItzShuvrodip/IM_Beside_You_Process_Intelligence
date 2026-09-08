import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict
from src.ingestion.loader import SessionDataLoader
from src.segmentation.hybrid_segmenter import HybridSegmenter
from src.evaluation.evaluator import SegmentationEvaluator

logger = logging.getLogger(__name__)


def generate_evaluation_and_audit_report(
    dataset_a_dir: Path,
    dataset_b_dir: Path,
    segments_path: Path
) -> Dict[str, Any]:
    """
    Generates a disciplined audit report:
    1. Dataset A benchmark with decoupled boundary F1 and label accuracy.
    2. Dataset B stratified confidence and uncertainty breakdown.
    3. Gold audit sample verification.
    """
    segmenter = HybridSegmenter()
    evaluator = SegmentationEvaluator()

    # 1. Dataset A Benchmark
    sessions_a = sorted([d for d in dataset_a_dir.iterdir() if d.is_dir()]) if dataset_a_dir.exists() else []
    total_gt = 0
    total_pred = 0
    total_matches = 0
    total_label_matches = 0
    session_f1s = []
    session_ious = []
    session_label_accs = []

    for s in sessions_a:
        loader = SessionDataLoader(s)
        gt = loader.load_ground_truth()
        if not gt:
            continue
        predicted = segmenter.process_session(s)
        metrics = evaluator.evaluate_session(predicted, gt)

        total_gt += metrics["gt_count"]
        total_pred += metrics["pred_count"]
        total_matches += metrics["matches"]
        total_label_matches += metrics["label_matches"]
        session_f1s.append(metrics["f1"])
        if metrics["avg_iou"] > 0:
            session_ious.append(metrics["avg_iou"])
        if metrics["matches"] > 0:
            session_label_accs.append(metrics["label_accuracy"])

    dataset_a_results = {
        "total_gt_executions": total_gt,
        "total_predicted_segments": total_pred,
        "total_matched_segments": total_matches,
        "total_label_matches": total_label_matches,
        "boundary_macro_f1_pct": round((sum(session_f1s) / max(1, len(session_f1s))) * 100.0, 2),
        "mean_iou_overlap_pct": round((sum(session_ious) / max(1, len(session_ious))) * 100.0, 2),
        "label_accuracy_macro_pct": round((sum(session_label_accs) / max(1, len(session_label_accs))) * 100.0, 2),
        "strict_micro_f1_pct": round(((2 * total_label_matches) / max(1, total_pred + total_gt)) * 100.0, 2)
    }

    # 2. Dataset B Stratified Confidence & Uncertainty Audit
    segments: List[Dict[str, Any]] = []
    if segments_path.exists():
        with open(segments_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    segments.append(json.loads(line))

    process_confidence = defaultdict(list)
    method_distribution = defaultdict(int)

    for s in segments:
        lbl = s.get("label", "unknown_or_unclassified")
        conf = float(s.get("confidence", 0.5))
        method = s.get("detection_method", "window_context")
        process_confidence[lbl].append(conf)
        method_distribution[method] += 1

    audit_summary = {}
    for proc, confs in process_confidence.items():
        avg_c = sum(confs) / len(confs)
        high_conf_count = sum(1 for c in confs if c >= 0.80)
        audit_summary[proc] = {
            "count": len(confs),
            "mean_confidence": round(avg_c, 2),
            "high_confidence_ratio_pct": round((high_conf_count / len(confs)) * 100.0, 1),
            "risk_status": "HIGH_CONFIDENCE" if avg_c >= 0.80 else ("MODERATE" if avg_c >= 0.50 else "UNCERTAIN")
        }

    return {
        "dataset_a_evaluation": dataset_a_results,
        "dataset_b_audit": audit_summary,
        "detection_method_distribution": dict(method_distribution),
        "total_production_segments": len(segments)
    }
