# -*- coding: utf-8 -*-
"""
crackxnet.py — CrackXNet inference module.

Authoritative model architecture (HybridBackbone + DDRM fusion + multi-task detector),
the severity/decision logic, and the `inspect_board()` inference pipeline.
"""

import os
import math
import time
from collections import OrderedDict
from datetime import datetime

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F

import torchvision
from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights
from torchvision.models.detection import FasterRCNN
from torchvision.models.detection.rpn import AnchorGenerator
from torchvision.models._utils import IntermediateLayerGetter
from torchvision.ops import MultiScaleRoIAlign, FeaturePyramidNetwork
import torchvision.transforms.functional as TF
from PIL import Image

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ---------------------------------------------------------------------------
# Configuration — architecture flags must match whatever the checkpoint was trained with.
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

CONFIG = {
    "img_size": 640,
    "num_classes": 7,  # 6 defect types + background(0)

    "checkpoint_dir": os.path.join(PROJECT_ROOT, "checkpoints"),
    "model_path": os.path.join(PROJECT_ROOT, "checkpoints", "crackxnet_final.pth"),
    "decision_net_path": os.path.join(PROJECT_ROOT, "checkpoints", "decision_net.pth"),
    "report_dir": os.path.join(PROJECT_ROOT, "reports"),
    "history_path": os.path.join(PROJECT_ROOT, "reports", "inspection_history.csv"),

    # --- architecture ablation switches — MUST match the checkpoint's training config ---
    "USE_TRANSFORMER": True,
    "USE_AFFM": True,
    "USE_COMPLEXITY_ANALYZER": True,
    "COMPLEXITY_EMBED_DIM": 32,
    "USE_MULTITASK": True,
    "USE_EXPLAIN_LOSS": True,
    "USE_SEVERITY_HEAD": True,
    "USE_CAM_CONSISTENCY": True,
    "EXPLAIN_LOSS_WEIGHT": 0.1,
    "CAM_CONSISTENCY_WEIGHT": 0.05,
    "SEVERITY_LOSS_WEIGHT": 0.1,
    "TRANSFORMER_EMBED_DIM": 256,
    "TRANSFORMER_HEADS": 4,
    "TRANSFORMER_LAYERS": 2,

    "USE_DECISION_NETWORK": True,
    "DECISION_HIDDEN_DIM": 32,
}

CLASS_NAMES = {
    0: "background", 1: "open", 2: "short", 3: "mousebite",
    4: "spur", 5: "spurious_copper", 6: "pin_hole",
}
NUM_CLASSES = len(CLASS_NAMES)

RISK_WEIGHT = {
    "open": 1.00, "short": 1.00, "pin_hole": 0.70,
    "spurious_copper": 0.60, "spur": 0.50, "mousebite": 0.45,
}

SEVERITY_BINS = [(25, "Low"), (50, "Medium"), (75, "High"), (101, "Critical")]

DECISION_RULES_NOTE = (
    "Any Critical defect -> REJECT. "
    "No Critical but any High, or 3+ Medium -> REWORK. "
    "Otherwise -> PASS."
)

DECISION_CLASSES = ["PASS", "REWORK", "REJECT"]
DECISION_COLORS = {"PASS": "#2e7d32", "REWORK": "#f9a825", "REJECT": "#c62828"}


# ===========================================================================
# Model architecture (authoritative CrackXNet)
# ===========================================================================

