#!/bin/sh
# Render docs/figures/*.svg to PNG at 2x, because a judge's viewer may not
# open SVG and because the PNG should never drift from the SVG by hand.
#
# Chrome rather than qlmanage: qlmanage makes a square thumbnail and crops,
# which silently clipped a third of one diagram on 2026-09-21.
set -e
cd "$(dirname "$0")/.."
chrome="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
[ -x "$chrome" ] || { echo "Chrome not found at $chrome" >&2; exit 1; }
render() {
  "$chrome" --headless --disable-gpu --hide-scrollbars \
    --force-device-scale-factor=2 --window-size="$2","$3" \
    --screenshot="docs/figures/$1.png" "file://$PWD/docs/figures/$1.svg" \
    >/dev/null 2>&1
  echo "  docs/figures/$1.png"
}
render architecture 1320 760
render deployment   1320 820
