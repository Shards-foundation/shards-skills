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
for folder in (ROOT/'skills').glob('*'):
 for p in folder.rglob('*'):
  if p.is_file() and p.suffix.lower() in {'.md','.py','.sh','.js','.ts','.json','.yml','.yaml'}:
   try: data=p.read_text(encoding='utf-8')
   except (UnicodeError,OSError): continue
   for label,pat in patterns.items():
    for m in pat.finditer(data): issues.append((p.relative_to(ROOT),label,data.count('\n',0,m.start())+1))
baseline=[]
imported=[]
for item in issues:
    rel=item[0]
    skill_dir=ROOT / rel.parts[0] / rel.parts[1] if len(rel.parts) > 1 else ROOT
    (imported if (skill_dir / 'UPSTREAM.md').exists() else baseline).append(item)
for p,label,line in issues: print(f"REVIEW {p}:{line}: {label}")
print(f"Security lint scanned skills; {len(issues)} finding(s) require contextual review ({len(imported)} imported, {len(baseline)} baseline).")
# Imported packages are explicitly review-stage: findings are a queue, not a release blocker.
# Baseline Shards-authored packages must remain clean.
raise SystemExit(1 if baseline else 0)
