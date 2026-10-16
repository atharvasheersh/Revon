"""Failure controls for package portability and independent evidence checks.

Every mutation is confined to TemporaryDirectory; real evidence is read only.
"""
import ast
import copy
import hashlib
import json
import shutil
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.build_review_package import ROOT,FIGURE_DIRECTORY,FIGURE_NAMES,build,required_assets
from tools.check_review_package import check as check_package
from tools.check_review_campaign import check_calibration,audit_revision
from tools.check_selector_cost import check as check_selector,check_provenance,DIAGNOSTIC_SOURCE,expected_prefix
from tools.check_review_baseline import check as check_baseline


def load(path):return json.loads(path.read_text(encoding='utf8'))
def save(path,obj):path.write_text(json.dumps(obj,indent=2),encoding='utf8')
def refresh(folder):
    manifest=load(folder/'SHA256SUMS.json')
    for name in manifest:manifest[name]=hashlib.sha256((folder/name).read_bytes()).hexdigest()
    save(folder/'SHA256SUMS.json',manifest)


class BaselinePortabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        protected={}
        for name,data in [('evidence/public/raw.json',b'actual science'),('evidence/local/.work/scratch.json',b'local scratch'),('evidence/public/__pycache__/cache.pyc',b'bytecode')]:
            protected[name]=hashlib.sha256(data).hexdigest()
            if '.work' not in Path(name).parts and '__pycache__' not in Path(name).parts:
                p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        for suffix in ['pdf','docx']:
            name='Revon Research Paper Springer.'+suffix
            protected['paper/'+name]=hashlib.sha256(b'old manuscript').hexdigest()
            p=self.root/'paper'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'revised manuscript')
            p=self.root/'paper/previous versions/review-baseline-20261016'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'old manuscript')
        p=self.root/'evidence/review-revision-20261016/baseline.json';p.parent.mkdir(parents=True);save(p,{'protected_files':protected})

    def test_portable_mode_omits_only_incidental_baseline_paths(self):
        result=check_baseline(self.root,portable=True)
        self.assertEqual((result['protected_files'],len(result['excluded_local_paths'])),(3,2))

    def test_strict_local_mode_still_requires_incidental_files(self):
        with self.assertRaisesRegex(ValueError,'unexpected protected file changes'):check_baseline(self.root)

    def test_portable_mode_still_rejects_changed_scientific_evidence(self):
        (self.root/'evidence/public/raw.json').write_bytes(b'changed science')
        with self.assertRaisesRegex(ValueError,'unexpected protected file changes'):check_baseline(self.root,portable=True)


