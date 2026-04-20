#!/usr/bin/env bash
set -euo pipefail

# Stereo USB probe helper:
# 1) Collects USB and V4L2 diagnostics
# 2) Optionally records short simultaneous clips from left/right endpoints
#
# Usage:
#   bash scripts/stereo_usb_probe.sh
#   bash scripts/stereo_usb_probe.sh /dev/video2 /dev/video4 1280x720 30 10

LEFT_DEV="${1:-}"
RIGHT_DEV="${2:-}"
VIDEO_SIZE="${3:-1280x720}"
FPS="${4:-30}"
DURATION="${5:-10}"
STREAM_TEST_TIMEOUT_SEC="${STREAM_TEST_TIMEOUT_SEC:-8}"

STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="bringup_logs/${STAMP}"
mkdir -p "$OUT_DIR"

log() {
  echo "[$(date +%H:%M:%S)] $*"
}

cmd_exists() {
  command -v "$1" >/dev/null 2>&1
}

log "Output directory: $OUT_DIR"

log "Collecting base system and USB info..."
{
  echo "===== uname ====="
  uname -a
  echo
  echo "===== lsusb ====="
  if cmd_exists lsusb; then lsusb; else echo "lsusb not found"; fi
  echo
  echo "===== recent dmesg ====="
  if cmd_exists dmesg; then dmesg | tail -n 200; else echo "dmesg not found"; fi
} >"$OUT_DIR/system_usb.txt" 2>&1

log "Collecting video node list..."
{
  echo "===== /dev/video* ====="
  ls -l /dev/video* 2>/dev/null || true
  echo
  echo "===== v4l2-ctl --list-devices ====="
  if cmd_exists v4l2-ctl; then v4l2-ctl --list-devices; else echo "v4l2-ctl not found"; fi
} >"$OUT_DIR/video_nodes.txt" 2>&1

if ! cmd_exists v4l2-ctl; then
  log "v4l2-ctl missing. Install with: sudo apt install -y v4l-utils"
  exit 1
fi

log "Probing each /dev/video* endpoint..."
for dev in /dev/video*; do
  [[ -e "$dev" ]] || continue
  base="$(basename "$dev")"
  has_capture_formats=0
  formats_text="$(v4l2-ctl -d "$dev" --list-formats-ext 2>&1 || true)"
  if echo "$formats_text" | grep -qE "^\s*\[[0-9]+\]:"; then
    has_capture_formats=1
  fi

  {
    echo "===== $dev --all ====="
    v4l2-ctl -d "$dev" --all || true
    echo
    echo "===== $dev --list-formats-ext ====="
    echo "$formats_text"
    echo
    echo "===== $dev --list-ctrls-menus ====="
    v4l2-ctl -d "$dev" --list-ctrls-menus || true
    echo
    echo "===== $dev stream smoke test ====="
    if [[ "$has_capture_formats" -eq 1 ]]; then
      if command -v timeout >/dev/null 2>&1; then
        timeout "${STREAM_TEST_TIMEOUT_SEC}s" v4l2-ctl -d "$dev" --stream-mmap=3 --stream-count=120 --stream-to=/dev/null || true
      else
        v4l2-ctl -d "$dev" --stream-mmap=3 --stream-count=120 --stream-to=/dev/null || true
      fi
    else
      echo "Skipping stream smoke test: no video capture pixel formats detected (likely metadata/control endpoint)."
    fi
  } >"$OUT_DIR/${base}_probe.txt" 2>&1
  log "Saved probe for $dev"
done

if [[ -n "$LEFT_DEV" && -n "$RIGHT_DEV" ]]; then
  if ! cmd_exists ffmpeg; then
    log "ffmpeg not found. Skipping dual recording. Install with: sudo apt install -y ffmpeg"
    exit 0
  fi

  if [[ ! -e "$LEFT_DEV" || ! -e "$RIGHT_DEV" ]]; then
    log "Provided endpoints not found: LEFT=$LEFT_DEV RIGHT=$RIGHT_DEV"
    exit 1
  fi

  LEFT_OUT="$OUT_DIR/left_${FPS}fps_${VIDEO_SIZE}.mkv"
  RIGHT_OUT="$OUT_DIR/right_${FPS}fps_${VIDEO_SIZE}.mkv"

  log "Starting dual capture for ${DURATION}s"
  ffmpeg -hide_banner -loglevel info -f v4l2 -framerate "$FPS" -video_size "$VIDEO_SIZE" -i "$LEFT_DEV" -t "$DURATION" -c:v copy "$LEFT_OUT" >"$OUT_DIR/ffmpeg_left.log" 2>&1 &
  PID_L=$!

  ffmpeg -hide_banner -loglevel info -f v4l2 -framerate "$FPS" -video_size "$VIDEO_SIZE" -i "$RIGHT_DEV" -t "$DURATION" -c:v copy "$RIGHT_OUT" >"$OUT_DIR/ffmpeg_right.log" 2>&1 &
  PID_R=$!

  wait "$PID_L" || true
  wait "$PID_R" || true

  log "Dual capture finished"

  {
    echo "===== left file ====="
    ls -lh "$LEFT_OUT" 2>/dev/null || true
    echo
    echo "===== right file ====="
    ls -lh "$RIGHT_OUT" 2>/dev/null || true
    echo
    if cmd_exists ffprobe; then
      echo "===== ffprobe left ====="
      ffprobe -hide_banner -show_streams -show_format "$LEFT_OUT" 2>&1 || true
      echo
      echo "===== ffprobe right ====="
      ffprobe -hide_banner -show_streams -show_format "$RIGHT_OUT" 2>&1 || true
    fi
  } >"$OUT_DIR/dual_capture_summary.txt" 2>&1

  log "Saved dual capture outputs and summaries"
else
  log "No left/right endpoints provided, skipping dual recording stage"
fi

log "Probe complete. Review logs under: $OUT_DIR"
