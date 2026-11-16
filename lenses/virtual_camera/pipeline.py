"""Build GStreamer pipeline argv for virtual camera profiles."""

from __future__ import annotations

from typing import Any

GST_RAW_FORMATS = {
    "YUYV": "YUY2",
    "YUY2": "YUY2",
    "UYVY": "UYVY",
    "RGB": "RGB",
    "BGR": "BGR",
    "NV12": "NV12",
    "GREY": "GRAY8",
    "GRAY": "GRAY8",
    "GRAY8": "GRAY8",
}

COMPRESSED_OUTPUT_FORMATS = frozenset({"MJPEG", "MJPG"})

UI_OUTPUT_FORMAT_ORDER = ("MJPEG", "NV12", "YUYV", "UYVY", "RGB", "BGR", "GREY")


def _fmt_fourcc(name: str) -> str:
    key = str(name or "").strip().upper()
    return GST_RAW_FORMATS.get(key, key)


def normalize_output_format(name: str) -> str:
    key = str(name or "").strip().upper()
    if key in ("MJPG", "MJPEG"):
        return "MJPEG"
    if key in ("YUY2", "YUYV"):
        return "YUYV"
    if key in ("GREY", "GRAY", "GRAY8"):
        return "GREY"
    if key == "NV12":
        return "NV12"
    return key or "YUYV"


def output_fourcc_for_v4l2(name: str) -> str:
    """Map profile output_format to v4l2-ctl fourcc strings."""
    key = normalize_output_format(name)
    if key == "MJPEG":
        return "MJPG"
    if key == "YUYV":
        return "YUY2"
    if key == "GREY":
        return "GREY"
    return key


def is_compressed_output_format(name: str) -> bool:
    return normalize_output_format(name) == "MJPEG"


def advertised_virtual_fourccs(formats: list[dict[str, Any]] | None) -> set[str]:
    out: set[str] = set()
    for fmt in formats or []:
        fourcc = str(fmt.get("fourcc") or "").strip().upper()
        if fourcc:
            out.add(fourcc)
    return out


def _fourcc_matches_output(advertised: str, output_format: str) -> bool:
    want = output_fourcc_for_v4l2(output_format)
    adv = advertised.strip().upper()
    if adv == want:
        return True
    norm = normalize_output_format(output_format)
    if norm == "MJPEG" and adv in ("MJPG", "MJPEG"):
        return True
    if norm == "YUYV" and adv in ("YUY2", "YUYV"):
        return True
    if norm == "GREY" and adv in ("GREY", "GRAY8", "GRAY"):
        return True
    if norm == "NV12" and adv == "NV12":
        return True
    if norm == adv:
        return True
    gst = _fmt_fourcc(norm)
    return gst.upper() == adv or adv == norm


def validate_virtual_output_format(
    output_format: str,
    virtual_formats: list[dict[str, Any]] | None,
) -> str | None:
    """Return error message when virtual device caps reject output_format."""
    advertised = advertised_virtual_fourccs(virtual_formats)
    if not advertised:
        return None
    for fourcc in advertised:
        if _fourcc_matches_output(fourcc, output_format):
            return None
    supported = ", ".join(sorted(advertised))
    label = normalize_output_format(output_format)
    return (
        f"Virtual device does not advertise output format {label}. "
        f"Supported fourccs: {supported}"
    )


def list_ui_output_formats(virtual_formats: list[dict[str, Any]] | None) -> list[str]:
    """UI labels for output format dropdown derived from virtual device caps."""
    advertised = advertised_virtual_fourccs(virtual_formats)
    if not advertised:
        return ["YUYV", "UYVY", "NV12", "MJPEG", "RGB", "BGR", "GREY"]
    found: list[str] = []
    for label in UI_OUTPUT_FORMAT_ORDER:
        for fourcc in advertised:
            if _fourcc_matches_output(fourcc, label):
                if label not in found:
                    found.append(label)
                break
    return found or ["YUYV"]


def vdi_friendly_formats(virtual_formats: list[dict[str, Any]] | None) -> dict[str, bool]:
    fmts = list_ui_output_formats(virtual_formats)
    return {
        "mjpeg": "MJPEG" in fmts,
        "nv12": "NV12" in fmts,
        "yuyv": "YUYV" in fmts,
    }


