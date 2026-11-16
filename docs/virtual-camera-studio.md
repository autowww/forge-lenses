# Virtual Camera Studio (Phase 1)

Local virtual V4L2 cameras for Forge Studio Desktop on Ubuntu.

## Feature gate

Set `LENSES_EXPERIMENTAL_VIRTUAL_CAMERA=1` before starting `python3 -m lenses`.

**Dedicated Electron app (recommended):** minimal shell on **port 8096** — separate from Forge Studio (`:8080`).

```bash
cd forge-lenses/desktop
npm install   # once
./launch-virtual-camera-studio.sh
# or: npm run start:virtual-camera
```

Opens **Virtual Camera Studio** at `http://127.0.0.1:8096/studio/labs/virtual-camera` with no top nav, sidebar, or copilot rail. Does not attach to an existing Forge Studio server on `:8080`.

**Full Forge Studio:** Settings gear → Labs → Virtual Camera Studio (`/studio/labs/virtual-camera`).

## System dependencies (Ubuntu)

Install on the host (not via pip):

```bash
sudo apt install \
  v4l-utils \
  v4l2loopback-dkms \
  gstreamer1.0-tools \
  gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad
```

Load virtual camera devices (requires sudo once per boot, or persist via modprobe.d):

```bash
sudo modprobe v4l2loopback devices=4 exclusive_caps=1 card_labels="Studio Cam 1,Studio Cam 2,Studio Cam 3,Studio Cam 4"
```

Studio does **not** run privileged commands automatically. When v4l2loopback is missing, Virtual Camera Studio shows a **popup** with copyable `sudo` commands (install, `modprobe`, verify).

## API (loopback only)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/virtual-camera/enabled` | Feature flag |
| GET | `/api/virtual-camera/cameras` | Discover physical/virtual devices |
| GET | `/api/virtual-camera/bootstrap` | v4l2loopback status + setup steps |
| GET | `/api/virtual-camera/profiles` | List profiles + runtime |
| POST | `/api/virtual-camera/profiles` | Create profile |
| PUT | `/api/virtual-camera/profiles/{id}` | Update profile |
| POST | `/api/virtual-camera/profiles/{id}/start` | Start pipeline |
| POST | `/api/virtual-camera/profiles/{id}/stop` | Stop pipeline |
| POST | `/api/virtual-camera/profiles/{id}/restart` | Restart pipeline (waits for device release) |
| POST | `/api/virtual-camera/profiles/{id}/force-restart` | Force restart (`{"confirm": true}`) — may terminate other apps using the camera |
| POST | `/api/virtual-camera/profiles/{id}/duplicate` | Duplicate profile |
| POST | `/api/virtual-camera/profiles/{id}/delete` | Delete profile |
| GET | `/api/virtual-camera/preview/{id}?view=processed\|source` | MJPEG preview |
| GET | `/api/virtual-camera/vdi-readiness` | Azure VDI / Teams readiness checklist |

Profiles persist in `<workspace>/.lenses-local/virtual-camera-profiles.json`.

Runtime state (including errors) persists in `<workspace>/.lenses-local/virtual-camera-runtime.json`.

## Error codes

Runtime and API responses may include:

| Code | Meaning |
|------|---------|
| `CAMERA_BUSY` | Physical camera held by another process |
| `FORMAT_NEGOTIATION_FAILED` | Resolution/FPS/format not supported |
| `DEVICE_MISSING` | Camera device path no longer exists |
| `PIPELINE_FAILED` | Other GStreamer failure |

`stderr_tail` retains raw GStreamer output for the Details panel in Studio.

## Force restart policy

- Normal **Start** / **Restart** never kills unrelated processes.
- **Force restart** requires UI confirmation and `POST .../force-restart` with `{"confirm": true}`.
- Implementation sends SIGTERM/SIGKILL to **specific PIDs** from `fuser` — not `fuser -k`.

## Pipeline architecture (Phase 1)

One owned `gst-launch-1.0` process per running profile:

```text
v4l2src → decode → convert → [mirror/crop] → tee
  ├→ v4l2sink (virtual camera — YUYV, NV12, or MJPEG)
  └→ jpegenc → multipartmux → fdsink (MJPEG preview; shared JPEG when sink is MJPEG)
```

Processed preview reads from the tee branch (no second capture on the virtual device).

Profiles may include `jpeg_quality` (30–100, default 85) when `output_format` is MJPEG.

## Azure VDI and Teams

See [virtual-camera-vdi-teams.md](virtual-camera-vdi-teams.md) for Cloud PC + Teams desktop on a Linux-primary client.

Optional Windows MF bridge (not on Linux): [virtual-camera-windows-bridge.md](virtual-camera-windows-bridge.md).

## Manual verification (acceptance)

1. Create profile: C920 → 640×360 @ 15 FPS → virtual device.
2. Start in UI; confirm one `gst-launch` per profile:

   ```bash
   pgrep -a gst-launch
   ```

3. Virtual device reports capture caps:

   ```bash
   v4l2-ctl -D -d /dev/video10
   v4l2-ctl -d /dev/video10 --get-fmt-video
   ```

   Expect approximately 640×360 YUYV.

4. External consumer:

   ```bash
   ffplay -f v4l2 -input_format yuyv422 -video_size 640x360 -framerate 15 /dev/video10
   ```

5. Stop profile — no orphan `gst-launch`.
6. Quit Studio — owned pipelines terminate.
7. Preview while running shows processed stream without extra `gst-launch` on virtual device.

## Tests

```bash
cd forge-lenses
python3 -m pytest tests/test_virtual_camera.py -q
```
