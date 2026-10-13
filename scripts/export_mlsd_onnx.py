"""Export M-LSD to ONNX so OpenCV 5's new DNN engine can be shown running it.

The model is not in this pipeline. It was measured against the classical
detector and lost, and that comparison is itself void because it predates
the carriageway() fix - see docs/opencv5.md. What survives is the narrower
finding that OpenCV 5's new engine loads and runs an ONNX model here at
all, which the classic engine's 13% operator coverage would not have
managed, and this script is what makes that re-runnable.

The weights are lhwcv/mlsd_pytorch, Apache-2.0, and are not committed:
5 MB of third-party weights for a model this project does not use is
clutter. This fetches them.

    python3 scripts/export_mlsd_onnx.py

Needs torch and onnx, which the pipeline does not. Nothing at runtime
imports either.
"""
from __future__ import annotations

import sys
import types
import urllib.request
from pathlib import Path

RAW = "https://raw.githubusercontent.com/lhwcv/mlsd_pytorch/main"
HERE = Path(__file__).resolve().parents[1] / "models" / "mlsd"
FILES = {
    "mbv2_mlsd.py": f"{RAW}/mlsd_pytorch/models/mbv2_mlsd.py",
    "layers.py": f"{RAW}/mlsd_pytorch/models/layers.py",
    "mlsd_tiny_512_fp32.pth": f"{RAW}/models/mlsd_tiny_512_fp32.pth",
    "LICENSE.mlsd": f"{RAW}/LICENSE",
}


def fetch() -> None:
    HERE.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        p = HERE / name
        if p.exists() and p.stat().st_size > 100:
            continue
        print(f"  fetching {name}")
        urllib.request.urlretrieve(url, p)
    # two upstream lines stop the file importing on its own: an unused
    # `import timm`, and an absolute import of its own package
    src = (HERE / "mbv2_mlsd.py").read_text()
    src = src.replace("import timm", "# import timm  # unused here")
    src = src.replace("from mlsd_pytorch.models.layers import *",
                      "from layers import *")
    (HERE / "mbv2_mlsd.py").write_text(src)


def export() -> int:
    import torch
    import torch.nn as nn
    sys.path.insert(0, str(HERE))
    import mbv2_mlsd as m

    # cfg is taken but only one field is read
    cfg = types.SimpleNamespace(model=types.SimpleNamespace(with_deconv=False))
    net = m.MobileV2_MLSD(cfg)
    # the checkpoint's stem takes four channels: M-LSD feeds RGB plus a
    # constant alpha plane. Swap it before loading, not after.
    old = net.backbone.features[0][0]
    net.backbone.features[0][0] = nn.Conv2d(4, old.out_channels,
                                            old.kernel_size, old.stride,
                                            old.padding, bias=False)
    sd = torch.load(HERE / "mlsd_tiny_512_fp32.pth", map_location="cpu",
                    weights_only=True)
    net.load_state_dict(sd, strict=True)
    net.eval()
    out = HERE / "mlsd_tiny_512.onnx"
    torch.onnx.export(net, torch.randn(1, 4, 512, 512), out,
                      input_names=["input"], output_names=["output"],
                      opset_version=13, dynamo=False)
    print(f"  wrote {out.name}, {out.stat().st_size/1048576:.1f} MiB")

    import cv2
    import numpy as np
    n = cv2.dnn.readNet(str(out), "", "", cv2.dnn.ENGINE_NEW)
    blob = cv2.dnn.blobFromImage(np.zeros((512, 512, 4), np.uint8),
                                 1/127.5, (512, 512), (127.5,)*4,
                                 swapRB=False)
    n.setInput(blob)
    print(f"  cv2.dnn ENGINE_NEW forward ok, output {n.forward().shape}")
    return 0


if __name__ == "__main__":
    fetch()
    sys.exit(export())