class PackagePortabilityTests(unittest.TestCase):
    def test_current_package_uses_only_versioned_asset_paths(self):
        path=ROOT/'paper/Revon_Review_Revision_Reproducibility_20261016.zip'
        self.assertTrue(check_package(path)['passed'])
        with zipfile.ZipFile(path) as z:
            self.assertFalse(any(n.startswith('output/') or n.endswith('/ALL_21_ISSUES_RECHECK.md') for n in z.namelist()))
            for asset in required_assets():self.assertEqual(z.read(asset.relative_to(ROOT).as_posix()),asset.read_bytes())

    def test_missing_required_asset_prevents_build_before_output(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/FIGURE_DIRECTORY;folder.mkdir(parents=True)
            for name in FIGURE_NAMES[:-1]:shutil.copy2(ROOT/FIGURE_DIRECTORY/name,folder/name)
            target=root/'must-not-exist.zip'
            with self.assertRaisesRegex(FileNotFoundError,'required publication figure missing'):
                build(root,target)
            self.assertFalse(target.exists())

    def test_absent_asset_directory_cannot_silently_build(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(FileNotFoundError,'required publication figure missing'):build(Path(tmp))

    def test_rehashed_archive_omitting_asset_is_rejected(self):
        source=ROOT/'paper/Revon_Review_Revision_Reproducibility_20261016.zip'
        missing=FIGURE_DIRECTORY+'/'+FIGURE_NAMES[0]
        with TemporaryDirectory() as tmp:
            target=Path(tmp)/'missing.zip'
            with zipfile.ZipFile(source) as original,zipfile.ZipFile(target,'w') as changed:
                hashes=json.loads(original.read('PACKAGE_SHA256SUMS.json'))
                del hashes[missing]
                for item in original.infolist():
                    if item.filename not in {missing,'PACKAGE_SHA256SUMS.json'}:changed.writestr(item,original.read(item))
                changed.writestr('PACKAGE_SHA256SUMS.json',json.dumps(hashes))
            with self.assertRaisesRegex(ValueError,'required figure missing'):check_package(target)


class CalibrationVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.campaign=Path(self.temp.name)/'campaign';self.campaign.mkdir()
        original=ROOT/'evidence/review-revision-20261016/campaign'
        self.protocol=load(original/'protocol.json')
        for name in ['protocol.json','frozen_selection.json','analysis.json']:shutil.copy2(original/name,self.campaign/name)
        for case in self.protocol['cases']:
            if case['suite'] not in {'calibration','validation'}:continue
            target=self.campaign/'cases'/case['name'];target.mkdir(parents=True)
            shutil.copy2(original/'cases'/case['name']/'started.json',target/'started.json')
            if case['suite']=='calibration':shutil.copy2(original/'cases'/case['name']/'result.json',target/'result.json')
        self.case=next(c for c in self.protocol['cases'] if c['suite']=='calibration')
        self.result=self.campaign/'cases'/self.case['name']/'result.json'

    def change_selection(self,threshold=None,scores=None):
        for filename in ['frozen_selection.json','analysis.json']:
            value=load(self.campaign/filename)
            if threshold is not None:value['threshold']=threshold
            if scores is not None:value['scores' if filename.startswith('frozen') else 'calibration_scores']=scores
            save(self.campaign/filename,value)

    def test_current_calibration_and_chronology_pass(self):
        report=check_calibration(self.campaign)
        self.assertEqual((report['calibration_cases'],report['validation_cases'],report['threshold']),(12,18,65536))
        self.assertTrue(report['chronology_checked'])

    def test_false_scores_are_rejected_even_when_analysis_agrees(self):
        self.change_selection(scores={str(t):0.0 for t in self.protocol['thresholds']})
        with self.assertRaisesRegex(ValueError,'scores disagree'):check_calibration(self.campaign)

    def test_nonminimal_winner_is_rejected(self):
        self.change_selection(threshold=4096)
        with self.assertRaisesRegex(ValueError,'winner/tie-break'):check_calibration(self.campaign)

    def test_exact_tie_requires_smallest_threshold(self):
        for case in self.protocol['cases']:
            if case['suite']!='calibration':continue
            path=self.campaign/'cases'/case['name']/'result.json';value=load(path)
            for row in value['records']:row['diff_ms']=1.0
            save(path,value)
        scores={str(t):1.0 for t in self.protocol['thresholds']}
        self.change_selection(threshold=512,scores=scores)
        self.assertEqual(check_calibration(self.campaign)['threshold'],512)
        self.change_selection(threshold=65536)
        with self.assertRaisesRegex(ValueError,'winner/tie-break'):check_calibration(self.campaign)

    def test_invalid_timings_and_zero_denominator_are_rejected(self):
        original=load(self.result)
        for bad in [0.0,-1.0,float('nan'),float('inf'),True]:
            with self.subTest(timing=bad):
                value=copy.deepcopy(original)
                next(r for r in value['records'] if r['trial_kind']=='measured')['diff_ms']=bad;save(self.result,value)
                with self.assertRaisesRegex(ValueError,'invalid calibration measured timing'):check_calibration(self.campaign)

    def test_missing_configuration_is_rejected(self):
        value=load(self.result);value['records'].pop();save(self.result,value)
        with self.assertRaisesRegex(ValueError,'configuration count'):check_calibration(self.campaign)

    def test_freeze_before_calibration_completion_is_rejected(self):
        value=load(self.result);value['finished_utc']='2099-01-01T00:00:00+00:00';save(self.result,value)
        with self.assertRaisesRegex(ValueError,'completion/freeze chronology'):check_calibration(self.campaign)

    def test_validation_before_freeze_is_rejected(self):
        case=next(c for c in self.protocol['cases'] if c['suite']=='validation')
        path=self.campaign/'cases'/case['name']/'started.json';value=load(path)
        value['started_utc']=load(self.campaign/'frozen_selection.json')['created_utc'];save(path,value)
        with self.assertRaisesRegex(ValueError,'validation preceded'):check_calibration(self.campaign)

    def test_validation_timings_do_not_select_threshold(self):
        expected=check_calibration(self.campaign)
        case=next(c for c in self.protocol['cases'] if c['suite']=='validation')
        save(self.campaign/'cases'/case['name']/'result.json',{'records':'deliberately unusable as calibration input'})
        self.assertEqual(check_calibration(self.campaign),expected)

    def test_complete_auditor_rejects_resigned_zero_scores(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);bundle=root/'evidence/review-revision-20261016'
            shutil.copytree(ROOT/'evidence/review-revision-20261016',bundle)
            for filename,key in [('frozen_selection.json','scores'),('analysis.json','calibration_scores')]:
                path=bundle/'campaign'/filename;value=load(path)
                value[key]={str(t):0.0 for t in self.protocol['thresholds']};save(path,value)
            refresh(bundle)
            with self.assertRaisesRegex(ValueError,'calibration scores disagree'):audit_revision(root)


class SelectorProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.folder=self.root/'evidence/selector-cost-20261016'
        shutil.copytree(ROOT/'evidence/selector-cost-20261016',self.folder)
        source=ROOT/'evidence/review-revision-20261016/campaign'
        self.campaign=self.root/'evidence/review-revision-20261016/campaign'
        shutil.copytree(source/'source',self.campaign/'source')
        for name in ['manifest.json','protocol.json']:shutil.copy2(source/name,self.campaign/name)
        retained=self.root/DIAGNOSTIC_SOURCE;retained.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/DIAGNOSTIC_SOURCE,retained)
        self.protocol=load(self.folder/'protocol.json')

    def test_archived_source_and_prefix_pass(self):
        self.assertTrue(check_provenance(self.root,self.protocol)['prefix_ast_verified'])

    def test_resigned_invalid_prefix_is_rejected_by_complete_checker(self):
        code="def production_decision_prefix(*args, **kwargs):\n    return 'invalid-path'\n"
        (self.folder/'extracted_prefix.py').write_text(code,encoding='utf8')
        self.protocol['prefix_sha256']=hashlib.sha256(code.encode()).hexdigest();save(self.folder/'protocol.json',self.protocol);refresh(self.folder)
        with self.assertRaisesRegex(ValueError,'prefix differs'):check_selector(self.root)

    def test_false_production_source_hash_is_rejected(self):
        self.protocol['versioned_db_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'production source mismatch'):check_provenance(self.root,self.protocol)

    def test_prefix_from_changed_production_function_is_rejected(self):
        source=(self.campaign/'source/versioned_db.py').read_text(encoding='utf8')
        tree=expected_prefix(source);tree.body[0].body[-1].value=ast.Constant(value='log')
        code=ast.unparse(ast.fix_missing_locations(tree));(self.folder/'extracted_prefix.py').write_text(code,encoding='utf8')
        self.protocol['prefix_sha256']=hashlib.sha256(code.encode()).hexdigest()
        with self.assertRaisesRegex(ValueError,'prefix differs'):check_provenance(self.root,self.protocol)

    def test_harmless_prefix_formatting_is_accepted(self):
        path=self.folder/'extracted_prefix.py';code='# harmless comment\n'+path.read_text(encoding='utf8')+'\n\n'
        path.write_text(code,encoding='utf8');self.protocol['prefix_sha256']=hashlib.sha256(code.encode()).hexdigest()
        self.assertTrue(check_provenance(self.root,self.protocol)['prefix_ast_verified'])

    def test_altered_retained_benchmark_source_is_rejected(self):
        (self.root/DIAGNOSTIC_SOURCE).write_text('# changed source\n',encoding='utf8')
        with self.assertRaisesRegex(ValueError,'retained source mismatch'):check_provenance(self.root,self.protocol)

    def test_changed_history_identity_is_rejected(self):
        self.protocol['cases'][0]['seed']=0
        with self.assertRaisesRegex(ValueError,'validation histories mismatch'):check_provenance(self.root,self.protocol)

    def test_existing_batch_accounting_remains_active(self):
        for case in self.protocol['cases']:
            target=self.campaign/'cases'/case['name'];target.mkdir(parents=True)
            shutil.copy2(ROOT/'evidence/review-revision-20261016/campaign/cases'/case['name']/'result.json',target/'result.json')
        path=self.folder/(self.protocol['cases'][0]['name']+'.json');value=load(path)
        value['records'][0]['calls']=999;save(path,value);refresh(self.folder)
        with self.assertRaisesRegex(ValueError,'observation mismatch'):check_selector(self.root)
