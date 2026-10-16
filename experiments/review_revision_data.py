"""Acquire two bounded public sources and retain record-level provenance.

CO2 uses observed file revisions; wine uses explicitly generated corrections.
No production database code or historical experiment records are modified.
"""
from __future__ import annotations
import csv,io,json,hashlib,random,subprocess,urllib.request,zipfile
from pathlib import Path
from datetime import datetime,timezone
from .workloads import Mutation,Workload,WorkloadSpec

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)

def sha(data):return hashlib.sha256(data).hexdigest()

def download(url,target):
    data=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Revon-research-revision/1.0'}),timeout=90).read()
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    return {'url':url,'file':target.name,'sha256':sha(data),'bytes':len(data)}

def acquire(directory,frozen_manifest=None):
    directory.mkdir(parents=True,exist_ok=False)
    if frozen_manifest is not None:
        original=json.loads(Path(frozen_manifest).read_text(encoding='utf8'))
        entries=original['co2']['records']+[original['co2']['datapackage']]+original['wine']['records']
        for record in entries:
            downloaded=download(record['url'],directory/record['file'])
            if downloaded['sha256']!=record['sha256']:raise ValueError('download differs from frozen source')
        (directory/'acquisition.json').write_text(json.dumps(original,indent=2),encoding='utf8')
        co2_states(directory);wine_state(directory)
        return original
    commits=json.loads(subprocess.check_output(['gh','api','repos/datasets/co2-ppm/commits?path=data/co2-mm-mlo.csv&per_page=11'],text=True))
    selected=[{'sha':c['sha'],'date':c['commit']['committer']['date']} for c in reversed(commits)]
    records=[]
    for i,c in enumerate(selected):
        r=download(f"https://raw.githubusercontent.com/datasets/co2-ppm/{c['sha']}/data/co2-mm-mlo.csv",directory/f'co2-{i:02d}.csv')
        records.append({**c,**r})
    metadata=download(f"https://raw.githubusercontent.com/datasets/co2-ppm/{selected[-1]['sha']}/datapackage.json",directory/'co2-datapackage.json')
    wine=download('https://archive.ics.uci.edu/static/public/186/wine+quality.zip',directory/'wine-quality.zip')
    result={'created_utc':datetime.now(timezone.utc).isoformat(),
      'co2':{'source':'https://github.com/datasets/co2-ppm','upstream':'NOAA Mauna Loa monthly CO2','license':'Open Data Commons Public Domain Dedication and License v1.0; verify retained datapackage',
      'selection':'11 most recent file-changing commits returned before any timing; chronological order; repository revisions, not original NOAA transaction logs',
      'history_kind':'observed published CSV snapshots; record differences reconstructed between adjacent retained snapshots',
      'key':'Date column; no renames inferred; absent keys are deletions; entire canonical CSV row retained as strings',
      'loss':'CSV formatting and row order ignored; one row per date; changes between sampled revisions are not reconstructed',
      'records':records,'datapackage':metadata},
      'wine':{'source':'https://archive.ics.uci.edu/dataset/186/wine+quality','doi':'10.24432/C56S3T','license':'CC BY 4.0',
      'attribution':'Cortez, Cerdeira, Almeida, Matos and Reis (2009), Wine Quality, UCI Machine Learning Repository',
      'history_kind':'generated seeded updates; not observed wine revisions','key':'wine colour plus original physical row ordinal; not a longitudinal specimen identifier',
      'records':[wine]}}
    result['co2']['premeasurement_exclusions']=[{'file':r['file'],'reason':'Header-only upstream publication failure; retained raw, excluded before timing; primary sequence joins adjacent nonempty published snapshots'} for r in records if len(list(csv.reader(io.StringIO((directory/r['file']).read_text(encoding='utf-8-sig')))))==1]
    result['co2']['extra_columns']='Source rows contain unnamed trailing fields beyond six headers; retain them as _extra_0 etc, without interpreting or dropping them'
    (directory/'acquisition.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    # Validate all source schemas before a performance protocol is frozen.
    co2_states(directory);wine_state(directory)
    return result

def verify_sources(directory):
    meta=json.loads((directory/'acquisition.json').read_text())
    for section in ['co2','wine']:
        for record in meta[section]['records']:
            if sha((directory/record['file']).read_bytes())!=record['sha256']:raise ValueError('source checksum mismatch')
    r=meta['co2']['datapackage']
    if sha((directory/r['file']).read_bytes())!=r['sha256']:raise ValueError('datapackage checksum mismatch')
    return meta

def co2_states(directory):
    states=[]
    meta=json.loads((directory/'acquisition.json').read_text())
    for record in meta['co2']['records']:
        lines=list(csv.reader(io.StringIO((directory/record['file']).read_text(encoding='utf-8-sig'))))
        if not lines or 'Date' not in lines[0]:raise ValueError(f"CO2 schema mismatch: {record['file']}")
        # A retained header-only publication failure is excluded before timing,
        # not interpreted as every atmospheric observation being deleted.
        if len(lines)==1:continue
        header=lines[0];rows=[]
        for values in lines[1:]:
            if len(values)<len(header):raise ValueError('truncated CO2 row')
            rows.append({header[i] if i<len(header) else f'_extra_{i-len(header)}':value for i,value in enumerate(values)})
        state={row['Date']:canonical(row) for row in rows}
        if len(state)!=len(rows):raise ValueError('duplicate CO2 date')
        states.append(state)
    return states

def wine_state(directory):
    result={}
    with zipfile.ZipFile(directory/'wine-quality.zip') as z:
        for colour in ['red','white']:
            rows=list(csv.DictReader(io.StringIO(z.read(f'winequality-{colour}.csv').decode('utf8')),delimiter=';'))
            if not rows or 'quality' not in rows[0]:raise ValueError('wine schema mismatch')
            for i,row in enumerate(rows):result[f'wine/{colour}/{i:06d}']=canonical(row)
    return result

def from_states(name,states,seed):
    batches=[]
    for before,after in zip(states,states[1:]):
        batch=tuple(Mutation(k,k in before,before.get(k),k in after,after.get(k)) for k in sorted(set(before)|set(after)) if before.get(k)!=after.get(k))
        if not batch:raise ValueError('empty observed revision: protocol requires an actual record change')
        batches.append(batch)
    digest=sha(canonical({'states':states}).encode())
    spec=WorkloadSpec(name,len(states[0]),len(batches),max(map(len,batches)),seed)
    return Workload(spec,states[0],tuple(batches),tuple(states),digest)

def public_workload(directory,name,seed=202610160):
    verify_sources(directory)
    if name=='co2-observed':return from_states(name,co2_states(directory),seed)
    if name!='wine-generated':raise ValueError(name)
    rng=random.Random(seed);state=wine_state(directory);states=[dict(state)]
    for revision in range(1,9):
        for key in rng.sample(sorted(state),64):
            row=json.loads(state[key]);row['quality']=str((int(row['quality'])+1)%11);state[key]=canonical(row)
        states.append(dict(state))
    return from_states(name,states,seed)
