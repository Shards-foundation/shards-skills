import copy
import hashlib
import json
import os
import runpy
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
VALIDATOR=ROOT/'.agents/skills/shards-native-agent-handoff/scripts/validate.py'
SAMPLE=ROOT/'fixtures/valid-multi-target.json'
MOD=runpy.run_path(str(VALIDATOR))
Invalid=MOD['Invalid']
parse_frontmatter = runpy.run_path(str(ROOT / 'scripts/validate_skills.py'))['parse_frontmatter']

def validate(checkpoint):
    return MOD['validate'](checkpoint, metadata={'extra_metadata'})

def command(source, output, *extra):
    return [sys.executable, str(VALIDATOR), '--input', str(source), '--output', str(output),
            '--confirm-sanitised', '--allow-metadata-field', 'extra_metadata', *extra]

def sample():
    return json.loads(SAMPLE.read_text())

class ShardsNativeRecovery(unittest.TestCase):
    def test_good_multirevision_and_lossless(self):
        s=sample(); v=validate(s)
        self.assertTrue(v['schema_valid'])
        self.assertFalse(v['external_evidence_verified'])
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp).resolve()/'result.json'
            r=subprocess.run(command(SAMPLE, out), capture_output=True, text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            raw = out.read_bytes()
            data=json.loads(raw)
            self.assertEqual(data['checkpoint'],s)
            self.assertEqual(data['checkpoint']['extra_metadata'],s['extra_metadata'])
            self.assertEqual(len(data['checkpoint']['targets']),2)
            text = raw.decode('utf-8').removeprefix('{"checkpoint":')
            _, end = json.JSONDecoder().raw_decode(text)
            checkpoint = text[:end].encode('utf-8')
            self.assertEqual(checkpoint, SAMPLE.read_bytes().strip())
            self.assertEqual(hashlib.sha256(checkpoint).hexdigest(), data['checkpoint_sha256'])
    def assert_cli_blocked(self, raw):
        """Malformed input must fail with exit 2 and never create an output."""
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'input.json'
            output = Path(tmp) / 'output.json'
            source.write_text(raw, encoding='utf-8')
            result = subprocess.run(
                command(source, output),
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn('BLOCKED:', result.stderr)
            self.assertNotIn('Traceback', result.stderr)
            self.assertFalse(output.exists())

    def test_missing_target_commit_sha_fails_closed(self):
        s = sample()
        del s['targets'][0]['commit_sha']
        with self.assertRaises(Invalid):
            validate(s)
        self.assert_cli_blocked(json.dumps(s))

    def test_missing_verified_subject_revision_sha_fails_closed(self):
        s = sample()
        e = s['evidence'][0]
        e['claim_level'] = 'INDEPENDENTLY_VERIFIED'
        e['locator'] = {
            'kind': 'github_commit',
            'value': 'https://github.com/Shards-foundation/shards-skills/commit/' + ('a' * 40),
        }
        del e['subject']['revision_sha']
        with self.assertRaises(Invalid):
            validate(s)
        self.assert_cli_blocked(json.dumps(s))

    def test_excessively_nested_json_fails_closed(self):
        self.assert_cli_blocked('[' * 1400 + '0' + ']' * 1400)

    def test_nested_metadata_depth_fails_closed(self):
        s = sample()
        value = 'end'
        for _ in range(130):
            value = {'layer': value}
        s['extra_metadata'] = value
        with self.assertRaises(Invalid):
            validate(s)

    def test_unhashable_enum_fails_closed(self):
        s = sample()
        s['next']['decision'] = []
        self.assert_cli_blocked(json.dumps(s))

    def test_nonfinite_metadata_fails_closed(self):
        record = sample()
        record['numeric_metadata'] = float('inf')
        with self.assertRaisesRegex(Invalid, 'nonfinite'):
            validate(record)
        self.assert_cli_blocked(json.dumps(record).replace('Infinity', '1e309'))

    def test_credential_shaped_metadata_key_is_rejected(self):
        record = sample()
        record['extra_metadata'] = {'ghp_' + 'X' * 28: 'synthetic'}
        with self.assertRaisesRegex(Invalid, 'invalid field name'):
            validate(record)

    def test_nested_credentials_and_authenticated_urls_fail_closed(self):
        for key in ('apiKey', 'access-token', 'privateKey', 'Authorization', 'X-Amz-Signature'):
            with self.subTest(key=key):
                record = sample()
                record['extra_metadata'] = {key: 'synthetic marker'}
                with self.assertRaisesRegex(Invalid, 'invalid field name'):
                    validate(record)
        for url in ('https://fixture-user:fixture-pass@example.invalid/receipt',
                    'https://example.invalid/r?X-Amz-%53ignature=fixture-marker'):
            with self.subTest(url=url):
                record = sample()
                record['evidence'][0]['locator'] = {'kind': 'local_artifact', 'value': url}
                self.assert_cli_blocked(json.dumps(record))

    def test_requires_sanitisation_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp).resolve() / 'receipt.json'
            argv = command(SAMPLE, out)
            argv.remove('--confirm-sanitised')
            result = subprocess.run(argv, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(out.exists())

    def test_symlinked_output_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            target = root / 'target'
            target.mkdir()
            link = root / 'alias'
            link.symlink_to(target, target_is_directory=True)
            result = subprocess.run(command(SAMPLE, link / 'receipt.json'),
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(list(target.iterdir()), [])

    def test_invalid_commit_rejected(self):
        s=sample(); s['targets'][0]['commit_sha']='not-a-commit'
        with self.assertRaises(Invalid):validate(s)
    def test_blank_evidence_rejected(self):
        s=sample();s['evidence'][0]['claim']='  '
        with self.assertRaises(Invalid):validate(s)
    def test_duplicate_ids_rejected(self):
        s=sample();s['evidence'].append(copy.deepcopy(s['evidence'][0]))
        with self.assertRaises(Invalid):validate(s)
    def test_synthetic_cannot_claim_independent_verified(self):
        s=sample()
        evidence = s['evidence'][0]
        evidence['claim_level'] = 'INDEPENDENTLY_VERIFIED'
        evidence['subject']['revision_sha'] = s['targets'][0]['commit_sha']
        evidence['locator'] = {'kind': 'github_commit', 'value': 'https://example.invalid/commit'}
        evidence['source_kind'] = 'synthetic'
        with self.assertRaisesRegex(Invalid, 'real source'):
            validate(s)

    def test_independent_claim_must_match_target_revision(self):
        s = sample()
        s['targets'][0]['commit_sha'] = 'a' * 64
        evidence = s['evidence'][0]
        evidence['claim_level'] = 'INDEPENDENTLY_VERIFIED'
        evidence['source_kind'] = 'git_commit'
        evidence['subject']['revision_sha'] = 'B' * 64
        evidence['locator'] = {'kind': 'github_commit', 'value': 'https://example.invalid/commit'}
        with self.assertRaisesRegex(Invalid, 'target revision'):
            validate(s)
        evidence['subject']['revision_sha'] = 'A' * 64
        self.assertEqual(validate(s)['independently_verified_claim_count'], 1)

    def test_target_requires_explicit_branch_field(self):
        s = sample()
        del s['targets'][0]['branch']
        with self.assertRaisesRegex(Invalid, 'branch'):
            validate(s)
    def test_missing_authority_rejected(self):
        s=sample();s.pop('authority')
        with self.assertRaises(Invalid):validate(s)
    def test_unknown_target_requires_hold(self):
        s=sample();s['targets'][0]['commit_sha']=None;s['targets'][0]['revision_status']='UNKNOWN';s['next']['decision']='CONTINUE'
        with self.assertRaises(Invalid):validate(s)
    def test_unknown_target_with_hold_allowed(self):
        s=sample();s['targets'][0]['commit_sha']=None;s['targets'][0]['revision_status']='UNKNOWN'
        self.assertTrue(validate(s)['unknown_target_revisions'])
    def test_close_with_pending_rejected(self):
        s=sample();s['next']['decision']='CLOSED'
        with self.assertRaises(Invalid):validate(s)
    def test_secret_value_rejected(self):
        s=sample();s['extra_metadata']='ghp_'+('A'*28)
        with self.assertRaises(Invalid):validate(s)
    def test_secret_field_rejected(self):
        s=sample();s['api_key']='abc'
        with self.assertRaises(Invalid):validate(s)
    def test_bad_timestamp_rejected(self):
        s=sample();s['observed_at']='2026-11-18'
        with self.assertRaises(Invalid):validate(s)
    def test_nonexistent_fixture_output_not_written_on_failure(self):
        s=sample();s['targets'][0]['commit_sha']='not-a-commit'
        with tempfile.TemporaryDirectory() as tmp:
            i=Path(tmp)/'invalid.json'; o=Path(tmp)/'out.json';i.write_text(json.dumps(s))
            r=subprocess.run(command(i, o), capture_output=True, text=True)
            self.assertEqual(r.returncode,2);self.assertFalse(o.exists())
    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            o=Path(tmp)/'out.json';o.write_text('original')
            r=subprocess.run(command(SAMPLE, o), capture_output=True, text=True)
            self.assertEqual(r.returncode,2);self.assertEqual(o.read_text(),'original')
    def test_duplicate_json_field_rejected(self):
        d=MOD['decode_without_duplicate_keys']
        with self.assertRaises(Invalid):d('{"a":1,"a":2}')
    def test_all_skills_native_frontmatter_and_scope(self):
        p=list((ROOT/'.agents/skills').glob('*/SKILL.md'))
        self.assertEqual(len(p),4)
        native_names = {path.parent.name for path in p}
        self.assertEqual(native_names, {
            'shards-native-agent-handoff', 'shards-native-context-recovery',
            'shards-native-progress-control', 'shards-native-a2a-self-preservation',
        })
        shipped_paths = [*ROOT.glob('skills/*/SKILL.md'),
                         *ROOT.glob('plugins/shards-core/skills/*/SKILL.md')]
        self.assertTrue(native_names.isdisjoint(path.parent.name for path in shipped_paths))
        for x in p:
            text = x.read_text(encoding='utf-8')
            self.assertIn('\n---\n', text[4:])
            metadata, body = parse_frontmatter(text)
            self.assertEqual(metadata['name'], x.parent.name)
            self.assertTrue(metadata['description'].strip())
            self.assertIn('authority', body.lower())

    def test_eval_cases_cover_each_native_candidate(self):
        data = json.loads((ROOT / 'evals/shards-native-recovery.json').read_text(encoding='utf-8'))
        cases = data['cases']
        self.assertEqual(data['status'], 'SCENARIOS_ONLY_NOT_EXECUTED')
        expected = {path.parent.name for path in (ROOT / '.agents/skills').glob('*/SKILL.md')}
        self.assertEqual({case['skill'] for case in cases}, expected)
        self.assertEqual(len({case['id'] for case in cases}), len(expected))
        for case in cases:
            self.assertTrue(all(case[key].strip() for key in ('scenario', 'expected_behavior', 'forbidden_claim')))
    def test_unknown_observed_metadata_preserved(self):
        s = sample()
        s['custom_origin'] = {'task_id': 'abc', 'other': 22}
        with self.assertRaisesRegex(Invalid, 'unreviewed metadata'):
            validate(s)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp).resolve() / 'input.json'
            output = Path(tmp).resolve() / 'receipt.json'
            number = '0.123456789012345678901234567890'
            source.write_text(json.dumps(s).replace('"other": 22', '"other": ' + number), encoding='utf-8')
            result = subprocess.run(command(source, output, '--allow-metadata-field', 'custom_origin'),
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = output.read_text(encoding='utf-8')
            self.assertIn(number, data)
            self.assertEqual(json.loads(data)['checkpoint']['custom_origin']['task_id'], 'abc')

    @unittest.skipUnless(os.link in os.supports_dir_fd, 'requires anchored output')
    def test_destination_swap_cannot_redirect_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            parent = root / 'destination'
            original = root / 'moved-away'
            parent.mkdir()
            link = os.link

            def swap_destination(source, target, **kwargs):
                parent.rename(original)
                parent.mkdir()
                return link(source, target, **kwargs)

            with patch.object(os, 'link', swap_destination), patch.object(
                    os, 'supports_dir_fd', os.supports_dir_fd | {swap_destination}):
                warnings = MOD['write_checkpoint'](parent / 'receipt.json', b'checkpoint')
            self.assertFalse((parent / 'receipt.json').exists())
            self.assertEqual((original / 'receipt.json').read_bytes(), b'checkpoint')
            self.assertIn('path changed', warnings[0])

    def test_file_changed_during_read_is_rejected(self):
        unchanged = SAMPLE.stat()
        changed = SimpleNamespace(st_size=unchanged.st_size, st_mtime_ns=unchanged.st_mtime_ns + 1,
                                  st_ctime_ns=unchanged.st_ctime_ns)
        with patch.object(os, 'fstat', side_effect=[unchanged, changed]):
            with self.assertRaisesRegex(Invalid, 'changed during reading'):
                MOD['read_checkpoint'](SAMPLE)

    @unittest.skipUnless(os.link in os.supports_dir_fd, 'requires anchored output')
    def test_cleanup_error_after_publication_keeps_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / 'receipt.json'
            original_unlink = os.unlink

            def fail_stage_unlink(path, **kwargs):
                if path == 'checkpoint.json':
                    raise OSError('synthetic cleanup failure')
                return original_unlink(path, **kwargs)

            with patch.object(os, 'unlink', fail_stage_unlink), patch.object(
                    os, 'supports_dir_fd', os.supports_dir_fd | {fail_stage_unlink}):
                warnings = MOD['write_checkpoint'](output, b'checkpoint')
            self.assertEqual(output.read_bytes(), b'checkpoint')
            self.assertIn('cleanup failed', warnings[0])

    @unittest.skipUnless(os.link in os.supports_dir_fd, 'requires anchored output')
    def test_sync_staged_file_before_link_and_destination_after_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / 'receipt.json'
            events = []
            real_link, real_fsync = os.link, os.fsync

            def track_link(source, destination, **kwargs):
                events.append('link')
                return real_link(source, destination, **kwargs)

            def track_sync(fd):
                events.append('directory sync' if stat.S_ISDIR(os.fstat(fd).st_mode) else 'file sync')
                return real_fsync(fd)

            with patch.object(os, 'link', track_link), patch.object(os, 'fsync', track_sync), patch.object(
                    os, 'supports_dir_fd', os.supports_dir_fd | {track_link}):
                warnings = MOD['write_checkpoint'](output, b'checkpoint')
            self.assertEqual(warnings, [])
            self.assertEqual(events, ['file sync', 'link', 'directory sync'])

if __name__=='__main__':
    unittest.main()
