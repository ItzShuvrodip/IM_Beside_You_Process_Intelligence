"""
Enterprise Project Configuration & Directory Abstraction for IMBY Platform.

Centralizes all root directory resolution, dataset paths, model paths,
and deliverable output locations in a single place.

Usage:
    from src.config import PROJECT_ROOT, DATASETS_DIR, DATASET_A_DIR, DATASET_B_DIR
    from src.config import DELIVERABLES_DIR, MODELS_DIR, SEGMENTS_FILE
"""
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Universal Project Root Resolution
# ---------------------------------------------------------------------------
# By default, dynamically resolves to the repository root (parent of 'src').
# Can be globally overridden via the IMBY_PROJECT_ROOT environment variable.
PROJECT_ROOT = Path(
    os.environ.get("IMBY_PROJECT_ROOT", Path(__file__).resolve().parent.parent)
).resolve()

# ---------------------------------------------------------------------------
# Data Directories
# ---------------------------------------------------------------------------
DATASETS_DIR = PROJECT_ROOT / "Datasets"
DATASET_A_DIR = DATASETS_DIR / "dataset_a"
DATASET_B_DIR = DATASETS_DIR / "dataset_b"

# ---------------------------------------------------------------------------
# Deliverables & Generated Artifacts
# ---------------------------------------------------------------------------
DELIVERABLES_DIR = PROJECT_ROOT / "deliverables"
SEGMENTS_FILE = DELIVERABLES_DIR / "segments.jsonl"
AUDIT_TRAIL_FILE = DELIVERABLES_DIR / "audit_trail.jsonl"
DASHBOARD_HTML = DELIVERABLES_DIR / "automation_dashboard.html"
AUDIT_CSV_FILE = DELIVERABLES_DIR / "dataset_b_audit.csv"
REVIEW_QUEUE_CSV = DELIVERABLES_DIR / "dataset_b_review_queue.csv"

# ---------------------------------------------------------------------------
# ML Model Checkpoints & Visual Caches
# ---------------------------------------------------------------------------
MODELS_DIR = PROJECT_ROOT / "models"
MULTIMODAL_MODEL_PATH = MODELS_DIR / "multimodal_process_net.pt"
BILSTM_COMPAT_PATH = MODELS_DIR / "boundary_bilstm_best.pt"
VISUAL_CACHE_PATH = MODELS_DIR / "visual_cache.pt"
