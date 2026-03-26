"""Map git remote URLs to HTTPS repo and commit pages (GitHub / GitLab)."""

from __future__ import annotations

import re
from urllib.parse import urlparse


def _github_ssh_to_https(url: str) -> str | None:
    m = re.match(r"^git@github\.com:([^/]+)/(.+?)(?:\.git)?$", url.strip())
    if not m:
        return None
    org, repo = m.group(1), m.group(2)
    return f"https://github.com/{org}/{repo}"


def _gitlab_ssh_to_https(url: str) -> str | None:
    m = re.match(r"^git@([^:]+):([^/]+)/(.+?)(?:\.git)?$", url.strip())
    if not m:
        return None
    host, group, repo = m.group(1), m.group(2), m.group(3)
    if "gitlab" not in host and not host.endswith(".gitlab.com"):
        return None
    return f"https://{host}/{group}/{repo}"


def remote_to_https_repo_url(origin_url: str) -> str | None:
    if not origin_url or not origin_url.strip():
        return None
    u = origin_url.strip()
    if u.startswith("git@github.com:"):
        return _github_ssh_to_https(u)
    if u.startswith("git@"):
        gl = _gitlab_ssh_to_https(u)
        if gl:
            return gl
        return None
    if "://" not in u:
        return None
    parsed = urlparse(u)
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    if "github.com" in host:
        path = path.strip("/")
        if path.endswith(".git"):
            path = path[: -4]
        if path.count("/") >= 1:
            return f"https://github.com/{path}"
    if "gitlab" in host or host.endswith("gitlab.com"):
        path = path.strip("/")
        if path.endswith(".git"):
            path = path[: -4]
        if path:
            return f"https://{host}/{path}"
    return None


def commit_url_for_remote(origin_url: str, head_full: str) -> str | None:
    if not head_full:
        return None
    base = remote_to_https_repo_url(origin_url)
    if not base:
        return None
    b = base.rstrip("/")
    if "github.com" in b:
        return f"{b}/commit/{head_full}"
    if "gitlab" in b:
        return f"{b}/-/commit/{head_full}"
    return None