def _pick_size(
    formats: list[dict[str, Any]],
    target_w: int,
    target_h: int,
    input_format: str,
) -> tuple[str, int, int, list[float]]:
    """Choose best matching format/size from discovery caps."""
    want = _fmt_fourcc(input_format)
    if want in ("MJPG", "MJPEG"):
        want = "MJPG"
    best: tuple[str, int, int, list[float]] | None = None
    best_score = -1
    for fmt in formats:
        fourcc = str(fmt.get("fourcc") or "")
        if want and fourcc.upper() != want.upper() and fourcc.upper() not in (want.upper(), "MJPG"):
            continue
        for size in fmt.get("sizes") or []:
            try:
                w = int(size.get("width") or 0)
                h = int(size.get("height") or 0)
            except (TypeError, ValueError):
                continue
            fps_list = []
            for f in size.get("fps") or []:
                try:
                    fps_list.append(float(f))
                except (TypeError, ValueError):
                    pass
            score = 0
            if w == target_w and h == target_h:
                score += 10000
            area = w * h
            target_area = target_w * target_h
            if area == target_area:
                score += 5000
            elif area <= target_area:
                score += 3000 - abs(target_area - area)
            else:
                score += 1000 - abs(target_area - area)
            if fourcc.upper() in ("MJPG", "MJPEG"):
                score += 50
            if score > best_score:
                best_score = score
                best = (fourcc, w, h, fps_list)
    if best:
        return best
    if formats:
        fmt = formats[0]
        fourcc = str(fmt.get("fourcc") or "MJPG")
        sizes = fmt.get("sizes") or []
        if sizes:
            size = sizes[0]
            try:
                w = int(size.get("width") or target_w)
                h = int(size.get("height") or target_h)
            except (TypeError, ValueError):
                w, h = target_w, target_h
            fps_list: list[float] = []
            for f in size.get("fps") or []:
                try:
                    fps_list.append(float(f))
                except (TypeError, ValueError):
                    pass
            return (fourcc, w, h, fps_list)
        return (fourcc, target_w, target_h, [])
    return (want or "MJPG", target_w, target_h, [])


def _jpeg_quality(profile: dict[str, Any]) -> int:
    try:
        q = int(profile.get("jpeg_quality") or 85)
    except (TypeError, ValueError):
        q = 85
    return max(30, min(100, q))


def _append_tee_v4l2_and_preview(
    elements: list[str],
    sink_dev: str,
    preview_fd: int | None,
    *,
    jpeg_preview_from_compressed: bool = False,
    jpeg_quality: int = 85,
) -> None:
    if preview_fd is not None:
        elements.extend(
            [
                "tee",
                "name=t",
                "t.",
                "!",
                "queue",
                "!",
                "v4l2sink",
                f"device={sink_dev}",
                "sync=false",
                "t.",
                "!",
                "queue",
                "!",
            ]
        )
        if not jpeg_preview_from_compressed:
            elements.extend(
                [
                    "jpegenc",
                    f"quality={jpeg_quality}",
                    "!",
                ]
            )
        elements.extend(
            [
                "multipartmux",
                "boundary=frame",
                "!",
                "fdsink",
                f"fd={preview_fd}",
                "sync=false",
            ]
        )
    else:
        elements.extend(
            [
                "v4l2sink",
                f"device={sink_dev}",
                "sync=false",
            ]
        )


