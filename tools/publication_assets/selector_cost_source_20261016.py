"""Post-campaign diagnostic of the actual production decision prefix.

Extracts the unchanged function AST up to the first selected-path dispatch.
The extracted prefix includes input checks, ancestry and the internal changeset
length count. No detached public-view copying or actual diff traversal is timed.
This is a warm prefix microbenchmark, not an overhead subtraction or a new
policy selection. Uses the already evaluated held-out profiles without tuning.
"""
from __future__ import annotations
import argparse,ast,hashlib,json,statistics,tempfile,time
from pathlib import Path
from dataclasses import asdict
from versioned_db import VersionedDatabase
from .review_revision import definitions,now
from .adapters import RevonAdapter
from .workloads import WorkloadSpec,build_workload

ROOT=Path(__file__).resolve().parents[1]

def extract_prefix():
    source=(ROOT/'versioned_db.py').read_text(encoding='utf8')
    tree=ast.parse(source)
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and any(isinstance(x,ast.FunctionDef) and x.name=='diff_versions' for x in n.body))
    fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='diff_versions')
    cutoff=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.If) and ast.unparse(n.test)=="selected == 'log'")
    fn.body=fn.body[:cutoff]+[ast.Return(value=ast.Name(id='selected',ctx=ast.Load()))]
    fn.name='production_decision_prefix'
    module=ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[]));namespace={}
    exec(compile(module,'<extracted-production-prefix>','exec'),namespace)
    return namespace[fn.name],ast.unparse(module)

def run(output):
    output.mkdir(parents=True,exist_ok=False)
    source=(ROOT/'versioned_db.py').read_bytes()
    expected=json.loads((ROOT/'evidence/review-revision-20261016/campaign/manifest.json').read_text())['source_hashes']['versioned_db.py']
    if hashlib.sha256(source).hexdigest()!=expected:raise ValueError('production source differs from timed campaign')
    prefix,code=extract_prefix();(output/'extracted_prefix.py').write_text(code,encoding='utf8')
    protocol={'created_utc':now(),'scope':'post-campaign warm extracted production-prefix microbenchmark; no policy tuning, diff work, detached-view copy, cold-cache or causal overhead subtraction',
      'cases':[c for c in definitions() if c['suite']=='validation'],'thresholds':[4096,65536],'warmup_batches':2,'measured_batches':7,'calls_per_batch':1000,
      'versioned_db_sha256':expected,'prefix_sha256':hashlib.sha256(code.encode()).hexdigest(),
      'source_hashes':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['experiments/selector_cost.py','experiments/workloads.py','experiments/adapters.py','sqlite_store.py']}}
    (output/'protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf8')
    results=[]
    for case in protocol['cases']:
        workload=build_workload(WorkloadSpec(**case['spec']));records=[]
        with tempfile.TemporaryDirectory(prefix='revon-selector-cost-') as tmp:
            adapter=RevonAdapter(Path(tmp),strategy='hybrid',hybrid_threshold=4096)
            adapter.initial_import(workload.initial)
            for batch in workload.batches:adapter.commit(batch)
            db=adapter.repository.database;right=len(workload.states)
            for threshold in protocol['thresholds']:
                db.hybrid_log_threshold=threshold;selected=prefix(db,1,right,'hybrid')
                adapter.diff(1,right)
                if selected!=adapter.repository.last_diff_stats.strategy:raise ValueError('prefix/production decision mismatch')
                for kind,count in [('warmup',2),('measured',7)]:
                    for batch in range(1,count+1):
                        start=time.perf_counter_ns()
                        for _ in range(1000):actual=prefix(db,1,right,'hybrid')
                        elapsed=time.perf_counter_ns()-start
                        if actual!=selected:raise ValueError('unstable decision')
                        records.append({'threshold':threshold,'trial_kind':kind,'batch':batch,'calls':1000,'elapsed_ns':elapsed,'ns_per_call':elapsed/1000,'selected':selected})
            adapter.close()
        row={'case':case,'workload_sha256':workload.digest,'records':records,'finished_utc':now()};results.append(row)
        (output/(case['name']+'.json')).write_text(json.dumps(row,indent=2),encoding='utf8')
    medians=[statistics.median(r['ns_per_call'] for r in case['records'] if r['trial_kind']=='measured' and r['threshold']==t) for case in results for t in [4096,65536]]
    report={'cases':len(results),'batches':sum(len(c['records']) for c in results),'timed_calls':sum(r['calls'] for c in results for r in c['records']),
      'measured_calls':sum(r['calls'] for c in results for r in c['records'] if r['trial_kind']=='measured'),
      'case_threshold_median_us':statistics.median(medians)/1000,'min_case_threshold_median_us':min(medians)/1000,'max_case_threshold_median_us':max(medians)/1000,
      'passed':True,'scope':protocol['scope']}
    (output/'summary.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.is_file()}
    (output/'SHA256SUMS.json').write_text(json.dumps(hashes,indent=2),encoding='utf8');print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);run(p.parse_args().output)
