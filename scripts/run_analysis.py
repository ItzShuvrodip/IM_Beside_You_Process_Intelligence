import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis.workload import WorkloadAnalyzer
from src.analysis.roi_model import ROIPrioritizationModel


def main():
    segments_file = PROJECT_ROOT / "deliverables" / "segments.jsonl"
    b_dir = PROJECT_ROOT / "Datasets" / "dataset_b"

    if not segments_file.exists():
        print("Error: deliverables/segments.jsonl does not exist. Run scripts/run_segmentation.py first.")
        return

    print("Executing Operational Workload & Financial ROI Analysis on Dataset B...")
    analyzer = WorkloadAnalyzer(segments_file, b_dir)
    analysis = analyzer.analyze()

    metrics = analysis["process_metrics"]
    model = ROIPrioritizationModel()
    rankings = model.rank_candidates(metrics)

    print("\n=========================================================================================")
    print("                    OPERATIONAL WORKLOAD & CONFIDENCE AUDIT (DATASET B)                  ")
    print("=========================================================================================")
    print(f"Total Recovered Segments: {analysis['total_segments']}")
    print(f"Total Active Work Time:   {analysis['total_work_minutes']:.1f} minutes ({analysis['total_work_seconds']:.0f} seconds)")
    print("-----------------------------------------------------------------------------------------")
    print(f"{'Process Label':<32} {'Count':<6} {'Total(min)':<11} {'Share%':<8} {'Mean(s)':<8} {'Conf':<6} {'Operators':<10}")
    print("-----------------------------------------------------------------------------------------")
    for m in metrics.values():
        print(f"{m['process_label']:<32} {m['execution_count']:<6} {m['total_duration_minutes']:<11.1f} {m['pct_of_total_time']:<8.1f} {m['mean_duration_seconds']:<8.1f} {m.get('mean_confidence', 0.5):<6.2f} {m['operators_count']:<10}")

    print("\n=========================================================================================")
    print("               AUTOMATION CANDIDATES PRIORITIZATION & FINANCIAL BUSINESS CASE            ")
    print("=========================================================================================")
    print(f"{'Rank':<5} {'Process / Family':<32} {'Dept':<12} {'Execs':<7} {'Payback(mo)':<13} {'3-Yr Net ROI':<14}")
    print("-----------------------------------------------------------------------------------------")
    for r in rankings:
        base_scen = r.get("financial_scenarios", {}).get("base_case", {})
        payback = f"{base_scen.get('payback_period_months', 99.0):.1f} mo"
        roi_pct = f"{base_scen.get('three_year_roi_pct', 0.0):+.1f}%"
        print(f"{r['rank']:<5} {r['process_label']:<32} {r['department']:<12} {r['execution_count']:<7} {payback:<13} {roi_pct:<14}")
    print("=========================================================================================\n")


if __name__ == "__main__":
    main()
