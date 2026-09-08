import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from src.ingestion.models import Segment, GroundTruthExecution
from src.segmentation.classifier import canonicalize_label

logger = logging.getLogger(__name__)


def compute_iou(s1_start: datetime, s1_end: datetime, s2_start: datetime, s2_end: datetime) -> float:
    start_inter = max(s1_start, s2_start)
    end_inter = min(s1_end, s2_end)
    inter_sec = max(0.0, (end_inter - start_inter).total_seconds())

    start_union = min(s1_start, s2_start)
    end_union = max(s1_end, s2_end)
    union_sec = max(1e-6, (end_union - start_union).total_seconds())

    return inter_sec / union_sec


class SegmentationEvaluator:
    """
    Evaluates predicted segments against ground truth executions using 1-to-1 matching.
    Decouples temporal boundary overlap from process label accuracy.
    """
    def __init__(self, tolerance_seconds: float = 10.0, min_iou: float = 0.25):
        self.tolerance_seconds = tolerance_seconds
        self.min_iou = min_iou

    def evaluate_session(
        self,
        predicted: List[Segment],
        ground_truth: List[GroundTruthExecution],
        label_mapping: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        empty_res = {
            "precision": 0.0, "recall": 0.0, "f1": 0.0,
            "avg_iou": 0.0,
            "label_accuracy": 0.0,
            "strict_precision": 0.0, "strict_recall": 0.0, "strict_f1": 0.0,
            "gt_count": 0, "pred_count": 0, "matches": 0, "label_matches": 0
        }

        if not ground_truth or not predicted:
            res = dict(empty_res)
            res["gt_count"] = len([gt for gt in (ground_truth or []) if gt.end_dt is not None])
            res["pred_count"] = len(predicted or [])
            return res

        valid_gt = [gt for gt in ground_truth if gt.end_dt is not None]
        if not valid_gt:
            res = dict(empty_res)
            res["pred_count"] = len(predicted)
            return res

        # Candidate pair IoU matrix for greedy 1-to-1 matching
        candidate_pairs = []
        for p_idx, pred in enumerate(predicted):
            p_start, p_end = pred.start_dt, pred.end_dt
            for g_idx, gt in enumerate(valid_gt):
                g_start, g_end = gt.start_dt, gt.end_dt
                iou = compute_iou(p_start, p_end, g_start, g_end)
                if iou >= self.min_iou:
                    candidate_pairs.append((iou, p_idx, g_idx))

        candidate_pairs.sort(key=lambda x: x[0], reverse=True)

        matched_preds = set()
        matched_gts = set()
        matched_ious = []
        label_matches = 0

        for iou, p_idx, g_idx in candidate_pairs:
            if p_idx in matched_preds or g_idx in matched_gts:
                continue

            matched_preds.add(p_idx)
            matched_gts.add(g_idx)
            matched_ious.append(iou)

            pred_label = canonicalize_label(predicted[p_idx].label)
            gt_obj = valid_gt[g_idx]
            gt_label = canonicalize_label(gt_obj.family_name or gt_obj.code)

            if pred_label == gt_label:
                label_matches += 1

        n_pred = len(predicted)
        n_gt = len(valid_gt)
        n_matches = len(matched_preds)

        boundary_precision = n_matches / max(1, n_pred)
        boundary_recall = n_matches / max(1, n_gt)
        boundary_f1 = (2 * boundary_precision * boundary_recall) / max(1e-6, boundary_precision + boundary_recall)
        avg_iou = sum(matched_ious) / max(1, len(matched_ious)) if matched_ious else 0.0

        label_accuracy = label_matches / max(1, n_matches) if n_matches > 0 else 0.0

        strict_precision = label_matches / max(1, n_pred)
        strict_recall = label_matches / max(1, n_gt)
        strict_f1 = (2 * strict_precision * strict_recall) / max(1e-6, strict_precision + strict_recall)

        return {
            "precision": round(boundary_precision, 4),
            "recall": round(boundary_recall, 4),
            "f1": round(boundary_f1, 4),
            "avg_iou": round(avg_iou, 4),
            "label_accuracy": round(label_accuracy, 4),
            "strict_precision": round(strict_precision, 4),
            "strict_recall": round(strict_recall, 4),
            "strict_f1": round(strict_f1, 4),
            "gt_count": n_gt,
            "pred_count": n_pred,
            "matches": n_matches,
            "label_matches": label_matches
        }
