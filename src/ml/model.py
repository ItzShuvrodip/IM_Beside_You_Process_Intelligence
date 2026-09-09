import torch  # type: ignore
import torch.nn as nn  # type: ignore
import torch.nn.functional as F  # type: ignore
from typing import Dict, Any, Optional

PROCESS_LABELS = [
    "payroll_deduction_adjustment",
    "leave_application_processing",
    "onboarding_verification",
    "resident_tax_confirmation",
    "expense_settlement_approval",
    "inventory_order_management",
    "budget_variance_analysis",
    "social_insurance_correction",
    "commute_allowance_entry",
    "employee_data_maintenance",
    "attendance_record_audit",
    "invoice_verification",
    "vendor_payment_processing",
    "year_end_tax_adjustment",
    "unknown_or_unclassified"
]

LABEL_TO_IDX = {label: i for i, label in enumerate(PROCESS_LABELS)}
IDX_TO_LABEL = {i: label for i, label in enumerate(PROCESS_LABELS)}

EVENT_TYPES = [
    "mouse_click",
    "mouse_down",
    "mouse_up",
    "key_down",
    "key_up",
    "text_input_complete",
    "window_focus",
    "window_close",
    "app_launch",
    "other"
]
EVENT_TO_IDX = {ev: i for i, ev in enumerate(EVENT_TYPES)}


class MultimodalProcessNet(nn.Module):
    """
    Multimodal Deep Learning Architecture for Process Boundary Detection and Classification.
    Combines mouse/keyboard telemetry, temporal pause dynamics, window semantic hashes,
    and GPU-accelerated screenshot visual representations into a unified sequence model.
    """
    def __init__(
        self,
        num_event_types: int = len(EVENT_TYPES) + 2,
        event_emb_dim: int = 32,
        num_numerical_features: int = 5,
        num_hash_buckets: int = 1024,
        text_emb_dim: int = 64,
        visual_in_dim: int = 256,
        visual_emb_dim: int = 64,
        hidden_dim: int = 96,
        num_classes: int = len(PROCESS_LABELS),
        dropout: float = 0.2
    ):
        super().__init__()
        self.num_classes = num_classes

        # 1. Interaction Event Type Embedding
        self.event_embed = nn.Embedding(num_event_types, event_emb_dim)

        # 2. Continuous Numerical Dynamics (gap, duration, x, y, text_length)
        self.num_proj = nn.Sequential(
            nn.Linear(num_numerical_features, 32),
            nn.LayerNorm(32),
            nn.GELU()
        )

        # 3. Semantic Window / URL Text Representation (Hash Embedding)
        self.text_embed = nn.EmbeddingBag(num_hash_buckets, text_emb_dim, mode="mean")

        # 4. Visual State Embedding (from MobileNetV3)
        self.vis_proj = nn.Sequential(
            nn.Linear(visual_in_dim, visual_emb_dim),
            nn.LayerNorm(visual_emb_dim),
            nn.GELU()
        )

        # 5. Multimodal Fusion Layer
        fusion_dim = event_emb_dim + 32 + text_emb_dim + visual_emb_dim
        self.fusion = nn.Sequential(
            nn.Linear(fusion_dim, 128),
            nn.LayerNorm(128),
            nn.GELU(),
            nn.Dropout(dropout)
        )

        # 6. Bidirectional Temporal Sequence Backbone
        self.lstm = nn.LSTM(
            input_size=128,
            hidden_size=hidden_dim,
            num_layers=2,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if dropout > 0 else 0
        )
        seq_out_dim = hidden_dim * 2

        # 7. Dual Output Heads
        # Head A: Per-timestep Boundary Detection Head P(boundary_t)
        self.boundary_head = nn.Sequential(
            nn.Linear(seq_out_dim, 64),
            nn.LayerNorm(64),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1)
        )

        # Head B: Process Classification Head P(class | segment)
        # Attention Pooling over sequence tokens
        self.attn_query = nn.Linear(seq_out_dim, 1)
        self.classifier_head = nn.Sequential(
            nn.Linear(seq_out_dim, 64),
            nn.LayerNorm(64),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes)
        )

    def forward(
        self,
        event_types: torch.Tensor,       # (B, T)
        numerical_feats: torch.Tensor,   # (B, T, 5)
        text_hashes: torch.Tensor,       # (B*T, num_hashes) for EmbeddingBag
        text_offsets: torch.Tensor,      # (B*T,)
        visual_feats: torch.Tensor,      # (B, T, 256)
        mask: Optional[torch.Tensor] = None # (B, T) bool
    ) -> Dict[str, torch.Tensor]:
        B, T = event_types.shape

        # 1. Embeddings
        ev_emb = self.event_embed(event_types) # (B, T, 32)
        num_emb = self.num_proj(numerical_feats) # (B, T, 32)

        # Text hash embedding
        txt_emb = self.text_embed(text_hashes, text_offsets).view(B, T, -1) # (B, T, 64)

        # Visual feature projection
        vis_emb = self.vis_proj(visual_feats) # (B, T, 64)

        # 2. Multimodal Fusion
        fused = torch.cat([ev_emb, num_emb, txt_emb, vis_emb], dim=-1) # (B, T, 192)
        fused_tokens = self.fusion(fused) # (B, T, 128)

        # 3. BiLSTM Sequence Modeling
        lstm_out, _ = self.lstm(fused_tokens) # (B, T, 192)

        # 4. Boundary Logits
        boundary_logits = self.boundary_head(lstm_out).squeeze(-1) # (B, T)

        # 5. Attention-Pooled Process Classification
        attn_scores = self.attn_query(lstm_out).squeeze(-1) # (B, T)
        if mask is not None:
            attn_scores = attn_scores.masked_fill(~mask, -1e4)
        attn_weights = F.softmax(attn_scores, dim=-1).unsqueeze(-1) # (B, T, 1)

        pooled_seq = torch.sum(lstm_out * attn_weights, dim=1) # (B, 192)
        class_logits = self.classifier_head(pooled_seq) # (B, num_classes)

        return {
            "boundary_logits": boundary_logits,
            "boundary_probs": torch.sigmoid(boundary_logits),
            "class_logits": class_logits,
            "class_probs": F.softmax(class_logits, dim=-1)
        }
