"""Prepare eval workspaces and (optionally) run an agent command on each.

For seeded defects, each case becomes a small git repository: the base model is committed on
`main`, the seeded change on branch `eval/<case-id>`, and the customization pack is copied in, so
Copilot (CLI or VS Code) sees the same instructions, skills and agents as in a real repository.

    # Prepare only (run the prompts by hand in VS Code and save outputs as <results>/<id>.md):
    python evals/runner/run_evals.py --set seeded --out evals/results/2026-11-01-manual

    # Run an agent command per case; {prompt} and {workdir} are substituted. Verify the Copilot CLI
    # flags for your installed version (non-interactive prompt mode, agent selection, tool permissions):
    python evals/runner/run_evals.py --set seeded --out evals/results/run1 \
        --agent-cmd 'copilot --agent gams-reviewer -p "{prompt}" --allow-all-tools'

Then grade with grade_review.py (seeded) or grade_qa.py (qa).
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from common import EVALS, ROOT, load_cases, materialize

REVIEW_PROMPT = (
    "Review the GAMS/CPLEX changes on this branch against main using the gams-review skill and its output "
    "contract. Cite file:line for every finding."
)


def git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def prepare_seeded(case: dict, base: Path, work: Path) -> Path:
    repo = work / case["id"]
    materialize(base, None, repo)
    shutil.copytree(ROOT / "pack" / ".github", repo / ".github", dirs_exist_ok=True)
    shutil.copytree(ROOT / "pack" / ".vscode", repo / ".vscode", dirs_exist_ok=True)
    (repo / ".gitignore").write_text(".gams-agent/\n")
    git("init", "-q", "-b", "main", cwd=repo)
    git("-c", "user.name=eval", "-c", "user.email=eval@example.invalid", "add", "-A", cwd=repo)
    git("-c", "user.name=eval", "-c", "user.email=eval@example.invalid", "commit", "-q", "-m", "base model", cwd=repo)
    git("checkout", "-q", "-b", f"eval/{case['id']}", cwd=repo)
    tmp = work / f".{case['id']}-seeded"
    materialize(base, case, tmp)
    for edit in case["edits"]:
        shutil.copy2(tmp / edit["file"], repo / edit["file"])
    shutil.rmtree(tmp)
    git("-c", "user.name=eval", "-c", "user.email=eval@example.invalid", "commit", "-q", "-am", "change under review", cwd=repo)
    return repo


def run_agent(cmd_template: str, prompt: str, workdir: Path, timeout: int) -> str:
    cmd = cmd_template.replace("{prompt}", prompt.replace('"', "'")).replace("{workdir}", str(workdir))
    proc = subprocess.run(shlex.split(cmd), cwd=workdir, capture_output=True, text=True, timeout=timeout, check=False)
    return proc.stdout + (f"\n\n<!-- stderr -->\n{proc.stderr}" if proc.returncode else "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=["seeded", "qa"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--agent-cmd", help="command template with {prompt} and {workdir}")
    ap.add_argument("--cases", default=str(EVALS / "seeded_defects" / "uc_small.yaml"))
    ap.add_argument("--timeout", type=int, default=1200)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = out / "workspaces"
    work.mkdir(exist_ok=True)

    if args.set == "seeded":
        base, cases = load_cases(Path(args.cases))
        items = [(c["id"], prepare_seeded(c, base, work), REVIEW_PROMPT) for c in cases]
    else:
        qs = yaml.safe_load((EVALS / "knowledge_qa" / "questions.yaml").read_text())["questions"]
        repo = work / "qa"
        materialize(EVALS / "models" / "uc_small", None, repo)
        shutil.copytree(ROOT / "pack" / ".github", repo / ".github", dirs_exist_ok=True)
        items = [(q["id"], repo, q["question"]) for q in qs]

    manifest = []
    for item_id, workdir, prompt in items:
        manifest.append({"id": item_id, "workdir": str(workdir), "prompt": prompt})
        if args.agent_cmd:
            (out / f"{item_id}.md").write_text(run_agent(args.agent_cmd, prompt, workdir, args.timeout), encoding="utf-8")
            print(f"{item_id}: done")
    (out / "manifest.yaml").write_text(yaml.safe_dump({"set": args.set, "items": manifest}, sort_keys=False))
    if not args.agent_cmd:
        print(f"Prepared {len(manifest)} workspaces in {work}. Run each prompt (see manifest.yaml) and save outputs as {out}/<id>.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
