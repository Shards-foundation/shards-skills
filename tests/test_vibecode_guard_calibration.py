"""Regression tests for the calibrated vibecode_guard (P0).

Three fixture families, no stubs and no monkeypatching of the tool's logic:
  A. the 13 findings from the real psf/requests run at 3c7baaa0
  B. the 5 seeded genuine defects + a real credential placed under tests/
  C. symlinks escaping the repository and symlinks staying inside it

The real-repository family runs against a real git clone when PSF_REQUESTS is set;
otherwise it is skipped explicitly (never silently passed).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import unittest
import tempfile

GUARD = Path(__file__).resolve().parents[1] / "scripts" / "vibecode_guard.py"
PSF = os.environ.get("PSF_REQUESTS")


def run_guard(repo: Path, *extra: str) -> tuple[int, dict | None, str]:
    proc = subprocess.run([sys.executable, str(GUARD), "--repo", str(repo), *extra],
                          capture_output=True, text=True)
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else None
    except json.JSONDecodeError:
        payload = None
    return proc.returncode, payload, proc.stderr


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                   check=True, capture_output=True)


def make_repo(root: Path, files: dict[str, str], links: dict[str, str] | None = None,
              outside: dict[str, str] | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q")
    for name, body in files.items():
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    if links:
        for name, target in links.items():
            p = root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(target, p)
    if outside:
        # Files placed OUTSIDE the repository, reachable only via escaping symlinks.
        for name, body in outside.items():
            p = root.parent / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body)
    git(root, "add", "-A")
    git(root, "commit", "-qm", "seed", "--allow-empty")
    return root


def by_path(payload: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for f in payload["findings"]:
        out.setdefault(f["path"], []).append(f)
    return out


# --------------------------------------------------------------------------
# Family A — the 13 reviewed real-world findings (7 key material, 2 symlinks, 4 TLS)
# --------------------------------------------------------------------------
EXPECTED_REAL = {
    "tests/certs/expired/ca/ca-private.key": ("TRACKED-KEY-MATERIAL", "CONFIRMED"),
    "tests/certs/expired/server/server.key": ("TRACKED-KEY-MATERIAL", "CONFIRMED"),
    "tests/certs/expired/server/server.pem": ("TRACKED-KEY-MATERIAL", "TEST_FIXTURE_LIKELY_INTENTIONAL"),
    "tests/certs/mtls/client/client.key": ("TRACKED-KEY-MATERIAL", "CONFIRMED"),
    "tests/certs/mtls/client/client.pem": ("TRACKED-KEY-MATERIAL", "TEST_FIXTURE_LIKELY_INTENTIONAL"),
    "tests/certs/valid/server/server.key": ("TRACKED-KEY-MATERIAL", "CONFIRMED"),
    "tests/certs/valid/server/server.pem": ("TRACKED-KEY-MATERIAL", "TEST_FIXTURE_LIKELY_INTENTIONAL"),
    "tests/certs/mtls/client/ca": ("SYMLINK-INTERNAL", "CONFIRMED"),
    "tests/certs/valid/ca": ("SYMLINK-INTERNAL", "CONFIRMED"),
}


def test_real_repository_findings_are_classified(tmp_path):
    code, payload, err = run_guard(Path(PSF))
    assert payload is not None, err
    assert payload["schema_version"] == 2
    assert payload["summary"]["total"] == 13, payload["summary"]
    got = by_path(payload)
    for path, (want_id, want_class) in EXPECTED_REAL.items():
        assert path in got, f"missing finding for {path}"
        f = got[path][0]
        assert f["id"] == want_id, f"{path}: {f['id']} != {want_id}"
        if want_id == "TRACKED-KEY-MATERIAL" and path.endswith(".pem"):
            assert f["classification"] in {"CONFIRMED", "TEST_FIXTURE_LIKELY_INTENTIONAL",
                                           "TEST_FIXTURE_UNCONFIRMED_DIRECTORY"}, f
        else:
            assert f["classification"] == want_class, f"{path}: {f['classification']}"
        if f["classification"] not in {"CONFIRMED", "LEGACY"}:
            assert f["suppression_reason"], f"{path}: classified without a reason"
    tls = [f for f in payload["findings"] if f["id"] == "TLS-VERIFY-DISABLED"]
    assert len(tls) == 4
    assert {f["line"] for f in tls} == {2949, 2982, 3015, 3055}
    # All four verify=False calls are on *successful* pool test requests,
    # outside the later `with pytest.raises(SSLError)` sections. The older
    # function-wide heuristic misattributed unrelated exception checks to them.
    # They must remain actionable for review, even if the eventual human
    # decision is that the integration test legitimately needs verify=False.
    for f in tls:
        assert f["classification"] == "TEST_CONTEXT_UNPROVEN", f
        assert f["confidence"] == "low"
        assert "no expected-failure assertion" in f["suppression_reason"]
    # 2 symlinks + 7 key material + 4 TLS is the whole set
    assert sum(f["id"] == "SYMLINK-INTERNAL" and f["classification"] == "CONFIRMED" for f in payload["findings"]) == 2
    assert payload["summary"]["by_classification"]["TEST_CONTEXT_UNPROVEN"] == 4
    # Seven tracked key/certificate files require review, including likely fixtures.
    assert payload["summary"]["actionable"] == 13
    assert code == 1


def test_legacy_mode_still_reports_all_13(tmp_path):
    """Triage must never reduce previously emitted findings, only annotate them."""
    code, payload, err = run_guard(Path(PSF), "--no-triage")
    assert payload is not None, err
    assert payload["triage_mode"] == "signature-only"
    assert payload["summary"]["total"] == 13
    assert payload["summary"]["actionable"] == 13
    assert code == 1


# --------------------------------------------------------------------------
# Family B — the 5 seeded genuine defects + a real credential under tests/
# --------------------------------------------------------------------------
def test_seeded_defects_and_credential_under_tests(tmp_path):
    repo = make_repo(tmp_path / "r", {
        "src/a.py": 'import requests\nrequests.get("https://x", verify=False)\n',
        "src/b.py": 'import yaml\nyaml.load(open("f"), Loader=yaml.Loader)\n',
        ".github/workflows/ci.yml": "permissions: write-all\non: [push]\njobs:\n  x:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n",
        "src/c.py": "app = eval(input())\n",
        "src/d.py": 'allow_origins = ["*"]\n',
        # A credential-shaped literal placed where a path-based suppression would hide it.
        "tests/test_leaked.py": 'TOKEN = "AKIAIOSFODNN7EXAMPLE"\n\ndef test_x():\n    assert True\n',
    })
    code, payload, err = run_guard(repo)
    assert payload is not None, err
    got = by_path(payload)
    for path, want in [("src/a.py", "TLS-VERIFY-DISABLED"), ("src/b.py", "WEAK-YAML-LOADER"),
                       (".github/workflows/ci.yml", "CI-WRITE-ALL"), ("src/c.py", "DYNAMIC-EVAL"),
                       ("src/d.py", "POTENTIAL-PUBLIC-CORS")]:
        assert path in got, f"missed seeded defect in {path}"
        f = got[path][0]
        assert f["id"] == want
        assert f["classification"] == "CONFIRMED"
        assert f["confidence"] == "high"
        assert f["suppression_reason"] is None
    cred = got["tests/test_leaked.py"][0]
    assert cred["id"] == "AWS-ACCESS-KEY-ID", cred
    assert cred["classification"] == "CONFIRMED"
    assert cred["severity"] == "high"
    assert payload["summary"]["actionable"] == 6
    assert code == 1


def test_private_key_block_under_tests_is_not_suppressed(tmp_path):
    repo = make_repo(tmp_path / "r", {
        "tests/fixtures/key.py": 'K = """-----BEGIN RSA PRIVATE KEY-----\nMIIE\n-----END RSA PRIVATE KEY-----"""\n',
    })
    code, payload, err = run_guard(repo)
    assert payload is not None, err
    f = payload["findings"][0]
    assert f["id"] == "PRIVATE-KEY-BLOCK"
    assert f["classification"] == "CONFIRMED"
    assert code == 1


def test_key_in_fixture_dir_but_referenced_by_production_stays_actionable(tmp_path):
    """A test-path certificate referenced from non-test source must never be suppressed."""
    repo = make_repo(tmp_path / "r", {
        "tests/certs/valid/server/server.key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADAN\n-----END PRIVATE KEY-----\n",
        "tests/certs/valid/server/server.pem": "-----BEGIN CERTIFICATE-----\nMIID\n-----END CERTIFICATE-----\n",
        "src/client.py": 'KEY = "tests/certs/valid/server/server.key"\n', 
    })
    code, payload, err = run_guard(repo)
    assert payload is not None, err
    got = by_path(payload)
    key = got["tests/certs/valid/server/server.key"][0]
    assert key["classification"] == "CONFIRMED", key
    assert "referenced from non-test source" in key["advice"]
    assert code == 1


def test_docs_only_reference_does_not_escalate_a_fixture(tmp_path):
    """Documentation prose is not production code; it must not force CONFIRMED."""
    repo = make_repo(tmp_path / "r", {
        "docs/advanced.rst": "Use tests/certs/valid/server/server.key with the bundle.\n",
        "tests/certs/valid/server/server.key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADAN\n-----END PRIVATE KEY-----\n",
        "tests/certs/valid/server/server.pem": "-----BEGIN CERTIFICATE-----\nMIID\n-----END CERTIFICATE-----\n",
    })
    code, payload, err = run_guard(repo)
    assert payload is not None, err
    key = by_path(payload)["tests/certs/valid/server/server.key"][0]
    assert "referenced from non-test source" not in key["advice"], key


def test_verify_false_in_test_without_expected_failure_stays_actionable(tmp_path):
    repo = make_repo(tmp_path / "r", {
        "tests/test_app.py": "def test_thing():\n    requests.get('u', verify=False)\n",
    })
    code, payload, err = run_guard(repo)
    assert payload is not None, err
    f = payload["findings"][0]
    assert f["classification"] == "TEST_CONTEXT_UNPROVEN"
    assert f["confidence"] == "low"
    assert code == 1


# --------------------------------------------------------------------------
# Family C — symlink escape vs internal
# --------------------------------------------------------------------------
def test_symlink_escape_is_high_severity(tmp_path):
    repo = make_repo(
        tmp_path / "r",
        {"src/a.py": "print(1)\n"},
        links={"src/leak.txt": "../../outside/secret.txt"},
        outside={"outside/secret.txt": "prod-password\n"},
    )
    code, payload, err = run_guard(repo)
    assert payload is not None, err
    f = by_path(payload)["src/leak.txt"][0]
    assert f["id"] == "SYMLINK-ESCAPE"
    assert f["severity"] == "high"
    assert f["classification"] == "CONFIRMED"
    assert "outside the repository" in f["advice"]
    assert code == 1


def test_symlink_internal_requires_review(tmp_path):
    repo = make_repo(
        tmp_path / "r",
        {"tests/certs/expired/ca/ca.pem": "-----BEGIN CERTIFICATE-----\nMIID\n-----END CERTIFICATE-----\n"},
        links={"tests/certs/valid/ca": "../expired/ca"},
    )
    code, payload, err = run_guard(repo)
    assert payload is not None, err
    f = by_path(payload)["tests/certs/valid/ca"][0]
    assert f["id"] == "SYMLINK-INTERNAL"
    assert f["severity"] == "medium"
    assert f["classification"] == "CONFIRMED"
    assert f["target"].endswith("expired/ca")
    assert code == 1
    assert payload["summary"]["actionable"] >= 1


def test_symlinked_content_is_never_read(tmp_path):
    """The escaping target's contents must not appear anywhere in the output."""
    repo = make_repo(
        tmp_path / "r",
        {"src/a.py": "print(1)\n"},
        links={"src/leak.txt": "../../outside/secret.txt"},
        outside={"outside/secret.txt": "PRODUCTION-ONLY-SECRET-VALUE\n"},
    )
    _, payload, err = run_guard(repo)
    assert payload is not None, err
    assert "PRODUCTION-ONLY-SECRET-VALUE" not in json.dumps(payload)


