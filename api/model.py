"""EfficientNet-B0 inference (+ Grad-CAM). Owner: Group 1 (Omkar).

If models/efficientnet_b0.pt is missing, a STUB is used so the other group can
build against the API before training finishes.
"""
import io, json, base64
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "models" / "efficientnet_b0.pt"
CLASSES_PATH = ROOT / "models" / "classes.json"

_state = {"model": None, "classes": None, "tf": None, "stub": None}


def _load():
    if _state["stub"] is not None:
        return
    if not (MODEL_PATH.exists() and CLASSES_PATH.exists()):
        _state.update(stub=True, classes=["Tomato___Late_blight", "Tomato___healthy"])
        print("[model] WEIGHTS NOT FOUND -> running in STUB mode")
        return
    try:
        import torch, torch.nn as nn
        from torchvision import models, transforms
        classes = json.loads(CLASSES_PATH.read_text())
        m = models.efficientnet_b0(weights=None)
        m.classifier[1] = nn.Linear(m.classifier[1].in_features, len(classes))
        m.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
        m.eval()
        _state["tf"] = transforms.Compose([
            transforms.Resize((224, 224)), transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
        _state.update(model=m, classes=classes, stub=False)
    except Exception as e:
        print(f"[model] PyTorch load error ({e}) -> running in STUB mode")
        classes = json.loads(CLASSES_PATH.read_text()) if CLASSES_PATH.exists() else ["Tomato___Late_blight", "Tomato___healthy"]
        _state.update(stub=True, classes=classes)


def classes() -> list[str]:
    _load()
    return _state["classes"]


def predict(img: Image.Image, topk: int = 3) -> dict:
    _load()
    if _state["stub"]:
        return {"label": "Tomato___Late_blight", "confidence": 0.55,
                "top": [{"label": "Tomato___Late_blight", "confidence": 0.55}], "stub": True}
    import torch
    x = _state["tf"](img).unsqueeze(0)
    with torch.no_grad():
        p = torch.softmax(_state["model"](x), dim=1)[0]
    conf, idx = p.topk(min(topk, len(p)))
    top = [{"label": _state["classes"][i], "confidence": float(c)} for c, i in zip(conf, idx)]
    return {"label": top[0]["label"], "confidence": top[0]["confidence"], "top": top, "stub": False}


def gradcam_overlay_b64(img: Image.Image) -> str | None:
    """'Model attention' heat-map (NOT lesion segmentation). None in stub mode."""
    _load()
    if _state["stub"]:
        return None
    import torch, torch.nn.functional as F, cv2
    m, x = _state["model"], _state["tf"](img).unsqueeze(0)
    acts = {}
    h = m.features[-1].register_forward_hook(lambda mod, i, o: acts.__setitem__("a", o))
    out = m(x)
    h.remove()
    a = acts["a"]
    grad = torch.autograd.grad(out[0, out[0].argmax()], a)[0]
    cam = F.relu((grad.mean(dim=(2, 3), keepdim=True) * a).sum(1, keepdim=True))
    cam = F.interpolate(cam, size=img.size[::-1], mode="bilinear", align_corners=False)[0, 0]
    cam = ((cam - cam.min()) / (cam.max() - cam.min() + 1e-8)).detach().numpy()
    heat = cv2.applyColorMap((cam * 255).astype(np.uint8), cv2.COLORMAP_JET)
    base = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    mix = cv2.addWeighted(base, 0.55, heat, 0.45, 0)
    ok, buf = cv2.imencode(".jpg", mix, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return base64.b64encode(buf).decode()
