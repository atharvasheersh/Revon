"""Read-only accounting and summary check for the production-prefix diagnostic."""
from pathlib import Path
import ast,copy,hashlib,json,statistics

ROOT=Path(__file__).resolve().parents[1]
DIAGNOSTIC_SOURCE='tools/publication_assets/selector_cost_source_20261016.py'

def expected_prefix(source):
    """Independently derive the AST from archived production bytes, without exec.

    AST comparison ignores comments, quote style and whitespace. Statements,
    signatures and expressions must match; location attributes are ignored.
    """
    tree=ast.parse(source)
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='VersionedDatabase')
    function=copy.deepcopy(next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='diff_versions'))
    def dispatch(node):
        if not isinstance(node,ast.If):return False
        test=node.test
        return (isinstance(test,ast.Compare) and isinstance(test.left,ast.Name) and test.left.id=='selected'
          and len(test.ops)==1 and isinstance(test.ops[0],ast.Eq) and len(test.comparators)==1
          and isinstance(test.comparators[0],ast.Constant) and test.comparators[0].value=='log')
    index=next(i for i,node in enumerate(function.body) if dispatch(node))
    function.body=function.body[:index]+[ast.Return(value=ast.Name(id='selected',ctx=ast.Load()))]
    function.name='production_decision_prefix'
    return ast.Module(body=[function],type_ignores=[])

def check_provenance(root,protocol):
    frozen=root/'evidence/review-revision-20261016/campaign'
    manifest=json.loads((frozen/'manifest.json').read_text(encoding='utf8'))
    source=frozen/'source/versioned_db.py'
    actual=hashlib.sha256(source.read_bytes()).hexdigest()
    if actual!=manifest['source_hashes']['versioned_db.py'] or actual!=protocol['versioned_db_sha256']:raise ValueError('selector-cost production source mismatch')
    expected_names={'experiments/selector_cost.py','experiments/workloads.py','experiments/adapters.py','sqlite_store.py'}
    if set(protocol['source_hashes'])!=expected_names:raise ValueError('selector-cost source identities missing')
    for name,h in protocol['source_hashes'].items():
        path=root/DIAGNOSTIC_SOURCE if name=='experiments/selector_cost.py' else frozen/'source'/name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=h:raise ValueError('selector-cost retained source mismatch: '+name)
        if name!='experiments/selector_cost.py' and manifest['source_hashes'][name]!=h:raise ValueError('selector-cost campaign source mismatch: '+name)
    prefix=root/'evidence/selector-cost-20261016/extracted_prefix.py'
    code=prefix.read_text(encoding='utf8')
    if hashlib.sha256(code.encode()).hexdigest()!=protocol['prefix_sha256']:raise ValueError('selector-cost extracted code mismatch')
    if ast.dump(ast.parse(code),include_attributes=False)!=ast.dump(expected_prefix(source.read_text(encoding='utf8')),include_attributes=False):raise ValueError('selector-cost prefix differs from archived production function')
    original=json.loads((frozen/'protocol.json').read_text(encoding='utf8'))
    if protocol['cases']!=[c for c in original['cases'] if c['suite']=='validation']:raise ValueError('selector-cost validation histories mismatch')
    return {'production_source_verified':True,'retained_source_files':1+len(expected_names),'prefix_ast_verified':True}

def check(root=ROOT):
    folder=root/'evidence/selector-cost-20261016'
    load=lambda p:json.loads(p.read_text(encoding='utf8'))
    hashes=load(folder/'SHA256SUMS.json')
    for name,h in hashes.items():
        if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=h:raise ValueError('selector-cost checksum mismatch: '+name)
    protocol=load(folder/'protocol.json');provenance=check_provenance(root,protocol);medians=[];batches=0;calls=0;measured=0
    if (protocol['thresholds'],protocol['warmup_batches'],protocol['measured_batches'],protocol['calls_per_batch'])!=([4096,65536],2,7,1000):raise ValueError('selector-cost batch protocol mismatch')
    frozen=root/'evidence/review-revision-20261016/campaign'
    for case in protocol['cases']:
        observed=load(folder/(case['name']+'.json'));original=load(frozen/'cases'/case['name']/'result.json')
        if observed['case']!=case or observed['workload_sha256']!=original['workload_sha256']:raise ValueError('selector-cost history mismatch')
        rows=observed['records']
        expected={(t,kind,i) for t in protocol['thresholds'] for kind,n in [('warmup',2),('measured',7)] for i in range(1,n+1)}
        if len(rows)!=18 or {(r['threshold'],r['trial_kind'],r['batch']) for r in rows}!=expected:raise ValueError('selector-cost query matrix mismatch')
        for row in rows:
            expected_path='log' if original['operations']<=row['threshold'] else 'merkle'
            if row['calls']!=1000 or row['selected']!=expected_path or row['elapsed_ns']<=0 or row['ns_per_call']!=row['elapsed_ns']/1000:raise ValueError('selector-cost observation mismatch')
            calls+=row['calls'];measured+=row['calls'] if row['trial_kind']=='measured' else 0
        batches+=len(rows)
        for t in protocol['thresholds']:medians.append(statistics.median(r['ns_per_call'] for r in rows if r['trial_kind']=='measured' and r['threshold']==t))
    retained=load(folder/'summary.json')
    expected={'cases':18,'batches':batches,'timed_calls':calls,'measured_calls':measured,
      'case_threshold_median_us':statistics.median(medians)/1000,'min_case_threshold_median_us':min(medians)/1000,'max_case_threshold_median_us':max(medians)/1000,'passed':True,'scope':protocol['scope']}
    if expected!=retained:raise ValueError('selector-cost summary mismatch')
    return {'passed':True,'cases':18,'measured_calls':measured,'provenance':provenance,'scope':'warm production-prefix diagnostic; not causal overhead or new selector tuning'}

if __name__=='__main__':print(json.dumps(check(),indent=2))
