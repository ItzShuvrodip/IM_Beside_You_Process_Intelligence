import logging
from pathlib import Path
from typing import List, Optional, Union
from datetime import datetime
from src.ingestion.models import RawEvent, Segment, format_iso_utc
from src.ingestion.loader import SessionDataLoader
from src.segmentation.classifier import ProcessClassifier, is_noise_event

try:
    from src.ml.inference import MultimodalInferenceEngine
    HAS_TORCH_ML = True
except Exception:
    HAS_TORCH_ML = False

logger = logging.getLogger(__name__)

AUXILIARY_APPS = [
    "excel",
    "word",
    "winword",
    "notepad",
    "calc"
]


def is_auxiliary_app(app_name: Optional[str]) -> bool:
    if not app_name:
        return False
    app = app_name.lower()
    return any(a in app for a in AUXILIARY_APPS)


class HybridSegmenter:
    """Multi-signal work unit segmenter using DOM actions, URL routes, document context, and inactivity gaps."""
    def __init__(
        self,
        dwell_gap_seconds: float = 24.0,
        min_segment_seconds: float = 6.0,
        min_segment_events: int = 3,
        merge_gap_seconds: float = 6.0,
        neural_checkpoint: Optional[Union[str, Path]] = None,
        neural_boundary_threshold: float = 0.65
    ):
        self.dwell_gap_seconds = dwell_gap_seconds
        self.min_segment_seconds = min_segment_seconds
        self.min_segment_events = min_segment_events
        self.merge_gap_seconds = merge_gap_seconds
        self.classifier = ProcessClassifier()
        self.neural_boundary_threshold = neural_boundary_threshold
        self.neural_engine: Optional[MultimodalInferenceEngine] = None

        if neural_checkpoint is not None and HAS_TORCH_ML:
            ckpt_p = Path(neural_checkpoint)
            if ckpt_p.exists():
                try:
                    self.neural_engine = MultimodalInferenceEngine(ckpt_p)
                    logger.info(f"Loaded neural multimodal inference engine from {ckpt_p}")
                except Exception as e:
                    logger.warning(f"Failed to load neural checkpoint {ckpt_p}: {e}")

    def segment_session(self, session_id: str, events: List[RawEvent]) -> List[Segment]:
        if not events:
            return []

        # Optional GPU neural boundary likelihood scoring
        neural_boundary_probs: List[float] = []
        if self.neural_engine:
            try:
                pred = self.neural_engine.predict_events(events)
                neural_boundary_probs = pred.get("boundary_probs", [])
            except Exception as e:
                logger.debug(f"Neural inference bypassed: {e}")

        raw_segments: List[Segment] = []
        current_cluster: List[RawEvent] = []
        current_label: Optional[str] = None
        cluster_has_neural_trigger: bool = False

        def flush_cluster(cluster: List[RawEvent], had_neural_trigger: bool):
            if not cluster or len(cluster) < self.min_segment_events:
                return
            if cluster[0].timestamp_ms > 0 and cluster[-1].timestamp_ms > 0:
                duration = max(0.0, (cluster[-1].timestamp_ms - cluster[0].timestamp_ms) / 1000.0)
            else:
                t_start = cluster[0].datetime_utc
                t_end = cluster[-1].datetime_utc
                duration = (t_end - t_start).total_seconds()
            if duration < self.min_segment_seconds:
                return

            res = self.classifier.classify_segment_events(cluster)
            label = str(getattr(res, "label", res))
            confidence: float = float(getattr(res, "confidence", 0.80))
            method = str(getattr(res, "detection_method", "hybrid_heuristic"))
            evidence = list(getattr(res, "evidence", []))

            if had_neural_trigger and method != "unclassified_fallback":
                confidence = min(0.98, round(confidence + 0.04, 2))
                method = "hybrid_neural_symbolic"

            raw_segments.append(Segment(
                session_id=session_id,
                start=cluster[0].timestamp_iso,
                end=cluster[-1].timestamp_iso,
                label=label,
                confidence=confidence,
                detection_method=method,
                evidence=evidence
            ))

        for i, ev in enumerate(events):
            if is_noise_event(ev):
                if current_cluster:
                    current_cluster.append(ev)
                continue

            app = (ev.app_name or "").lower()
            is_aux = is_auxiliary_app(app)
            ev_label = self.classifier.classify_event(ev)

            # If user is in an auxiliary tool (Word, Excel, Notepad), preserve active process context
            if is_aux and current_label:
                ev_label = current_label

            if not current_cluster:
                current_cluster.append(ev)
                if ev_label:
                    current_label = ev_label
                continue

            prev_ev = current_cluster[-1]
            if ev.timestamp_ms > 0 and prev_ev.timestamp_ms > 0:
                gap_seconds = max(0.0, (ev.timestamp_ms - prev_ev.timestamp_ms) / 1000.0)
            else:
                gap_seconds = (ev.datetime_utc - prev_ev.datetime_utc).total_seconds()

            # Trigger 1: Inactivity gap
            is_gap = gap_seconds > self.dwell_gap_seconds

            # Trigger 2: Process shift in primary system
            is_process_shift = False
            if ev_label is not None and current_label is not None and ev_label != current_label and not is_aux:
                is_process_shift = True

            # Trigger 3: Neural Boundary Trigger
            is_neural_boundary = False
            if (
                neural_boundary_probs
                and i < len(neural_boundary_probs)
                and neural_boundary_probs[i] >= self.neural_boundary_threshold
                and not is_aux
            ):
                is_neural_boundary = True

            if is_gap or is_process_shift or is_neural_boundary:
                flush_cluster(current_cluster, cluster_has_neural_trigger)
                current_cluster = [ev]
                current_label = ev_label or (None if is_process_shift else current_label)
                cluster_has_neural_trigger = is_neural_boundary
            else:
                current_cluster.append(ev)
                if ev_label and not current_label:
                    current_label = ev_label

        if current_cluster:
            flush_cluster(current_cluster, cluster_has_neural_trigger)

        # Merge adjacent segments with identical label if separated by small gap
        merged: List[Segment] = []
        for seg in raw_segments:
            if not merged:
                merged.append(seg)
                continue

            last = merged[-1]
            gap = (seg.start_dt - last.end_dt).total_seconds()
            if seg.label == last.label and 0 <= gap <= self.merge_gap_seconds:
                combined_evidence = list(dict.fromkeys(last.evidence + seg.evidence))
                combined_conf = round((last.confidence + seg.confidence) / 2.0, 2)
                merged[-1] = Segment(
                    session_id=session_id,
                    start=last.start,
                    end=seg.end,
                    label=last.label,
                    confidence=combined_conf,
                    detection_method=last.detection_method,
                    evidence=combined_evidence
                )
            else:
                merged.append(seg)

        return merged

    def process_session(self, session_path: Path) -> List[Segment]:
        loader = SessionDataLoader(session_path)
        events = loader.load_events()
        return self.segment_session(loader.session_id, events)

    def process_all_sessions(self, dataset_dir: Path) -> List[Segment]:
        all_segments: List[Segment] = []
        p = Path(dataset_dir)
        if not p.exists() or not p.is_dir():
            return []
        sessions = sorted([d for d in p.iterdir() if d.is_dir()])
        for s in sessions:
            segs = self.process_session(s)
            all_segments.extend(segs)
        return all_segments


# Backwards compatibility alias
SegmentationPipeline = HybridSegmenter
BoundaryDetector = HybridSegmenter
