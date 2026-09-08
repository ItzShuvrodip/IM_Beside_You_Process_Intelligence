import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from src.ingestion.models import RawEvent, Segment, format_iso_utc
from src.ingestion.loader import SessionDataLoader
from src.segmentation.classifier import ProcessClassifier, is_noise_event

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
    """
    Production Hybrid Segmenter with Signal Confidence Scoring.
    Consolidates DOM button anchors, active browser URL propagation,
    document context, and inactivity gaps into verified work units.
    """
    def __init__(
        self,
        dwell_gap_seconds: float = 24.0,
        min_segment_seconds: float = 6.0,
        min_segment_events: int = 3,
        merge_gap_seconds: float = 6.0
    ):
        self.dwell_gap_seconds = dwell_gap_seconds
        self.min_segment_seconds = min_segment_seconds
        self.min_segment_events = min_segment_events
        self.merge_gap_seconds = merge_gap_seconds
        self.classifier = ProcessClassifier()

    def segment_session(self, session_id: str, events: List[RawEvent]) -> List[Segment]:
        if not events:
            return []

        raw_segments: List[Segment] = []
        current_cluster: List[RawEvent] = []
        current_label: Optional[str] = None

        def flush_cluster(cluster: List[RawEvent]):
            if not cluster or len(cluster) < self.min_segment_events:
                return
            t_start = cluster[0].datetime_utc
            t_end = cluster[-1].datetime_utc
            duration = (t_end - t_start).total_seconds()
            if duration < self.min_segment_seconds:
                return

            label, confidence, method, evidence = self.classifier.classify_segment_events(cluster)

            raw_segments.append(Segment(
                session_id=session_id,
                start=cluster[0].timestamp_iso,
                end=cluster[-1].timestamp_iso,
                label=label,
                confidence=confidence,
                detection_method=method,
                evidence=evidence
            ))

        for ev in events:
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
            gap_seconds = (ev.datetime_utc - prev_ev.datetime_utc).total_seconds()

            # Trigger 1: Inactivity gap
            is_gap = gap_seconds > self.dwell_gap_seconds

            # Trigger 2: Process shift in primary system
            is_process_shift = False
            if ev_label is not None and current_label is not None and ev_label != current_label and not is_aux:
                is_process_shift = True

            if is_gap or is_process_shift:
                flush_cluster(current_cluster)
                current_cluster = [ev]
                current_label = ev_label or (None if is_process_shift else current_label)
            else:
                current_cluster.append(ev)
                if ev_label and not current_label:
                    current_label = ev_label

        if current_cluster:
            flush_cluster(current_cluster)

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
        sessions = sorted([d for d in Path(dataset_dir).iterdir() if d.is_dir()])
        for s in sessions:
            segs = self.process_session(s)
            all_segments.extend(segs)
        return all_segments


# Backwards compatibility alias
SegmentationPipeline = HybridSegmenter
BoundaryDetector = HybridSegmenter