class ChannelAttention(nn.Module):
    def __init__(self, channels, reduction=16):
        super().__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)
        hidden = max(channels // reduction, 8)
        self.mlp = nn.Sequential(
            nn.Conv2d(channels, hidden, 1, bias=False),
            nn.ReLU(inplace=True),
            nn.Conv2d(hidden, channels, 1, bias=False),
        )
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        avg_out = self.mlp(self.avg_pool(x))
        max_out = self.mlp(self.max_pool(x))
        return x * self.sigmoid(avg_out + max_out)


class SpatialAttention(nn.Module):
    def __init__(self, kernel_size=7):
        super().__init__()
        self.conv = nn.Conv2d(2, 1, kernel_size, padding=kernel_size // 2, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        avg_out = torch.mean(x, dim=1, keepdim=True)
        max_out, _ = torch.max(x, dim=1, keepdim=True)
        attn = self.sigmoid(self.conv(torch.cat([avg_out, max_out], dim=1)))
        return x * attn


class CBAM(nn.Module):
    def __init__(self, channels, reduction=16, kernel_size=7):
        super().__init__()
        self.channel_att = ChannelAttention(channels, reduction)
        self.spatial_att = SpatialAttention(kernel_size)

    def forward(self, x):
        return self.spatial_att(self.channel_att(x))


class TransformerBranch(nn.Module):
    """Lightweight Transformer encoder run on the deepest CNN feature map."""
    def __init__(self, in_channels, embed_dim=256, num_heads=4, num_layers=2, dropout=0.1):
        super().__init__()
        self.proj_in = nn.Conv2d(in_channels, embed_dim, 1)
        layer = nn.TransformerEncoderLayer(
            d_model=embed_dim, nhead=num_heads, dim_feedforward=embed_dim * 2,
            dropout=dropout, batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(layer, num_layers=num_layers)
        self.embed_dim = embed_dim
        self._pe_cache = {}

    def _positional_encoding(self, h, w, device):
        key = (h, w)
        if key not in self._pe_cache:
            n = h * w
            pe = torch.zeros(1, n, self.embed_dim, device=device)
            position = torch.arange(0, n, dtype=torch.float, device=device).unsqueeze(1)
            div = torch.exp(torch.arange(0, self.embed_dim, 2, device=device).float()
                             * (-math.log(10000.0) / self.embed_dim))
            pe[0, :, 0::2] = torch.sin(position * div)
            pe[0, :, 1::2] = torch.cos(position * div)
            self._pe_cache[key] = pe
        return self._pe_cache[key]

    def forward(self, x):
        b, c, h, w = x.shape
        z = self.proj_in(x)
        tokens = z.flatten(2).transpose(1, 2)
        tokens = tokens + self._positional_encoding(h, w, x.device)
        tokens = self.encoder(tokens)
        return tokens.transpose(1, 2).reshape(b, self.embed_dim, h, w)


class AFFM(nn.Module):
    """Adaptive Feature Fusion Module — plain gated fusion (used when USE_COMPLEXITY_ANALYZER=False)."""
    def __init__(self, channels, reduction=4):
        super().__init__()
        hidden = max(channels // reduction, 8)
        self.gate = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(channels * 2, hidden, 1), nn.ReLU(inplace=True),
            nn.Conv2d(hidden, channels, 1), nn.Sigmoid(),
        )

    def forward(self, cnn_feat, transformer_feat):
        g = self.gate(torch.cat([cnn_feat, transformer_feat], dim=1))
        return g * cnn_feat + (1 - g) * transformer_feat


class DefectComplexityAnalyzer(nn.Module):
    """First half of DDRM — summarizes CNN/Transformer disagreement + local texture busy-ness."""
    def __init__(self, channels, embed_dim=32):
        super().__init__()
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.encoder = nn.Sequential(
            nn.Linear(channels * 3, 64), nn.ReLU(inplace=True),
            nn.Linear(64, embed_dim), nn.ReLU(inplace=True),
        )

    def forward(self, cnn_feat, transformer_feat):
        disagreement = (cnn_feat - transformer_feat).pow(2)
        cnn_var = cnn_feat.var(dim=(2, 3), unbiased=False)
        cnn_mean = self.pool(cnn_feat).flatten(1)
        disagreement_pooled = self.pool(disagreement).flatten(1)
        descriptor = torch.cat([cnn_mean, cnn_var, disagreement_pooled], dim=1)
        return self.encoder(descriptor)


class DDRM(nn.Module):
    """Dynamic Defect-Aware Feature Fusion (D²AFF) — complexity-conditioned gated fusion."""
    def __init__(self, channels, embed_dim=32, reduction=4):
        super().__init__()
        self.complexity_analyzer = DefectComplexityAnalyzer(channels, embed_dim=embed_dim)
        hidden = max(channels // reduction, 8)
        self.complexity_proj = nn.Linear(embed_dim, channels)
        self.gate = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(channels * 2, hidden, 1), nn.ReLU(inplace=True),
            nn.Conv2d(hidden, channels, 1),
        )
        self.sigmoid = nn.Sigmoid()

    def forward(self, cnn_feat, transformer_feat):
        complexity = self.complexity_analyzer(cnn_feat, transformer_feat)
        complexity_bias = self.complexity_proj(complexity).unsqueeze(-1).unsqueeze(-1)
        gate_logits = self.gate(torch.cat([cnn_feat, transformer_feat], dim=1)) + complexity_bias
        g = self.sigmoid(gate_logits)
        return g * cnn_feat + (1 - g) * transformer_feat


class HybridBackbone(nn.Module):
    """EfficientNet-B0+CBAM CNN branch + Transformer branch, fused per-level by DDRM/AFFM, + FPN."""
    RETURN_LAYERS = {"3": "0", "5": "1", "8": "2"}
    OUT_CHANNELS_BY_LAYER = {"3": 40, "5": 112, "8": 1280}
    FPN_OUT_CHANNELS = 256

    def __init__(self, pretrained=False, use_transformer=True, use_affm=True, use_complexity_analyzer=True,
                 transformer_embed_dim=256, transformer_heads=4, transformer_layers=2,
                 complexity_embed_dim=32):
        super().__init__()
        weights = EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained else None
        eff = efficientnet_b0(weights=weights)
        self.body = IntermediateLayerGetter(eff.features, return_layers=self.RETURN_LAYERS)

        self.cbams = nn.ModuleDict({
            out_key: CBAM(self.OUT_CHANNELS_BY_LAYER[in_key])
            for in_key, out_key in self.RETURN_LAYERS.items()
        })

        self.use_transformer = use_transformer
        self.use_affm = use_affm and use_transformer
        self.use_complexity_analyzer = use_complexity_analyzer and self.use_affm

        if self.use_transformer:
            self.transformer = TransformerBranch(
                in_channels=self.OUT_CHANNELS_BY_LAYER["8"],
                embed_dim=transformer_embed_dim, num_heads=transformer_heads,
                num_layers=transformer_layers,
            )
            self.trans_proj = nn.ModuleDict({
                out_key: nn.Conv2d(transformer_embed_dim, self.OUT_CHANNELS_BY_LAYER[in_key], 1)
                for in_key, out_key in self.RETURN_LAYERS.items()
            })
            if self.use_affm:
                if self.use_complexity_analyzer:
                    self.affm = nn.ModuleDict({
                        out_key: DDRM(self.OUT_CHANNELS_BY_LAYER[in_key], embed_dim=complexity_embed_dim)
                        for in_key, out_key in self.RETURN_LAYERS.items()
                    })
                else:
                    self.affm = nn.ModuleDict({
                        out_key: AFFM(self.OUT_CHANNELS_BY_LAYER[in_key])
                        for in_key, out_key in self.RETURN_LAYERS.items()
                    })

        fpn_in_channels = [self.OUT_CHANNELS_BY_LAYER[k] for k in self.RETURN_LAYERS.keys()]
        self.fpn = FeaturePyramidNetwork(fpn_in_channels, out_channels=self.FPN_OUT_CHANNELS)
        self.out_channels = self.FPN_OUT_CHANNELS

    def forward(self, x):
        feats = self.body(x)
        feats = {k: self.cbams[k](v) for k, v in feats.items()}

        if self.use_transformer:
            global_ctx = self.transformer(feats["2"])
            fused = {}
            for k, v in feats.items():
                ctx = F.interpolate(global_ctx, size=v.shape[-2:], mode="bilinear", align_corners=False)
                ctx = self.trans_proj[k](ctx)
                fused[k] = self.affm[k](v, ctx) if self.use_affm else (v + ctx)
            feats = fused

        return self.fpn(feats)


def build_backbone(pretrained=False):
    return HybridBackbone(
        pretrained=pretrained,
        use_transformer=CONFIG["USE_TRANSFORMER"],
        use_affm=CONFIG["USE_AFFM"],
        use_complexity_analyzer=CONFIG.get("USE_COMPLEXITY_ANALYZER", True),
        transformer_embed_dim=CONFIG["TRANSFORMER_EMBED_DIM"],
        transformer_heads=CONFIG["TRANSFORMER_HEADS"],
        transformer_layers=CONFIG["TRANSFORMER_LAYERS"],
        complexity_embed_dim=CONFIG.get("COMPLEXITY_EMBED_DIM", 32),
    )


def boxes_to_mask(boxes, label_h, label_w, device):
    mask = torch.zeros((label_h, label_w), device=device)
    for b in boxes:
        x1, y1, x2, y2 = b.tolist()
        x1, y1 = max(0, int(x1)), max(0, int(y1))
        x2, y2 = min(label_w, int(x2)), min(label_h, int(y2))
        if x2 > x1 and y2 > y1:
            mask[y1:y2, x1:x2] = 1.0
    return mask


def gt_severity_target(box_xyxy, label_id, image_hw, area_reference=0.05):
    cls_name = CLASS_NAMES.get(int(label_id), "unknown")
    x1, y1, x2, y2 = box_xyxy
    box_area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    board_area = image_hw[0] * image_hw[1]
    ratio = box_area / board_area if board_area > 0 else 0.0
    size_score = min(1.0, math.sqrt(ratio) / math.sqrt(area_reference))
    risk = RISK_WEIGHT.get(cls_name, 0.5)
    dsi = 100.0 * (0.5 * risk + 0.3 * size_score + 0.2 * 1.0)
    return float(np.clip(dsi, 0, 100))


class ExplainabilityHead(nn.Module):
    def __init__(self, in_channels=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_channels, 64, 3, padding=1), nn.ReLU(inplace=True),
            nn.Conv2d(64, 1, 1),
        )

    def forward(self, feat):
        return self.net(feat)


class SeverityHead(nn.Module):
    def __init__(self, in_features=1024):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_features, 128), nn.ReLU(inplace=True),
            nn.Linear(128, 1), nn.Sigmoid(),
        )

    def forward(self, box_features):
        return self.net(box_features).squeeze(-1) * 100.0


