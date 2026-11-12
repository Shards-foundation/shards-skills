#!/usr/bin/env python3
"""Read-only, heuristic checks for tracked local source. Never executes project code.

Calibrated build (P0). Adds contextual triage to the pattern engine:

  * No global exclusion of tests/, fixtures or certificate material. Every finding
    is emitted and carries `classification`, `confidence` and `suppression_reason`.
  * Verification against default-named test directories is evidence-based: a
    finding is only classified as likely-intentional when independent contextual
    signals agree (declared test tree, fixture declaration, parsed certificate
    identity, absence of production references, expected-failure context).
  * Potentially real credentials remain actionable even inside tests.
  * Tracked symlinks are resolved (never read through) and classified as
    internal or escape; escapes are reported as high severity.
  * `--no-triage` reproduces the legacy signature-only behaviour for baseline
    comparison, so triage can never hide a previously emitted finding.

Exit codes: 0 = complete scan/no actionable findings, 1 = actionable warnings, 2 = blocked or incomplete scan.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

MAX_FILES = 3000
MAX_FILE_BYTES = 256_000
MAX_TOTAL_BYTES = 20_000_000
MAX_FINDINGS = 200
SOURCE_EXT = {".js", ".jsx", ".ts", ".tsx", ".py", ".sql", ".tf", ".yml", ".yaml", ".toml", ".json"}
KEY_EXT = {".pem", ".key"}
CONTAINER_EXT = {".p12", ".pfx"}

RULES = [
    ("TLS-VERIFY-DISABLED", "high", re.compile(r"\bverify\s*=\s*False\b|rejectUnauthorized\s*:\s*false\b", re.I), "Review TLS certificate verification; this may permit interception"),
    ("DYNAMIC-EVAL", "medium", re.compile(r"(?<![\w.])eval\s*\("), "Dynamic code evaluation requires a trusted input boundary"),
    ("WEAK-YAML-LOADER", "high", re.compile(r"\byaml\.load\s*\([^\n]*\bLoader\s*=\s*yaml\.(?:Loader|UnsafeLoader)"), "Unsafe deserialisation of untrusted YAML may enable code execution"),
    ("CI-WRITE-ALL", "high", re.compile(r"\bpermissions\s*:\s*write-all\b", re.I), "Broad CI permissions require least-privilege review"),
    ("POTENTIAL-PUBLIC-CORS", "medium", re.compile(r"allow_origins\s*=\s*\[\s*['\"]\*['\"]\s*\]|(?:origin|Access-Control-Allow-Origin)\s*[:=,]\s*['\"]\*['\"]", re.I), "Wildcard CORS should be reviewed against authentication and credential use"),
    ("DEPLOYMENT-DEBUG", "medium", re.compile(r"(?<![\w])DEBUG\s*=\s*True\b"), "Development debugging must not be exposed in production"),
    ("PERMISSIVE-RLS", "medium", re.compile(r"\bUSING\s*\(\s*true\s*\)", re.I), "Permissive database row policy may expose tenant data"),
]

# Credential shapes that are actionable regardless of path, including under tests/.
LIVE_CREDENTIAL = [
    ("AWS-ACCESS-KEY-ID", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "high"),
    ("GITHUB-TOKEN", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"), "high"),
    ("OPENAI-STYLE-KEY", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "high"),
    ("PRIVATE-KEY-BLOCK", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"), "high"),
    ("SLACK-TOKEN", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "high"),
]

TEST_DIR_NAMES = {"test", "tests", "spec", "specs", "__tests__", "testing"}
FIXTURE_DIR_NAMES = {"fixtures", "fixture", "testdata", "test_data", "certs", "certs_test", "cassettes", "__fixtures__", "mocks"}
TEST_IDENTITY_TOKENS = {"localhost", "127", "example", "dummy", "test", "invalid",
                        "fake", "sample", "sandbox"}

GENERATED_HINT = ("conftest.py", "pytest.ini", "tox.ini", "setup.cfg", "pyproject.toml")


class Repo:
    """Cached, read-only repository context used for contextual triage."""

    def __init__(self, root: Path, files: list[str]):
        self.root = root
        self.files = files
        self._source_cache = None
        self._declared_test_dirs = None
        self._source_scan_complete = True

    # -- path classification -------------------------------------------------
    def parts(self, name: str) -> tuple[str, ...]:
        return Path(name).parts

    def is_test_path(self, name: str) -> bool:
        p = self.parts(name)
        base = p[-1]
        if any(seg.lower() in TEST_DIR_NAMES for seg in p[:-1]):
            return True
        return base.startswith("test_") or base.endswith(("_test.py", "_test.ts", "_test.js")) or base == "conftest.py"

    def in_fixture_tree(self, name: str) -> bool:
        return any(seg.lower() in FIXTURE_DIR_NAMES for seg in self.parts(name)[:-1])

    def has_fixture_declaration(self, name: str) -> bool:
        """True when an ancestor directory within the repo declares a test/fixture setup."""
        if self._declared_test_dirs is None:
            self._declared_test_dirs = set()
            for f in self.files:
                p = self.parts(f)
                for i in range(1, len(p)):
                    if p[i - 1].lower() in TEST_DIR_NAMES:
                        self._declared_test_dirs.add("/".join(p[:i]))
        cur = self.parts(name)[:-1]
        for i in range(len(cur), 0, -1):
            prefix = "/".join(cur[:i])
            if prefix not in self._declared_test_dirs:
                continue
            for hint in GENERATED_HINT:
                try:
                    if relative_file(self.root, prefix + "/" + hint).is_file():
                        return True
                except (OSError, ValueError, UnicodeError):
                    continue
        return False

    def production_references(self, name: str) -> list[str]:
        """Tracked non-test source files that mention this artifact's basename."""
        if self._source_cache is None:
            self._source_cache = {}
            source_bytes = 0
            for f in self.files:
                if self.is_test_path(f) or not (Path(f).suffix.lower() in SOURCE_EXT or
                                               Path(f).name in {"Dockerfile", "Containerfile", "Makefile"} or
                                               Path(f).name.startswith(("Dockerfile.", "Containerfile."))):
                    continue
                try:
                    # Never traverse a tracked symlink or symlinked ancestor.
                    path = relative_file(self.root, f)
                    # Tracked source files may be replaced by a FIFO or socket.
                    # Reject non-regular inputs instead of blocking in read_bytes().
                    if not path.is_file():
                        self._source_scan_complete = False
                        continue
                    size = path.stat().st_size
                    if size > MAX_FILE_BYTES or source_bytes + size > MAX_TOTAL_BYTES:
                        self._source_scan_complete = False
                        continue
                    blob = path.read_bytes()
                except (ValueError, OSError, UnicodeError):
                    self._source_scan_complete = False
                    continue
                if len(blob) > MAX_FILE_BYTES or b"\0" in blob:
                    self._source_scan_complete = False
                    continue
                source_bytes += len(blob)
                self._source_cache[f] = blob
        base = Path(name).name.encode("utf-8", "surrogateescape")
        return [f for f, blob in self._source_cache.items() if base in blob]

    # -- certificate identity ------------------------------------------------
    def cert_subject(self, path: Path) -> dict | None:
        """Parse a PEM certificate subject. Returns None when unreadable.

        Deliberately optional: if `cryptography` is absent the caller keeps the
        finding actionable (fail closed) rather than assuming a fixture.
        """
        try:
            from cryptography import x509
        except Exception:
            return None
        try:
            safe_path = relative_file(self.root, str(path.relative_to(self.root)))
            if safe_path.stat().st_size > MAX_FILE_BYTES:
                return None
            blob = safe_path.read_bytes()
            # A bundle containing private material must not be excused by a
            # neighbouring/embedded test certificate identity.
            if b"PRIVATE KEY-----" in blob or not blob.lstrip().startswith(b"-----BEGIN CERTIFICATE-----"):
                return None
            cert = x509.load_pem_x509_certificate(blob)
        except Exception:
            return None
        out = {}
        for attr in cert.subject:
            try:
                out[attr.oid._name] = str(attr.value)
            except Exception:
                continue
        return out or None


