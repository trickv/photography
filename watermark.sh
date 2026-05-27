#!/usr/bin/env bash
#
# Overlay brand1.png into the bottom-right corner of one or more photos.
#
# Usage:
#   ./watermark.sh                       # watermark all *.JPG at native size
#   ./watermark.sh IMG_8198.JPG          # just one photo
#   WIDTH_PCT=15 ./watermark.sh          # scale watermark to 15% of photo width
#
# Originals are never overwritten; output is written as <name>_wm.<ext>.

set -euo pipefail

WATERMARK="brand1.png"
SUFFIX="_wm"
MARGIN_PCT="${MARGIN_PCT:-1.5}"   # extra inset from the edges, as % of photo width
WIDTH_PCT="${WIDTH_PCT:-}"        # watermark width as % of photo width; empty = native size
QUALITY="${QUALITY:-95}"

# Photos: use args if given, otherwise every *.JPG that isn't already a _wm output.
if [ "$#" -gt 0 ]; then
  photos=("$@")
else
  photos=()
  for f in *.JPG *.jpg; do
    [ -e "$f" ] || continue
    case "$f" in *"$SUFFIX".*) continue;; esac
    photos+=("$f")
  done
fi

for photo in "${photos[@]}"; do
  read -r pw ph < <(magick identify -format "%w %h\n" "$photo")

  # Margin in pixels (same offset on x and y, derived from width for consistency).
  margin=$(printf '%.0f' "$(echo "$pw * $MARGIN_PCT / 100" | bc -l)")

  # Resize the watermark only if a target width % was requested.
  if [ -n "$WIDTH_PCT" ]; then
    target_w=$(printf '%.0f' "$(echo "$pw * $WIDTH_PCT / 100" | bc -l)")
    wm_resize=(-resize "${target_w}x")
  else
    wm_resize=()
  fi

  out="${photo%.*}${SUFFIX}.${photo##*.}"

  magick "$photo" \
    \( "$WATERMARK" ${wm_resize[@]+"${wm_resize[@]}"} \) \
    -gravity southeast -geometry "+${margin}+${margin}" \
    -compose over -composite \
    -quality "$QUALITY" "$out"

  echo "wrote $out  (photo ${pw}x${ph}, margin ${margin}px)"
done
