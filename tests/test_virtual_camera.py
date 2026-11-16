"""Tests for virtual camera profile persistence and hardening."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from lenses.virtual_camera.discovery import parse_formats_ext, wait_until_device_free
from lenses.virtual_camera.errors import classify_gst_stderr
from lenses.virtual_camera.pipeline import (
    build_gst_launch_argv,
    build_preview_argv,
    list_ui_output_formats,
    validate_virtual_output_format,
)
from lenses.virtual_camera.profiles_store import (
    create_profile,
    delete_profile,
    duplicate_profile,
    get_profile,
    list_profiles,
    load_raw,
    update_profile,
)


def test_create_and_list_profile(tmp_path: Path) -> None:
    p = create_profile(
        tmp_path,
        {
            "name": "VDI Low",
            "source": {"stable_id": "usb:1", "device_path": "/dev/video2", "label": "C920"},
            "virtual": {"device_path": "/dev/video10", "card_label": "VDI Cam"},
            "resolution": {"width": 640, "height": 360},
            "fps": 15,
        },
    )
    assert p["name"] == "VDI Low"
    assert p["fps"] == 15
    profiles = list_profiles(tmp_path)
    assert len(profiles) == 1
    assert profiles[0]["id"] == p["id"]


def test_update_profile(tmp_path: Path) -> None:
    p = create_profile(tmp_path, {"name": "A"})
    updated = update_profile(tmp_path, p["id"], {"name": "B", "fps": 30})
    assert updated is not None
    assert updated["name"] == "B"
    assert updated["fps"] == 30


def test_duplicate_and_delete(tmp_path: Path) -> None:
    p = create_profile(tmp_path, {"name": "Original"})
    dup = duplicate_profile(tmp_path, p["id"])
    assert dup is not None
    assert dup["name"] == "Original (copy)"
    assert dup["id"] != p["id"]
    assert delete_profile(tmp_path, p["id"])
    assert get_profile(tmp_path, p["id"]) is None
    assert len(list_profiles(tmp_path)) == 1


def test_persisted_json_version(tmp_path: Path) -> None:
    create_profile(tmp_path, {"name": "x"})
    raw = load_raw(tmp_path)
    assert raw["version"] == 1
    path = tmp_path / ".lenses-local" / "virtual-camera-profiles.json"
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "profiles" in data


def test_extract_complete_jpeg_frames() -> None:
    from lenses.virtual_camera.process_manager import (
        _extract_complete_jpeg_frames,
        _format_mjpeg_part,
    )

    jpeg = bytes([0xff, 0xd8, 0xff, 0xd9])
    buf = bytearray(_format_mjpeg_part(jpeg) + _format_mjpeg_part(jpeg))
    frames = _extract_complete_jpeg_frames(buf)
    assert len(frames) == 2
    assert frames[0] == jpeg
    assert frames[1] == jpeg


def test_build_gst_launch_argv_mjpeg() -> None:
    profile = {
        "source": {"device_path": "/dev/video2"},
        "virtual": {"device_path": "/dev/video10"},
        "resolution": {"width": 640, "height": 360},
        "fps": 15,
        "input_format": "MJPEG",
        "output_format": "YUYV",
        "mirror": False,
    }
    formats = parse_formats_ext(
        "[0]: 'MJPG' (Motion-JPEG, compressed)\n"
        "        Size: Discrete 640x360\n"
        "            Interval: Discrete 15.000fps\n"
    )
    argv = build_gst_launch_argv(profile, formats)
    assert argv[0] == "gst-launch-1.0"
    assert "v4l2src" in argv
    assert "device=/dev/video2" in argv
    assert "device=/dev/video10" in argv
    assert "jpegdec" in argv


def test_build_gst_launch_argv_grey_fallback() -> None:
    profile = {
        "source": {"device_path": "/dev/video2"},
        "virtual": {"device_path": "/dev/video10"},
        "resolution": {"width": 640, "height": 360},
        "fps": 15,
        "input_format": "MJPEG",
        "output_format": "YUYV",
    }
    formats = parse_formats_ext(
        "[0]: 'GREY' (8-bit Greyscale)\n"
        "        Size: Discrete 400x360\n"
        "            Interval: Discrete 15.000fps\n"
    )
    argv = build_gst_launch_argv(profile, formats)
    joined = " ".join(argv)
    assert "jpegdec" not in joined
    assert "format=GRAY8" in joined


def test_start_pipeline_passes_preview_fd(tmp_path: Path) -> None:
    from unittest.mock import MagicMock, patch

    from lenses.virtual_camera.process_manager import (
        prepare_preview_pipe,
        start_pipeline,
        stop_profile_processes,
    )

    profile_id = "pipe-test"
    stop_profile_processes(profile_id)
    read_fd, write_fd = prepare_preview_pipe(profile_id)
    argv = ["gst-launch-1.0", "-e", "fdsink", f"fd={write_fd}"]

    with patch("subprocess.Popen") as mock_popen, patch(
        "lenses.virtual_camera.process_manager._start_preview_fanout",
    ):
        proc = MagicMock()
        proc.pid = 4242
        proc.poll.return_value = None
        mock_popen.return_value = proc
        start_pipeline(
            tmp_path,
            profile_id,
            argv,
            preview_read_fd=read_fd,
            preview_write_fd=write_fd,
        )
        mock_popen.assert_called_once()
        assert mock_popen.call_args.kwargs["pass_fds"] == (write_fd,)

    stop_profile_processes(profile_id)


def test_build_gst_launch_argv_tee_preview() -> None:
    profile = {
        "source": {"device_path": "/dev/video2"},
        "virtual": {"device_path": "/dev/video10"},
        "resolution": {"width": 640, "height": 360},
        "fps": 15,
        "input_format": "MJPEG",
        "output_format": "YUYV",
    }
    argv = build_gst_launch_argv(profile, preview_fd=7)
    assert "tee" in argv
    assert "fdsink" in argv
    assert "fd=7" in argv
    assert "multipartmux" in argv


def test_build_preview_argv_mjpeg_uses_jpegdec() -> None:
    formats = [
        {
            "fourcc": "MJPG",
            "sizes": [{"width": 1280, "height": 720, "fps": [15.0, 30.0]}],
        }
    ]
    argv = build_preview_argv(
        "/dev/video0",
        640,
        360,
        formats=formats,
        input_format="MJPEG",
    )
    assert "jpegdec" in argv
    assert "image/jpeg" in " ".join(argv)


def test_classify_gst_stderr_busy() -> None:
    out = classify_gst_stderr("ERROR: Device or resource busy")
    assert out["code"] == "CAMERA_BUSY"


def test_classify_gst_stderr_negotiation() -> None:
    out = classify_gst_stderr("streaming stopped, reason not-negotiated")
    assert out["code"] == "FORMAT_NEGOTIATION_FAILED"


def test_classify_gst_stderr_missing_device() -> None:
    out = classify_gst_stderr("No such file or directory")
    assert out["code"] == "DEVICE_MISSING"


def test_loopback_privileged_commands() -> None:
    from lenses.virtual_camera.loopback import bootstrap_status, privileged_commands, setup_issue

    cmds = privileged_commands()
    assert cmds["modprobe"].startswith("sudo modprobe v4l2loopback")
    assert "v4l2loopback-dkms" in cmds["install"]
    assert setup_issue(False, False, False) == "module_not_installed"
    assert setup_issue(True, False, False) == "module_not_loaded"

    status = bootstrap_status()
    assert "primary_sudo_command" in status
    assert "privileged_commands" in status
    assert status["primary_sudo_command"]
    with patch("lenses.virtual_camera.discovery.is_device_busy", return_value=False):
        assert wait_until_device_free("/dev/video2", timeout_ms=100) is True


def test_build_gst_launch_argv_nv12_output() -> None:
    profile = {
        "source": {"device_path": "/dev/video2"},
        "virtual": {"device_path": "/dev/video10"},
        "resolution": {"width": 640, "height": 360},
        "fps": 15,
        "input_format": "MJPEG",
        "output_format": "NV12",
    }
    argv = build_gst_launch_argv(profile)
    joined = " ".join(argv)
    assert "format=NV12" in joined
    assert "v4l2sink" in joined


def test_build_gst_launch_argv_mjpeg_output() -> None:
    profile = {
        "source": {"device_path": "/dev/video2"},
        "virtual": {"device_path": "/dev/video10"},
        "resolution": {"width": 640, "height": 360},
        "fps": 15,
        "input_format": "MJPEG",
        "output_format": "MJPEG",
        "jpeg_quality": 80,
    }
    argv = build_gst_launch_argv(profile, preview_fd=9)
    joined = " ".join(argv)
    assert "image/jpeg,parsed=true" in joined
    assert "jpegenc" in joined
    assert "quality=80" in joined
    assert "tee" in argv
    assert "fd=9" in argv
    # Preview branch should not re-encode JPEG when sink is already MJPEG
    fdsink_idx = argv.index("fdsink")
    preview_slice = argv[:fdsink_idx]
    assert preview_slice.count("jpegenc") == 1


def test_validate_virtual_output_format() -> None:
    formats = [{"fourcc": "YUY2", "sizes": []}, {"fourcc": "MJPG", "sizes": []}]
    assert validate_virtual_output_format("YUYV", formats) is None
    assert validate_virtual_output_format("MJPEG", formats) is None
    err = validate_virtual_output_format("NV12", formats)
    assert err is not None
    assert "NV12" in err


def test_list_ui_output_formats() -> None:
    formats = [{"fourcc": "MJPG", "sizes": []}, {"fourcc": "NV12", "sizes": []}]
    opts = list_ui_output_formats(formats)
    assert "MJPEG" in opts
    assert "NV12" in opts


def test_vdi_readiness_payload(tmp_path: Path) -> None:
    from lenses.virtual_camera.vdi import vdi_readiness_payload

    create_profile(tmp_path, {"name": "t", "virtual": {"device_path": "/dev/video10"}})
    payload = vdi_readiness_payload(tmp_path)
    assert payload["ok"] is True
    assert "rdp_property_lines" in payload
    assert payload["recommended_preset_id"] == "avd_teams"
