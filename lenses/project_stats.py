"""Git-derived stats for a single repo (stdlib + git CLI)."""

from __future__ import annotations

import html
import subprocess
import time
from collections import Counter
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_LOG_BOUNDARY = "<<<LENSES_COMMIT>>>"


def _run_git_bytes(cwd: Path, *args: str, timeout: float = 120.0) -> tuple[int, bytes, bytes]:
    try:
        r = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            timeout=timeout,
        )
        return r.returncode, r.stdout or b"", r.stderr or b""
    except (OSError, subprocess.TimeoutExpired):
        return -1, b"", b"Git invocation failed"


def _run_git_text(cwd: Path, *args: str, timeout: float = 120.0) -> str | None:
    code, out, _ = _run_git_bytes(cwd, *args, timeout=timeout)
    if code != 0:
        return None
    return out.decode("utf-8", errors="replace").strip()


def git_commit_count(cwd: Path) -> int | None:
    s = _run_git_text(cwd, "rev-list", "--count", "HEAD")
    if s is None:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _iter_log_dates_since(cwd: Path, since_days: int = 90) -> Iterator[str]:
    """Yields YYYY-MM-DD for each commit in the window."""
    since = (datetime.now(timezone.utc) - timedelta(days=since_days)).strftime("%Y-%m-%d")
    s = _run_git_text(
        cwd,
        "log",
        f"--since={since}",
        "--pretty=format:%ad",
        "--date=short",
        timeout=180.0,
    )
    if not s:
        return
    for line in s.splitlines():
        line = line.strip()
        if line:
            yield line


def commits_by_week_last_n_days(cwd: Path, days: int = 90) -> list[tuple[str, int]]:
    """Bucket commit counts by ISO week label (e.g. 2025-W12)."""
    counts: Counter[str] = Counter()
    for d in _iter_log_dates_since(cwd, since_days=days):
        try:
            dt = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        iso = dt.isocalendar()
        key = f"{iso.year}-W{iso.week:02d}"
        counts[key] += 1
    ordered = sorted(counts.items(), key=lambda x: x[0])
    return ordered


def git_recent_commits(cwd: Path, limit: int = 5) -> list[dict[str, str]]:
    """Recent commits with subject and body (multi-line)."""
    top = cwd.resolve()
    if not (top / ".git").exists():
        return []
    fmt = f"%H%n%h%n%cI%n%s%n%B%n{_LOG_BOUNDARY}"
    s = _run_git_text(
        top,
        "log",
        f"-n{limit}",
        f"--pretty=format:{fmt}",
        timeout=90.0,
    )
    if not s:
        return []
    out: list[dict[str, str]] = []
    for part in s.split(_LOG_BOUNDARY):
        part_st = part.strip()
        if not part_st:
            continue
        lines = part_st.split("\n")
        if len(lines) < 4:
            continue
        h_full, h_short, date, subj = lines[0], lines[1], lines[2], lines[3]
        body = "\n".join(lines[4:]).strip()
        out.append(
            {
                "hash_full": h_full.strip(),
                "hash_short": h_short.strip(),
                "date": date.strip(),
                "subject": subj.strip(),
                "body": body,
            }
        )
    return out


def git_numstat_since(cwd: Path, days: int = 7) -> tuple[int, int]:
    """Sum insertions and deletions from numstat over commits in the window."""
    top = cwd.resolve()
    if not (top / ".git").exists():
        return 0, 0
    since = f"{days} days ago"
    s = _run_git_text(
        top,
        "log",
        f"--since={since}",
        "--pretty=tformat:",
        "--numstat",
        timeout=120.0,
    )
    if not s:
        return 0, 0
    added = deleted = 0
    for line in s.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        a, d = parts[0], parts[1]
        if a == "-" or d == "-":
            continue
        try:
            added += int(a)
            deleted += int(d)
        except ValueError:
            continue
    return added, deleted


def top_contributors(cwd: Path, limit: int = 15) -> list[tuple[int, str]]:
    s = _run_git_text(cwd, "shortlog", "-sn", "HEAD", timeout=120.0)
    if not s:
        return []
    out: list[tuple[int, str]] = []
    for line in s.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        try:
            n = int(parts[0].strip())
        except ValueError:
            continue
        out.append((n, parts[1].strip()))
        if len(out) >= limit:
            break
    return out