def compute_gradcam_target(features, rpn_head, feature_key):
    feat = features[feature_key]
    objectness_logits, _ = rpn_head([feat])
    score = objectness_logits[0].mean()
    grads = torch.autograd.grad(score, feat, retain_graph=True, create_graph=False)[0]
    weights = grads.mean(dim=(2, 3), keepdim=True)
    cam = F.relu((weights * feat).sum(dim=1, keepdim=True))
    cam_min = cam.amin(dim=(2, 3), keepdim=True)
    cam_max = cam.amax(dim=(2, 3), keepdim=True)
    cam = (cam - cam_min) / (cam_max - cam_min + 1e-6)
    return cam.detach()


class CrackXNetDetector(FasterRCNN):
    """Subclasses torchvision's FasterRCNN to splice in the explainability + severity heads."""

    def __init__(self, backbone, num_classes, use_explain=True, use_severity=True,
                 use_cam_consistency=True, explain_weight=0.1, severity_weight=0.1,
                 cam_consistency_weight=0.05, explain_level="0", **kwargs):
        super().__init__(backbone, num_classes=num_classes, **kwargs)
        self.use_explain = use_explain
        self.use_severity = use_severity
        self.use_cam_consistency = use_cam_consistency and use_explain
        self.explain_weight = explain_weight
        self.severity_weight = severity_weight
        self.cam_consistency_weight = cam_consistency_weight
        self.explain_level = explain_level
        self.explain_head = ExplainabilityHead(backbone.out_channels) if use_explain else None
        self.severity_head = SeverityHead(1024) if use_severity else None

    def forward(self, images, targets=None):
        original_image_sizes = [tuple(img.shape[-2:]) for img in images]
        images_t, targets_t = self.transform(images, targets)
        features = self.backbone(images_t.tensors)
        if isinstance(features, torch.Tensor):
            features = OrderedDict([("0", features)])

        proposals, proposal_losses = self.rpn(images_t, features, targets_t)
        detections, detector_losses = self.roi_heads(features, proposals, images_t.image_sizes, targets_t)

        losses = {}
        losses.update(detector_losses)
        losses.update(proposal_losses)

        if self.training:
            if self.use_explain:
                sal_logits = self.explain_head(features[self.explain_level])
                sal_logits = F.interpolate(sal_logits, size=images_t.tensors.shape[-2:],
                                            mode="bilinear", align_corners=False)
                target_masks = torch.stack([
                    boxes_to_mask(t["boxes"], images_t.tensors.shape[-2], images_t.tensors.shape[-1],
                                  images_t.tensors.device)
                    for t in targets_t
                ]).unsqueeze(1)
                losses["loss_explain"] = self.explain_weight * F.binary_cross_entropy_with_logits(
                    sal_logits, target_masks)

                if self.use_cam_consistency:
                    cam_target = compute_gradcam_target(features, self.rpn.head, self.explain_level)
                    cam_target_up = F.interpolate(cam_target, size=sal_logits.shape[-2:],
                                                   mode="bilinear", align_corners=False)
                    losses["loss_cam_consistency"] = self.cam_consistency_weight * F.mse_loss(
                        torch.sigmoid(sal_logits), cam_target_up)

            if self.use_severity and any(len(t["boxes"]) > 0 for t in targets_t):
                per_image_boxes, per_image_targets = [], []
                for i, t in enumerate(targets_t):
                    per_image_boxes.append(t["boxes"])
                    per_image_targets.append([
                        gt_severity_target(b.tolist(), int(l), images_t.image_sizes[i])
                        for b, l in zip(t["boxes"], t["labels"])
                    ])
                nonempty = [i for i, b in enumerate(per_image_boxes) if len(b) > 0]
                if nonempty:
                    box_feats = self.roi_heads.box_roi_pool(
                        features, [per_image_boxes[i] for i in nonempty],
                        [images_t.image_sizes[i] for i in nonempty])
                    box_feats = self.roi_heads.box_head(box_feats)
                    pred_severity = self.severity_head(box_feats)
                    target_severity = torch.tensor(
                        sum((per_image_targets[i] for i in nonempty), []),
                        device=pred_severity.device, dtype=torch.float32)
                    losses["loss_severity"] = self.severity_weight * F.mse_loss(pred_severity, target_severity)

            return losses

        detections = self.transform.postprocess(detections, images_t.image_sizes, original_image_sizes)
        return detections

    @torch.no_grad()
    def predict_with_extras(self, images):
        """Inference helper: standard detections + learned saliency map + per-box severity."""
        self.eval()
        original_image_sizes = [tuple(img.shape[-2:]) for img in images]
        images_t, _ = self.transform(images, None)
        features = self.backbone(images_t.tensors)
        proposals, _ = self.rpn(images_t, features, None)
        detections, _ = self.roi_heads(features, proposals, images_t.image_sizes, None)
        detections_pp = self.transform.postprocess(
            [dict(d) for d in detections], images_t.image_sizes, original_image_sizes)

        saliency_maps = None
        if self.use_explain:
            sal_logits = self.explain_head(features[self.explain_level])
            sal_logits = F.interpolate(sal_logits, size=images_t.tensors.shape[-2:],
                                        mode="bilinear", align_corners=False)
            saliency_maps = torch.sigmoid(sal_logits)

        severities = []
        if self.use_severity:
            for i, det in enumerate(detections):
                boxes = det["boxes"]
                if len(boxes) == 0:
                    severities.append(torch.empty(0))
                    continue
                bf = self.roi_heads.box_roi_pool(features, [boxes], [images_t.image_sizes[i]])
                bf = self.roi_heads.box_head(bf)
                severities.append(self.severity_head(bf).detach().cpu())

        return detections_pp, saliency_maps, severities


