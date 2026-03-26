"""Optional headless-Chromium screenshots via html2image (shared by docs previews + board thumbs)."""

from __future__ import annotations

from pathlib import Path


def capture_url_to_png(
    url: str,
    output_path: Path,
    *,
    size: tuple[int, int] = (1280, 900),
    virtual_time_budget_ms: int = 8000,
) -> bool:
    """Load ``url`` in Chromium and save viewport PNG to ``output_path``. Returns True on success."""
    try:
        from html2image import Html2Image
    except ImportError:
        return False

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out_dir = output_path.parent
    name = output_path.name

    hti = Html2Image(
        output_path=str(out_dir),
        size=size,
        custom_flags=[
            "--hide-scrollbars",
            f"--virtual-time-budget={int(virtual_time_budget_ms)}",
        ],
    )
    try:
        hti.screenshot(url=url, save_as=name)
    except Exception:
        return False
    return output_path.is_file()
