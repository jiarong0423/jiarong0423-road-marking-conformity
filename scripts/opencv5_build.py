"""What OpenCV 5 actually exposes in the build this project runs on.

docs/opencv5.md is a table of seven capabilities with a column headed "in
this build". Every cell in that column is a claim about an installed
package, and not one of them was in results/ - so by standing rule 2 the
whole table was unverified. It is also the cheapest thing in this project
to verify: it is introspection of an already-installed module, no imagery
and no pipeline.

What this script does NOT establish, said here so the registry entries
cannot be read as more than they are:

  * it introspects the wheel installed on the machine it runs on. The
    document's subject is `opencv-python-headless==5.0.0.93` in the
    Lambda image; this records the package version it found so the two
    can be compared, but a macOS arm64 wheel and a manylinux arm64 wheel
    are different builds of the same version and may expose different
    modules. `platform` is in the output for that reason.
  * `getCPUFeaturesLine()` is recorded as the string this host reports.
    Reading Graviton dispatch off it requires the host to be the Lambda
    one, which is a deployment claim, not this script's.
  * the DNN timing is a wall-clock median over repeated forward passes on
    one machine under whatever else it was doing. `n` is in the output.
    It is the weakest figure here and is registered as such.

    /opt/anaconda3/bin/python3 scripts/opencv5_build.py --write
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "opencv5_build.json"
ONNX = ROOT / "models" / "mlsd" / "mlsd_tiny_512.onnx"

# The five new element types OpenCV 5 adds, plus the one the document says
# is not reachable from Python.
NEW_TYPES = ("CV_32U", "CV_64U", "CV_64S", "CV_Bool", "CV_16F")
BFLOAT_TYPE = "CV_16BF"

# calib3d was split in OpenCV 5. The document claims only one of the four
# pieces reaches Python.
CALIB3D_SPLIT = ("geometry", "calib", "stereo", "ptcloud")

# Features2D was renamed Features. The document claims neither name is a
# Python module in this build.
FEATURES_NAMES = ("features", "features2d")

DNN_ENGINES = ("ENGINE_AUTO", "ENGINE_CLASSIC", "ENGINE_NEW", "ENGINE_ORT")

TIMING_RUNS = 20
TIMING_SIDE = 512


def package_version() -> str | None:
    try:
        from importlib.metadata import version

        for name in ("opencv-python-headless", "opencv-python"):
            try:
                return f"{name}=={version(name)}"
            except Exception:
                continue
    except Exception:
        pass

    return None


def time_onnx() -> dict:
    """Load the M-LSD export through the new engine and time a forward pass."""
    if not ONNX.exists():
        return {"available": False,
                "why": f"{ONNX.relative_to(ROOT)} is not present"}

    try:
        net = cv2.dnn.readNet(str(ONNX), "", "", cv2.dnn.ENGINE_NEW)
    except Exception as error:
        return {"available": False,
                "why": f"{type(error).__name__}: {error}"}

    image = np.random.default_rng(0).integers(
        0, 255, (TIMING_SIDE, TIMING_SIDE, 3), dtype=np.uint8)
    blob = cv2.dnn.blobFromImage(image, 1 / 255.0,
                                 (TIMING_SIDE, TIMING_SIDE), swapRB=True)

    # One untimed pass: the first forward allocates and is not the figure
    # anyone means by "runs it in N ms".
    net.setInput(blob)
    net.forward()

    times = []

    for _ in range(TIMING_RUNS):
        net.setInput(blob)
        start = time.perf_counter()
        net.forward()
        times.append((time.perf_counter() - start) * 1000.0)

    times.sort()

    return {
        "available": True,
        "engine": "ENGINE_NEW",
        "input": f"{TIMING_SIDE}x{TIMING_SIDE}",
        "n": TIMING_RUNS,
        "median_ms": round(times[len(times) // 2], 1),
        "min_ms": round(times[0], 1),
        "max_ms": round(times[-1], 1),
        "caveat": "wall clock on one machine, synthetic input, forward pass "
                  "only - no pre- or post-processing. Machine-dependent.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                        help=f"write {OUT.relative_to(ROOT)}")
    args = parser.parse_args()

    missing_types = [t for t in NEW_TYPES if not hasattr(cv2, t)]

    result = {
        "question": "which OpenCV 5 capabilities the installed build "
                    "actually exposes to Python",
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "opencv_version": cv2.__version__,
        "opencv_python_package": package_version(),
        "new_element_types_exposed": not missing_types,
        "new_element_types_missing": missing_types,
        "bfloat16_exposed": hasattr(cv2, BFLOAT_TYPE),
        "calib3d_submodules_present": [
            name for name in CALIB3D_SPLIT if hasattr(cv2, name)],
        "features_module_present": [
            name for name in FEATURES_NAMES if hasattr(cv2, name)],
        "dnn_engines_present": [
            name for name in DNN_ENGINES if hasattr(cv2.dnn, name)],
        "cpu_features_line_present": hasattr(cv2, "getCPUFeaturesLine"),
        "cpu_features_line": (cv2.getCPUFeaturesLine()
                              if hasattr(cv2, "getCPUFeaturesLine") else None),
        "cpu_features_line_is": "what THIS host reports. Reading Graviton "
                                "dispatch off it requires the host to be the "
                                "Lambda one; that is a deployment claim and "
                                "not established here.",
        "mlsd_onnx": {
            "path": str(ONNX.relative_to(ROOT)),
            "bytes": ONNX.stat().st_size if ONNX.exists() else None,
            "mib": (round(ONNX.stat().st_size / 1048576, 1)
                    if ONNX.exists() else None),
        },
        "mlsd_forward": time_onnx(),
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))

    if args.write:
        OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        print(f"\nwrote {OUT.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