CrackXNet = CrackXNetDetector


def build_model(num_classes=7, img_size=None, pretrained_backbone=False):
    img_size = img_size or CONFIG["img_size"]
    backbone = build_backbone(pretrained=pretrained_backbone)

    anchor_generator = AnchorGenerator(
        sizes=((16, 32), (64, 128), (256, 512)),
        aspect_ratios=((0.5, 1.0, 2.0),) * 3,
    )
    roi_pooler = MultiScaleRoIAlign(featmap_names=["0", "1", "2"], output_size=7, sampling_ratio=2)

    if CONFIG["USE_MULTITASK"]:
        model = CrackXNetDetector(
            backbone, num_classes=num_classes,
            use_explain=CONFIG["USE_EXPLAIN_LOSS"], use_severity=CONFIG["USE_SEVERITY_HEAD"],
            use_cam_consistency=CONFIG.get("USE_CAM_CONSISTENCY", True),
            explain_weight=CONFIG["EXPLAIN_LOSS_WEIGHT"], severity_weight=CONFIG["SEVERITY_LOSS_WEIGHT"],
            cam_consistency_weight=CONFIG.get("CAM_CONSISTENCY_WEIGHT", 0.05),
            rpn_anchor_generator=anchor_generator, box_roi_pool=roi_pooler,
            min_size=img_size, max_size=img_size,
        )
    else:
        model = FasterRCNN(
            backbone, num_classes=num_classes,
            rpn_anchor_generator=anchor_generator, box_roi_pool=roi_pooler,
            min_size=img_size, max_size=img_size,
        )
    return model


