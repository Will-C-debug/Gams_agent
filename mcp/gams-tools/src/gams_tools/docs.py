"""Keyword search over version-pinned documentation folders listed in `.gams-agent.yaml`.

This is deliberately simple (no embeddings, no network): passages are paragraphs of
Markdown/text/HTML files, ranked by how many query terms they contain.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from .config import Config

_EXTS = {".md", ".txt", ".html", ".htm", ".rst"}
_TAG_RE = re.compile(r"<[^>]+>")
_WORD_RE = re.compile(r"[A-Za-z0-9_$.%]+")


def _paragraphs(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix in (".html", ".htm"):
        text = html.unescape(_TAG_RE.sub(" ", text))
    line_no = 1
    for block in re.split(r"\n\s*\n", text):
        stripped = block.strip()
        if stripped:
            yield line_no, stripped
        line_no += block.count("\n") + 2


def search(cfg: Config, query: str, scope: str | None = None, limit: int = 8) -> dict:
    terms = [t.lower() for t in _WORD_RE.findall(query) if len(t) > 1]
    if not terms:
        return {"ok": False, "error": "empty query"}
    hits = []
    for d in cfg.docs_dirs:
        root = cfg.resolve(d)
        if scope and scope.lower() not in d.lower():
            continue
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.suffix.lower() not in _EXTS or not path.is_file():
                continue
            for line, para in _paragraphs(path):
                low = para.lower()
                score = sum(low.count(t) for t in terms) + 3 * sum(1 for t in set(terms) if t in low)
                if score and all(t in low for t in terms[:1]):
                    hits.append((score, cfg.relpath(path), line, para[:800]))
    hits.sort(key=lambda h: -h[0])
    return {
        "ok": True,
        "query": query,
        "searched": cfg.docs_dirs,
        "results": [{"source": f"{p}:{ln}", "score": s, "text": t} for s, p, ln, t in hits[:limit]],
        "note": None if cfg.docs_dirs else "no docs.dirs configured in .gams-agent.yaml",
    }