# Approximate LoC: tracked text files only, hard caps so /projects stays responsive.
_LOC_MAX_FILES = 4000
_LOC_MAX_FILE_BYTES = 512 * 1024
_LOC_MAX_TOTAL_BYTES = 40 * 1024 * 1024
_LOC_WALL_SECONDS = 25.0
_LOC_BINARY_SUFFIXES = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".ico",
        ".pdf",
        ".zip",
        ".gz",
        ".tgz",
        ".bz2",
        ".xz",
        ".7z",
        ".rar",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".mp3",
        ".mp4",
        ".webm",
        ".mov",
        ".avi",
        ".sqlite",
        ".db",
        ".bin",
        ".pyc",
        ".pyo",
        ".class",
        ".o",
        ".a",
    }
)


def approx_tracked_lines(repo: Path) -> int | None:
    """Count newlines in git-tracked files under *repo* (approximate LoC).

    Skips large files, common binary extensions, and blobs with NUL in the first 8KiB.
    Stops after a wall-clock budget, byte budget, or file count cap.
    """
    top = repo.resolve()
    if not (top / ".git").exists():
        return None
    code, raw, _ = _run_git_bytes(top, "ls-files", "-z", timeout=60.0)
    if code != 0:
        return None
    names = [x.decode("utf-8", errors="replace") for x in raw.split(b"\0") if x]
    if not names:
        return 0
    deadline = time.monotonic() + _LOC_WALL_SECONDS
    total_lines = 0
    bytes_read = 0
    for i, rel in enumerate(names):
        if i >= _LOC_MAX_FILES:
            break
        if time.monotonic() > deadline:
            break
        rel = rel.replace("\\", "/").strip("/")
        if not rel or ".." in rel.split("/"):
            continue
        fp = (top / rel).resolve()
        try:
            fp.relative_to(top)
        except ValueError:
            continue
        try:
            if not fp.is_file():
                continue
            st = fp.stat()
        except OSError:
            continue
        if st.st_size > _LOC_MAX_FILE_BYTES:
            continue
        if fp.suffix.lower() in _LOC_BINARY_SUFFIXES:
            continue
        try:
            data = fp.read_bytes()
        except OSError:
            continue
        if len(data) > _LOC_MAX_FILE_BYTES:
            continue
        sample = data[:8192]
        if b"\x00" in sample:
            continue
        bytes_read += len(data)
        if bytes_read > _LOC_MAX_TOTAL_BYTES:
            break
        total_lines += data.count(b"\n")
    return total_lines


def file_extension_counts(cwd: Path, limit: int = 20) -> tuple[list[tuple[str, int]], int]:
    code, raw, _ = _run_git_bytes(cwd, "ls-files", "-z", timeout=120.0)
    if code != 0:
        return [], 0
    names = [x.decode("utf-8", errors="replace") for x in raw.split(b"\0") if x]
    ext_counts: Counter[str] = Counter()
    for name in names:
        part = Path(name)
        suf = part.suffix.lower() or "(no extension)"
        ext_counts[suf] += 1
    items = sorted(ext_counts.items(), key=lambda x: (-x[1], x[0]))
    return items[:limit], len(names)


