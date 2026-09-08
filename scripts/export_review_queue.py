"""Export ambiguous Dataset B segments for a human screenshot/event review."""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deliverables" / "segments.jsonl"
TARGET = ROOT / "deliverables" / "dataset_b_review_queue.csv"


def main() -> None:
    segments = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines() if line.strip()]
    candidates = [
        segment for segment in segments
        if segment.get("label") == "unknown_or_unclassified" or float(segment.get("confidence", 0)) <= 0.60
    ]
    with TARGET.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "session_id", "start", "end", "label", "confidence", "detection_method", "evidence",
            "reviewer", "review_status", "reviewed_label", "boundary_correct", "review_notes"
        ])
        writer.writeheader()
        for segment in candidates:
            writer.writerow({
                "session_id": segment.get("session_id", ""),
                "start": segment.get("start", ""),
                "end": segment.get("end", ""),
                "label": segment.get("label", ""),
                "confidence": segment.get("confidence", ""),
                "detection_method": segment.get("detection_method", ""),
                "evidence": " | ".join(segment.get("evidence", [])),
                "reviewer": "", "review_status": "pending", "reviewed_label": "",
                "boundary_correct": "", "review_notes": ""
            })
    print(f"Wrote {len(candidates)} review candidates to {TARGET}")


if __name__ == "__main__":
    main()
