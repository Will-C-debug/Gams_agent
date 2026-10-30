"""Structural checks for the Copilot customization pack (run in CI).

- copilot-instructions.md stays under the code-review reading limit
- every instructions/prompt/agent/skill file has valid YAML frontmatter with the required keys
- skill names follow the Agent Skills rules and match their folder
- relative Markdown links inside the pack resolve
- JSON files parse
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "pack"
GH = PACK / ".github"
INSTRUCTION_LIMIT = 4000
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")

errors: list[str] = []


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        errors.append(f"{path.relative_to(ROOT)}: missing YAML frontmatter")
        return {}
    try:
        _, fm, _ = text.split("---\n", 2)
        data = yaml.safe_load(fm) or {}
    except (ValueError, yaml.YAMLError) as exc:
        errors.append(f"{path.relative_to(ROOT)}: bad frontmatter: {exc}")
        return {}
    if not isinstance(data, dict):
        errors.append(f"{path.relative_to(ROOT)}: frontmatter must be a mapping")
        return {}
    return data


def require(path: Path, data: dict, *keys: str) -> None:
    for key in keys:
        if not data.get(key):
            errors.append(f"{path.relative_to(ROOT)}: frontmatter needs '{key}'")


def main() -> int:
    ci = GH / "copilot-instructions.md"
    size = len(ci.read_text(encoding="utf-8"))
    if size > INSTRUCTION_LIMIT:
        errors.append(f"{ci.relative_to(ROOT)}: {size} characters, over the {INSTRUCTION_LIMIT} code-review limit")

    for p in sorted((GH / "instructions").glob("*.instructions.md")):
        require(p, frontmatter(p), "applyTo")

    for p in sorted((GH / "prompts").glob("*.prompt.md")):
        require(p, frontmatter(p), "description")

    agent_names = set()
    for p in sorted((GH / "agents").glob("*.agent.md")):
        fm = frontmatter(p)
        require(p, fm, "name", "description", "tools")
        agent_names.add(fm.get("name"))
        if fm.get("name") and p.name != f"{fm['name']}.agent.md":
            errors.append(f"{p.relative_to(ROOT)}: name '{fm['name']}' does not match the file name")
    for p in sorted((GH / "agents").glob("*.agent.md")):
        for h in frontmatter(p).get("handoffs") or []:
            if h.get("agent") not in agent_names:
                errors.append(f"{p.relative_to(ROOT)}: handoff to unknown agent {h.get('agent')!r}")
    for p in sorted((GH / "prompts").glob("*.prompt.md")):
        agent = frontmatter(p).get("agent")
        if agent and agent not in agent_names and agent not in ("agent", "ask", "edit"):
            errors.append(f"{p.relative_to(ROOT)}: unknown agent {agent!r}")

    for d in sorted(p for p in (GH / "skills").iterdir() if p.is_dir()):
        skill = d / "SKILL.md"
        if not skill.exists():
            errors.append(f"{d.relative_to(ROOT)}: missing SKILL.md")
            continue
        fm = frontmatter(skill)
        require(skill, fm, "name", "description")
        name = fm.get("name", "")
        if name != d.name or not SKILL_NAME_RE.match(name) or len(name) > 64:
            errors.append(f"{skill.relative_to(ROOT)}: name must be lower-case-hyphenated, <= 64 chars and match the folder")
        if len(fm.get("description", "")) > 1024:
            errors.append(f"{skill.relative_to(ROOT)}: description over 1024 characters")

    for md in sorted(PACK.rglob("*.md")):
        for target in LINK_RE.findall(md.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (md.parent / target).resolve().exists():
                errors.append(f"{md.relative_to(ROOT)}: broken link {target}")

    for js in sorted(PACK.rglob("*.json")):
        try:
            json.loads(js.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{js.relative_to(ROOT)}: invalid JSON: {exc}")

    if errors:
        print("Pack validation failed:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"Pack OK: copilot-instructions.md is {size} characters; {len(agent_names)} agents; "
          f"{len(list((GH / 'skills').iterdir()))} skills; {len(list((GH / 'prompts').glob('*.prompt.md')))} prompts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