def _test_identity(subject: dict | None) -> bool:
    if not subject:
        return False
    # Match complete subject tokens, never substrings ("latest" != "test").
    # Project names and real organisations are not proof of test identity.
    tokens = set()
    for value in subject.values():
        tokens.update(token for token in re.split(r"[\s.,_/-]+", str(value).casefold()) if token)
    return bool(tokens & TEST_IDENTITY_TOKENS)


def _expected_failure_context(lines: list[str], lineno: int, rule: str) -> tuple[str | None, bool]:
    """Associate TLS findings only with an enclosing SSL-error assertion.

    A pytest.raises elsewhere in the function is NOT evidence of a negative
    TLS test. Parsing failures remain actionable (fail-closed).
    """
    try:
        tree = ast.parse("\n".join(lines))
    except (SyntaxError, RecursionError, MemoryError, ValueError):
        return None, False
    function = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.lineno <= lineno <= node.end_lineno:
            if function is None or node.lineno >= function.lineno:
                function = node
    if function is None:
        return None, False
    if rule != "TLS-VERIFY-DISABLED":
        return function.name, False
    for node in ast.walk(function):
        if not isinstance(node, (ast.With, ast.AsyncWith)) or not node.body:
            continue
        # The flagged line must actually be inside the with block, not merely
        # in the same test function as an unrelated raises() assertion.
        if not node.body[0].lineno <= lineno <= node.body[-1].end_lineno:
            continue
        for item in node.items:
            call = item.context_expr
            if not isinstance(call, ast.Call) or not call.args:
                continue
            callee = ast.unparse(call.func)
            if not (callee == "pytest.raises" or callee.endswith(".assertRaises") or callee == "assertRaises"):
                continue
            exception_name = ast.unparse(call.args[0])
            if exception_name.endswith("SSLError"):
                return function.name, True
    return function.name, False