# --------------------------------------------------------------------------
# Fail-closed behaviour
# --------------------------------------------------------------------------
def test_non_git_directory_is_blocked(tmp_path):
    d = tmp_path / "plain"
    d.mkdir()
    (d / "f.txt").write_text("x")
    proc = subprocess.run([sys.executable, str(GUARD), "--repo", str(d)],
                          capture_output=True, text=True)
    assert proc.returncode == 2
    assert json.loads(proc.stderr)["status"] == "BLOCKED"


def test_clean_repository_is_clear(tmp_path):
    repo = make_repo(tmp_path / "r", {"src/a.py": "print('hello')\n"})
    code, payload, err = run_guard(repo)
    assert payload is not None, err
    assert payload["status"] == "CLEAR_HEURISTICS_ONLY"
    assert code == 0


class VibeCodeGuardCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    @unittest.skipUnless(PSF and Path(PSF).is_dir(), "PSF_REQUESTS checkout unavailable")
    def test_real_repository_findings_are_classified(self):
        test_real_repository_findings_are_classified(Path(self.temp.name))

    @unittest.skipUnless(PSF and Path(PSF).is_dir(), "PSF_REQUESTS checkout unavailable")
    def test_legacy_mode_still_reports_all_13(self):
        test_legacy_mode_still_reports_all_13(Path(self.temp.name))

    def test_seeded_defects_and_credential_under_tests(self):
        test_seeded_defects_and_credential_under_tests(Path(self.temp.name))

    def test_private_key_block_under_tests_is_not_suppressed(self):
        test_private_key_block_under_tests_is_not_suppressed(Path(self.temp.name))

    def test_key_in_fixture_dir_but_referenced_by_production_stays_actionable(self):
        test_key_in_fixture_dir_but_referenced_by_production_stays_actionable(Path(self.temp.name))

    def test_docs_only_reference_does_not_escalate_a_fixture(self):
        test_docs_only_reference_does_not_escalate_a_fixture(Path(self.temp.name))

    def test_verify_false_in_test_without_expected_failure_stays_actionable(self):
        test_verify_false_in_test_without_expected_failure_stays_actionable(Path(self.temp.name))

    def test_symlink_escape_is_high_severity(self):
        test_symlink_escape_is_high_severity(Path(self.temp.name))

    def test_symlink_internal_requires_review(self):
        test_symlink_internal_requires_review(Path(self.temp.name))

    def test_symlinked_content_is_never_read(self):
        test_symlinked_content_is_never_read(Path(self.temp.name))

    def test_non_git_directory_is_blocked(self):
        test_non_git_directory_is_blocked(Path(self.temp.name))

    def test_clean_repository_is_clear(self):
        test_clean_repository_is_clear(Path(self.temp.name))
