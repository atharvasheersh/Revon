"""Frozen local review campaign: disjoint histories, public revisions and scale.

All evidence is new. Queries share a durable repository within a case; cases
run in fresh workers. Historical Linux timing rows are never pooled here.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,os,platform,random,shutil,sqlite3,statistics,subprocess,sys,time,threading,traceback
from dataclasses import asdict
from datetime import datetime,timezone
from pathlib import Path
import psutil
from sqlite_store import SQLiteRevonRepository
from .adapters import RevonAdapter,DoltAdapter,canonical_bytes,canonical_diff_bytes,decode_diff_bytes,canonical_state_bytes,value_digest
from .workloads import WorkloadSpec,build_workload
from .threshold_validation import selection
from .review_revision_data import public_workload,verify_sources

ROOT=Path(__file__).resolve().parents[1]
THRESHOLDS=(512,4096,16384,65536)
WARMUPS,TRIALS=2,7
SOURCES=('versioned_db.py','sqlite_store.py','experiments/adapters.py','experiments/workloads.py','experiments/threshold_validation.py','experiments/review_revision.py','experiments/review_revision_data.py')

def now():return datetime.now(timezone.utc).isoformat()
def sha(data):return hashlib.sha256(data).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf8'))
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf8')

def cleanup_repository(path,parent):
    if path.resolve().parent!=parent.resolve():raise ValueError('scratch containment failure')
    # Windows Dolt helper processes can briefly retain their working directory.
    for attempt in range(100):
        try:shutil.rmtree(path);return
        except PermissionError:
            if attempt==99:raise
            time.sleep(.1)

def definitions():
    cases=[]
    for split,seeds in [('calibration',(202610161,202610162)),('validation',(202610171,202610172,202610173))]:
        for seed in seeds:
            for locality in ['spread','repeated-key']:
                for changes in [64,512,4096]:
                    spec=WorkloadSpec(f'{split}-{seed}-{locality}-c{changes}',12000,8,changes,seed,32,locality)
                    cases.append({'name':spec.name,'suite':split,'spec':asdict(spec),'b':8,'d':4,'monitor':False})
    for seed in [202610171,202610172,202610173]:
        variants=[('rows24000',24000,8,512,32,'spread',8,4),('history16',12000,16,256,32,'spread',8,4),
                  ('payload256',12000,8,512,256,'spread',8,4),('geometry4x6',12000,8,512,32,'spread',4,6),
                  ('geometry16x3',12000,8,512,32,'spread',16,3),('route8',12000,8,8,32,'hash-route-local',8,4),
                  ('route-control8',12000,8,8,32,'spread',8,4)]
        for label,n,h,c,p,loc,b,d in variants:
            spec=WorkloadSpec(f'sensitivity-{seed}-{label}',n,h,c,seed,p,loc)
            cases.append({'name':spec.name,'suite':'sensitivity','spec':asdict(spec),'b':b,'d':d,'monitor':False})
    for repeat in range(1,4):
        for monitored in [False,True]:
            spec=WorkloadSpec(f'monitor-{repeat}-{int(monitored)}',12000,8,512,202610190,32,'spread')
            cases.append({'name':spec.name,'suite':'monitor','spec':asdict(spec),'b':8,'d':4,'monitor':monitored,'replicate':repeat})
    for dataset in ['co2-observed','wine-generated']:
        for repeat in range(1,4):
            # CO2 repeats one observed sequence; wine repeats three generated histories.
            for model in ['revon-m','revon-h','dolt']:
                cases.append({'name':f'{dataset}-{repeat}-{model}','suite':'public','dataset':dataset,'seed':202610200+repeat,
                              'replicate':repeat,'model':model,'monitor':True})
    for n in [100000,1000000]:
        for repeat in range(1,4):
            for model in ['revon-m','revon-h','dolt']:
                spec=WorkloadSpec(f'scale-n{n}-seed{202610220+repeat}',n,4,64,202610220+repeat)
                cases.append({'name':f'scale-{n}-{repeat}-{model}','suite':'scale','spec':asdict(spec),'model':model,'monitor':True,'replicate':repeat})
    # Rotate cross-system order by replicate before any timing is observed.
    for suite in ['public','scale']:
        indices=[i for i,c in enumerate(cases) if c['suite']==suite]
        for i in range(0,len(indices),3):
            group=[cases[j] for j in indices[i:i+3]];shift=(group[0]['replicate']-1)%3
            group=group[shift:]+group[:shift]
            for j,c in zip(indices[i:i+3],group):cases[j]=c
    return cases

def prepare(output,public_sources):
    meta=verify_sources(public_sources)
    output.mkdir(parents=True,exist_ok=False)
    sources={p:sha((ROOT/p).read_bytes()) for p in SOURCES}
    for p in SOURCES:
        target=output/'source'/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/p,target)
    protocol={'created_utc':now(),'cases':definitions(),'thresholds':THRESHOLDS,'warmups':WARMUPS,'trials':TRIALS,
      'selection_rule':'equal-weight calibration-case mean hybrid median / faster forced-path median; tie -> smaller threshold; freeze before validation',
      'units':'independent generated seed histories within fixed profiles; repeated cached queries within one durable repository; 3 CO2 fresh-repository repetitions share one observed sequence',
      'scope':'author-run Windows local campaign; no cross-machine pooling or independent-party reproduction',
      'failure_policy':'record failure and halt; no exclusion based on observed latency; changed source requires a new campaign',
      'timing':'diff API plus canonical output; observed equality checks, decision probes and all-history/reopen verification outside timers',
      'cache':'resident objects and filesystem cache retained; no cold-cache claim; fresh worker/repository per case',
      'uncertainty':'per-case median/IQR and paired ratios; seed-level median/range (n=3), not population confidence intervals; no multiple-testing claim',
      'scale':'3 separate generated histories/repositories per size/system; 2 warmup + 7 cached queries per repository; initial import/commit/checkout recorded once per repository',
      'sensitivity':'staged matched design, not full factorial; N fixed for locality/density; H and changes/commit necessarily trade off at fixed operation count; hash-route C8 has matched spread C8',
      'monitor':'paired worker-condition diagnostic at fixed history; no simultaneous workloads; not a causal exact correction',
      'public_source_sha256':sha((public_sources/'acquisition.json').read_bytes()),'public_sources':str(public_sources.resolve())}
    write(output/'protocol.json',protocol)
    env={'created_utc':now(),'python':sys.version,'platform':platform.platform(),'processor':platform.processor(),'machine':platform.machine(),
      'sqlite':sqlite3.sqlite_version,'psutil':psutil.__version__,'dolt':subprocess.check_output(['dolt','version'],text=True).splitlines()[0],
      'logical_cpus':psutil.cpu_count(),'physical_cpus':psutil.cpu_count(logical=False),'memory':psutil.virtual_memory()._asdict(),
      'disk':psutil.disk_usage(str(ROOT))._asdict(),'cpu_freq':psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
      'hashseed':'20261016 for all workers','source_hashes':sources,'protocol_sha256':sha((output/'protocol.json').read_bytes()),
      'background_processes':[{'name':p.info['name'],'pid':p.info['pid']} for p in psutil.process_iter(['name','pid'])],
      'io_scope':'OS-reported process I/O; Windows counts are not proof of physical disk activity; worker plus descendants; includes setup and verification'}
    write(output/'manifest.json',env)
    return protocol

class PhasedDolt(DoltAdapter):
    """Instrument the same native JSON-diff contract as the production adapter."""
    def diff(self,left,right):
        if not 1<=left<=right<=len(self.version_hashes):raise KeyError('invalid versions')
        begin=time.perf_counter_ns()
        output=self._run(['diff','-r','json',self.version_hashes[left-1],self.version_hashes[right-1],'records']).stdout
        command=(time.perf_counter_ns()-begin)/1e6
        begin=time.perf_counter_ns();parsed=self._parse_diff_json(output);parse=(time.perf_counter_ns()-begin)/1e6
        begin=time.perf_counter_ns();result=canonical_diff_bytes(parsed);encode=(time.perf_counter_ns()-begin)/1e6
        self.last_phases={'command_ms':command,'parse_ms':parse,'canonical_ms':encode}
        return result

def expected_diff(workload):
    a,b=workload.states[0],workload.states[-1]
    return {k:(value_digest(a.get(k)),value_digest(b.get(k))) for k in workload.expected_diff_keys}

def oracle_bytes(expected):
    return canonical_bytes({'changes':[{'key':k,'old_value_sha256':a,'new_value_sha256':b} for k,(a,b) in sorted(expected.items())]})

def aggregate_io(counters,io_pids):
    # Empty supported sample set means unavailable; observed all-zero is zero.
    return (sum(counters[p][1] or 0 for p in io_pids),sum(counters[p][2] or 0 for p in io_pids)) if io_pids else (None,None)

def check_output(output,expected):
    observed=decode_diff_bytes(output)
    if observed!=expected:raise ValueError('observed diff disagrees with semantic oracle')
    return sha(output)

def worker(config):
    case=config['case'];output=Path(config['output']);case_dir=output/'cases'/case['name'];case_dir.mkdir(parents=True,exist_ok=False)
    write(case_dir/'started.json',{'started_utc':now(),'case':case})
    begin=time.perf_counter()
    if case.get('dataset'):workload=public_workload(Path(config['public_sources']),case['dataset'],case['seed'])
    else:workload=build_workload(WorkloadSpec(**case['spec']))
    expected=expected_diff(workload);right=len(workload.states)
    repo_path=case_dir/'repository';repo_path.mkdir()
    commands=0
    if case['suite'] in ['calibration','validation','sensitivity','monitor']:
        adapter=RevonAdapter(repo_path,strategy='hybrid',hybrid_threshold=4096,branching_factor=case['b'],tree_depth=case['d'])
        configs=[('log',0),('merkle',0)]+[('hybrid',t) for t in THRESHOLDS]
    elif case['model']=='dolt':adapter=PhasedDolt(repo_path);configs=[('dolt',0)]
    else:
        adapter=RevonAdapter(repo_path,strategy='merkle' if case['model']=='revon-m' else 'hybrid',hybrid_threshold=4096)
        configs=[(adapter.strategy_requested,4096)]
    start=time.perf_counter_ns();adapter.initial_import(workload.initial);import_ms=(time.perf_counter_ns()-start)/1e6
    commit_times=[]
    for batch in workload.batches:
        start=time.perf_counter_ns();adapter.commit(batch);commit_times.append((time.perf_counter_ns()-start)/1e6)
    records=[]
    for kind,count in [('warmup',WARMUPS),('measured',TRIALS)]:
        for trial in range(1,count+1):
            order=list(configs);random.Random(f"{workload.digest}/{kind}/{trial}").shuffle(order)
            for position,(strategy,threshold) in enumerate(order,1):
                if isinstance(adapter,RevonAdapter):
                    adapter.strategy_requested=strategy;adapter.repository.database.hybrid_log_threshold=threshold
                start=time.perf_counter_ns();observed=adapter.diff(1,right);diff_ms=(time.perf_counter_ns()-start)/1e6
                output_hash=check_output(observed,expected)
                decision_ms=None
                if isinstance(adapter,RevonAdapter):
                    start=time.perf_counter_ns();choice=selection(adapter.repository.database,1,right,threshold);decision_ms=(time.perf_counter_ns()-start)/1e6
                    selected=adapter.repository.last_diff_stats.strategy
                    wanted=strategy if strategy!='hybrid' else choice['selected']
                    if selected!=wanted:raise ValueError('selected path disagreement')
                else:selected='dolt-native'
                record={'case':case['name'],'suite':case['suite'],'trial_kind':kind,'trial':trial,'execution_order':position,
                  'strategy':strategy,'threshold':threshold,'selected':selected,'diff_ms':diff_ms,'decision_probe_ms':decision_ms,
                  'output_sha256':output_hash,'correctness':True}
                if isinstance(adapter,PhasedDolt):record.update(adapter.last_phases)
                records.append(record)
    # No state verification or hash-oracle work is inside operation timers.
    history=[]
    for version,state in enumerate(workload.states,1):
        observed=adapter.checkout(version);observed_sha=sha(observed);oracle_sha=sha(canonical_state_bytes(state))
        if observed_sha!=oracle_sha:raise ValueError('historical state disagreement')
        history.append({'version':version,'observed_sha256':observed_sha,'oracle_sha256':oracle_sha})
    start=time.perf_counter_ns();checkout_output=adapter.checkout(right);checkout_ms=(time.perf_counter_ns()-start)/1e6
    if sha(checkout_output)!=history[-1]['oracle_sha256']:raise ValueError('timed checkout disagreement')
    integrity=None
    if isinstance(adapter,RevonAdapter):
        for strategy in ['log','merkle','hybrid']:
            if adapter.repository.diff_versions(1,1,strategy):raise ValueError('identity diff disagreement')
            reverse=adapter.repository.diff_versions(right,1,strategy)
            check_output(canonical_diff_bytes({e.key:(e.old_value,e.new_value) for e in reverse}),{k:(b,a) for k,(a,b) in expected.items()})
        integrity=asdict(adapter.repository.verify_integrity())
    adapter.close()
    if isinstance(adapter,RevonAdapter):
        with SQLiteRevonRepository.open(repo_path/'revon.sqlite') as reopened:
            if sha(canonical_state_bytes(reopened.checkout(right)))!=history[-1]['oracle_sha256']:raise ValueError('reopen disagreement')
    size=sum(p.stat().st_size for p in repo_path.rglob('*') if p.is_file())
    result={'case':case,'finished_utc':now(),'workload_sha256':workload.digest,'initial_rows':len(workload.initial),'commits':len(workload.batches),
      'operations':sum(map(len,workload.batches)),'changes_per_commit':[len(b) for b in workload.batches],
      'expected_changed_keys':len(expected),'oracle_diff_sha256':sha(oracle_bytes(expected)),
      'history':history,'integrity':integrity,'import_ms':import_ms,'commit_ms':commit_times,'checkout_ms':checkout_ms,
      'storage_bytes':size,'records':records,'duration_seconds':time.perf_counter()-begin,'correctness':True}
    write(case_dir/'result.json',result)
    # Remove only the known scratch repository beneath this case, after successful verification.
    cleanup_repository(repo_path,case_dir)
    return result

def run_worker(output,case,protocol):
    config={'case':case,'output':str(output.resolve()),'public_sources':protocol['public_sources']}
    path=output/'worker-configs'/(case['name']+'.json');write(path,config)
    env={**os.environ,'PYTHONHASHSEED':'20261016','PYTHONIOENCODING':'utf-8'}
    stdout=output/'logs'/(case['name']+'.stdout');stderr=output/'logs'/(case['name']+'.stderr');stdout.parent.mkdir(exist_ok=True)
    started=now();stop=threading.Event();peaks=[0];counters={};io_pids=set()
    with stdout.open('w',encoding='utf8') as out,stderr.open('w',encoding='utf8') as err:
        process=subprocess.Popen([sys.executable,'-m','experiments.review_revision','--worker',str(path)],cwd=ROOT,env=env,stdout=out,stderr=err)
        tracked=psutil.Process(process.pid)
        def sample():
            while not stop.is_set():
                rss=0
                try:children=[tracked,*tracked.children(recursive=True)]
                except psutil.Error:children=[]
                for child in children:
                    try:
                        rss+=child.memory_info().rss;cpu=child.cpu_times();old=counters.get(child.pid,(0.0,None,None))
                        reads,writes=old[1],old[2]
                        try:
                            io_counts=child.io_counters();reads=max(reads or 0,io_counts.read_bytes);writes=max(writes or 0,io_counts.write_bytes);io_pids.add(child.pid)
                        except (psutil.Error,AttributeError,NotImplementedError,OSError):pass
                        counters[child.pid]=(max(old[0],cpu.user+cpu.system),reads,writes)
                    except psutil.Error:pass
                peaks[0]=max(peaks[0],rss);stop.wait(.01)
        thread=threading.Thread(target=sample,daemon=True)
        if case['monitor']:thread.start()
        try:code=process.wait(timeout=1800)
        except subprocess.TimeoutExpired:
            for child in tracked.children(recursive=True):
                try:child.kill()
                except psutil.Error:pass
            process.kill();process.wait();code=-1
        finally:
            stop.set()
            if case['monitor']:thread.join()
    reads,writes=aggregate_io(counters,io_pids)
    telemetry={'started_utc':started,'finished_utc':now(),'monitor_enabled':case['monitor'],'sample_interval_ms':10,
      'peak_rss_bytes':peaks[0] if case['monitor'] else None,'cpu_seconds':sum(x[0] for x in counters.values()) if counters else None,
      'os_read_bytes':reads,'os_write_bytes':writes,
      'scope':'worker and sampled descendants, including setup and verification; OS-reported I/O, not physical/logical database reads'}
    write(output/'cases'/case['name']/'telemetry.json',telemetry)
    if code!=0:
        write(output/'failures'/(case['name']+'.json'),{'returncode':code,'started_utc':started,'stderr':stderr.read_text(encoding='utf8')})
        raise RuntimeError(f"worker failed: {case['name']}; see {stderr}")

def source_check(output):
    manifest=read(output/'manifest.json')
    for p,h in manifest['source_hashes'].items():
        if sha((ROOT/p).read_bytes())!=h or sha((output/'source'/p).read_bytes())!=h:raise ValueError(f'frozen source changed: {p}')
    if sha((output/'protocol.json').read_bytes())!=manifest['protocol_sha256']:raise ValueError('protocol changed')

def freeze(output,protocol):
    scores={}
    for threshold in THRESHOLDS:
        ratios=[]
        for case in protocol['cases']:
            if case['suite']!='calibration':continue
            records=[r for r in read(output/'cases'/case['name']/'result.json')['records'] if r['trial_kind']=='measured']
            med=lambda s,t:statistics.median(r['diff_ms'] for r in records if (r['strategy'],r['threshold'])==(s,t))
            ratios.append(med('hybrid',threshold)/min(med('log',0),med('merkle',0)))
        scores[threshold]=statistics.mean(ratios)
    selected=min(THRESHOLDS,key=lambda t:(scores[t],t))
    selection={'created_utc':now(),'threshold':selected,'scores':scores,'validation_not_started':True,'rule':protocol['selection_rule']}
    path=output/'frozen_selection.json'
    if path.exists():
        if read(path)['threshold']!=selected:raise ValueError('frozen selection changed')
    else:write(path,selection)

def execute(output,suites):
    source_check(output);protocol=read(output/'protocol.json')
    for case in protocol['cases']:
        if case['suite'] not in suites:continue
        if case['suite']=='validation':freeze(output,protocol)
        result=output/'cases'/case['name']/'result.json'
        if result.exists():continue
        print(f"START {case['name']}",flush=True)
        run_worker(output,case,protocol)
        r=read(result);print(f"OK {case['name']}: {len(r['records'])} checked queries, {r['duration_seconds']:.1f}s",flush=True)
    audit(output,require_complete=False)

def audit(output,require_complete=True):
    source_check(output);protocol=read(output/'protocol.json');results=[];pending=[]
    for case in protocol['cases']:
        p=output/'cases'/case['name']/'result.json'
        if not p.exists():pending.append(case['name']);continue
        result=read(p)
        if result['case']!=case or not result['correctness']:raise ValueError('case identity/correctness mismatch')
        expected_configs=6 if case['suite'] in ['calibration','validation','sensitivity','monitor'] else 1
        if len(result['records'])!=(WARMUPS+TRIALS)*expected_configs:raise ValueError('query count mismatch')
        identities=set()
        for r in result['records']:
            identity=(r['trial_kind'],r['trial'],r['strategy'],r['threshold'])
            if identity in identities:raise ValueError('duplicate trial identity')
            identities.add(identity)
            if not r['correctness'] or r['output_sha256']!=result['oracle_diff_sha256']:raise ValueError('semantic proof mismatch')
            if r['case']!=case['name'] or r['suite']!=case['suite'] or r['trial_kind'] not in ['warmup','measured']:raise ValueError('query identity mismatch')
            if r['trial'] not in range(1,(WARMUPS if r['trial_kind']=='warmup' else TRIALS)+1):raise ValueError('trial index mismatch')
            if r['diff_ms']<0 or not __import__('math').isfinite(r['diff_ms']):raise ValueError('invalid timing')
            if r['strategy']=='hybrid' and r['selected']!=('log' if result['operations']<=r['threshold'] else 'merkle'):raise ValueError('path mismatch')
        if len(result['history'])!=result['commits']+1 or any(h['observed_sha256']!=h['oracle_sha256'] for h in result['history']):raise ValueError('history proof mismatch')
        results.append(result)
        if require_complete:
            workload=public_workload(Path(protocol['public_sources']),case['dataset'],case['seed']) if case.get('dataset') else build_workload(WorkloadSpec(**case['spec']))
            if workload.digest!=result['workload_sha256'] or sha(oracle_bytes(expected_diff(workload)))!=result['oracle_diff_sha256']:raise ValueError('regenerated workload/oracle mismatch')
            for state,proof in zip(workload.states,result['history']):
                if sha(canonical_state_bytes(state))!=proof['oracle_sha256']:raise ValueError('regenerated state mismatch')
            del workload
    if (output/'frozen_selection.json').exists():
        frozen=read(output/'frozen_selection.json')
        for r in results:
            if r['case']['suite']=='validation' and read(output/'cases'/r['case']['name']/'started.json')['started_utc']<=frozen['created_utc']:raise ValueError('validation preceded freeze')
    failures=list((output/'failures').glob('*.json')) if (output/'failures').exists() else []
    report={'passed':not pending and not failures,'completed_cases':len(results),'planned_cases':len(protocol['cases']),
      'queries':sum(len(r['records']) for r in results),'measured_queries':sum(sum(x['trial_kind']=='measured' for x in r['records']) for r in results),
      'pending':pending,'failures':[p.name for p in failures],'scope':'internal accounting/hash checks, not independent timing reproduction','checked_utc':now()}
    write(output/'audit.json',report)
    if require_complete and not report['passed']:raise ValueError('campaign incomplete; see audit.json')
    return report

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);parser.add_argument('--prepare',action='store_true');parser.add_argument('--public-sources',type=Path)
    parser.add_argument('--worker',type=Path);parser.add_argument('--audit',action='store_true');parser.add_argument('--suites',default='calibration,validation,sensitivity,monitor,public,scale')
    args=parser.parse_args()
    if args.worker:
        try:worker(read(args.worker))
        except Exception:traceback.print_exc();raise
    elif args.prepare:print(json.dumps({'cases':len(prepare(args.output,args.public_sources)['cases'])}))
    elif args.audit:print(json.dumps(audit(args.output),indent=2))
    else:execute(args.output,set(args.suites.split(',')))

if __name__=='__main__':main()
