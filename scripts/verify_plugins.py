#!/usr/bin/env python3
"""Validate curated plugin files and dispatcher contracts without running skills."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from dispatch_skills import CORE, REGISTRY, ROOT, _repository_path

MANIFESTS = ("plugin.json", ".claude-plugin/plugin.json",
             ".codex-plugin/plugin.json", ".cursor-plugin/plugin.json")
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

def validate(root: Path = ROOT, core: Path = CORE) -> dict:
    errors, warnings, skills = [], [], []
    names = set()
    try:
        for path in MANIFESTS:
            target = core / path
            if target.is_symlink() or not target.is_file():
                errors.append("Missing or symlinked manifest: " + path)
                continue
            data = json.loads(target.read_text(encoding="utf-8"))
            if data.get("name") != "shards-agent-core":
                errors.append("Incorrect plugin name in " + path)
            if not isinstance(data.get("version"), str) or not data["version"]:
                errors.append("Missing plugin version in " + path)
        marketplace = json.loads((root / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
        entries = marketplace.get("plugins", [])
        if not any(isinstance(item, dict) and item.get("name") == "shards-agent-core"
                   and item.get("source", {}).get("path") == "./plugins/shards-core" for item in entries):
            errors.append("Local marketplace does not point to curated plugin")
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append("Invalid plugin manifest: " + str(exc))
    for descriptor in sorted((core / "skills").glob("*/SKILL.md")):
        directory = descriptor.parent
        name = directory.name
        try:
            if not NAME.fullmatch(name) or descriptor.is_symlink() or directory.is_symlink():
                raise ValueError("Invalid or symlinked skill path")
            if (directory / "UPSTREAM.md").exists():
                raise ValueError("Imported descriptor is forbidden in curated plugin")
            content = descriptor.read_text(encoding="utf-8")
            match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", content, re.S)
            if not match:
                raise ValueError("Frontmatter missing")
            values = {}
            for line in match.group(1).splitlines():
                if ":" not in line or line[:1].isspace():
                    raise ValueError("Unsupported YAML frontmatter")
                key, value = line.split(":", 1)
                values[key.strip()] = value.strip().strip("\"'")
            if values.get("name") != name:
                raise ValueError("Skill name mismatch")
            if not (20 <= len(values.get("description", "")) <= 1024):
                raise ValueError("Description length outside allowed bounds")
            for heading in ("## Workflow", "## Execution", "## Output contract",
                            "## Verification", "## Failure handling"):
                if heading not in content:
                    raise ValueError("Missing section: " + heading)
            for match in re.finditer(r"\[[^\]]*]\(([^)]+)\)", content):
                link = match.group(1).split("#", 1)[0]
                if link and not link.startswith(("http://", "https://", "mailto:")):
                    resolved = (directory / link).resolve()
                    if not resolved.is_relative_to(directory.resolve()) or not resolved.is_file():
                        raise ValueError("Unsafe or missing link: " + link)
            names.add(name)
            skills.append({"name": name, "status": "descriptor-valid"})
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(name + ": " + str(exc))
    if names != set(REGISTRY):
        errors.append("Curated registry/skill mismatch: missing=" + repr(sorted(set(REGISTRY) - names)) +
                      "; unknown=" + repr(sorted(names - set(REGISTRY))))
    for name, (effect, script, operation) in REGISTRY.items():
        try:
            # Only resolve known first-party script files; do not execute them here.
            if root.resolve() == ROOT.resolve():
                _repository_path(script)
            else:
                target = root / script
                if target.is_symlink() or not target.is_file() or not target.resolve().is_relative_to(root.resolve()):
                    raise ValueError("Missing or symlinked trusted script")
        except (ValueError, OSError) as exc:
            errors.append(name + ": " + str(exc))
    if not (root / "AGENTS.md").is_file() or not (root / "agent.md").is_file():
        errors.append("Agent identity/governance files missing")
    return {"workflow": "plugin-integrity", "status": "PASS" if not errors else "FAIL",
            "checked_skills": len(skills), "registered_skills": len(REGISTRY),
            "manifests_checked": list(MANIFESTS), "errors": errors, "warnings": warnings,
            "scope": "local-file-structure-only; host installation not tested"}

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate plugin and registry without execution")
    args = parser.parse_args(argv)
    result = validate()
    print(json.dumps(result, sort_keys=True, indent=2))
    return int(result["status"] != "PASS")

if __name__ == "__main__":
    raise SystemExit(main())
