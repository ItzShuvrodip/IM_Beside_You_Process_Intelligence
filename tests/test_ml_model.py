import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest  # type: ignore
import torch  # type: ignore
from src.ml.model import MultimodalProcessNet, PROCESS_LABELS, EVENT_TYPES
from src.ml.dataset import hash_text_tokens


def test_hash_text_tokens():
    tokens = hash_text_tokens("payroll items adjustment portal")
    assert len(tokens) > 0
    assert all(isinstance(t, int) and t > 0 for t in tokens)

    # Empty text fallback
    empty_tokens = hash_text_tokens("")
    assert empty_tokens == [0]


def test_multimodal_process_net_shapes():
    B = 2
    T = 16
    model = MultimodalProcessNet(
        num_classes=len(PROCESS_LABELS),
        dropout=0.1
    )
    model.eval()

    event_types = torch.randint(0, len(EVENT_TYPES), (B, T))
    numerical_feats = torch.randn(B, T, 5)
    visual_feats = torch.randn(B, T, 256)
    
    # Text hash bag
    text_hashes = torch.randint(0, 1024, (B * T * 4,))
    text_offsets = torch.arange(0, B * T * 4, 4)

    with torch.no_grad():
        out = model(
            event_types=event_types,
            numerical_feats=numerical_feats,
            text_hashes=text_hashes,
            text_offsets=text_offsets,
            visual_feats=visual_feats
        )

    assert "boundary_logits" in out
    assert "boundary_probs" in out
    assert "class_logits" in out
    assert "class_probs" in out

    assert out["boundary_logits"].shape == (B, T)
    assert out["boundary_probs"].shape == (B, T)
    assert out["class_logits"].shape == (B, len(PROCESS_LABELS))
    assert out["class_probs"].shape == (B, len(PROCESS_LABELS))

    # Assert probability ranges
    assert (out["boundary_probs"] >= 0.0).all() and (out["boundary_probs"] <= 1.0).all()
    assert (out["class_probs"] >= 0.0).all() and (out["class_probs"] <= 1.0).all()


if __name__ == "__main__":
    pytest.main([__file__])
