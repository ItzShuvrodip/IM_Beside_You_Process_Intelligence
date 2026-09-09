from pathlib import Path
from typing import List, Dict, Any, Optional
import torch  # type: ignore

from src.ingestion.models import RawEvent
from src.ml.model import MultimodalProcessNet, EVENT_TO_IDX, IDX_TO_LABEL
from src.ml.dataset import hash_text_tokens


class MultimodalInferenceEngine:
    """
    Optimized GPU Sequence Inference Engine.
    Computes per-event boundary probabilities and process predictions.
    """
    def __init__(
        self,
        checkpoint_path: Path,
        device: Optional[torch.device] = None
    ):
        self.device = device or (torch.device("cuda:0") if torch.cuda.is_available() else torch.device("cpu"))
        self.checkpoint_path = Path(checkpoint_path)

        if not self.checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found at {checkpoint_path}")

        checkpoint = torch.load(self.checkpoint_path, map_location=self.device)
        self.model = MultimodalProcessNet()
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.to(self.device)
        self.model.eval()

        self.metadata = checkpoint.get("metadata", {})
        
        # Automatically load visual cache if present in same directory
        cache_file = self.checkpoint_path.parent / "visual_cache.pt"
        self.visual_cache: Dict[str, torch.Tensor] = {}
        if cache_file.exists():
            try:
                self.visual_cache = torch.load(cache_file, map_location="cpu")
            except Exception:
                pass

    @torch.no_grad()
    def predict_events(
        self,
        events: List[RawEvent],
        visual_cache: Optional[Dict[str, torch.Tensor]] = None
    ) -> Dict[str, Any]:
        if not events:
            return {"boundary_probs": [], "class_predictions": []}

        visual_cache = self.visual_cache if visual_cache is None else visual_cache
        n_events = len(events)
        ev_types = []
        numericals = []
        text_buckets_list = []
        vis_tensors = []

        for i, ev in enumerate(events):
            ev_t = ev.event_type.lower()
            ev_idx = EVENT_TO_IDX.get(ev_t, EVENT_TO_IDX["other"])
            ev_types.append(ev_idx)

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

            txt_context = f"{ev.app_name or ''} {ev.window_title or ''} {ev.browser_url or ''} {ev.extracted_text or ''}"
            text_buckets_list.append(hash_text_tokens(txt_context))

            scr_filename = (
                ev.payload.get("file_reference", {}).get("filename")
                or ev.payload.get("screenshot")
                or ""
            )
            vis_tensors.append(visual_cache.get(scr_filename, torch.zeros(256, dtype=torch.float32)))

        # Run inference in chunks
        window_size = 64
        step_size = 32
        accum_boundary_probs = [0.0] * n_events
        accum_counts = [0] * n_events

        for start_idx in range(0, max(1, n_events - window_size + 1), step_size):
            end_idx = min(start_idx + window_size, n_events)
            cur_len = end_idx - start_idx
            if cur_len < 4:
                continue

            sub_ev = torch.tensor([ev_types[start_idx:end_idx]], dtype=torch.long, device=self.device)
            sub_num = torch.tensor([numericals[start_idx:end_idx]], dtype=torch.float32, device=self.device)
            sub_vis = torch.stack(vis_tensors[start_idx:end_idx]).unsqueeze(0).to(self.device)

            flat_hashes = []
            offsets = []
            curr_offset = 0
            for t_i in range(cur_len):
                offsets.append(curr_offset)
                h_list = text_buckets_list[start_idx + t_i]
                flat_hashes.extend(h_list)
                curr_offset += len(h_list)

            txt_h = torch.tensor(flat_hashes, dtype=torch.long, device=self.device)
            txt_off = torch.tensor(offsets, dtype=torch.long, device=self.device)

            with torch.amp.autocast("cuda", enabled=self.device.type == "cuda"):
                out = self.model(
                    event_types=sub_ev,
                    numerical_feats=sub_num,
                    text_hashes=txt_h,
                    text_offsets=txt_off,
                    visual_feats=sub_vis
                )

            probs = out["boundary_probs"][0].cpu().tolist()
            for rel_idx, p in enumerate(probs):
                abs_idx = start_idx + rel_idx
                accum_boundary_probs[abs_idx] += p
                accum_counts[abs_idx] += 1

        final_probs = [
            (accum_boundary_probs[i] / max(1, accum_counts[i])) if accum_counts[i] > 0 else 0.0
            for i in range(n_events)
        ]

        return {
            "boundary_probs": final_probs,
            "device": str(self.device)
        }
