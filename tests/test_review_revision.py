"""Failure-oriented checks before freezing the reviewer-revision campaign."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json,unittest,shutil
from experiments.review_revision import (definitions,expected_diff,check_output,oracle_bytes,aggregate_io,worker,PhasedDolt,cleanup_repository)
from experiments.review_revision_data import from_states,co2_states
from experiments.adapters import canonical_diff_bytes,DoltAdapter
from experiments.workloads import WorkloadSpec,build_workload

class ReviewRevisionTests(unittest.TestCase):
    def test_observed_diff_is_not_filled_from_oracle(self):
        w=from_states('actual',[{'a':'one'},{'a':'two','b':'three'}],1)
        expected=expected_diff(w)
        with self.assertRaisesRegex(ValueError,'observed diff'):
            check_output(canonical_diff_bytes({'a':('one','two')}),expected)
        self.assertEqual(json.loads(oracle_bytes(expected))['changes'][1]['key'],'b')

    def test_observed_deletion_and_history_order(self):
        w=from_states('history',[{'a':'one','b':'two'},{'b':'three'},{'b':'three','a':'four'}],1)
        self.assertFalse(w.batches[0][0].new_exists)
        self.assertTrue(w.batches[1][0].new_exists)
        with self.assertRaisesRegex(ValueError,'empty observed'):
            from_states('empty',[{'a':'one'},{'a':'one'}],1)

    def test_publication_outage_and_unnamed_fields_are_explicit(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)
            (path/'full.csv').write_text('Date,Average\n2000-01,2,extra\n')
            (path/'outage.csv').write_text('Date,Average\n')
            (path/'acquisition.json').write_text(json.dumps({'co2':{'records':[{'file':'full.csv'},{'file':'outage.csv'}]}}))
            states=co2_states(path)
            self.assertEqual(len(states),1)
            self.assertEqual(json.loads(states[0]['2000-01'])['_extra_0'],'extra')

    def test_split_and_matched_controls(self):
        cases=definitions();cal={c['spec']['seed'] for c in cases if c['suite']=='calibration'}
        val={c['spec']['seed'] for c in cases if c['suite']=='validation'}
        self.assertFalse(cal&val)
        primary=[c for c in cases if c['suite'] in ['calibration','validation']]
        self.assertEqual({(c['spec']['rows'],c['spec']['commits']) for c in primary},{(12000,8)})
        self.assertEqual(sum(c['suite']=='scale' for c in cases),18)

    def test_zero_is_not_missing(self):
        self.assertEqual(aggregate_io({9:(.1,0,0)},{9}),(0,0))
        self.assertEqual(aggregate_io({9:(.1,None,None)},set()),(None,None))

    def test_generator_mix_matches_documentation(self):
        w=build_workload(WorkloadSpec('mix',100,2,20,7))
        for batch in w.batches:
            self.assertEqual(sum(not m.old_exists for m in batch),1)
            self.assertEqual(sum(not m.new_exists for m in batch),1)

    def test_extracted_production_prefix_matches_forward_reverse_and_limits(self):
        from experiments.selector_cost import extract_prefix
        from versioned_db import VersionedDatabase
        prefix,code=extract_prefix();db=VersionedDatabase()
        db.commit({'a':'one'});db.commit({'a':'two','b':'three'})
        for threshold in [0,2,65536]:
            db.hybrid_log_threshold=threshold
            for left,right in [(1,2),(2,1),(1,1)]:
                selected=prefix(db,left,right,'hybrid');db.diff_versions(left,right,'hybrid')
                self.assertEqual(selected,db.last_diff_stats.strategy)
        self.assertIn('self._changesets',code)
        self.assertNotIn('self.changeset_store',code)

    def test_extracted_prefix_rejects_invalid_inputs(self):
        from experiments.selector_cost import extract_prefix
        from versioned_db import VersionedDatabase
        prefix,_=extract_prefix();db=VersionedDatabase();db.commit({'a':1})
        with self.assertRaises(KeyError):prefix(db,1,2,'hybrid')
        with self.assertRaises(ValueError):prefix(db,1,1,'unknown')

    def test_worker_proves_states_and_reopen(self):
        with TemporaryDirectory() as directory:
            case={'name':'small-preflight','suite':'validation','spec':WorkloadSpec('small-preflight',30,2,3,9).__dict__,'b':8,'d':4,'monitor':False}
            result=worker({'case':case,'output':directory})
            self.assertEqual(len(result['history']),3)
            self.assertEqual(len(result['records']),54)
            self.assertTrue(all(r['output_sha256']==result['oracle_diff_sha256'] for r in result['records']))
            self.assertFalse((Path(directory)/'cases'/'small-preflight'/'repository').exists())

    @unittest.skipUnless(shutil.which('dolt'),'Dolt unavailable')
    def test_phased_dolt_matches_actual_native_adapter(self):
        with TemporaryDirectory() as directory:
            d=PhasedDolt(Path(directory)/'dolt')
            w=from_states('actual',[{'a':'one','b':'two'},{'a':'changed','c':'new'}],1)
            d.initial_import(w.initial);d.commit(w.batches[0])
            measured=d.diff(1,2)
            native=DoltAdapter.diff(d,1,2)
            self.assertEqual(measured,native)
            check_output(measured,expected_diff(w))
            self.assertTrue(all(x>=0 for x in d.last_phases.values()))
            d.close();cleanup_repository(Path(directory)/'dolt',Path(directory))

if __name__=='__main__':unittest.main()