# ===========================================================================
# Post-hoc Grad-CAM
# ===========================================================================

class DetectorGradCAM:
    """Backprops a predicted defect's class-logit through the FPN feature maps that fed its
    ROI-Align, independent of the ExplainabilityHead."""
    def __init__(self, model, device):
        self.model = model
        self.device = device

    def generate(self, img_tensor, box_xyxy, target_class):
        self.model.eval()
        img_tensor = img_tensor.to(self.device)

        images, _ = self.model.transform([img_tensor], None)
        feats = self.model.backbone(images.tensors)
        for v in feats.values():
            v.retain_grad()

        orig_h, orig_w = img_tensor.shape[-2:]
        new_h, new_w = images.image_sizes[0]
        scale_x, scale_y = new_w / orig_w, new_h / orig_h
        x1, y1, x2, y2 = box_xyxy
        scaled_box = torch.tensor(
            [[x1 * scale_x, y1 * scale_y, x2 * scale_x, y2 * scale_y]],
            dtype=torch.float32, device=self.device,
        )

        box_features = self.model.roi_heads.box_roi_pool(feats, [scaled_box], [(new_h, new_w)])
        box_features = self.model.roi_heads.box_head(box_features)
        class_logits, _ = self.model.roi_heads.box_predictor(box_features)
        score = class_logits[0, target_class]

        self.model.zero_grad()
        score.backward(retain_graph=True)

        raw_cams = []
        for level, act in feats.items():
            grad = act.grad
            if grad is None:
                continue
            weights = grad.mean(dim=(2, 3), keepdim=True)
            cam = (weights * act).sum(dim=1, keepdim=True)
            cam = F.interpolate(cam, size=(orig_h, orig_w), mode="bilinear", align_corners=False)
            raw_cams.append(cam)

        if not raw_cams:
            return np.zeros((orig_h, orig_w), dtype=np.float32)

        combined = torch.stack(raw_cams, dim=0).sum(dim=0)
        combined = F.relu(combined).squeeze().detach().cpu().numpy()
        denom = (combined.max() - combined.min() + 1e-8)
        combined = (combined - combined.min()) / denom
        return combined


