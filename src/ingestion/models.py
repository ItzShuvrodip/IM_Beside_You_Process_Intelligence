from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List


def format_iso_utc(ts: str) -> str:
    """Normalizes any ISO timestamp string to strict UTC format: YYYY-MM-DDTHH:MM:SSZ"""
    if not ts:
        return ""
    clean = ts.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(clean)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return ts


@dataclass
class RawEvent:
    event_id: str
    session_id: str
    timestamp_ms: int
    timestamp_iso: str
    layer: str
    event_type: str
    app_name: Optional[str] = None
    window_title: Optional[str] = None
    browser_url: Optional[str] = None
    browser_title: Optional[str] = None
    ms_since_last_event: Optional[int] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    extracted_text: Optional[str] = None

    @property
    def datetime_utc(self) -> datetime:
        clean_iso = self.timestamp_iso.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_iso)


@dataclass
class GroundTruthExecution:
    code: str
    family_name: str
    domain: str
    case_id: str
    start_ts: str
    end_ts: Optional[str]
    variant: Optional[str] = None
    apps: List[str] = field(default_factory=list)
    split_id: Optional[str] = None
    phase: int = 1

    @property
    def start_dt(self) -> datetime:
        return datetime.fromisoformat(self.start_ts.replace("Z", "+00:00"))

    @property
    def end_dt(self) -> Optional[datetime]:
        if not self.end_ts:
            return None
        return datetime.fromisoformat(self.end_ts.replace("Z", "+00:00"))


@dataclass
class Segment:
    session_id: str
    start: str
    end: str
    label: str
    confidence: float = 1.0
    detection_method: str = "hybrid_heuristic"
    evidence: List[str] = field(default_factory=list)

    @property
    def start_dt(self) -> datetime:
        return datetime.fromisoformat(self.start.replace("Z", "+00:00"))

    @property
    def end_dt(self) -> datetime:
        return datetime.fromisoformat(self.end.replace("Z", "+00:00"))

    @property
    def duration_seconds(self) -> float:
        return max(0.0, (self.end_dt - self.start_dt).total_seconds())

    @property
    def is_valid(self) -> bool:
        """Validates that interval has non-empty identity and non-negative duration."""
        try:
            return bool(self.session_id and self.start and self.end and self.label and self.start_dt <= self.end_dt)
        except Exception:
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Outputs strict standardized deliverable schema compatible with all consumers."""
        return {
            "session_id": self.session_id,
            "start": format_iso_utc(self.start),
            "end": format_iso_utc(self.end),
            "label": self.label,
            "start_time": format_iso_utc(self.start),
            "end_time": format_iso_utc(self.end),
            "duration_seconds": round(self.duration_seconds, 1),
            "confidence": round(self.confidence, 2),
            "detection_method": self.detection_method,
            "evidence": self.evidence
        }
