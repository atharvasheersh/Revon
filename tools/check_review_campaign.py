"""Audit the archived review campaign on a disposable, path-localised copy.

Collected bytes are never rewritten. A fresh interpreter imports the executed
source snapshot, not the working tree. The historical absolute data path is
mapped to the supplied public source directory only for reconstruction.
"""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib,json,shutil,subprocess,sys
import math,statistics
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]

def load(p):return json.loads(p.read_text(encoding='utf8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

SELECTION_RULE='equal-weight calibration-case mean hybrid median / faster forced-path median; tie -> smaller threshold; freeze before validation'
SCORE_REL_TOL=1e-12

def timestamp(value):
    try:result=datetime.fromisoformat(value.replace('Z','+00:00'))
    except (ValueError,TypeError,AttributeError) as error:raise ValueError('invalid calibration timestamp') from error
    if result.tzinfo is None or result.utcoffset() is None:raise ValueError('calibration timestamp requires timezone')
    return result

def positive_number(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>0

def check_calibration(campaign):
    """Recalculate the objective from raw calibration timings, never validation.

    Relative tolerance 1e-12 (no absolute tolerance) permits floating-point
    summation variation between supported Python versions. Winner/tie selection
    uses the actual recalculated scores, without approximate ties. This live
    check deliberately does not call the executed snapshot's freeze/analyze.
    """
    protocol=load(campaign/'protocol.json');frozen=load(campaign/'frozen_selection.json')
    thresholds=protocol['thresholds']
    if not thresholds or any(type(t) is not int or t<0 for t in thresholds) or len(set(thresholds))!=len(thresholds):raise ValueError('invalid calibration thresholds')
    if protocol['selection_rule']!=SELECTION_RULE or frozen['rule']!=SELECTION_RULE:raise ValueError('calibration selection rule mismatch')
    if frozen.get('validation_not_started') is not True:raise ValueError('calibration freeze declaration missing')
    created=timestamp(protocol['created_utc']);freeze=timestamp(frozen['created_utc'])
    if freeze<created:raise ValueError('calibration freeze preceded protocol')
    calibration=[c for c in protocol['cases'] if c['suite']=='calibration']
    validation=[c for c in protocol['cases'] if c['suite']=='validation']
    if not calibration or not validation:raise ValueError('calibration/validation split missing')
    if len({c['name'] for c in protocol['cases']})!=len(protocol['cases']):raise ValueError('duplicate calibration case identity')
    if {c['spec']['seed'] for c in calibration}&{c['spec']['seed'] for c in validation}:raise ValueError('calibration/validation seeds overlap')
    ratios={t:[] for t in thresholds}
    for case in calibration:
        folder=campaign/'cases'/case['name'];result=load(folder/'result.json');started=load(folder/'started.json')
        if result['case']!=case or started['case']!=case:raise ValueError('calibration case identity mismatch')
        if not created<=timestamp(started['started_utc'])<=timestamp(result['finished_utc'])<=freeze:raise ValueError('calibration completion/freeze chronology mismatch')
        check_case_matrix(case,result['records'],protocol)
        groups={('log',0):[],('merkle',0):[],**{('hybrid',t):[] for t in thresholds}}
        for row in result['records']:
            if row['trial_kind']!='measured':continue
            value=row['diff_ms']
            if not positive_number(value):raise ValueError('invalid calibration measured timing')
            groups[(row['strategy'],row['threshold'])].append(value)
        medians={key:statistics.median(values) for key,values in groups.items()}
        denominator=min(medians[('log',0)],medians[('merkle',0)])
        for t in thresholds:ratios[t].append(medians[('hybrid',t)]/denominator)
    scores={str(t):statistics.mean(ratios[t]) for t in thresholds}
    winner=min(thresholds,key=lambda t:(scores[str(t)],t))
    analysis=load(campaign/'analysis.json')
    for label,reported,chosen in [('frozen selection',frozen['scores'],frozen['threshold']),('retained analysis',analysis['calibration_scores'],analysis['threshold'])]:
        if not isinstance(reported,dict) or set(reported)!=set(scores):raise ValueError('calibration score candidates mismatch: '+label)
        if any(not positive_number(reported[key]) or not math.isclose(reported[key],value,rel_tol=SCORE_REL_TOL,abs_tol=0) for key,value in scores.items()):raise ValueError('calibration scores disagree with raw timings: '+label)
        if type(chosen) is not int or chosen!=winner:raise ValueError('calibration winner/tie-break mismatch: '+label)
    for case in validation:
        started=load(campaign/'cases'/case['name']/'started.json')
        if started['case']!=case or timestamp(started['started_utc'])<=freeze:raise ValueError('validation preceded calibration freeze')
    return {'passed':True,'calibration_cases':len(calibration),'validation_cases':len(validation),'threshold':winner,'scores':scores,'relative_tolerance':SCORE_REL_TOL,'chronology_checked':True}

def check_case_matrix(case,rows,protocol):
    expected={('log',0),('merkle',0)}|{('hybrid',t) for t in protocol['thresholds']}
    if case['suite'] not in ['calibration','validation','sensitivity','monitor']:
        model=case['model'];expected={(('dolt' if model=='dolt' else 'merkle' if model=='revon-m' else 'hybrid'),0 if model=='dolt' else 4096)}
    if len(rows)!=(protocol['warmups']+protocol['trials'])*len(expected):raise ValueError('review configuration count mismatch')
    for kind,count in [('warmup',protocol['warmups']),('measured',protocol['trials'])]:
        for trial in range(1,count+1):
            block=[r for r in rows if r['trial_kind']==kind and r['trial']==trial]
            if len(block)!=len(expected) or {(r['strategy'],r['threshold']) for r in block}!=expected:raise ValueError('review configuration matrix mismatch')
            if sorted(r['execution_order'] for r in block)!=list(range(1,len(expected)+1)):raise ValueError('review execution-order mismatch')

def audit_revision(root=ROOT):
    bundle=root/'evidence/review-revision-20261016';campaign=bundle/'campaign'
    hashes=load(bundle/'SHA256SUMS.json')
    for relative,expected in hashes.items():
        p=bundle/relative
        if not p.is_file() or digest(p)!=expected:raise ValueError(f'review collection checksum mismatch: {relative}')
    protocol=load(campaign/'protocol.json')
    for case in protocol['cases']:
        result=load(campaign/'cases'/case['name']/'result.json');rows=result['records']
        check_case_matrix(case,rows,protocol)
    calibration=check_calibration(campaign)
    with TemporaryDirectory(prefix='revon-review-audit-') as temp:
        target=Path(temp);copy=target/'campaign';sources=target/'public_sources'
        shutil.copytree(campaign,copy);shutil.copytree(bundle/'public_sources',sources)
        code='''import sys,json
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from experiments import review_revision as r
actual=r.public_workload
r.public_workload=lambda ignored,*args,**kwargs:actual(Path(sys.argv[3]),*args,**kwargs)
report=r.audit(Path(sys.argv[2]))
from experiments.analyze_review_revision import analyze
derived=analyze(Path(sys.argv[2]))
print(json.dumps({'audit':report,'analysis':derived}))
'''
        result=subprocess.run([sys.executable,'-c',code,str(copy/'source'),str(copy),str(sources)],cwd=copy/'source',capture_output=True,text=True,encoding='utf8',timeout=1800)
        if result.returncode:raise ValueError('frozen review-source audit failed: '+result.stderr[-2500:])
        regenerated=json.loads(result.stdout)
        retained=load(campaign/'analysis.json')
        for key in ['threshold','calibration_scores','validation','public_and_scale','monitor_diagnostic','scope']:
            if regenerated['analysis'][key]!=retained[key]:raise ValueError(f'review analysis recomputation differs: {key}')
    # Confirm the read-only check did not mutate any collected input.
    if any(digest(bundle/p)!=h for p,h in hashes.items()):raise ValueError('audit changed collected bytes')
    return {'passed':True,'cases':regenerated['audit']['completed_cases'],'queries':regenerated['audit']['queries'],
      'measured_queries':regenerated['audit']['measured_queries'],'hashes':len(hashes),
      'calibration':calibration,
      'scope':'frozen-source semantic/accounting and analysis audit on disposable copy; not timing reproduction'}

if __name__=='__main__':print(json.dumps(audit_revision(),indent=2))