# ===========================================================================
# Severity Index (DSI) — rule-based, transparent
# ===========================================================================

def severity_level(score):
    for upper, label in SEVERITY_BINS:
        if score < upper:
            return label
    return SEVERITY_BINS[-1][1]


def compute_severity(defect_class_name, box_xyxy, confidence, image_hw, area_reference=0.05):
    x1, y1, x2, y2 = box_xyxy
    box_area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    board_area = image_hw[0] * image_hw[1]
    area_ratio = box_area / board_area if board_area > 0 else 0.0

    size_score = min(1.0, math.sqrt(area_ratio) / math.sqrt(area_reference))
    risk = RISK_WEIGHT.get(defect_class_name, 0.5)

    dsi = 100.0 * (0.5 * risk + 0.3 * size_score + 0.2 * confidence)
    dsi = float(np.clip(dsi, 0, 100))
    return dsi, severity_level(dsi)


def decide_board_status(severity_levels):
    counts = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    for lvl in severity_levels:
        counts[lvl] = counts.get(lvl, 0) + 1

    if counts.get("Critical", 0) > 0:
        decision = "REJECT"
        reason = f"{counts['Critical']} critical-severity defect(s) detected."
    elif counts.get("High", 0) > 0:
        decision = "REWORK"
        reason = f"{counts['High']} high-severity defect(s) detected."
    elif counts.get("Medium", 0) >= 3:
        decision = "REWORK"
        reason = f"{counts['Medium']} medium-severity defects detected (threshold: 3)."
    elif counts.get("Medium", 0) > 0 or counts.get("Low", 0) > 0:
        decision = "PASS"
        reason = "Only low/minor-medium severity defects present; within acceptable tolerance."
    else:
        decision = "PASS"
        reason = "No defects detected."

    return decision, reason, counts


def decision_feature_vector(severity_scores, severity_levels):
    counts = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    for lvl in severity_levels:
        counts[lvl] = counts.get(lvl, 0) + 1
    n = len(severity_scores)
    max_s = (max(severity_scores) / 100.0) if n else 0.0
    mean_s = ((sum(severity_scores) / n) / 100.0) if n else 0.0
    return torch.tensor([
        float(counts["Low"]), float(counts["Medium"]), float(counts["High"]), float(counts["Critical"]),
        float(n), max_s, mean_s,
    ], dtype=torch.float32)


class DecisionNetwork(nn.Module):
    """Small MLP mapping a board's aggregated severity profile to PASS/REWORK/REJECT logits."""
    def __init__(self, in_features=7, hidden=32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_features, hidden), nn.ReLU(inplace=True),
            nn.Linear(hidden, hidden), nn.ReLU(inplace=True),
            nn.Linear(hidden, 3),
        )

    def forward(self, x):
        return self.net(x)


@torch.no_grad()
def decide_board_status_learned(severity_scores, severity_levels, net=None):
    net = net if net is not None else _decision_net
    if net is None:
        return None, None
    x = decision_feature_vector(severity_scores, severity_levels).unsqueeze(0)
    x = x.to(next(net.parameters()).device)
    probs = F.softmax(net(x), dim=-1)[0]
    idx = int(probs.argmax())
    return DECISION_CLASSES[idx], {c: round(float(p), 4) for c, p in zip(DECISION_CLASSES, probs.tolist())}


# ===========================================================================
# Model loading
# ===========================================================================

_model = None
_decision_net = None
_gradcam = None


