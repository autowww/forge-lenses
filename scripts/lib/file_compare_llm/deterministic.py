from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Literal

CompareMode = Literal["document", "code"]

CODE_EXTENSIONS = frozenset(
    {
        ".py",
        ".pyi",
        ".rs",
        ".go",
        ".java",
        ".kt",
        ".kts",
        ".c",
        ".h",
        ".cpp",
        ".hpp",
        ".cc",
        ".cs",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".ts",
        ".tsx",
        ".swift",
        ".rb",
        ".php",
        ".scala",
        ".sql",
        ".sh",
        ".bash",
        ".zsh",
    }
)


def infer_compare_mode(path_a: Path, path_b: Path, mode: str) -> CompareMode:
    if mode == "code":
        return "code"
    if mode == "document":
        return "document"

    def is_code(p: Path) -> bool:
        return p.suffix.lower() in CODE_EXTENSIONS

    if is_code(path_a) and is_code(path_b):
        return "code"
    return "document"


def read_text(path: Path, encoding: str = "utf-8") -> tuple[str, int, str]:
    raw = path.read_bytes()
    text = raw.decode(encoding, errors="replace")
    sha = hashlib.sha256(raw).hexdigest()
    return text, len(raw), sha


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def lines_of(text: str) -> list[str]:
    return text.splitlines()


_MD_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_DEF_LIKE = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:function\s+\w+|def\s+\w+|fn\s+\w+|fun\s+\w+|"
    r"func\s+\w+|proc\s+\w+|public|private|protected|static|class\s+\w+|"
    r"interface\s+\w+|struct\s+\w+|enum\s+\w+|impl\s+|trait\s+)",
    re.IGNORECASE,
)


@dataclass
class FileSignals:
    path: str
    byte_size: int
    sha256: str
    line_count: int
    non_empty_lines: int
    blank_line_ratio: float
    max_line_length: int
    # document
    headings: list[str] = field(default_factory=list)
    paragraph_count: int = 0
    avg_paragraph_len: float = 0.0
    code_fence_count: int = 0
    json_top_keys: list[str] = field(default_factory=list)
    json_entity_ids: list[str] = field(default_factory=list)  # nodes[].id or fragments[].taxonomy_id
    json_parse_ok: bool = False
    # code
    def_like_lines: int = 0
    comment_line_ratio: float = 0.0
    brace_balance_hint: int = 0  # naive { } count delta


def _json_entity_extraction(data: Any) -> tuple[list[str], list[str]]:
    keys: list[str] = []
    ids: list[str] = []
    if isinstance(data, dict):
        keys = sorted(str(k) for k in data.keys())
        nodes = data.get("nodes")
        if isinstance(nodes, list):
            for n in nodes:
                if isinstance(n, dict) and n.get("id") is not None:
                    ids.append(str(n["id"]))
        fr = data.get("fragments")
        if isinstance(fr, list):
            for item in fr:
                if isinstance(item, dict) and item.get("taxonomy_id"):
                    ids.append(str(item["taxonomy_id"]))
    return keys, sorted(set(ids))


def _markdown_signals(text: str) -> tuple[list[str], int, float, int]:
    headings = [m.group(2).strip() for m in _MD_HEADING.finditer(text)]
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    n = len(paras)
    avg = sum(len(p) for p in paras) / n if n else 0.0
    fences = len(re.findall(r"^```", text, flags=re.MULTILINE))
    return headings, n, avg, fences


def _code_signals(lines: list[str]) -> tuple[int, float, int]:
    n = len(lines)
    if not n:
        return 0, 0.0, 0
    nonempty = [ln for ln in lines if ln.strip()]
    ne = len(nonempty)
    if not ne:
        return 0, 0.0, 0
    commentish = 0
    def_like = 0
    opens = 0
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if _DEF_LIKE.match(s):
            def_like += 1
        if s.startswith("#") or s.startswith("//") or s.startswith("/*") or s.startswith("*"):
            commentish += 1
        elif "#" in s and not s.startswith('"'):
            # weak: mid-line # often comment in py
            pass
        opens += s.count("{") - s.count("}")
    return def_like, min(1.0, commentish / ne), opens


