import json
import statistics
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict, Counter
from datetime import datetime
from src.ingestion.loader import SessionDataLoader
from src.ingestion.models import RawEvent


class ProcessMiningEngine:
    """
    Enterprise Process Mining & Conformance Engine.
    Discovers Directly-Follows Graphs (DFG), bottleneck transition latencies,
    and intra-process execution variants from desktop telemetry.
    """

    def __init__(self, dataset_path: Optional[Path] = None):
        self.dataset_path = Path(dataset_path) if dataset_path else None

    def extract_directly_follows_graph(self, filter_noise: bool = True, target_label: Optional[str] = None, segments: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Builds the Directly-Follows Graph (DFG) mapping transitions between
        applications, web views, and document artifacts.
        Can optionally be filtered to events strictly within confirmed segment intervals.
        """
        transitions = Counter()
        transition_latencies = defaultdict(list)
        node_frequencies = Counter()

        # Build lookup table of intervals per session if target_label & segments provided
        session_intervals: Dict[str, List[Tuple[datetime, datetime]]] = defaultdict(list)
        if target_label and segments:
            for s in segments:
                lbl = s.get("label") if isinstance(s, dict) else getattr(s, "label", None)
                if lbl == target_label:
                    sid = s.get("session_id") if isinstance(s, dict) else getattr(s, "session_id", None)
                    s_str = s.get("start") if isinstance(s, dict) else getattr(s, "start", None)
                    e_str = s.get("end") if isinstance(s, dict) else getattr(s, "end", None)
                    if sid and s_str and e_str:
                        dt_s = datetime.fromisoformat(str(s_str).replace("Z", "+00:00"))
                        dt_e = datetime.fromisoformat(str(e_str).replace("Z", "+00:00"))
                        session_intervals[sid].append((dt_s, dt_e))

        target = self.dataset_path or (Path(__file__).resolve().parent.parent.parent / "Datasets" / "dataset_b")
        if not target.exists():
            target = Path(__file__).resolve().parent.parent.parent / "data" / "dataset_b"
        sessions = sorted([d for d in target.iterdir() if d.is_dir()]) if target.exists() else []
        
        for s in sessions:
            loader = SessionDataLoader(s)
            events = loader.load_events()

            prev_activity = None
            prev_time = None

            for ev in events:
                curr_time = ev.datetime_utc

                # If interval filtering active, skip events outside target process intervals
                if target_label and segments:
                    intervals = session_intervals.get(loader.session_id, [])
                    in_interval = any(st <= curr_time <= et for (st, et) in intervals)
                    if not in_interval:
                        prev_activity = None
                        prev_time = None
                        continue

                app = ev.app_name or "System"
                url = ev.browser_url or ""
                wtitle = ev.window_title or ""

                # Abstract activity identity
                if "Edge" in app or "Chrome" in app:
                    if "#" in url:
                        route = url.split("#")[-1]
                        activity = f"WebPortal({route})"
                    elif "HR人事給与" in wtitle:
                        activity = "WebPortal(HR)"
                    elif "財務会計" in wtitle:
                        activity = "WebPortal(Finance)"
                    elif "受発注在庫" in wtitle:
                        activity = "WebPortal(Logistics)"
                    else:
                        activity = "WebBrowser"
                elif "Word" in app:
                    doc = "PolicyDoc"
                    for d in ["gyomu_itaku_kyuuyo_kitei", "nyusha_checklist", "keiyaku_kaijo", "settai_keihi"]:
                        if d in wtitle:
                            doc = f"Word({d})"
                            break
                    activity = doc
                elif "Excel" in app:
                    sheet = "Spreadsheet"
                    for sc in ["expense_calc", "budget_analysis", "m1_reference"]:
                        if sc in wtitle:
                            sheet = f"Excel({sc})"
                            break
                    activity = sheet
                elif "Notepad" in app:
                    activity = "NotepadMemo"
                elif any(term in app.lower() for term in ["terminal", "powershell", "cmd"]):
                    if filter_noise:
                        continue
                    activity = "Terminal(PowerShell)"
                elif any(term in app.lower() for term in ["slack", "teams"]):
                    if filter_noise:
                        continue
                    activity = "Chat(Communication)"
                else:
                    activity = f"DesktopApp({app[:15]})"

                node_frequencies[activity] += 1

                if prev_activity is not None and prev_activity != activity and prev_time is not None:
                    edge = (prev_activity, activity)
                    transitions[edge] += 1
                    latency = max(0.1, (curr_time - prev_time).total_seconds())
                    transition_latencies[edge].append(latency)

                prev_activity = activity
                prev_time = curr_time

        # Format DFG edges
        dfg_edges = []
        for (src, dst), count in transitions.most_common(25):
            lats = transition_latencies[(src, dst)]
            mean_lat = statistics.mean(lats) if lats else 0.0
            med_lat = statistics.median(lats) if lats else 0.0
            dfg_edges.append({
                "source": src,
                "target": dst,
                "frequency": count,
                "mean_latency_seconds": round(mean_lat, 2),
                "median_latency_seconds": round(med_lat, 2)
            })

        return {
            "node_frequencies": dict(node_frequencies.most_common(15)),
            "edges": dfg_edges
        }

    def analyze_bottlenecks(self, target_label: Optional[str] = None, segments: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Analyzes operational dwell times and identifies latency bottlenecks.
        When target_label and segments are provided, attributes dwell times
        strictly within the confirmed intervals of that process.
        """
        activity_times = defaultdict(list)
        session_intervals: Dict[str, List[Tuple[datetime, datetime]]] = defaultdict(list)
        if target_label and segments:
            for s in segments:
                lbl = s.get("label") if isinstance(s, dict) else getattr(s, "label", None)
                if lbl == target_label:
                    sid = s.get("session_id") if isinstance(s, dict) else getattr(s, "session_id", None)
                    s_str = s.get("start") if isinstance(s, dict) else getattr(s, "start", None)
                    e_str = s.get("end") if isinstance(s, dict) else getattr(s, "end", None)
                    if sid and s_str and e_str:
                        dt_s = datetime.fromisoformat(str(s_str).replace("Z", "+00:00"))
                        dt_e = datetime.fromisoformat(str(e_str).replace("Z", "+00:00"))
                        session_intervals[sid].append((dt_s, dt_e))

        target = self.dataset_path or (Path(__file__).resolve().parent.parent.parent / "Datasets" / "dataset_b")
        if not target.exists():
            target = Path(__file__).resolve().parent.parent.parent / "data" / "dataset_b"
        sessions = sorted([d for d in target.iterdir() if d.is_dir()]) if target.exists() else []

        for s in sessions:
            loader = SessionDataLoader(s)
            events = loader.load_events()
            if len(events) < 2:
                continue

            intervals = session_intervals.get(loader.session_id, [])

            for i in range(len(events) - 1):
                ev = events[i]
                next_ev = events[i+1]

                # Filter strictly by segment interval if requested
                if target_label and segments:
                    in_interval = any(st <= ev.datetime_utc <= et for (st, et) in intervals)
                    if not in_interval:
                        continue

                app = ev.app_name or "Unknown"
                url = ev.browser_url or ""
                wtitle = ev.window_title or ""

                if "#" in url:
                    cat = f"WebPortal({url.split('#')[-1]})"
                elif "Word" in app:
                    cat = "WordGuidelines"
                elif "Excel" in app:
                    cat = "ExcelCalculations"
                elif "Notepad" in app:
                    cat = "NotepadScratchpad"
                elif "Edge" in app or "Chrome" in app:
                    cat = "BrowserNavigation"
                else:
                    cat = app

                duration = min(60.0, max(0.1, (next_ev.datetime_utc - ev.datetime_utc).total_seconds()))
                activity_times[cat].append(duration)

        bottlenecks = []
        for cat, times in activity_times.items():
            tot = sum(times)
            bottlenecks.append({
                "activity": cat,
                "total_time_seconds": round(tot, 1),
                "total_time_minutes": round(tot / 60.0, 2),
                "interaction_count": len(times),
                "mean_dwell_seconds": round(statistics.mean(times), 2),
                "median_dwell_seconds": round(statistics.median(times), 2)
            })

        bottlenecks.sort(key=lambda x: x["total_time_seconds"], reverse=True)
        return {"bottlenecks": bottlenecks}

    def mine_dataset(self, dataset_path: Optional[Path] = None, segments: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Extracts process-level DFG metrics and application dwell times for segmented processes.
        Explicitly separates overall dataset dwell from process-attributed segment dwell.
        """
        if segments is None:
            seg_file = Path(__file__).resolve().parent.parent.parent / "deliverables" / "segments.jsonl"
            if seg_file.exists():
                segments = []
                with open(seg_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            segments.append(json.loads(line))

        # 1. Global pooled metrics across all Dataset B activity
        overall_dfg = self.extract_directly_follows_graph()
        overall_bottlenecks = self.analyze_bottlenecks()

        # 2. Process-specific metrics strictly attributed to payroll deduction adjustment intervals
        payroll_dfg = self.extract_directly_follows_graph(target_label="payroll_deduction_adjustment", segments=segments)
        payroll_bottlenecks = self.analyze_bottlenecks(target_label="payroll_deduction_adjustment", segments=segments)

        trans_dict = {}
        for edge in payroll_dfg.get("edges", []):
            trans_dict[(edge["source"], edge["target"])] = edge["frequency"]

        app_dwell = {}
        for b in payroll_bottlenecks.get("bottlenecks", []):
            app_dwell[b["activity"]] = b["total_time_seconds"]

        return {
            "payroll_deduction_adjustment": {
                "transitions": trans_dict,
                "app_dwell_seconds": app_dwell,
                "bottlenecks": payroll_bottlenecks.get("bottlenecks", []),
                "dfg": payroll_dfg
            },
            "overall_dfg": overall_dfg,
            "overall_bottlenecks": overall_bottlenecks
        }


# Alias for backward and notebook compatibility
DirectlyFollowsGraphMiner = ProcessMiningEngine