def load_model(weights_path=None, decision_weights_path=None, device=None):
    """Builds the architecture, loads trained weights, and puts the model in eval mode."""
    global _model, _decision_net, _gradcam

    device = device or DEVICE
    weights_path = weights_path or CONFIG["model_path"]

    # Fallback to search known paths if not found at default
    if not os.path.exists(weights_path):
        candidates = [
            os.path.join(PROJECT_ROOT, "checkpoints", "crackxnet_final.pth"),
            os.path.join(BASE_DIR, "checkpoints", "crackxnet_final.pth"),
            os.path.join(PROJECT_ROOT, "ai", "weights", "crackxnet_final.pth"),
            os.path.join(PROJECT_ROOT, "ai", "weights", "crackxnet_best.pth"),
        ]
        for c in candidates:
            if os.path.exists(c):
                weights_path = c
                break

    if not os.path.exists(weights_path):
        raise FileNotFoundError(
            f"CrackXNet checkpoint not found at {weights_path}. "
            "Train one with train_crackxnet.py, or point load_model() at your .pth file."
        )

    model = build_model(CONFIG["num_classes"], pretrained_backbone=False).to(device)
    checkpoint = torch.load(weights_path, map_location=device)
    state_dict = checkpoint["model_state"] if isinstance(checkpoint, dict) and "model_state" in checkpoint else checkpoint

    # Clean out profiler buffers (total_ops / total_params from thop profiler) if present
    if isinstance(state_dict, dict):
        clean_sd = {k: v for k, v in state_dict.items() if not (k.endswith("total_ops") or k.endswith("total_params"))}
    else:
        clean_sd = state_dict

    model.load_state_dict(clean_sd)
    model.eval()

    _model = model
    _gradcam = DetectorGradCAM(model, device)

    decision_weights_path = decision_weights_path or CONFIG["decision_net_path"]
    if CONFIG.get("USE_DECISION_NETWORK", True) and os.path.exists(decision_weights_path):
        dnet = DecisionNetwork(in_features=7, hidden=CONFIG.get("DECISION_HIDDEN_DIM", 32)).to(device)
        dnet.load_state_dict(torch.load(decision_weights_path, map_location=device))
        dnet.eval()
        _decision_net = dnet

    os.makedirs(CONFIG["report_dir"], exist_ok=True)
    return model


def get_model():
    if _model is None:
        raise RuntimeError("Model not loaded. Call crackxnet.load_model() first (e.g. at app startup).")
    return _model


def is_loaded():
    return _model is not None


# ===========================================================================
# Inference pipeline
# ===========================================================================

def preprocess_image(pil_img, img_size=None):
    """PIL.Image (any mode/size) -> normalized float tensor (C,H,W) ready for inspect_board()."""
    img_size = img_size or CONFIG["img_size"]
    pil_img = pil_img.convert("RGB").resize((img_size, img_size), Image.BILINEAR)
    return TF.to_tensor(pil_img)


@torch.no_grad()
def _run_detection(img_tensor, score_thresh=0.5):
    model = get_model()
    device = next(model.parameters()).device
    if CONFIG["USE_MULTITASK"]:
        detections, saliency_maps, severities = model.predict_with_extras([img_tensor.to(device)])
        pred = detections[0]
        learned_sal = saliency_maps[0, 0].cpu().numpy() if saliency_maps is not None else None
        learned_sev = severities[0] if len(severities) else torch.empty(0)
    else:
        pred = model([img_tensor.to(device)])[0]
        learned_sal, learned_sev = None, torch.empty(0)

    keep = pred["scores"] >= score_thresh
    return {
        "boxes": pred["boxes"][keep].cpu(),
        "labels": pred["labels"][keep].cpu(),
        "scores": pred["scores"][keep].cpu(),
        "learned_saliency": learned_sal,
        "learned_severity": learned_sev[keep.cpu()] if len(learned_sev) else torch.empty(0),
    }