def collect_signals(
    path: Path,
    text: str,
    mode: CompareMode,
    *,
    raw_byte_size: int,
    sha256_hex: str,
) -> FileSignals:
    lines = lines_of(text)
    nonempty = sum(1 for ln in lines if ln.strip())
    blanks = sum(1 for ln in lines if not ln.strip())
    lc = len(lines)
    blank_ratio = blanks / lc if lc else 0.0
    max_ll = max((len(ln) for ln in lines), default=0)

    sig = FileSignals(
        path=str(path),
        byte_size=raw_byte_size,
        sha256=sha256_hex,
        line_count=lc,
        non_empty_lines=nonempty,
        blank_line_ratio=blank_ratio,
        max_line_length=max_ll,
    )

    if path.suffix.lower() == ".json":
        try:
            data = json.loads(text)
            sig.json_parse_ok = True
            sig.json_top_keys, sig.json_entity_ids = _json_entity_extraction(data)
        except json.JSONDecodeError:
            sig.json_parse_ok = False

    if mode == "document":
        h, pc, apl, fc = _markdown_signals(text)
        sig.headings = h
        sig.paragraph_count = pc
        sig.avg_paragraph_len = apl
        sig.code_fence_count = fc
        if not sig.headings and sig.json_entity_ids:
            # use taxonomy / fragment ids as pseudo-headings for overlap metrics
            sig.headings = list(sig.json_entity_ids[:500])  # cap for memory
        if sig.json_parse_ok and path.suffix.lower() == ".json" and pc <= 2 and nonempty:
            # JSON is one "paragraph" by split; use avg non-empty line length as depth proxy
            sig.avg_paragraph_len = sum(len(ln) for ln in lines if ln.strip()) / nonempty

    if mode == "code":
        d, cr, bb = _code_signals(lines)
        sig.def_like_lines = d
        sig.comment_line_ratio = cr
        sig.brace_balance_hint = bb

    return sig


@dataclass
class DiffStats:
    similarity_ratio: float
    lines_a: int
    lines_b: int
    changed_blocks: int  # number of non-equal opcodes
    chars_a: int
    chars_b: int


def diff_stats(lines_a: list[str], lines_b: list[str]) -> DiffStats:
    sm = SequenceMatcher(a=lines_a, b=lines_b)
    ratio = sm.ratio()
    blocks = sum(1 for tag, _, _, _, _ in sm.get_opcodes() if tag != "equal")
    ca = sum(len(l) + 1 for l in lines_a)
    cb = sum(len(l) + 1 for l in lines_b)
    return DiffStats(
        similarity_ratio=ratio,
        lines_a=len(lines_a),
        lines_b=len(lines_b),
        changed_blocks=blocks,
        chars_a=ca,
        chars_b=cb,
    )


def hunk_line_indices(lines_a: list[str], lines_b: list[str], max_hunks: int = 12) -> list[int]:
    """0-based line indices in A to prioritize for code excerpts."""
    sm = SequenceMatcher(a=lines_a, b=lines_b)
    spans: list[tuple[int, int]] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if i2 > i1:
            spans.append((max(0, i1 - 2), min(len(lines_a), i2 + 2)))
    if not spans:
        return []
    merged: list[tuple[int, int]] = []
    for a, b in sorted(spans):
        if not merged or a > merged[-1][1]:
            merged.append((a, b))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
    out: list[int] = []
    for a, b in merged[:max_hunks]:
        out.extend(range(a, b))
    return sorted(set(out))[:400]


def sample_json_excerpt(text: str, max_chars: int) -> str:
    try:
        data = json.loads(text)
        pretty = json.dumps(data, indent=2, ensure_ascii=False)
        if len(pretty) <= max_chars:
            return pretty
        half = max_chars // 2 - 40
        return (
            "[JSON excerpt: start + end; middle omitted]\n"
            + pretty[:half]
            + "\n\n…\n\n"
            + pretty[-half:]
        )
    except json.JSONDecodeError:
        return text[:max_chars]


def sample_document_excerpt(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    headings_block = "\n".join(m.group(0) for m in _MD_HEADING.finditer(text))[:8000]
    chunks: list[str] = [f"[Truncated: showing headings block + sampled paragraphs, total {len(text)} chars]\n"]
    if headings_block.strip():
        chunks.append(headings_block + "\n\n")
    budget = max_chars - sum(len(c) for c in chunks) - 80
    step = max(1, len(paras) // 20) if paras else 1
    acc = []
    for i in range(0, len(paras), step):
        acc.append(paras[i])
        if sum(len(x) for x in acc) > budget:
            break
    chunks.append("\n\n".join(acc))
    s = "\n".join(chunks)
    return s[:max_chars]


def sample_code_excerpt(lines_a: list[str], lines_b: list[str], max_chars: int) -> str:
    head = "\n".join(lines_a[:40])
    hunks = hunk_line_indices(lines_a, lines_b)
    parts: list[str] = [f"[First 40 lines of file A / {len(lines_a)} lines]\n{head}\n"]
    if hunks:
        blocks = []
        for i in hunks[:80]:
            lo = max(0, i - 2)
            hi = min(len(lines_a), i + 3)
            blocks.append(f"--- around line {i+1} ---\n" + "\n".join(lines_a[lo:hi]))
        parts.append("\n\n".join(blocks))
    s = "\n\n".join(parts)
    if len(s) > max_chars:
        return s[: max_chars - 30] + "\n[...truncated...]\n"
    return s


def jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    u = len(sa | sb)
    if not u:
        return 0.0
    return len(sa & sb) / u
