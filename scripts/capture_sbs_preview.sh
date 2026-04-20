#!/usr/bin/env bash
set -euo pipefail

# Capture one frame from a side-by-side stereo stream and split into left/right images.
#
# Usage:
#   ./scripts/capture_sbs_preview.sh
#   ./scripts/capture_sbs_preview.sh /dev/video0 2560x800 30 mjpeg
#
# Args:
#   1) device        default: /dev/video0
#   2) frame size    default: 2560x800
#   3) fps           default: 30
#   4) input format  default: mjpeg

DEV="${1:-/dev/video0}"
SIZE="${2:-2560x800}"
FPS="${3:-30}"
INPUT_FORMAT="${4:-mjpeg}"

STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="bringup_logs/sbs_preview_${STAMP}"
mkdir -p "$OUT_DIR"

log() {
  echo "[$(date +%H:%M:%S)] $*"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1"
    exit 1
  fi
}

require_cmd ffmpeg

if [[ ! -e "$DEV" ]]; then
  echo "Video device not found: $DEV"
  exit 1
fi

FULL_IMG="$OUT_DIR/full_sbs.jpg"
LEFT_IMG="$OUT_DIR/left.jpg"
RIGHT_IMG="$OUT_DIR/right.jpg"

log "Capturing one frame from $DEV ($SIZE @ ${FPS}fps, format=$INPUT_FORMAT)"
ffmpeg -hide_banner -loglevel error \
  -f v4l2 \
  -input_format "$INPUT_FORMAT" \
  -framerate "$FPS" \
  -video_size "$SIZE" \
  -i "$DEV" \
  -frames:v 1 \
  -y "$FULL_IMG"

log "Splitting side-by-side frame into left/right"
ffmpeg -hide_banner -loglevel error \
  -i "$FULL_IMG" \
  -filter_complex "[0:v]crop=iw/2:ih:0:0[left];[0:v]crop=iw/2:ih:iw/2:0[right]" \
  -map "[left]" -frames:v 1 -y "$LEFT_IMG" \
  -map "[right]" -frames:v 1 -y "$RIGHT_IMG"

cat >"$OUT_DIR/README.txt" <<EOF
Source device: $DEV
Capture size: $SIZE
Capture fps: $FPS
Input format: $INPUT_FORMAT

Outputs:
- $FULL_IMG
- $LEFT_IMG
- $RIGHT_IMG
EOF

log "Saved outputs under: $OUT_DIR"
