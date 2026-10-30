"""Copy the customization pack into GAMS repositories and open a pull request in each.

Usage (in the sync-pack workflow, or locally with an authenticated `gh`):
    python sync/sync_pack.py --version v0.1.0 [--dry-run] [--repo org/name ...]

Only pack-owned paths are written. A repository's other `.github/` files are left alone,
and `.vscode/settings.json` is created only when it does not exist yet.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "pack"
OWNED = [
    ".github/copilot-instructions.md",
    ".github/instructions",
    ".github/skills",
    ".github/agents",
    ".github/prompts",
    ".github/hooks/gams-sme.json",
    ".github/gams-agent.schema.json",
    ".vscode/mcp.json",
    ".vscode/tasks.json",
    ".vscode/extensions.json",
]
CREATE_ONLY = [".vscode/settings.json"]
MARKER = ".github/gams-sme-pack.json"


def run(cmd: list[str], cwd: Path | None = None) -> str:
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def copy_pack(dest: Path, version: str) -> list[str]:
    changed = []
    for rel in OWNED:
        src, dst = PACK / rel, dest / rel
        if src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        changed.append(rel)
    for rel in CREATE_ONLY:
        if not (dest / rel).exists():
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PACK / rel, dest / rel)
            changed.append(rel)
    (dest / MARKER).write_text(json.dumps({"pack": "gams-sme", "version": version, "source": "Will-C-debug/Gams_agent"}, indent=2) + "\n")
    return changed


def sync_repo(repo: str, base: str, version: str, dry_run: bool) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "repo"
        run(["gh", "repo", "clone", repo, str(work), "--", "--depth", "1", "--branch", base])
        branch = f"gams-sme-pack/{version}"
        run(["git", "checkout", "-b", branch], cwd=work)
        copy_pack(work, version)
        if not (work / ".gams-agent.yaml").exists():
            shutil.copy2(ROOT / "templates" / "gams-agent.yaml", work / ".gams-agent.yaml")
        status = run(["git", "status", "--porcelain"], cwd=work)
        if not status:
            return f"{repo}: already up to date"
        if dry_run:
            return f"{repo}: would update\n{status}"
        run(["git", "add", "-A"], cwd=work)
        run(["git", "commit", "-m", f"Update gams-sme Copilot pack to {version}"], cwd=work)
        run(["git", "push", "-u", "origin", branch], cwd=work)
        body = (
            f"Updates the gams-sme Copilot customization pack to **{version}** "
            "(instructions, skills, agents, prompts, hooks, VS Code MCP/tasks config).\n\n"
            "Review `.gams-agent.yaml` if this is the first sync: entry points, test cases, protected paths "
            "and the Jira/Confluence scope must match this repository.\n\n"
            "Source: https://github.com/Will-C-debug/Gams_agent"
        )
        url = run(["gh", "pr", "create", "--base", base, "--head", branch, "--title", f"gams-sme pack {version}", "--body", body], cwd=work)
        return f"{repo}: {url}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--repo", action="append", help="limit to these repositories")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    targets = yaml.safe_load((ROOT / "sync" / "targets.yaml").read_text()).get("targets") or []
    if args.repo:
        targets = [t for t in targets if t["repo"] in args.repo] or [{"repo": r, "base": "main"} for r in args.repo]
    if not targets:
        print("No targets configured in sync/targets.yaml")
        return 0
    failed = False
    for t in targets:
        try:
            print(sync_repo(t["repo"], t.get("base", "main"), args.version, args.dry_run))
        except subprocess.CalledProcessError as exc:
            failed = True
            print(f"{t['repo']}: FAILED: {exc.stderr or exc}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
