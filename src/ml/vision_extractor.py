from pathlib import Path
from typing import List, Dict, Optional, Union
import torch  # type: ignore
import torch.nn as nn  # type: ignore
from PIL import Image  # type: ignore
import torchvision.transforms as transforms  # type: ignore
import torchvision.models as models  # type: ignore
import logging

logger = logging.getLogger(__name__)

class VisualFeatureExtractor(nn.Module):
    """
    High-throughput Visual Feature Extractor using MobileNetV3 on NVIDIA RTX GPU.
    Converts desktop operation screenshots into compact 256-dimensional visual state vectors.
    """
    def __init__(
        self,
        output_dim: int = 256,
        device: Optional[torch.device] = None
    ):
        super().__init__()
        self.device = device or (torch.device("cuda:0") if torch.cuda.is_available() else torch.device("cpu"))
        self.output_dim = output_dim

        # Load MobileNetV3-Small backbone
        try:
            weights = models.MobileNet_V3_Small_Weights.DEFAULT
            backbone = models.mobilenet_v3_small(weights=weights)
        except Exception as e:
            logger.warning(f"Could not load online weights ({e}), initializing standard MobileNetV3-Small.")
            backbone = models.mobilenet_v3_small()

        # Extract features up to pooling
        self.features = backbone.features
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        
        # 576 is mobilenet_v3_small final feature channel count
        in_features = 576
        self.projection = nn.Sequential(
            nn.Linear(in_features, output_dim),
            nn.LayerNorm(output_dim),
            nn.GELU()
        )
        
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
        
        self.to(self.device)
        self.eval()

    @torch.no_grad()
    def extract_image_tensor(self, img_path: Union[str, Path]) -> Optional[torch.Tensor]:
        path = Path(img_path)
        if not path.exists():
            return None
        try:
            with Image.open(path) as img:
                img_rgb = img.convert("RGB")
                tensor = self.transform(img_rgb).unsqueeze(0).to(self.device)
                
            with torch.amp.autocast("cuda", enabled=self.device.type == "cuda"):
                feat = self.features(tensor)
                pooled = self.avgpool(feat).flatten(1)
                emb = self.projection(pooled)
            return emb.squeeze(0).cpu()
        except Exception as e:
            logger.debug(f"Error extracting features from {path}: {e}")
            return None

    @torch.no_grad()
    def extract_batch(self, img_paths: List[Union[str, Path]], batch_size: int = 64) -> Dict[str, torch.Tensor]:
        results: Dict[str, torch.Tensor] = {}
        batch_tensors: List[torch.Tensor] = []
        batch_keys: List[str] = []

        for p in img_paths:
            path = Path(p)
            if not path.exists():
                continue
            try:
                with Image.open(path) as img:
                    img_rgb = img.convert("RGB")
                    tensor = self.transform(img_rgb)
                    batch_tensors.append(tensor)
                    batch_keys.append(str(path))
            except Exception:
                continue

            if len(batch_tensors) >= batch_size:
                stack = torch.stack(batch_tensors).to(self.device)
                with torch.amp.autocast("cuda", enabled=self.device.type == "cuda"):
                    feat = self.features(stack)
                    pooled = self.avgpool(feat).flatten(1)
                    embs = self.projection(pooled).cpu()
                for k, emb in zip(batch_keys, embs):
                    results[k] = emb
                batch_tensors = []
                batch_keys = []

        if batch_tensors:
            stack = torch.stack(batch_tensors).to(self.device)
            with torch.amp.autocast("cuda", enabled=self.device.type == "cuda"):
                feat = self.features(stack)
                pooled = self.avgpool(feat).flatten(1)
                embs = self.projection(pooled).cpu()
            for k, emb in zip(batch_keys, embs):
                results[k] = emb

        return results
