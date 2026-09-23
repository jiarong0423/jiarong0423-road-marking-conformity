#!/bin/sh
# Street View Static API, for the one thing a browser screenshot cannot give:
# a known field of view.
#
# A screenshot of the Street View viewer is a re-projection of a panorama at
# whatever zoom and heading the viewer was at, so its focal length is
# unknown, and without focal length two vanishing points do not give a ground
# angle. This API takes `fov` as a parameter, so the focal length is
#
#     f = (width / 2) / tan(fov / 2)
#
# in pixels, which is the whole of what was missing.
#
#   ./scripts/fetch_streetview.sh <lat> <lon> <heading> <pitch> <fov> <out.jpg>
#
# The key is read from .mapskey, which .gitignore excludes, and is never
# echoed. Each request is billed against the account's Street View quota.
set -e
cd "$(dirname "$0")/.."
test -f .mapskey || { echo "put the key in .mapskey (one line, no quotes)"; exit 1; }
KEY=$(tr -d ' \n\r' < .mapskey)

LAT=$1; LON=$2; HEAD=${3:-0}; PITCH=${4:--10}; FOV=${5:-60}; OUT=${6:-output/streetview/api.jpg}
test -n "$LAT" && test -n "$LON" || { echo "need <lat> <lon>"; exit 1; }
mkdir -p "$(dirname "$OUT")"

code=$(curl -s -o "$OUT" -w '%{http_code}' \
  "https://maps.googleapis.com/maps/api/streetview?size=640x640&location=$LAT,$LON&heading=$HEAD&pitch=$PITCH&fov=$FOV&return_error_code=true&key=$KEY")

if [ "$code" != "200" ]; then
  echo "HTTP $code"
  head -c 300 "$OUT"; echo
  rm -f "$OUT"
  exit 1
fi

# The API returns a grey "no imagery" tile with HTTP 200 unless asked not to;
# return_error_code=true above makes it a 404 instead, so reaching here means
# a real photograph. Record the geometry beside it - the fov is the point.
printf '{"lat":%s,"lon":%s,"heading":%s,"pitch":%s,"fov":%s,"size":[640,640]}\n' \
  "$LAT" "$LON" "$HEAD" "$PITCH" "$FOV" > "${OUT%.*}.json"
echo "wrote $OUT  ($(wc -c < "$OUT") bytes) and ${OUT%.*}.json"
