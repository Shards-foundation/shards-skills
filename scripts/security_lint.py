#!/usr/bin/env python3
"""Standalone heuristic scan; output is a review queue, not a safety certificate."""
from pathlib import Path
import re, sys
ROOT=Path(__file__).resolve().parents[1]
patterns={
 "possible-secret-literal":re.compile(r"(?i)\b(sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})\b"),
 "remote-shell-pipe":re.compile(r"(?i)\b(curl|wget)\b[^\n|]*\|\s*(sh|bash)\b"),
 "privilege-escalation":re.compile(r"(?i)\bsudo\s+(?:-S\s+)?(?:rm|chmod|chown|curl|wget|bash|sh)\b"),
 "disable-security-controls":re.compile(r"(?i)(disable|turn off|bypass).{0,60}(verification|tls|certificate|security scan|approval gate)"),
}
issues=[]
baseline=[]
imported=[]
for skill_root in (ROOT / 'skills', ROOT / '.agents' / 'skills'):
    for folder in skill_root.iterdir() if skill_root.is_dir() else ():
        findings = imported if skill_root == ROOT / 'skills' and (folder / 'UPSTREAM.md').exists() else baseline
        for path in folder.rglob('*'):
            if path.is_file() and path.suffix.lower() in {'.md', '.py', '.sh', '.js', '.ts', '.json', '.yml', '.yaml'}:
                try:
                    data = path.read_text(encoding='utf-8')
                except (UnicodeError, OSError):
                    continue
                for label, pattern in patterns.items():
                    for match in pattern.finditer(data):
                        item = (path.relative_to(ROOT), label, data.count('\n', 0, match.start()) + 1)
                        findings.append(item)
                        issues.append(item)
for p,label,line in issues: print(f"REVIEW {p}:{line}: {label}")
print(f"Security lint scanned skills; {len(issues)} finding(s) require contextual review ({len(imported)} imported, {len(baseline)} baseline).")
# Imported packages are explicitly review-stage: findings are a queue, not a release blocker.
# Baseline Shards-authored packages must remain clean.
raise SystemExit(1 if baseline else 0)
