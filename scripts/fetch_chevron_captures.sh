#!/bin/sh
# The exact captures behind results/chevron_angle.json.
#
# One panorama on 116 縣道, New Taipei, photographed 2025-06, requested at
# three fields of view and two pitches. The lens varies and the road does
# not, which is what makes the spread across them a measurement of the
# method rather than of the road.
#
# These parameters were only in a shell history until 2026-09-20, when the
# images were deleted and measure_chevron.py correctly refused to produce a
# number rather than inventing one - which is also how it was noticed that a
# published figure had no way back to its source.
#
#   ./scripts/fetch_chevron_captures.sh
#   /opt/anaconda3/bin/python3 scripts/measure_chevron.py --write
set -e
cd "$(dirname "$0")/.."
test -f .mapskey || { echo "put a Google Maps API key in .mapskey"; exit 1; }
KEY=$(tr -d ' \n\r' < .mapskey)

PANO=CLY3PO0CcluEBc0vpcvPOg
HEADING=128.14
mkdir -p output/api

for FOV in 40 60 90; do
  for PITCH in -20 -35; do
    OUT="output/api/f${FOV}_p${PITCH}.jpg"
    test -f "$OUT" && { echo "  $OUT already here"; continue; }
    code=$(curl -s -o "$OUT" -w '%{http_code}' \
      "https://maps.googleapis.com/maps/api/streetview?size=640x640&pano=$PANO&heading=$HEADING&pitch=$PITCH&fov=$FOV&return_error_code=true&key=$KEY")

    if [ "$code" != 200 ]; then
      echo "  fov $FOV pitch $PITCH: HTTP $code"
      rm -f "$OUT"
      continue
    fi

    # The geometry beside the image, because the fov is what makes the
    # ground angle recoverable and a bare jpg does not carry it.
    printf '{"pano":"%s","heading":%s,"pitch":%s,"fov":%s,"size":[640,640]}\n' \
      "$PANO" "$HEADING" "$PITCH" "$FOV" > "${OUT%.jpg}.json"
    echo "  fov $FOV pitch $PITCH  $(wc -c < "$OUT") bytes"
  done
done

echo "six captures, about \$0.04 of Street View quota"
