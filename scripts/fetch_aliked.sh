#!/bin/sh
# ALIKED keypoints (BSD-3-Clause) and the LightGlue matcher trained for them (Apache-2.0), as ONNX:
# the same files and SHA-1 that OpenCV's own test data uses (opencv_extra testdata/dnn/download_models.py),
# pinned to one commit of the repository it fetches them from.
set -eu
cd "$(dirname "$0")/.."
B=https://raw.githubusercontent.com/YangGuanyuhan/lightglue_opencv_project/78c4fa54ad3bd4638ccf2b58af9f152e7f85a5f2/model
mkdir -p models/aliked
for pair in aliked-n16rot-top1k-640.onnx:41faa7bf5d7eb68a2851471ba03aa20c9db30e4c \
            aliked_lightglue.onnx:02723aa521990e57fe33d90b67977590c460e351; do
  f=${pair%%:*}; want=${pair#*:}
  [ -f "models/aliked/$f" ] || { curl -sSfL -o "models/aliked/$f.part" "$B/$f"; mv "models/aliked/$f.part" "models/aliked/$f"; }
  got=$(python3 -c "import hashlib,sys;print(hashlib.sha1(open(sys.argv[1],'rb').read()).hexdigest())" "models/aliked/$f")
  [ "$got" = "$want" ] && echo "$f ok" || { echo "ERROR $f sha1 $got, expected $want"; exit 1; }
done
