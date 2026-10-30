"""Snapshot a Confluence page (e.g. the GAMS standard in the STD space) into the pack.

The enforced standard lives in Git so reviews are reproducible and code review can use it
without Atlassian access. Run this, review the diff, and merge it like any other change.

Usage:
    ATLASSIAN_SITE=yourcompany.atlassian.net ATLASSIAN_EMAIL=svc@... ATLASSIAN_API_TOKEN=... \
    python sync/confluence_snapshot.py --page-id 123456 \
        --out pack/.github/skills/org-gams-standards/references/standard.md
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

_BLOCK_TAGS = {"p": "\n\n", "br": "\n", "li": "\n- ", "tr": "\n", "h1": "\n\n# ", "h2": "\n\n## ", "h3": "\n\n### ", "h4": "\n\n#### "}


def fetch_page(site: str, email: str, token: str, page_id: str) -> dict:
    url = f"https://{site}/wiki/api/v2/pages/{page_id}?body-format=storage"
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - fixed https URL
        return json.load(resp)


def storage_to_markdown(storage: str) -> str:
    """Rough conversion of Confluence storage format to Markdown (headings, paragraphs, lists, code)."""
    text = re.sub(r"<ac:structured-macro[^>]*ac:name=\"code\"[^>]*>.*?<!\[CDATA\[(.*?)\]\]>.*?</ac:structured-macro>",
                  lambda m: "\n\n```\n" + m.group(1) + "\n```\n\n", storage, flags=re.S)
    text = re.sub(r"<(td|th)[^>]*>", " | ", text)
    for tag, rep in _BLOCK_TAGS.items():
        text = re.sub(rf"<{tag}(\s[^>]*)?/?>", rep, text)
    text = re.sub(r"<code>(.*?)</code>", r"`\1`", text, flags=re.S)
    text = re.sub(r"<(strong|b)>(.*?)</\1>", r"**\2**", text, flags=re.S)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--page-id", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    site, email, token = (os.environ.get(k) for k in ("ATLASSIAN_SITE", "ATLASSIAN_EMAIL", "ATLASSIAN_API_TOKEN"))
    if not all((site, email, token)):
        print("Set ATLASSIAN_SITE, ATLASSIAN_EMAIL and ATLASSIAN_API_TOKEN (read-only service account).", file=sys.stderr)
        return 2
    page = fetch_page(site, email, token, args.page_id)
    version = page.get("version", {})
    header = (
        f"<!-- Snapshot of Confluence page {args.page_id}: \"{page.get('title')}\" "
        f"version {version.get('number')} ({version.get('createdAt')}). Do not edit here; edit in Confluence and re-run sync/confluence_snapshot.py. -->\n\n"
        f"# {page.get('title')}\n\n"
        f"Source: Confluence page {args.page_id}, version {version.get('number')}, updated {version.get('createdAt')}\n\n"
    )
    body = storage_to_markdown(page.get("body", {}).get("storage", {}).get("value", ""))
    Path(args.out).write_text(header + body, encoding="utf-8")
    print(f"wrote {args.out} from version {version.get('number')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
