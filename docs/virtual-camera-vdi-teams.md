# Virtual Camera Studio — Azure VDI and Teams

Linux-primary workflow for **Azure Virtual Desktop** and **Windows 365 Cloud PC** with **Microsoft Teams desktop** in the remote session.

## Architecture

```text
Physical webcam (Linux)
  → Virtual Camera Studio (GStreamer)
  → v4l2loopback (/dev/videoN)
  → AVD / Remote Desktop client on Linux (camera redirect)
  → Windows Cloud PC session
  → Teams desktop
```

**Media Foundation virtual cameras are Windows-only.** On Ubuntu, the native path is **V4L2** via `v4l2loopback`, not MF.

## Two Teams video paths

| Path | When | Quality |
|------|------|---------|
| **Teams media optimization** | Supported AVD client + session host setup + WebRTC Redirector | Best (WebRTC; up to 720p) |
| **RDP camera redirect** | Generic Linux Remote Desktop client | Variable — use MJPEG/NV12 output + low resolution |

Teams optimization on Linux is limited to **partner thin clients** listed in [Azure thin clients](https://learn.microsoft.com/en-us/azure/virtual-desktop/thin-clients). Generic Ubuntu + Remote Desktop usually stays on **RDP redirect**.

Teams in the **browser** inside Cloud PC does **not** get optimization — use **Teams desktop**.

## Recommended profile (AVD Teams preset)

In Virtual Camera Studio, use **Apply AVD Teams preset** or select quality preset **AVD Teams (Cloud PC)**:

| Setting | Value |
|---------|-------|
| Resolution | 640×360 (or **VDI ultra-low** 320×160 / **VDI minimal** 160×120 if still blocky) |
| FPS | 15 |
| Input | MJPEG (from physical camera) |
| Output | **MJPEG** if virtual device supports MJPG; else **NV12**; else YUYV |

### Output format guide

| Output | Use when |
|--------|----------|
| **MJPEG** | Azure VDI RDP camera redirect — compressed stream, less bandwidth than raw YUYV |
| **NV12** | Raw but efficient; some stacks negotiate better than YUYV |
| **YUYV** | Default; highest uncompressed bandwidth through RDP |

Verify virtual device caps:

```bash
v4l2-ctl -d /dev/video10 --list-formats-ext
```

MJPEG/NV12 depend on **v4l2loopback** version and kernel.

## IT checklist — host pool RDP properties

Ask your Azure admin to set on the Cloud PC host pool:

```text
camerastoredirect:s:*
redirected video capture encoding quality:i:2
encode redirected video capture:i:1
audiocapturemode:i:1
audiomode:i:0
```

- Default encoding quality `0` = high compression (blocky motion). **`2`** = higher picture quality.
- Reference: [RDP properties](https://learn.microsoft.com/en-us/azure/virtual-desktop/rdp-properties)
- Teams setup: [Teams on AVD](https://learn.microsoft.com/en-us/azure/virtual-desktop/teams-on-avd)

## Cloud PC diagnostic script

Inside your **Windows Cloud PC**, run:

```powershell
# Default: saves to Documents\forge-vc-avd-diagnostic-<timestamp>.txt
powershell -ExecutionPolicy Bypass -File scripts/avd-teams-vc-diagnostic.ps1

# Or choose a path:
powershell -ExecutionPolicy Bypass -File scripts/avd-teams-vc-diagnostic.ps1 -OutputPath "$env:USERPROFILE\Desktop\vc-diagnostic.txt"
```

Paste the file contents (or console output) into **Virtual Camera Studio → Azure Cloud VDI / Teams → Parse diagnostic**.

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/virtual-camera/vdi-readiness` | Bootstrap, virtual output formats, RDP checklist, running profiles |

## Windows Media Foundation bridge

Optional **Windows-only** component for MF virtual cameras — see [virtual-camera-windows-bridge.md](virtual-camera-windows-bridge.md). Not required for Linux-primary Cloud PC workflow.

## Manual acceptance

1. Load v4l2loopback; create profile with **AVD Teams** preset and **MJPEG** output (if supported).
2. Start profile; confirm `v4l2-ctl -d /dev/videoN --get-fmt-video` shows MJPEG or expected fourcc.
3. Connect Cloud PC from Linux AVD client; join Teams call.
4. Confirm virtual camera label appears in Teams device list.
5. Compare video vs previous YUYV @ same resolution.
6. Run PowerShell diagnostic in Cloud PC; paste into Studio checklist.
