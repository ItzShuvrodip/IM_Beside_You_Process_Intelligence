"""
Central configuration for workspace paths, datasets, models, and deliverables.
"""
import os
from pathlib import Path

# Project root
PROJECT_ROOT = Path(
    os.environ.get("IMBY_PROJECT_ROOT", Path(__file__).resolve().parent.parent)
).resolve()

# Data paths
DATASETS_DIR = PROJECT_ROOT / "Datasets"
DATASET_A_DIR = DATASETS_DIR / "dataset_a"
DATASET_B_DIR = DATASETS_DIR / "dataset_b"

# Deliverable outputs
DELIVERABLES_DIR = PROJECT_ROOT / "deliverables"
SEGMENTS_FILE = DELIVERABLES_DIR / "segments.jsonl"
AUDIT_TRAIL_FILE = DELIVERABLES_DIR / "audit_trail.jsonl"
DASHBOARD_HTML = DELIVERABLES_DIR / "automation_dashboard.html"
AUDIT_CSV_FILE = DELIVERABLES_DIR / "dataset_b_audit.csv"
REVIEW_QUEUE_CSV = DELIVERABLES_DIR / "dataset_b_review_queue.csv"

# Model checkpoints
MODELS_DIR = PROJECT_ROOT / "models"
MULTIMODAL_MODEL_PATH = MODELS_DIR / "multimodal_process_net.pt"
BILSTM_COMPAT_PATH = MODELS_DIR / "boundary_bilstm_best.pt"
VISUAL_CACHE_PATH = MODELS_DIR / "visual_cache.pt"
