import sys
import json
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DATASET_B_DIR, DELIVERABLES_DIR, SEGMENTS_FILE, MULTIMODAL_MODEL_PATH
from src.segmentation.hybrid_segmenter import HybridSegmenter


def main():
    b_dir = DATASET_B_DIR
    deliverables_dir = DELIVERABLES_DIR
    deliverables_dir.mkdir(parents=True, exist_ok=True)
    out_file = SEGMENTS_FILE  # deliverables/segments.jsonl

    model_path = MULTIMODAL_MODEL_PATH
    segmenter = HybridSegmenter(
        dwell_gap_seconds=24.0,
        min_segment_seconds=6.0,
        min_segment_events=3,
        merge_gap_seconds=6.0,
        neural_checkpoint=model_path if model_path.exists() else None
    )

    all_segments = segmenter.process_all_sessions(b_dir)

    print(f"Recovered {len(all_segments)} work unit segments across {len(list(b_dir.iterdir()))} production sessions.")

    # Write deliverables/segments.jsonl only
    with open(out_file, "w", encoding="utf-8") as f:
        for seg in all_segments:
            line = json.dumps(seg.to_dict(), ensure_ascii=False)
            f.write(line + "\n")

    print(f"Successfully written to {out_file}")

    # Strict Validation
    print("\nPerforming strict schema and format verification on deliverables/segments.jsonl...")
    total_valid = 0
    labels = {}
    confidences = []
    
    with open(out_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            obj = json.loads(line)
            assert "session_id" in obj, f"Missing session_id on line {line_num}"
            assert "start" in obj, f"Missing start on line {line_num}"
            assert "end" in obj, f"Missing end on line {line_num}"
            assert "label" in obj, f"Missing label on line {line_num}"
            assert "confidence" in obj, f"Missing confidence on line {line_num}"
            assert obj["start"].endswith("Z"), f"Start timestamp must end with Z: {obj['start']}"
            assert obj["end"].endswith("Z"), f"End timestamp must end with Z: {obj['end']}"

            dt_start = datetime.fromisoformat(obj["start"].replace("Z", "+00:00"))
            dt_end = datetime.fromisoformat(obj["end"].replace("Z", "+00:00"))
            assert dt_start <= dt_end, f"start > end on line {line_num}: {obj['start']} > {obj['end']}"

            lbl = obj["label"]
            labels[lbl] = labels.get(lbl, 0) + 1
            confidences.append(float(obj["confidence"]))
            total_valid += 1

    avg_conf = sum(confidences) / max(1, len(confidences))
    print(f"Verification PASSED! All {total_valid} lines in {out_file.name} are strictly valid.")
    print(f"Mean Segment Confidence: {avg_conf:.2f}")
    print("\nDataset B Process Label Distribution:")
    for lbl, cnt in sorted(labels.items(), key=lambda x: x[1], reverse=True):
        print(f"  {lbl:<35}: {cnt:4d} segments ({cnt/total_valid*100:.1f}%)")


if __name__ == "__main__":
    main()