def inspect_board(img_tensor, board_id=None, score_thresh=0.5, with_gradcam=True):
    """Runs one preprocessed image through the full pipeline: detection -> severity -> decision."""
    board_id = board_id or f"board_{int(time.time())}"
    h, w = img_tensor.shape[-2:]

    det = _run_detection(img_tensor, score_thresh)
    defects = []

    # Select top defects for Grad-CAM generation to ensure sub-second response times
    max_cams = 5
    if with_gradcam and len(det["scores"]) > 0:
        sorted_indices = set(torch.argsort(det["scores"], descending=True)[:max_cams].tolist())
    else:
        sorted_indices = set()

    for i, (box, label, score) in enumerate(zip(det["boxes"], det["labels"], det["scores"])):
        cls_name = CLASS_NAMES[int(label)]
        box_xyxy = box.tolist()
        heatmap = _gradcam.generate(img_tensor, box_xyxy, int(label)) if (i in sorted_indices) else None
        dsi, level = compute_severity(cls_name, box_xyxy, float(score), (h, w))
        learned_dsi = float(det["learned_severity"][i]) if len(det["learned_severity"]) > i else None
        defects.append({
            "class": cls_name, "confidence": float(score), "box": box_xyxy,
            "severity_score": round(dsi, 1), "severity_level": level,
            "learned_severity_score": None if learned_dsi is None else round(learned_dsi, 1),
            "heatmap": heatmap,
        })

    severity_scores = [d["severity_score"] for d in defects]
    severity_levels = [d["severity_level"] for d in defects]
    decision, reason, counts = decide_board_status(severity_levels)
    learned_decision, learned_decision_probs = decide_board_status_learned(severity_scores, severity_levels)

    return {
        "board_id": board_id, "timestamp": datetime.now().isoformat(timespec="seconds"),
        "num_defects": len(defects), "severity_counts": counts,
        "decision": decision, "decision_reason": reason,
        "learned_decision": learned_decision, "learned_decision_probs": learned_decision_probs,
        "defects": defects,
        "learned_saliency": det["learned_saliency"],
    }


def report_to_json(report):
    clean = {k: v for k, v in report.items() if k != "learned_saliency"}
    clean["defects"] = [{k: v for k, v in d.items() if k != "heatmap"} for d in report["defects"]]
    return clean


def log_inspection(report, history_path=None):
    history_path = history_path or CONFIG["history_path"]
    row = {
        "timestamp": report["timestamp"], "board_id": report["board_id"],
        "num_defects": report["num_defects"],
        "low": report["severity_counts"].get("Low", 0),
        "medium": report["severity_counts"].get("Medium", 0),
        "high": report["severity_counts"].get("High", 0),
        "critical": report["severity_counts"].get("Critical", 0),
        "decision": report["decision"], "reason": report["decision_reason"],
        "learned_decision": report.get("learned_decision"),
    }
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    df_row = pd.DataFrame([row])
    if os.path.exists(history_path):
        df_row.to_csv(history_path, mode="a", header=False, index=False)
    else:
        df_row.to_csv(history_path, mode="w", header=True, index=False)
    return row


def get_history(history_path=None, n=20):
    history_path = history_path or CONFIG["history_path"]
    if not os.path.exists(history_path):
        return pd.DataFrame()
    return pd.read_csv(history_path).tail(n)


def render_report(img_tensor, report, save_path=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches

    img_np = img_tensor.permute(1, 2, 0).numpy()
    h, w = img_np.shape[:2]

    n_panels = 3 if report.get("learned_saliency") is not None else 2
    fig, axes = plt.subplots(1, n_panels, figsize=(6.2 * n_panels, 6))

    axes[0].imshow(img_np)
    for d in report["defects"]:
        x1, y1, x2, y2 = d["box"]
        rect = patches.Rectangle((x1, y1), x2 - x1, y2 - y1, linewidth=2, edgecolor="red", facecolor="none")
        axes[0].add_patch(rect)
        label_txt = f"{d['class']} | {d['severity_level']} ({d['severity_score']:.0f})"
        axes[0].text(x1, max(y1 - 5, 0), label_txt, color="white", fontsize=7, weight="bold",
                     bbox=dict(facecolor="red", alpha=0.7, pad=1))
    axes[0].set_title(f"Board: {report['board_id']}  |  {report['num_defects']} defect(s)")
    axes[0].axis("off")

    combined_heat = np.zeros((h, w), dtype=np.float32)
    for d in report["defects"]:
        if d.get("heatmap") is not None:
            combined_heat = np.maximum(combined_heat, d["heatmap"])
    axes[1].imshow(img_np)
    axes[1].imshow(combined_heat, cmap="jet", alpha=0.45)
    axes[1].set_title("Post-hoc Grad-CAM (per detection, combined)")
    axes[1].axis("off")

    if n_panels == 3:
        axes[2].imshow(img_np)
        axes[2].imshow(report["learned_saliency"], cmap="jet", alpha=0.45)
        axes[2].set_title("Learned saliency (ExplainabilityHead)")
        axes[2].axis("off")

    decision_color = DECISION_COLORS.get(report["decision"], "black")
    title = f"Decision (rule): {report['decision']}  —  {report['decision_reason']}"
    if report.get("learned_decision"):
        probs = report["learned_decision_probs"]
        probs_txt = ", ".join(f"{c}={p:.2f}" for c, p in probs.items())
        title += f"\nDecision (learned): {report['learned_decision']}  ({probs_txt})"
    fig.suptitle(title, color=decision_color, fontsize=12, weight="bold")
    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return save_path
