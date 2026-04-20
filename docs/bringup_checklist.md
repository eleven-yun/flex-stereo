# Stereo USB Camera Bring-Up Checklist (Linux)

This checklist is for first connection of two synchronized monocular cameras via a USB adapter board.

## 0) One-time package prep

Install probe tools:

sudo apt update
sudo apt install -y v4l-utils usbutils ffmpeg

Optional preview tools:

sudo apt install -y cheese guvcview

## 1) Plug in hardware and verify USB detection

Run:

lsusb
sudo dmesg --ctime | tail -n 120

What to confirm:
- A new USB camera or adapter device appears in lsusb
- Kernel log shows uvcvideo bound to the device
- No repeated USB reset or bandwidth errors

## 2) Verify video nodes

Run:

ls -l /dev/video*
v4l2-ctl --list-devices

What to confirm:
- Two camera endpoints are visible and stable
- You can map each endpoint to left and right channels

## 3) Inspect capabilities per endpoint

For each candidate node, run:

v4l2-ctl -d /dev/videoX --all
v4l2-ctl -d /dev/videoX --list-formats-ext

What to confirm:
- Matching resolution and frame rate options on both cameras
- Same pixel format selected for both cameras

## 4) Lock critical controls before stereo work

Read control list:

v4l2-ctl -d /dev/videoX --list-ctrls-menus

Disable auto controls and set fixed values (example names vary by camera):

v4l2-ctl -d /dev/videoX --set-ctrl=exposure_auto=1
v4l2-ctl -d /dev/videoX --set-ctrl=exposure_absolute=200
v4l2-ctl -d /dev/videoX --set-ctrl=gain=32
v4l2-ctl -d /dev/videoX --set-ctrl=white_balance_temperature_auto=0
v4l2-ctl -d /dev/videoX --set-ctrl=white_balance_temperature=4500
v4l2-ctl -d /dev/videoX --set-ctrl=focus_auto=0

Apply equivalent settings to both left and right streams.

## 5) Quick stream sanity check

Run for each endpoint:

v4l2-ctl -d /dev/videoX --stream-mmap=3 --stream-count=300 --stream-to=/dev/null

What to confirm:
- Stream runs without timeout or frame corruption errors
- Effective fps is stable and close to target

## 6) Dual-stream recording test

Example (replace nodes and format as needed):

ffmpeg -hide_banner -f v4l2 -framerate 30 -video_size 1280x720 -i /dev/videoL -t 15 -c:v copy left.mkv
ffmpeg -hide_banner -f v4l2 -framerate 30 -video_size 1280x720 -i /dev/videoR -t 15 -c:v copy right.mkv

For strict simultaneity testing, start both from one script (see scripts/stereo_usb_probe.sh).

## 7) Timestamp/synchronization validation

Minimum practical target for synchronized stereo:
- No frequent drop bursts on either side
- Frame count mismatch remains very small over short runs
- Time offset is stable, not drifting over minutes

If your adapter board embeds hardware timestamps, prioritize those over host timestamps.

## 8) Common failure modes and fixes

- No /dev/videoX nodes:
  - Replug device, recheck dmesg, ensure uvcvideo is loaded
- Black preview:
  - Force supported format and frame size from --list-formats-ext
- Works for one camera only:
  - Lower resolution/fps, use USB 3 port/hub, avoid bus contention
- Random device index changes:
  - Add udev rules and use stable symlinks

## 9) Recommended next step in this repo

After successful bring-up, add:
- A left/right device mapping config file
- A capture module that records frame index and timestamp for both streams
- A repeatable sync report (frame count, drop rate, offset drift)

## 10) Validate side-by-side packed output quickly

If the adapter exposes one capture stream (for example /dev/video0) and one metadata node
(for example /dev/video1), capture and split one frame:

./scripts/capture_sbs_preview.sh /dev/video0 2560x800 30 mjpeg

This writes one full frame and split left/right images under bringup_logs/sbs_preview_*/.
