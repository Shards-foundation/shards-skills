"""Independent adversarial regressions for read-only guard gating."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest
import tempfile

GUARD = Path(__file__).resolve().parents[1] / 'scripts' / 'vibecode_guard.py'


def make_repo(tmp_path, files, links=None):
    repo = tmp_path / 'repo'
    repo.mkdir()
    subprocess.run(['git', '-C', str(repo), 'init', '-q'], check=True)
    for name, body in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    for name, target in (links or {}).items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(target)
    subprocess.run(['git', '-C', str(repo), 'add', '-A'], check=True)
    return repo


def scan(repo, *args):
    p = subprocess.run([sys.executable, str(GUARD), '--repo', str(repo), *args], capture_output=True, text=True)
    return p.returncode, json.loads(p.stdout or p.stderr)


def test_finding_limit_is_not_a_clean_pass(tmp_path):
    repo = make_repo(tmp_path, {
        'a/target.txt': 'fixture',
        'z/insecure.py': 'import requests\nrequests.get("https://x", verify=False)\n',
    }, {f'a/x{i:03}.link': 'target.txt' for i in range(200)})
    rc, report = scan(repo)
    assert report['truncated']
    assert report['status'] == 'INCOMPLETE_SCAN'
    assert rc == 2  # Incomplete inspection cannot approve a repository.


def test_saturation_preserves_no_triage_metadata(tmp_path):
    repo = make_repo(tmp_path, {'a/target.txt': 'fixture'},
                     {f'a/x{i:03}.link': 'target.txt' for i in range(200)})
    rc, report = scan(repo, '--no-triage')
    assert report['schema_version'] == 1
    assert report['triage_mode'] == 'signature-only'
    assert report['truncated'] and rc == 2


def test_unrelated_exception_does_not_suppress_tls_warning(tmp_path):
    repo = make_repo(tmp_path, {'tests/test_app.py': '''import pytest, requests

def test_request():
    with pytest.raises(ValueError):
        raise ValueError('fine')
    requests.get('https://x', verify=False)
'''})
    rc, report = scan(repo)
    assert rc == 1
    tls = next(f for f in report['findings'] if f['id'] == 'TLS-VERIFY-DISABLED')
    assert tls['classification'] == 'TEST_CONTEXT_UNPROVEN'
    assert report['summary']['actionable'] == 1


def test_expected_ssl_failure_requires_line_in_raises_body(tmp_path):
    repo = make_repo(tmp_path, {'tests/test_app.py': '''import pytest, requests

def test_request():
    with pytest.raises(requests.exceptions.SSLError):
        requests.get('https://invalid', verify=False)
'''})
    rc, report = scan(repo)
    assert rc == 0
    tls = next(f for f in report['findings'] if f['id'] == 'TLS-VERIFY-DISABLED')
    assert tls['classification'] == 'EXPECTED_NEGATIVE_TEST'


def test_tracked_source_symlink_does_not_read_outside_repo(tmp_path):
    repo = make_repo(tmp_path, {'tests/certs/server.key': 'not a private key'},
                     {'src/external.py': '../../outside.py'})
    outside = tmp_path / 'outside.py'
    outside.write_text('# server.key is mentioned in an external file\n')
    rc, report = scan(repo)
    f = next(f for f in report['findings'] if f['id'] == 'TRACKED-KEY-MATERIAL')
    assert 'referenced from non-test source' not in f['advice']
    assert 'production reference scan incomplete' in f['advice']
    assert any(x['id'] == 'SYMLINK-ESCAPE' for x in report['findings'])
    outside.write_text('# no longer mentioned\n')
    _, again = scan(repo)
    f2 = next(f for f in again['findings'] if f['id'] == 'TRACKED-KEY-MATERIAL')
    assert f2['advice'] == f['advice']


def test_symlinked_sibling_certificate_cannot_be_read(tmp_path):
    repo = make_repo(tmp_path, {'tests/certs/server.key': 'KEY'},
                     {'tests/certs/server.pem': '../../../outside.pem'})
    (tmp_path/'outside.pem').write_text('-----BEGIN CERTIFICATE-----\nnot-certificate\n-----END CERTIFICATE-----\n')
    rc, report = scan(repo)
    assert rc == 1
    key = next(f for f in report['findings'] if f['id'] == 'TRACKED-KEY-MATERIAL')
    assert key['classification'] == 'CONFIRMED'
    assert any(f['id'] == 'SYMLINK-ESCAPE' for f in report['findings'])


def test_oversized_source_blocks_clean_gate(tmp_path):
    repo = make_repo(tmp_path, {'src/oversized.py': ' ' * 256_100 + '\nrequests.get("u", verify=False)\n'})
    rc, report = scan(repo)
    assert rc == 2
    assert report['status'] == 'INCOMPLETE_SCAN'
    assert report['skipped_paths'][0]['path'] == 'src/oversized.py'


def test_missing_indexed_source_blocks_clean_gate(tmp_path):
    repo = make_repo(tmp_path, {'src/vanished.py': 'requests.get("u", verify=False)\n'})
    (repo / 'src/vanished.py').unlink()  # Still in the index, missing from worktree.
    rc, report = scan(repo)
    assert rc == 2
    assert report['status'] == 'INCOMPLETE_SCAN'
    assert report['skipped_paths'][0]['path'] == 'src/vanished.py'


def test_nested_handler_does_not_steal_parent_test_context(tmp_path):
    # Matches the structural pattern of psf/requests' TLS pool regression tests:
    # verify=False request succeeds before a *different* SSL-error assertion.
    repo = make_repo(tmp_path, {'tests/test_requests.py': '''import pytest, requests
class TestRequests:
    def test_tls_pool(self):
        def response_handler(sock):
            sock.send(b'data')
        r1 = requests.get('https://localhost', verify=False)
        assert r1.status_code == 200
        with pytest.raises(requests.exceptions.SSLError):
            requests.get('https://localhost')
'''})
    rc, report = scan(repo)
    assert rc == 1
    finding = next(f for f in report['findings'] if f['id'] == 'TLS-VERIFY-DISABLED')
    assert finding['classification'] == 'TEST_CONTEXT_UNPROVEN'
    assert 'test_tls_pool' in finding['suppression_reason']
    assert 'response_handler' not in finding['suppression_reason']


class VibeCodeGuardAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def test_finding_limit_is_not_a_clean_pass(self):
        test_finding_limit_is_not_a_clean_pass(Path(self.temp.name))

    def test_saturation_preserves_no_triage_metadata(self):
        test_saturation_preserves_no_triage_metadata(Path(self.temp.name))

    def test_unrelated_exception_does_not_suppress_tls_warning(self):
        test_unrelated_exception_does_not_suppress_tls_warning(Path(self.temp.name))

    def test_expected_ssl_failure_requires_line_in_raises_body(self):
        test_expected_ssl_failure_requires_line_in_raises_body(Path(self.temp.name))

    def test_tracked_source_symlink_does_not_read_outside_repo(self):
        test_tracked_source_symlink_does_not_read_outside_repo(Path(self.temp.name))

    def test_symlinked_sibling_certificate_cannot_be_read(self):
        test_symlinked_sibling_certificate_cannot_be_read(Path(self.temp.name))

    def test_oversized_source_blocks_clean_gate(self):
        test_oversized_source_blocks_clean_gate(Path(self.temp.name))

    def test_missing_indexed_source_blocks_clean_gate(self):
        test_missing_indexed_source_blocks_clean_gate(Path(self.temp.name))

    def test_nested_handler_does_not_steal_parent_test_context(self):
        test_nested_handler_does_not_steal_parent_test_context(Path(self.temp.name))
