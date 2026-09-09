import sys
import os
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging
import torch  # type: ignore
import torch.nn as nn  # type: ignore
import torch.nn.functional as F  # type: ignore
from torch.utils.data import DataLoader  # type: ignore

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ml.model import MultimodalProcessNet, PROCESS_LABELS
from src.ml.dataset import MultimodalTelemetryDataset, multimodal_collate_fn
from src.ml.vision_extractor import VisualFeatureExtractor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TrainMultimodal")


def sample_session_screenshots(sess_dir: Path, max_per_sess: int = 25) -> list:
    all_imgs = sorted(list(sess_dir.glob("**/screenshots/*.jpg")))
    if len(all_imgs) <= max_per_sess:
        return all_imgs
    step = len(all_imgs) / max_per_sess
    return [all_imgs[int(i * step)] for i in range(max_per_sess)]


def train_model(
    epochs: int = 12,
    batch_size: int = 32,
    lr: float = 1e-3,
    max_train_sessions: Optional[int] = None
):
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    logger.info(f"============================================================")
    logger.info(f"Starting Multimodal Model Training on: {device}")
    if device.type == "cuda":
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")
    logger.info(f"============================================================")

    data_dir = PROJECT_ROOT / "Datasets" / "dataset_a"
    b_data_dir = PROJECT_ROOT / "Datasets" / "dataset_b"
    models_dir = PROJECT_ROOT / "models"
    models_dir.mkdir(exist_ok=True)

    # 1. Pre-extract comprehensive visual cache across ALL sessions in Dataset A and Dataset B
    cache_file = models_dir / "visual_cache.pt"
    visual_cache = {}
    if cache_file.exists():
        logger.info(f"Checking existing visual cache from {cache_file}...")
        try:
            visual_cache = torch.load(cache_file, map_location="cpu")
            logger.info(f"Found {len(visual_cache)} cached keys.")
        except Exception as e:
            logger.warning(f"Could not load cache: {e}")

    # Re-extract if cache doesn't cover all sessions
    if len(visual_cache) < 1500:
        logger.info("Initializing GPU visual feature extractor across ALL 63 sessions in A and 15 sessions in B...")
        extractor = VisualFeatureExtractor(output_dim=256, device=device)
        
        a_sessions = sorted([d for d in data_dir.iterdir() if d.is_dir()])
        b_sessions = sorted([d for d in b_data_dir.iterdir() if d.is_dir()])
        
        sample_jpgs = []
        for s in a_sessions:
            sample_jpgs.extend(sample_session_screenshots(s, max_per_sess=25))
        for s in b_sessions:
            sample_jpgs.extend(sample_session_screenshots(s, max_per_sess=25))

        logger.info(f"Extracting visual features for {len(sample_jpgs)} screenshots across all {len(a_sessions)+len(b_sessions)} sessions...")
        t0 = time.time()
        batch_res = extractor.extract_batch(sample_jpgs, batch_size=64)
        for k, v in batch_res.items():
            visual_cache[k] = v
            visual_cache[Path(k).name] = v  # Also key by basename for fast event lookup
        dur = time.time() - t0
        logger.info(f"Extracted {len(sample_jpgs)} visual representations in {dur:.2f}s ({len(sample_jpgs)/max(1e-3, dur):.1f} img/s).")
        torch.save(visual_cache, cache_file)

    # 2. Build Dataset across 100% of Dataset A sessions (~162k events)
    logger.info("Loading 100% of sessions in Dataset A into MultimodalTelemetryDataset...")
    train_dataset = MultimodalTelemetryDataset(
        sessions_dir=data_dir,
        window_size=64,
        step_size=32,
        visual_cache=visual_cache,
        max_sessions=max_train_sessions
    )
    logger.info(f"Constructed {len(train_dataset)} multimodal sequence windows covering the COMPLETE dataset.")

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=multimodal_collate_fn,
        drop_last=True
    )

    # 3. Model, Optimizer, Loss
    model = MultimodalProcessNet(
        hidden_dim=96,
        num_classes=len(PROCESS_LABELS),
        dropout=0.2
    ).to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")

    pos_weight = torch.tensor([4.0], device=device)
    bce_loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    ce_loss_fn = nn.CrossEntropyLoss()

    best_loss = float("inf")
    best_checkpoint: Optional[Dict[str, Any]] = None

    logger.info("Beginning sequence training loop with mixed precision (AMP)...")
    start_time = time.time()

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        total_b_loss = 0.0
        total_c_loss = 0.0
        n_batches = 0

        for batch in train_loader:
            ev_types = batch["event_types"].to(device)
            num_feats = batch["numerical_feats"].to(device)
            txt_hashes = batch["text_hashes"].to(device)
            txt_offsets = batch["text_offsets"].to(device)
            vis_feats = batch["visual_feats"].to(device)
            targets_b = batch["boundaries"].to(device)
            targets_c = batch["majority_classes"].to(device)
            mask = batch["mask"].to(device)

            optimizer.zero_grad()

            with torch.amp.autocast("cuda", enabled=device.type == "cuda"):
                out = model(
                    event_types=ev_types,
                    numerical_feats=num_feats,
                    text_hashes=txt_hashes,
                    text_offsets=txt_offsets,
                    visual_feats=vis_feats,
                    mask=mask
                )
                b_logits = out["boundary_logits"]
                loss_boundary = bce_loss_fn(b_logits[mask], targets_b[mask])
                loss_class = ce_loss_fn(out["class_logits"], targets_c)
                loss = loss_boundary + 0.4 * loss_class

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            total_loss += loss.item()
            total_b_loss += loss_boundary.item()
            total_c_loss += loss_class.item()
            n_batches += 1

        avg_loss = total_loss / max(1, n_batches)
        avg_b = total_b_loss / max(1, n_batches)
        avg_c = total_c_loss / max(1, n_batches)

        logger.info(
            f"Epoch [{epoch:02d}/{epochs:02d}] "
            f"Loss: {avg_loss:.4f} | Boundary Loss: {avg_b:.4f} | Class Loss: {avg_c:.4f}"
        )

        if avg_loss < best_loss:
            best_loss = avg_loss
            best_checkpoint = {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "loss": best_loss,
                "metadata": {
                    "device": str(device),
                    "parameters": sum(p.numel() for p in model.parameters()),
                    "epochs": epoch,
                    "best_loss": best_loss,
                    "num_classes": len(PROCESS_LABELS),
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
            }

    total_training_time = time.time() - start_time
    logger.info(f"Training complete in {total_training_time:.2f}s. Best Epoch Loss: {best_loss:.4f}")

    if best_checkpoint is None:
        raise RuntimeError("Training did not produce any valid checkpoint.")

    # Save to both target locations
    target_path = models_dir / "multimodal_process_net.pt"
    bilstm_compat_path = models_dir / "boundary_bilstm_best.pt"

    torch.save(best_checkpoint, target_path)
    torch.save(best_checkpoint, bilstm_compat_path)

    logger.info(f"Saved primary checkpoint to {target_path}")
    logger.info(f"Saved compatibility checkpoint to {bilstm_compat_path}")
    metadata = best_checkpoint.get("metadata", {})
    num_params = metadata.get("parameters", 0) if isinstance(metadata, dict) else 0
    logger.info(f"Model parameters: {num_params:,}")
    return best_checkpoint


if __name__ == "__main__":
    train_model(epochs=12, batch_size=32)
