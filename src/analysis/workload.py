import json
import statistics
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict
from datetime import datetime


class WorkloadAnalyzer:
    """
    Quantifies operational workload, duration variance, and confidence distribution
    across recovered production segments in Dataset B.
    """
    def __init__(self, segments_path: Path, dataset_b_path: Path):
        self.segments_path = Path(segments_path)
        self.dataset_b_path = Path(dataset_b_path)

    def analyze(self) -> Dict[str, Any]:
        segments: List[Dict[str, Any]] = []
        if self.segments_path.exists():
            with open(self.segments_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        segments.append(json.loads(line))

        # Map machines/operators to sessions
        session_machines = {}
        if self.dataset_b_path.exists():
            for s_dir in self.dataset_b_path.iterdir():
                if s_dir.is_dir():
                    parts = s_dir.name.split("-")
                    machine = parts[-1] if len(parts) >= 3 else "unknown"
                    session_machines[s_dir.name] = machine

        proc_stats = defaultdict(lambda: {
            "count": 0,
            "durations": [],
            "confidences": [],
            "sessions": set(),
            "machines": set(),
        })

        for seg in segments:
            lbl = seg.get("label", "unknown_or_unclassified")
            s_id = seg.get("session_id", "")
            mach = session_machines.get(s_id, "unknown")
            s_time = seg.get("start") or seg.get("start_time")
            e_time = seg.get("end") or seg.get("end_time")
            conf = float(seg.get("confidence", 0.5))

            dur = float(seg.get("duration_seconds", 0.0))
            if dur <= 0.0 and s_time and e_time:
                dt_s = datetime.fromisoformat(s_time.replace("Z", "+00:00"))
                dt_e = datetime.fromisoformat(e_time.replace("Z", "+00:00"))
                dur = max(1.0, (dt_e - dt_s).total_seconds())

            proc_stats[lbl]["count"] += 1
            proc_stats[lbl]["durations"].append(dur)
            proc_stats[lbl]["confidences"].append(conf)
            proc_stats[lbl]["sessions"].add(s_id)
            proc_stats[lbl]["machines"].add(mach)

        results = {}
        total_work_time = sum(sum(d["durations"]) for d in proc_stats.values())

        for lbl, data in proc_stats.items():
            durations = data["durations"]
            confs = data["confidences"]
            tot_sec = sum(durations)
            avg_sec = statistics.mean(durations) if durations else 0.0
            std_sec = statistics.stdev(durations) if len(durations) > 1 else 0.0
            avg_conf = statistics.mean(confs) if confs else 0.5

            results[lbl] = {
                "process_label": lbl,
                "execution_count": data["count"],
                "total_duration_seconds": round(tot_sec, 1),
                "total_duration_minutes": round(tot_sec / 60.0, 2),
                "pct_of_total_time": round((tot_sec / max(1.0, total_work_time)) * 100.0, 1),
                "mean_duration_seconds": round(avg_sec, 1),
                "std_duration_seconds": round(std_sec, 1),
                "mean_confidence": round(avg_conf, 2),
                "sessions_count": len(data["sessions"]),
                "operators_count": len(data["machines"]),
                "machines_involved": sorted(list(data["machines"]))
            }

        return {
            "total_segments": len(segments),
            "total_work_seconds": round(total_work_time, 1),
            "total_work_minutes": round(total_work_time / 60.0, 2),
            "process_metrics": results
        }


# Backwards compatibility alias
DatasetBAnalyzer = WorkloadAnalyzer
