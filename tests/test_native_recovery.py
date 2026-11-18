import copy
import json
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VALIDATOR=ROOT/'.agents/skills/shards-agent-handoff/scripts/validate.py'
SAMPLE=ROOT/'fixtures/valid-multi-target.json'
MOD=runpy.run_path(str(VALIDATOR))
validate=MOD['validate']
Invalid=MOD['Invalid']

def sample():
 return json.loads(SAMPLE.read_text())

class ShardsNativeRecovery(unittest.TestCase):
 def test_good_multirevision_and_lossless(self):
 s=sample(); v=validate(s)
 self.assertTrue(v['schema_valid'])
 self.assertFalse(v['external_evidence_verified'])
 with tempfile.TemporaryDirectory() as tmp:
 out=Path(tmp)/'result.json'
 r=subprocess.run([sys.executable,str(VALIDATOR),'--input',str(SAMPLE),'--output',str(out)],capture_output=True,text=True)
 self.assertEqual(r.returncode,0,r.stderr)
 data=json.loads(out.read_text())
 self.assertEqual(data['checkpoint'],s)
 self.assertEqual(data['checkpoint']['extra_metadata'],s['extra_metadata'])
 self.assertEqual(len(data['checkpoint']['targets']),2)
 def test_invalid_commit_rejected(self):
 s=sample(); s['targets'][0]['commit_sha']='not-a-commit'
 with self.assertRaises(Invalid):validate(s)
 def test_blank_evidence_rejected(self):
 s=sample();s['evidence'][0]['claim']=' '
 with self.assertRaises(Invalid):validate(s)
 def test_duplicate_ids_rejected(self):
 s=sample();s['evidence'].append(copy.deepcopy(s['evidence'][0]))
 with self.assertRaises(Invalid):validate(s)
 def test_synthetic_cannot_claim_independent_verified(self):
 s=sample();s['evidence'][0]['claim_level']='INDEPENDENTLY_VERIFIED'
 with self.assertRaises(Invalid):validate(s)
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
 r=subprocess.run([sys.executable,str(VALIDATOR),'--input',str(i),'--output',str(o)],capture_output=True,text=True)
 self.assertEqual(r.returncode,2);self.assertFalse(o.exists())
 def test_no_overwrite(self):
 with tempfile.TemporaryDirectory() as tmp:
 o=Path(tmp)/'out.json';o.write_text('original')
 r=subprocess.run([sys.executable,str(VALIDATOR),'--input',str(SAMPLE),'--output',str(o)],capture_output=True,text=True)
 self.assertEqual(r.returncode,2);self.assertEqual(o.read_text(),'original')
 def test_duplicate_json_field_rejected(self):
 d=MOD['decode_without_duplicate_keys']
 with self.assertRaises(Invalid):d('{"a":1,"a":2}')
 def test_all_skills_native_frontmatter_and_scope(self):
 p=list((ROOT/'.agents/skills').glob('*/SKILL.md'))
 self.assertEqual(len(p),4)
 for x in p:
 t=x.read_text()
 self.assertTrue(t.startswith('---\n'))
 self.assertIn('name: '+x.parent.name,t)
 self.assertIn('description:',t)
 self.assertIn('authority',t.lower())
 def test_unknown_observed_metadata_preserved(self):
 s=sample();s['custom_origin']={'task_id':'abc','other':22}
 self.assertTrue(validate(s)['schema_valid'])

if __name__=='__main__':
 unittest.main()