def build_gst_launch_argv(
    profile: dict[str, Any],
    formats: list[dict[str, Any]] | None = None,
    *,
    preview_fd: int | None = None,
) -> list[str]:
    source = profile.get("source") or {}
    virtual = profile.get("virtual") or {}
    resolution = profile.get("resolution") or {}
    src_dev = str(source.get("device_path") or "").strip()
    sink_dev = str(virtual.get("device_path") or "").strip()
    if not src_dev or not sink_dev:
        raise ValueError("source and virtual device_path are required")

    try:
        out_w = int(resolution.get("width") or 640)
        out_h = int(resolution.get("height") or 360)
        fps = int(profile.get("fps") or 15)
    except (TypeError, ValueError):
        out_w, out_h, fps = 640, 360, 15

    input_format = str(profile.get("input_format") or "MJPEG")
    output_label = normalize_output_format(str(profile.get("output_format") or "YUYV"))
    mirror = bool(profile.get("mirror"))
    jpeg_quality = _jpeg_quality(profile)

    fourcc, cap_w, cap_h, fps_list = _pick_size(
        formats or [],
        out_w,
        out_h,
        input_format,
    )
    if fps_list:
        closest = min(fps_list, key=lambda f: abs(f - fps))
        if abs(closest - fps) <= 2:
            fps = int(round(closest))

    elements: list[str] = [
        "gst-launch-1.0",
        "-e",
        "v4l2src",
        f"device={src_dev}",
        "io-mode=2",
        "!",
    ]

    if fourcc.upper() in ("MJPG", "MJPEG"):
        elements.extend(
            [
                f"image/jpeg,width={cap_w},height={cap_h},framerate={fps}/1",
                "!",
                "jpegdec",
                "!",
            ]
        )
    elif fourcc.upper() == "H264":
        elements.extend(
            [
                f"video/x-h264,width={cap_w},height={cap_h},framerate={fps}/1",
                "!",
                "h264parse",
                "!",
                "avdec_h264",
                "!",
            ]
        )
    else:
        gst_fmt = _fmt_fourcc(fourcc)
        elements.extend(
            [
                f"video/x-raw,format={gst_fmt},width={cap_w},height={cap_h},framerate={fps}/1",
                "!",
            ]
        )

    if out_w != cap_w or out_h != cap_h:
        elements.extend(["videoscale", "!"])

    crop = profile.get("crop")
    if isinstance(crop, dict):
        try:
            cx, cy, cw, ch = int(crop["x"]), int(crop["y"]), int(crop["w"]), int(crop["h"])
            if cw > 0 and ch > 0:
                elements.extend(
                    [
                        f"videocrop left={cx} top={cy} right={cap_w - cx - cw} bottom={cap_h - cy - ch}",
                        "!",
                    ]
                )
        except (KeyError, TypeError, ValueError):
            pass

    if mirror:
        elements.extend(["videoflip method=horizontal-flip", "!"])

    elements.extend(["videoconvert", "!"])

    if is_compressed_output_format(output_label):
        # v4l2sink on v4l2loopback requires parsed JPEG (see v4l2loopback issue #97).
        elements.extend(
            [
                "jpegenc",
                f"quality={jpeg_quality}",
                "!",
                "image/jpeg,parsed=true",
                "!",
            ]
        )
        _append_tee_v4l2_and_preview(
            elements,
            sink_dev,
            preview_fd,
            jpeg_preview_from_compressed=True,
            jpeg_quality=jpeg_quality,
        )
    else:
        gst_out = _fmt_fourcc(output_label)
        elements.extend(
            [
                f"video/x-raw,format={gst_out},width={out_w},height={out_h},framerate={fps}/1",
                "!",
            ]
        )
        _append_tee_v4l2_and_preview(
            elements,
            sink_dev,
            preview_fd,
            jpeg_preview_from_compressed=False,
            jpeg_quality=jpeg_quality,
        )
    return elements


def build_preview_argv(
    device_path: str,
    width: int,
    height: int,
    fps: int = 15,
    formats: list[dict[str, Any]] | None = None,
    input_format: str = "MJPEG",
) -> list[str]:
    """Standalone preview for source device when pipeline is not running."""
    dev = str(device_path or "").strip()
    fourcc, cap_w, cap_h, fps_list = _pick_size(
        formats or [],
        width,
        height,
        input_format,
    )
    if fps_list:
        closest = min(fps_list, key=lambda f: abs(f - fps))
        fps = int(round(closest))

    elements: list[str] = [
        "gst-launch-1.0",
        "-q",
        "v4l2src",
        f"device={dev}",
        "io-mode=2",
        "!",
    ]

    if fourcc.upper() in ("MJPG", "MJPEG"):
        elements.extend(
            [
                f"image/jpeg,width={cap_w},height={cap_h},framerate={fps}/1",
                "!",
                "jpegdec",
                "!",
            ]
        )
    elif fourcc.upper() == "H264":
        elements.extend(
            [
                f"video/x-h264,width={cap_w},height={cap_h},framerate={fps}/1",
                "!",
                "h264parse",
                "!",
                "avdec_h264",
                "!",
            ]
        )
    else:
        gst_fmt = _fmt_fourcc(fourcc)
        elements.extend(
            [
                f"video/x-raw,format={gst_fmt},width={cap_w},height={cap_h},framerate={fps}/1",
                "!",
            ]
        )

    if width != cap_w or height != cap_h:
        elements.extend(["videoscale", "!"])

    elements.extend(
        [
            "videoconvert",
            "!",
            f"video/x-raw,width={width},height={height},framerate={fps}/1",
            "!",
            "jpegenc",
            "quality=85",
            "!",
            "multipartmux",
            "boundary=frame",
            "!",
            "fdsink",
            "fd=1",
            "sync=false",
        ]
    )
    return elements
