import math
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import torch  # type: ignore
from torch.utils.data import Dataset  # type: ignore

from src.ingestion.loader import SessionDataLoader
from src.ingestion.models import RawEvent, GroundTruthExecution
from src.ml.model import LABEL_TO_IDX, EVENT_TO_IDX, PROCESS_LABELS
from src.segmentation.classifier import JAPANESE_GT_TO_CANONICAL, is_noise_event


def hash_text_tokens(text: str, num_buckets: int = 1024, max_tokens: int = 12) -> List[int]:
    """Generates deterministic subword / n-gram hash bucket IDs."""
    if not text:
        return [0]
    cleaned = text.strip().lower()
    tokens = [cleaned[i:i+3] for i in range(max(1, len(cleaned) - 2))]
    if not tokens:
        tokens = [cleaned]
    buckets = []
    for t in tokens[:max_tokens]:
        h = int(hashlib.md5(t.encode("utf-8")).hexdigest()[:6], 16) % (num_buckets - 1) + 1
        buckets.append(h)
    return buckets if buckets else [0]


class MultimodalTelemetryDataset(Dataset):
    """
    Multimodal Dataset vectorizing raw telemetry events, mouse dynamics,
    textual semantic hashes, and visual screenshot embeddings into sequence windows.
    """
    def __init__(
        self,
        sessions_dir: Path,
        window_size: int = 64,
        step_size: int = 32,
        visual_cache: Optional[Dict[str, torch.Tensor]] = None,
        max_sessions: Optional[int] = None
    ):
        self.window_size = window_size
        self.step_size = step_size
        self.visual_cache = visual_cache or {}
        self.samples: List[Dict[str, Any]] = []

        session_paths = sorted([p for p in sessions_dir.iterdir() if p.is_dir() and p.name.startswith("ses_")])
        if max_sessions:
            session_paths = session_paths[:max_sessions]

        for p in session_paths:
            self._process_session(p)

    def _process_session(self, session_path: Path):
        loader = SessionDataLoader(session_path)
        events = loader.load_events()
        gt_list = loader.load_ground_truth()

        if not events or len(events) < 5:
            return

        # Prepare GT interval boundaries
        gt_intervals: List[Tuple[float, float, str]] = []
        for gt in gt_list:
            if gt.start_dt and gt.end_dt:
                t0 = gt.start_dt.timestamp()
                t1 = gt.end_dt.timestamp()
                canonical = JAPANESE_GT_TO_CANONICAL.get(gt.family_name, "unknown_or_unclassified")
                gt_intervals.append((t0, t1, canonical))

        # Event-level feature vectors
        n_events = len(events)
        ev_types = []
        numericals = []
        text_buckets_list = []
        vis_tensors = []
        boundaries = []
        class_labels = []

        for i, ev in enumerate(events):
            # 1. Event Type
            ev_t = ev.event_type.lower()
            ev_idx = EVENT_TO_IDX.get(ev_t, EVENT_TO_IDX["other"])
            ev_types.append(ev_idx)

            # 2. Numerical Dynamics
            gap = (ev.ms_since_last_event or 0) / 1000.0
            if gap <= 0 and i > 0:
                gap = max(0.0, (ev.timestamp_ms - events[i-1].timestamp_ms) / 1000.0)
            norm_gap = min(gap / 60.0, 1.0)
            dur_ms = float(ev.payload.get("duration_ms") or 0.0)
            norm_dur = min((dur_ms / 1000.0) / 60.0, 1.0)
            
            x_val = ev.payload.get("x") or ev.payload.get("mouse_position", {}).get("x", 0.0) or 0.0
            y_val = ev.payload.get("y") or ev.payload.get("mouse_position", {}).get("y", 0.0) or 0.0
            norm_x = float(x_val) / 1920.0
            norm_y = float(y_val) / 1080.0
            
            text_val = ev.payload.get("text") or ev.extracted_text or ""
            norm_txt = min(len(text_val) / 40.0, 1.0)
            numericals.append([norm_gap, norm_dur, norm_x, norm_y, norm_txt])

            # 3. Text Semantic Hashes
            txt_context = f"{ev.app_name or ''} {ev.window_title or ''} {ev.browser_url or ''} {ev.extracted_text or ''}"
            tokens = hash_text_tokens(txt_context)
            text_buckets_list.append(tokens)

            # 4. Visual Vector
            scr_filename = (
                ev.payload.get("file_reference", {}).get("filename")
                or ev.payload.get("screenshot")
                or ""
            )
            vis_vec = self.visual_cache.get(scr_filename, torch.zeros(256, dtype=torch.float32))
            vis_tensors.append(vis_vec)

            # 5. GT Labels & Boundary Target
            curr_ts = ev.timestamp_ms / 1000.0
            is_boundary = 0.0
            active_class = "unknown_or_unclassified"
            for t0, t1, cname in gt_intervals:
                if t0 <= curr_ts <= t1:
                    active_class = cname
                if abs(curr_ts - t0) <= 2.5 or abs(curr_ts - t1) <= 2.5:
                    is_boundary = 1.0

            boundaries.append(is_boundary)
            class_labels.append(LABEL_TO_IDX.get(active_class, LABEL_TO_IDX["unknown_or_unclassified"]))

        # Slice into sliding windows
        for start_idx in range(0, max(1, n_events - self.window_size + 1), self.step_size):
            end_idx = min(start_idx + self.window_size, n_events)
            cur_len = end_idx - start_idx
            if cur_len < 8:
                continue

            # Majority class in window
            window_classes = class_labels[start_idx:end_idx]
            majority_class = max(set(window_classes), key=window_classes.count)

            self.samples.append({
                "ev_types": ev_types[start_idx:end_idx],
                "numericals": numericals[start_idx:end_idx],
                "text_buckets": text_buckets_list[start_idx:end_idx],
                "vis_tensors": vis_tensors[start_idx:end_idx],
                "boundaries": boundaries[start_idx:end_idx],
                "majority_class": majority_class,
                "cur_len": cur_len
            })

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> Dict[str, Any]:
        return self.samples[index]