def svg_commit_bar_chart(
    weekly: list[tuple[str, int]],
    *,
    width: int = 720,
    height: int = 200,
    bar_color: str = "rgba(6,182,212,0.85)",
) -> str:
    if not weekly:
        return '<p class="forge-support mb-0">No commits in the last 90 days.</p>'
    labels = [w[0] for w in weekly]
    values = [w[1] for w in weekly]
    vmax = max(values) if values else 1
    n = len(values)
    margin_l, margin_r, margin_t, margin_b = 36, 12, 12, 28
    inner_w = width - margin_l - margin_r
    inner_h = height - margin_t - margin_b
    bw = max(2.0, (inner_w / n) * 0.72)
    gap = max(0.5, (inner_w / n) * 0.28)
    bars = []
    for i, v in enumerate(values):
        x = margin_l + i * (bw + gap) + gap * 0.25
        h = (v / vmax) * inner_h if vmax else 0
        y = margin_t + inner_h - h
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{max(h, 1):.1f}" '
            f'fill="{bar_color}" rx="2"><title>{labels[i]}: {v} commits</title></rect>'
        )
    # x-axis tick: show first, middle, last week labels
    tick_idx = [0, n // 2, n - 1] if n > 2 else list(range(n))
    ticks = []
    for idx in tick_idx:
        if idx < 0 or idx >= n:
            continue
        x = margin_l + idx * (bw + gap) + gap * 0.25 + bw / 2
        ticks.append(
            f'<text x="{x:.1f}" y="{height - 6}" text-anchor="middle" '
            f'fill="var(--forge-muted,#94a3b8)" font-size="10">{labels[idx]}</text>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="Commits by week" style="width:100%;max-width:{width}px;height:auto">'
        f'<rect width="100%" height="100%" fill="transparent"/>'
        + "".join(bars)
        + "".join(ticks)
        + "</svg>"
    )


def svg_loc_added_horizontal_bars(
    rows: list[tuple[str, int]],
    *,
    width: int = 680,
    row_height: int = 26,
    label_width: int = 168,
    margin_r: int = 56,
    bar_color: str = "rgba(6,182,212,0.88)",
) -> str:
    """Horizontal bars: repo label + lines added (7d). rows: (display_name, additions)."""
    if not rows:
        return '<p class="forge-support mb-0">No line additions in the last 7 days (or no git repos).</p>'
    values = [max(0, int(v)) for _, v in rows]
    vmax = max(values) if values else 1
    n = len(rows)
    height = 28 + n * row_height
    inner_w = width - label_width - margin_r - 16
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="Lines added by repository" '
        f'style="width:100%;max-width:{width}px;height:auto">',
        '<rect width="100%" height="100%" fill="transparent"/>',
    ]
    for i, (name, v) in enumerate(rows):
        v = max(0, int(v))
        y = 20 + i * row_height
        label = html.escape(name[:48], quote=True)
        parts.append(
            f'<text x="4" y="{y + 14}" fill="var(--forge-muted,#94a3b8)" font-size="11" '
            f'text-anchor="start">{label}</text>'
        )
        bw = (v / vmax) * inner_w if vmax else 0
        bw = max(bw, 1.0) if v > 0 else 0
        x0 = label_width
        parts.append(
            f'<rect x="{x0:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{row_height - 8:.1f}" '
            f'fill="{bar_color}" rx="3"><title>{label}: {v} lines added</title></rect>'
        )
        parts.append(
            f'<text x="{x0 + inner_w + 6:.1f}" y="{y + 14}" fill="var(--forge-muted,#94a3b8)" '
            f'font-size="11" text-anchor="start">{v}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def extension_heatmap_html(ext_rows: list[tuple[str, int]], total_files: int) -> str:
    if not ext_rows or total_files <= 0:
        return '<p class="forge-support mb-0">No tracked files.</p>'
    parts: list[str] = []
    for ext, cnt in ext_rows:
        pct = 100.0 * cnt / total_files
        w = max(4.0, pct)
        label = html.escape(ext, quote=True)
        parts.append(
            f'<div class="mb-2"><div class="d-flex justify-content-between small mb-1">'
            f"<span><code>{label}</code></span><span>{cnt}</span></div>"
            f'<div class="lenses-ext-bar" style="width:{w:.1f}%"></div></div>'
        )
    return "\n".join(parts)


def collect_project_stats(repo_path: Path) -> dict[str, Any]:
    """Serializable stats for JSON API and HTML rendering."""
    p = repo_path.resolve()
    commits_total = git_commit_count(p)
    weekly = commits_by_week_last_n_days(p, days=90)
    contributors = top_contributors(p)
    ext_rows, total_tracked = file_extension_counts(p, limit=25)
    lines_approx = approx_tracked_lines(p)
    out: dict[str, Any] = {
        "commits_total": commits_total,
        "commits_by_week": [{"week": w, "count": c} for w, c in weekly],
        "contributors": [{"commits": n, "name": name} for n, name in contributors],
        "extensions": [{"extension": e, "count": c} for e, c in ext_rows],
        "tracked_files": total_tracked,
    }
    if lines_approx is not None:
        out["tracked_lines_approx"] = lines_approx
    return out
