#!/bin/sh
# The Seoul Sidewalk Accessibility Image Dataset, which is the only thing on
# this project's critical path that cannot be regenerated.
#
# Zenodo record 22699523, published 2026-09-11 by researchers at MIT,
# licensed CC-Zero - public domain, so it may train a model, set a product
# parameter and be redistributed. 513 pedestrian-perspective photographs at
# 5712x4284 with field-measured width, running slope, cross slope and a
# damage grade, plus GPS.
#
# 4.6 GB. The summary and the protocol are small and come first, so the
# ground truth is on disk before the imagery starts.
set -e
cd "$(dirname "$0")/../data"
BASE="https://zenodo.org/records/22699523/files"

for small in summary_attributes.csv ground_truth_protocol.zip; do
  test -f "$small" || curl -fsSL -o "$small" "$BASE/$small?download=1"
  echo "  $small  $(wc -c < "$small") bytes"
done

for part in 1 2 3; do
  name="imagery_$part.zip"
  test -f "$name" && { echo "  $name already here"; continue; }
  echo "  fetching $name"
  curl -fL --retry 3 --retry-delay 5 -o "$name" "$BASE/$name?download=1"
done

echo "done; unzip the imagery_*.zip in place when you need the photographs"