def multimodal_collate_fn(batch: List[Dict[str, Any]]) -> Dict[str, torch.Tensor]:
    """Collates variable-length windows and text hash lists for EmbeddingBag."""
    B = len(batch)
    max_len = max(item["cur_len"] for item in batch)

    event_types = torch.zeros((B, max_len), dtype=torch.long)
    numerical_feats = torch.zeros((B, max_len, 5), dtype=torch.float32)
    visual_feats = torch.zeros((B, max_len, 256), dtype=torch.float32)
    boundaries = torch.zeros((B, max_len), dtype=torch.float32)
    mask = torch.zeros((B, max_len), dtype=torch.bool)
    majority_classes = torch.zeros(B, dtype=torch.long)

    flat_hashes = []
    offsets = []
    current_offset = 0

    for b, item in enumerate(batch):
        L = item["cur_len"]
        event_types[b, :L] = torch.tensor(item["ev_types"], dtype=torch.long)
        numerical_feats[b, :L] = torch.tensor(item["numericals"], dtype=torch.float32)
        visual_feats[b, :L] = torch.stack(item["vis_tensors"])
        boundaries[b, :L] = torch.tensor(item["boundaries"], dtype=torch.float32)
        mask[b, :L] = True
        majority_classes[b] = item["majority_class"]

        for t_idx in range(max_len):
            offsets.append(current_offset)
            if t_idx < L:
                h_list = item["text_buckets"][t_idx]
            else:
                h_list = [0]
            flat_hashes.extend(h_list)
            current_offset += len(h_list)

    return {
        "event_types": event_types,
        "numerical_feats": numerical_feats,
        "text_hashes": torch.tensor(flat_hashes, dtype=torch.long),
        "text_offsets": torch.tensor(offsets, dtype=torch.long),
        "visual_feats": visual_feats,
        "boundaries": boundaries,
        "mask": mask,
        "majority_classes": majority_classes
    }