# -- deprecated: order preserved for legacy mode ------------------------------
def relative_file(root: Path, raw: str) -> Path:
    rel = Path(raw)
    if not raw or rel.is_absolute() or ".." in rel.parts or raw.startswith("-") or any(ord(c) < 32 for c in raw):
        raise ValueError("Unsafe tracked path")
    cursor = root
    for part in rel.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("Symlinked tracked path blocked")
    path = cursor.resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Tracked path escapes repository")
    return path


def symlink_state(root: Path, raw: str) -> dict:
    """Resolve a tracked symlink WITHOUT reading through it and compare to repo root."""
    link = root / raw
    try:
        target_text = os.readlink(link)
    except OSError as exc:
        return {"state": "UNRESOLVABLE", "target": None, "detail": str(exc)}
    resolved = Path(os.path.realpath(link))
    rootr = Path(os.path.realpath(root))
    inside = resolved.is_relative_to(rootr) if hasattr(resolved, "is_relative_to") else str(resolved).startswith(str(rootr))
    return {"state": "INTERNAL" if inside else "ESCAPE", "target": str(resolved), "link_target": target_text}


def tracked(root: Path) -> list[str]:
    try:
        # Git index reads can invoke core.fsmonitor from local Git config.
        # Override it, disable optional locks and drop inherited GIT_* overrides.
        env = {key: os.environ[key] for key in ("PATH", "HOME", "SYSTEMROOT", "WINDIR", "TMPDIR", "LANG")
               if key in os.environ}
        env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"})
        proc = subprocess.run(
            ["git", "--no-optional-locks", "-c", "core.fsmonitor=false",
             "-c", "core.hooksPath=" + os.devnull, "-C", str(root),
             "ls-files", "-z", "--cached"],
            capture_output=True, timeout=15, check=False, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Cannot enumerate tracked files") from exc
    if proc.returncode:
        raise ValueError("Target is not a readable Git repository")
    names = proc.stdout.decode("utf-8", errors="surrogateescape").split("\0")
    return [n for n in names if n]


def _finding(code, severity, name, line, advice, classification, confidence, reason):
    return {"id": code, "severity": severity, "path": name, "line": line, "advice": advice,
            "classification": classification, "confidence": confidence, "suppression_reason": reason}


def triage_key_material(repo: Repo, name: str) -> dict:
    """Classify a tracked key/certificate artifact. Escalates anything that looks real."""
    path = repo.root / name
    suffix = path.suffix.lower()
    base_advice = "Review whether tracked key or certificate material is private; never expose its contents"

    if suffix in CONTAINER_EXT:
        return _finding("TRACKED-KEY-MATERIAL", "high", name, None, base_advice,
                        "CONFIRMED", "high",
                        None) | {"advice": base_advice + " (encrypted container: contents not inspected)"}

    production = repo.production_references(name)
    source_complete = repo._source_scan_complete
    # Never infer the safety of a private key from a neighbouring certificate.
    # Preserve external-reference evidence without reading private-key bytes.
    if suffix == ".key":
        advice = base_advice
        if production:
            advice += "; referenced from non-test source"
        elif not source_complete:
            advice += "; production reference scan incomplete"
        return _finding("TRACKED-KEY-MATERIAL", "high", name, None, advice,
                        "CONFIRMED", "high" if source_complete else "low", None)
    subject = repo.cert_subject(path)
    if suffix in {".pem", ".crt", ".cer"} and subject is None:
        return _finding("TRACKED-KEY-MATERIAL", "high", name, None, base_advice,
                        "CONFIRMED", "medium", None)

    identity_ok = _test_identity(subject)

    signals = {
        "test_path": repo.is_test_path(name),
        "fixture_tree": repo.in_fixture_tree(name),
        "fixture_declaration": repo.has_fixture_declaration(name),
        "test_identity": identity_ok,
        "no_production_reference": not production and source_complete,
    }
    if production:
        return _finding("TRACKED-KEY-MATERIAL", "high", name, None,
                        base_advice + "; referenced from non-test source",
                        "CONFIRMED", "high", None)
    if not suffix == ".key" and subject is not None and not _test_identity(subject):
        org = subject.get("organizationName") or subject.get("commonName") or "unknown"
        return _finding("TRACKED-KEY-MATERIAL", "high", name, None,
                        base_advice + f"; certificate identity {org!r} is not a known test identity",
                        "CONFIRMED", "high", None)
    if not source_complete:
        return _finding("TRACKED-KEY-MATERIAL", "high", name, None, base_advice + "; production reference scan incomplete",
                        "CONFIRMED", "low", None)
    if signals["test_path"] and signals["fixture_tree"] and signals["test_identity"] and signals["no_production_reference"]:
        conf = "high" if signals["fixture_declaration"] else "medium"
        reason = ("declared test fixture: test path, fixture directory, certificate/paired-key declares a "
                  "test identity, no non-test source references it")
        return _finding("TRACKED-KEY-MATERIAL", "high", name, None, base_advice,
                        "TEST_FIXTURE_LIKELY_INTENTIONAL", conf, reason)
    if signals["test_path"] and signals["test_identity"] and signals["no_production_reference"]:
        return _finding("TRACKED-KEY-MATERIAL", "high", name, None, base_advice,
                        "TEST_FIXTURE_UNCONFIRMED_DIRECTORY", "low",
                        "test path and test certificate identity, but no declared fixture directory; "
                        "kept actionable pending human confirmation")
    return _finding("TRACKED-KEY-MATERIAL", "high", name, None, base_advice,
                    "CONFIRMED", "medium", None)


def inspect(root: Path, files: list[str], triage: bool = True) -> dict:
    root = root.resolve()
    if not root.is_dir() or len(files) > MAX_FILES:
        raise ValueError("Invalid repository or too many tracked paths")
    repo = Repo(root, files)
    findings = []
    consumed = 0
    seen = set()
    skipped = []
    for name in sorted(files):
        if name in seen:
            continue
        seen.add(name)
        entry = root / name
        if entry.is_symlink():
            if not triage:
                findings.append(_finding("SKIPPED-UNSAFE-PATH", "medium", name, None,
                                         "Tracked path could not be inspected safely; review independently",
                                         "LEGACY", "medium", "legacy mode: symlinks are not triaged"))
            else:
                state = symlink_state(root, name)
                if state["state"] == "ESCAPE":
                    findings.append(_finding("SYMLINK-ESCAPE", "high", name, None,
                                             "Tracked symlink resolves outside the repository; do not follow it",
                                             "CONFIRMED", "high", None) | {"target": state["target"]})
                elif state["state"] == "INTERNAL":
                    # Internal links may point to unscanned text assets.
                    # Never infer credential safety from repository containment.
                    # The tracked link may have a benign name while its
                    # resolved in-repository target is an untracked .env/key.
                    # Check path metadata only: never open the destination.
                    link_candidates = (Path(name), Path(state["target"]))
                    is_env = any(p.name.startswith(".env") and
                                 p.name not in {".env.example", ".env.sample", ".env.template"}
                                 for p in link_candidates)
                    is_key = any(p.suffix.lower() in (KEY_EXT | CONTAINER_EXT)
                                 for p in link_candidates)
                    if is_env or is_key:
                        findings.append(_finding(
                            "TRACKED-ENV" if is_env else "TRACKED-KEY-MATERIAL",
                            "high", name, None,
                            "Tracked credential-like symlink; review the target without following the link",
                            "CONFIRMED", "high", None) | {"target": state["target"]})
                    else:
                        # A benign filename is not evidence of benign content.
                        # In particular the resolved target may be untracked and
                        # outside the configured source extensions. Never read
                        # through the link; require review instead of exit 0.
                        findings.append(_finding("SYMLINK-INTERNAL", "medium", name, None,
                                                 "Internal symlink target was not inspected; review required before approval",
                                                 "CONFIRMED", "medium", None) | {"target": state["target"]})
                else:
                    findings.append(_finding("SYMLINK-UNRESOLVABLE", "medium", name, None,
                                             "Tracked symlink could not be resolved; review independently",
                                             "CONFIRMED", "low", None))
            if len(findings) >= MAX_FINDINGS:
                return report(findings, len(seen), consumed, truncated=True, triage=triage)
            continue
        try:
            path = relative_file(root, name)
        except (ValueError, OSError, UnicodeError):
            findings.append(_finding("SKIPPED-UNSAFE-PATH", "medium",
                                     name.encode("unicode_escape").decode("ascii"), None,
                                     "Tracked path could not be inspected safely; review independently",
                                     "CONFIRMED", "low", None))
            if len(findings) >= MAX_FINDINGS:
                return report(findings, len(seen), consumed, truncated=True, triage=triage)
            continue
        if not path.is_file():
            if path.is_dir():
                # A tracked gitlink is a separate repository boundary, not a
                # missing source file. Do not recurse into it.
                continue
            # Gitlink/submodule directories and unscanned README/media paths
            # are not configured source inspections. Missing configured inputs
            # still block a clean result.
            if path.suffix.lower() in (SOURCE_EXT | KEY_EXT | CONTAINER_EXT) or path.name.startswith(".env"):
                skipped.append({"path": name, "reason": "Tracked configured path missing or not a regular file"})
            continue
        if path.name.startswith(".env") and path.name not in {".env.example", ".env.sample", ".env.template"}:
            findings.append(_finding("TRACKED-ENV", "high", name, None,
                                     "A tracked environment file may disclose credentials; inspect privately and rotate exposed values",
                                     "CONFIRMED", "high", None))
            continue
        if path.suffix.lower() in (KEY_EXT | CONTAINER_EXT):
            findings.append(triage_key_material(repo, name) if triage else
                            _finding("TRACKED-KEY-MATERIAL", "high", name, None,
                                     "Review whether tracked key or certificate material is private; never expose its contents",
                                     "LEGACY", "medium", "legacy mode: no contextual triage"))
            continue
        if path.suffix.lower() not in SOURCE_EXT:
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            skipped.append({"path": name, "reason": "Source file exceeds per-file inspection budget"})
            continue
        blob = path.read_bytes()
        consumed += len(blob)
        if consumed > MAX_TOTAL_BYTES:
            raise ValueError("Source scan byte budget exceeded")
        if b"\0" in blob:
            skipped.append({"path": name, "reason": "Source file contains NUL bytes"})
            continue
        try:
            body = blob.decode("utf-8")
        except UnicodeDecodeError:
            skipped.append({"path": name, "reason": "Source file is not UTF-8"})
            continue
        # Match Python tokenizer's physical-line boundaries (CRLF, CR, LF).
        # str.splitlines() also splits on form feeds and Unicode separators,
        # shifting AST lineno values and corrupting rule classification.
        lines = re.split(r"\r\n|\r|\n", body)
        # Detect Python TLS bypasses spanning physical lines. The original
        # per-line rule remains for other languages and ordinary occurrences.
        # AST supplies correct source positions and ignores strings/comments.
        if path.suffix.lower() == ".py":
            try:
                syntax = ast.parse(body)
            except SyntaxError:
                syntax = None
            except (RecursionError, MemoryError, ValueError):
                skipped.append({"path": name, "reason": "Python source too complex to parse for TLS checks"})
                continue
            if syntax is not None:
                for node in ast.walk(syntax):
                    if not isinstance(node, ast.Call):
                        continue
                    for kw in node.keywords:
                        if kw.arg != "verify" or not isinstance(kw.value, ast.Constant) or kw.value.value is not False:
                            continue
                        number = kw.value.lineno
                        if number == kw.value.end_lineno and RULES[0][2].search(lines[number - 1]):
                            continue
                        classification, confidence, reason = "CONFIRMED", "high", None
                        if triage and repo.is_test_path(name):
                            fname, expected = _expected_failure_context(lines, number, "TLS-VERIFY-DISABLED")
                            if expected and fname:
                                classification, confidence = "EXPECTED_NEGATIVE_TEST", "high"
                                reason = f"test file; enclosing test {fname}() asserts an expected exception"
                            elif fname:
                                classification, confidence = "TEST_CONTEXT_UNPROVEN", "low"
                                reason = f"test file and enclosing test {fname}(), but no expected-failure assertion found"
                        findings.append(_finding("TLS-VERIFY-DISABLED", "high", name, number,
                                                "Review TLS certificate verification; this may permit interception",
                                                classification, confidence, reason))
                        if len(findings) >= MAX_FINDINGS:
                            return report(findings, len(seen), consumed, truncated=True, triage=triage)
        for number, line in enumerate(lines, 1):
            # Credentials are actionable anywhere, including inside tests.
            for code, pattern, severity in LIVE_CREDENTIAL:
                if pattern.search(line):
                    findings.append(_finding(code, severity, name, number,
                                             "Credential-shaped literal in tracked source; verify whether it is live and rotate if so",
                                             "CONFIRMED", "high", None))
                    if len(findings) >= MAX_FINDINGS:
                        return report(findings, len(seen), consumed, truncated=True, triage=triage)
            for code, severity, pattern, advice in RULES:
                if not pattern.search(line):
                    continue
                classification, confidence, reason = "CONFIRMED", "medium", None
                if triage and repo.is_test_path(name):
                    fname, expected = _expected_failure_context(lines, number, code)
                    if expected and fname:
                        classification = "EXPECTED_NEGATIVE_TEST"
                        confidence = "high"
                        reason = f"test file; enclosing test {fname}() asserts an expected exception"
                    elif fname:
                        classification = "TEST_CONTEXT_UNPROVEN"
                        confidence = "low"
                        reason = f"test file and enclosing test {fname}(), but no expected-failure assertion found"
                elif triage and not repo.is_test_path(name):
                    classification = "CONFIRMED"
                    confidence = "high"
                findings.append(_finding(code, severity, name, number, advice,
                                         classification, confidence, reason))
                if len(findings) >= MAX_FINDINGS:
                    return report(findings, len(seen), consumed, truncated=True, triage=triage)
    return report(findings, len(seen), consumed, truncated=False, triage=triage, skipped=skipped)


def report(findings: list[dict], inspected: int, byte_count: int, truncated: bool,
           triage: bool = True, skipped: list[dict] | None = None) -> dict:
    skipped = skipped or []
    # Tracked key/certificate material is never silently suppressed on
    # heuristic fixture evidence. The classification is advisory only.
    actionable = [f for f in findings if f["id"] == "TRACKED-KEY-MATERIAL" or
                  f["classification"] in {"CONFIRMED", "TEST_CONTEXT_UNPROVEN", "LEGACY",
                                          "TEST_FIXTURE_UNCONFIRMED_DIRECTORY"}]
    suppressed = [f for f in findings if f not in actionable]
    if truncated or skipped:
        status = "INCOMPLETE_SCAN"
    elif not findings:
        status = "CLEAR_HEURISTICS_ONLY"
    elif actionable:
        status = "WARNINGS_FOUND"
    else:
        status = "REVIEWED_NO_ACTIONABLE_FINDINGS"
    return {"schema_version": 2 if triage else 1, "status": status,
            "risk_boundary": "Heuristic tracked-source inspection only; not a vulnerability scan, safety proof or approval",
            "triage_mode": "contextual" if triage else "signature-only",
            "inspected_paths": inspected, "inspected_source_bytes": byte_count,
            "truncated": truncated,
            "incomplete": bool(truncated or skipped), "skipped_paths": skipped,
            "summary": {"total": len(findings), "actionable": len(actionable),
                        "suppressed_with_reason": len(suppressed),
                        "by_classification": {c: sum(1 for f in findings if f["classification"] == c)
                                              for c in sorted({f["classification"] for f in findings})}},
            "findings": findings}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--output")
    parser.add_argument("--no-triage", action="store_true",
                        help="Reproduce legacy signature-only behaviour for baseline comparison")
    args = parser.parse_args(argv)
    try:
        root = Path(args.repo)
        if root.is_symlink() or not root.is_dir():
            raise ValueError("Repository path must be a directory, not symlink")
        result = inspect(root, tracked(root.resolve()), triage=not args.no_triage)
        content = json.dumps(result, indent=2) + "\n"
        if args.output:
            output = Path(args.output)
            if output.is_symlink():
                raise ValueError("Symlinked output rejected")
            with output.open("x", encoding="utf-8") as stream:
                stream.write(content)
        print(content, end="")
        if result["incomplete"]:
            return 2  # Never pass an incomplete scan, even when every seen item was benign.
        return 1 if result["summary"]["actionable"] else 0
    except (ValueError, OSError, UnicodeError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())