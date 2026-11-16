# Windows Media Foundation virtual camera bridge (spike / optional)

## Scope

**Cannot run on Linux.** Media Foundation (MF) and classic DirectShow virtual camera drivers are **Windows APIs**. Virtual Camera Studio on Ubuntu uses **v4l2loopback + GStreamer** instead.

This document records the **spike outcome** and a future path if you need a Windows-native virtual camera — for example when connecting to Azure VDI from a **Windows laptop** with Teams media optimization.

## When MF helps vs Linux V4L2

| Scenario | Recommended path |
|----------|------------------|
| Linux Ubuntu → Cloud PC → Teams | v4l2loopback + **MJPEG/NV12** output + RDP redirect ([virtual-camera-vdi-teams.md](virtual-camera-vdi-teams.md)) |
| Windows laptop → Cloud PC → Teams (optimization ON) | MF virtual cam on **Windows client** enumerated by WebRTC redirector |
| Teams inside Cloud PC only (no client redirect) | MF virtual cam **inside VM** — separate from client-side optimization |

For **Linux-primary** workflows, implement **Track A** (compressed V4L2 output) before any MF work.

## Spike evaluation (Phase C0)

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **softcam** (DirectShow DLL + frame injection) | Mature pattern; inject RGB/NV12 frames from a feeder process | DirectShow legacy; not pure MF; maintenance | **Default spike target** for MVP |
| **Windows Virtual Camera / Frame Server** (Win10+) | Modern stack; Teams-friendly | Higher engineering cost; packaging/signing | Long-term native option |
| **OBS Virtual Camera** | Ships today; user installs OBS | Not Forge-owned; extra UX | Document as interim for power users |
| **Network bridge → Cloud PC agent** | Could feed VM-local cam from Linux encoder | Security, latency, IT approval | **Not recommended** for v1 |

## Proposed IPC contract (future Linux ↔ Windows)

```text
Linux: GStreamer → MJPEG or NV12 stream → localhost TCP or stdout pipe
Windows feeder: read stream → inject frames → virtual camera driver
Teams / Camera app: sees "Forge Studio Virtual Camera"
```

Formats: **MJPEG** (parse JPEG frames) or **raw NV12** fixed resolution (640×360 @ 15 fps).

## Phase C1 MVP (if approved)

- Package: `forge-lenses/desktop/windows-vc-bridge/` (or separate repo)
- **softcam**-style DLL + C# or C++ feeder
- Input: named pipe `\\.\pipe\forge-vc-mjpeg` or TCP `127.0.0.1:9787`
- Installer: zip or MSI; requires admin for driver registration (driver-specific)
- Verification: Windows Camera app + Teams device picker on **Windows machine**

## Phase C2 — Cloud PC agent (deferred)

Windows service on session host ingesting network stream from Linux host.

- Requires inbound network policy and security review
- Does not replace client-side Teams optimization
- **Defer** until Linux V4L2 + RDP tuning is insufficient

## Interim workaround (no Forge bridge)

1. Run **Teams on the Linux host** with virtual cam locally (bypasses VDI re-encode).
2. On Windows client: install **OBS Studio**, use OBS Virtual Camera, pipe via OBS (manual).
3. Tune RDP properties (`redirected video capture encoding quality:i:2`) + **MJPEG** virtual output on Linux.

## References

- [Teams on Azure Virtual Desktop](https://learn.microsoft.com/en-us/azure/virtual-desktop/teams-on-avd)
- [Teams VDI requirements](https://learn.microsoft.com/en-us/microsoftteams/teams-client-vdi-requirements-deploy)
- [Azure RDP properties](https://learn.microsoft.com/en-us/azure/virtual-desktop/rdp-properties)

## Status

**Spike documented — not shipped.** Production MF bridge requires explicit approval after VDI-1–VDI-4 validation on Linux.
