import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.ingestion.models import RawEvent, GroundTruthExecution

logger = logging.getLogger(__name__)


def parse_event_line(line: str) -> Optional[RawEvent]:
    line = line.strip()
    if not line:
        return None
    try:
        data = json.loads(line)
    except Exception:
        return None

    ctx = data.get("context") or {}
    app = ctx.get("active_app") or {}
    tab = ctx.get("active_browser_tab") or {}
    corr = data.get("correlation") or {}
    payload = data.get("payload") or {}

    ext_text_raw = ctx.get("extracted_text")
    ext_text = None
    if isinstance(ext_text_raw, dict):
        ext_text = ext_text_raw.get("text")
    elif isinstance(ext_text_raw, str):
        ext_text = ext_text_raw

    return RawEvent(
        event_id=data.get("event_id", ""),
        session_id=data.get("session_id", ""),
        timestamp_ms=data.get("timestamp_ms", 0),
        timestamp_iso=data.get("timestamp_iso", ""),
        layer=data.get("layer", ""),
        event_type=data.get("event_type", ""),
        app_name=app.get("app_name"),
        window_title=app.get("window_title"),
        browser_url=tab.get("url"),
        browser_title=tab.get("title"),
        ms_since_last_event=corr.get("ms_since_last_event"),
        payload=payload,
        extracted_text=ext_text
    )


class SessionDataLoader:
    """
    Ingests and validates raw telemetry event streams and ground-truth manifests.
    """
    def __init__(self, session_path: Path):
        self.session_path = Path(session_path)
        self.session_id = self.session_path.name

    def iter_events(self):
        """
        Yields events sequentially from chunks without loading all into memory at once.
        Note: For globally timestamp-sorted sequence across chunks, use load_events().
        """
        if not self.session_path.exists() or not self.session_path.is_dir():
            return

        chunks = sorted([
            d for d in self.session_path.iterdir()
            if d.is_dir() and d.name.startswith("chunk_")
        ], key=lambda x: x.name)

        for chunk_dir in chunks:
            events_file = chunk_dir / "events.jsonl"
            if not events_file.exists():
                continue
            with open(events_file, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    ev = parse_event_line(line)
                    if ev:
                        yield ev

    def load_events(self) -> List[RawEvent]:
        """
        Loads all events from all chunks in this session,
        sorted chronologically by timestamp_ms.
        """
        if not self.session_path.exists() or not self.session_path.is_dir():
            return []

        events: List[RawEvent] = list(self.iter_events())
        events.sort(key=lambda e: (e.timestamp_ms, e.event_id))
        return events

    def load_ground_truth(self) -> List[GroundTruthExecution]:
        """
        Loads ground truth executions from gt_manifest.json if present.
        """
        manifest_file = self.session_path / "gt_manifest.json"
        if not manifest_file.exists():
            return []

        with open(manifest_file, "r", encoding="utf-8", errors="replace") as f:
            try:
                data = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read {manifest_file}: {e}")
                return []

        gt_list: List[GroundTruthExecution] = []
        if "processes" in data:
            for proc in data.get("processes", []):
                code = proc.get("code", "")
                family_name = proc.get("family_name", "")
                domain = proc.get("domain", "")
                for ex in proc.get("executions", []):
                    gt_list.append(GroundTruthExecution(
                        code=code,
                        family_name=family_name,
                        domain=domain,
                        case_id=ex.get("case_id", ""),
                        start_ts=ex.get("start_ts", ""),
                        end_ts=ex.get("end_ts"),
                        variant=ex.get("variant"),
                        apps=ex.get("apps", []),
                        split_id=ex.get("split_id"),
                        phase=ex.get("phase", 1)
                    ))
        elif "executions" in data:
            for ex in data.get("executions", []):
                gt_list.append(GroundTruthExecution(
                    code=ex.get("code", ""),
                    family_name=ex.get("family_name", ""),
                    domain=ex.get("domain", ""),
                    case_id=ex.get("case_id", ""),
                    start_ts=ex.get("start_ts", ""),
                    end_ts=ex.get("end_ts"),
                    variant=ex.get("variant"),
                    apps=ex.get("apps", []),
                    split_id=ex.get("split_id"),
                    phase=ex.get("phase", 1)
                ))

        return gt_list
