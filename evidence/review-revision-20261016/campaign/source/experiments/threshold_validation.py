"""Held-out selector calibration on shared durable repositories; no legacy edits.

Supplemental in-process repeated-query study, not independent repository trials.
Run with Python 3.14: python -m experiments.threshold_validation --output DIR
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import platform
import random
import shutil
import statistics
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from .adapters import canonical_diff_bytes, decode_diff_bytes
from .workloads import WorkloadSpec, build_workload
from sqlite_store import SQLiteRevonRepository

THRESHOLDS = (1024, 2048, 4096, 8192, 16384)
OPERATIONS = (512, 1024, 2048, 4096, 8192, 16384, 32768)
# Split is predefined before measurements. Each tuple uses a distinct seed.
PROFILES = (
    ("calibration", 10000, 4, "spread", 20261003),
    ("calibration", 100000, 16, "spread", 20261004),
    ("calibration", 10000, 64, "repeated-key", 20261005),
    ("validation", 100000, 4, "repeated-key", 20261006),
    ("validation", 10000, 16, "spread", 20261007),
    ("validation", 100000, 64, "spread", 20261008),
)

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def percentile(values, q):
    values = sorted(values); x = (len(values)-1)*q
    i = int(x); j = min(i+1, len(values)-1)
    return values[i]*(1-(x-i)) + values[j]*(x-i)

def emit_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)

def selection(db, left, right, threshold):
    path = db._ancestor_path(left, right)
    reverse = False
    if path is None:
        path = db._ancestor_path(right, left); reverse = path is not None
    count = sum(len(db.changeset_store[db.commits[v].changeset_hash]) for v in path) if path is not None else None
    return {"operations": count, "reverse": reverse,
            "selected": "log" if count is not None and count <= threshold else "merkle"}

def run_case(directory, profile, operations, *, warmups=2, trials=7):
    split, rows, commits, locality, seed = profile
    name = f"{split}-n{rows}-h{commits}-{locality}-o{operations}"
    case = directory / "cases" / name
    case.mkdir(parents=True, exist_ok=True)
    complete = case / "result.json"
    if complete.exists():
        return json.loads(complete.read_text())
    spec = WorkloadSpec(name, rows, commits, operations//commits, seed)
    spec = WorkloadSpec(**{**asdict(spec), "locality": locality})
    workload = build_workload(spec)
    # Case-specific file enables interrupted execution to resume safely.
    path = case / "repository.sqlite"
    if path.exists():
        path.unlink()
    repo = SQLiteRevonRepository.create(path, hybrid_log_threshold=4096)
    start = time.perf_counter()
    root = repo.commit(workload.initial, message="threshold initial")
    for number, batch in enumerate(workload.batches, 1):
        root = repo.apply_changes(root,
            puts={m.key:m.new_value for m in batch if m.new_exists},
            deletes={m.key for m in batch if not m.new_exists},
            message=f"threshold revision {number}")
    construction_ms = (time.perf_counter()-start)*1000
    left, right = 1, commits+1
    expected = {key:(workload.states[0].get(key), workload.states[-1].get(key)) for key in workload.expected_diff_keys}
    from .adapters import value_digest
    expected_hashed = {k:(value_digest(a),value_digest(b)) for k,(a,b) in expected.items()}
    actual_count = selection(repo.database,left,right,4096)["operations"]
    assert actual_count == operations, (actual_count,operations)
    configs = [("log",0),("merkle",0)] + [("hybrid",t) for t in THRESHOLDS]
    records=[]
    for kind,count in (("warmup",warmups),("measured",trials)):
        for trial in range(1,count+1):
            order=list(configs)
            random.Random(f"{name}:{kind}:{trial}:{seed}").shuffle(order)
            for position,(strategy,threshold) in enumerate(order,1):
                repo.database.hybrid_log_threshold = threshold
                before=time.perf_counter_ns()
                entries=repo.diff_versions(left,right,strategy)
                output=canonical_diff_bytes({e.key:(e.old_value,e.new_value) for e in entries})
                elapsed=(time.perf_counter_ns()-before)/1e6
                stats=asdict(repo.last_diff_stats)
                assert decode_diff_bytes(output)==expected_hashed
                expected_path = strategy if strategy!="hybrid" else ("log" if operations<=threshold else "merkle")
                assert stats["strategy"]==expected_path
                before=time.perf_counter_ns()
                choice=selection(repo.database,left,right,threshold)
                decision_ms=(time.perf_counter_ns()-before)/1e6
                records.append(dict(scenario=name,split=split,rows=rows,commits=commits,
                    locality=locality,seed=seed,operations=operations,
                    changes_per_commit=operations//commits,trial_kind=kind,trial=trial,
                    execution_order=position,strategy=strategy,threshold=threshold,
                    selected=stats["strategy"],diff_ms=elapsed,
                    decision_probe_ms=decision_ms,correctness=True,
                    output_sha256=hashlib.sha256(output).hexdigest(),stats=stats))
    # Reverse, identity and reopen checks are outside timing.
    for strategy in ("log","merkle","hybrid"):
        assert repo.diff_versions(left,left,strategy)==[]
        reverse=repo.diff_versions(right,left,strategy)
        assert decode_diff_bytes(canonical_diff_bytes({e.key:(e.old_value,e.new_value) for e in reverse})) == {k:(b,a) for k,(a,b) in expected_hashed.items()}
    for version in (1,commits//2+1,commits+1):
        assert repo.checkout(version)==workload.states[version-1]
    components = [dict(kind=r[0],objects=r[1],payload_bytes=r[2]) for r in repo._connection.execute("SELECT kind,COUNT(*),SUM(length(payload)) FROM objects GROUP BY kind")]
    integrity=asdict(repo.verify_integrity())
    repo.close()
    footprint=path.stat().st_size
    with SQLiteRevonRepository.open(path) as reopened:
        assert reopened.checkout(right)==workload.states[-1]
        checked=reopened.diff_versions(left,right,"merkle")
        assert decode_diff_bytes(canonical_diff_bytes({e.key:(e.old_value,e.new_value) for e in checked}))==expected_hashed
    result=dict(spec=asdict(spec),workload_sha256=workload.digest,construction_ms=construction_ms,
                storage_bytes=footprint,components=components,integrity=integrity,
                semantic_checks=True,records=records)
    complete.write_text(json.dumps(result,indent=2),encoding="utf-8")
    # Retain measurements and checks, not bulky reproducible repositories.
    path.unlink()
    print(f"completed {name}: {len(records)} checked queries",flush=True)
    return result

def summarize(results):
    summaries=[]
    for case in results:
        measured=[r for r in case["records"] if r["trial_kind"]=="measured"]
        for strategy,threshold in [("log",0),("merkle",0)]+[("hybrid",t) for t in THRESHOLDS]:
            selected=[r for r in measured if (r["strategy"],r["threshold"])==(strategy,threshold)]
            values=[r["diff_ms"] for r in selected]
            summaries.append({k:selected[0][k] for k in ("scenario","split","rows","commits","locality","seed","operations","changes_per_commit","strategy","threshold","selected")} |
                dict(n=len(values),median_ms=statistics.median(values),p25_ms=percentile(values,.25),p75_ms=percentile(values,.75),
                decision_probe_median_ms=statistics.median(r["decision_probe_ms"] for r in selected),storage_bytes=case["storage_bytes"]))
    return summaries

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--output",type=Path,required=True); parser.add_argument("--pilot",action="store_true")
    args=parser.parse_args(); directory=args.output; directory.mkdir(parents=True,exist_ok=True)
    sources=[Path(p) for p in ("experiments/threshold_validation.py","experiments/workloads.py","experiments/adapters.py","sqlite_store.py","versioned_db.py")]
    hashes={str(p):digest(p) for p in sources}
    manifest_path=directory/"manifest.json"
    if manifest_path.exists():
        assert json.loads(manifest_path.read_text())["source_code_sha256"]==hashes,"source changed during resume"
    else:
        import psutil
        manifest=dict(study="held-out operation threshold",mode="pilot" if args.pilot else "evaluation",created_utc=datetime.now(timezone.utc).isoformat(),
            python=platform.python_version(),platform=platform.platform(),processor=platform.processor(),
            logical_cpus=psutil.cpu_count(),ram_bytes=psutil.virtual_memory().total,available_ram_bytes=psutil.virtual_memory().available,
            thresholds=THRESHOLDS,operations=OPERATIONS,profiles=PROFILES,warmups=2,measured_queries=7,
            scope="same-repository in-process repeated queries; one fixed workload per profile/count; cached objects; no cross-machine or repeated-repository uncertainty",
            timing="diff_versions plus shared canonical output; correctness and standalone decision probes outside timed diff; ancestry/count probe not a causal overhead subtraction",
            selection_rule="equal-weight mean latency divided by faster forced-path median over calibration cases; lowest score; exact tie chooses smaller threshold; freeze before validation",
            source_code_sha256=hashes)
        manifest_path.write_text(json.dumps(manifest,indent=2))
        for p in sources:
            target=directory/"source"/p; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,target)
    profiles=PROFILES[:1] if args.pilot else PROFILES
    operations=OPERATIONS[-1:] if args.pilot else OPERATIONS
    results=[]
    for split in ("calibration","validation"):
        if split=="validation" and not args.pilot:
            cal=summarize(results)
            scores={t:statistics.mean(r["median_ms"]/min(x["median_ms"] for x in cal if x["scenario"]==r["scenario"] and x["strategy"] in ("log","merkle")) for r in cal if r["strategy"]=="hybrid" and r["threshold"]==t) for t in THRESHOLDS}
            winner=min(THRESHOLDS,key=lambda t:(scores[t],t))
            frozen=dict(threshold=winner,calibration_scores=scores,frozen_utc=datetime.now(timezone.utc).isoformat(),validation_started=False)
            freeze_path=directory/"frozen_selection.json"
            if freeze_path.exists():
                assert json.loads(freeze_path.read_text())["threshold"]==winner
            else:
                freeze_path.write_text(json.dumps(frozen,indent=2))
            print(f"FROZEN threshold {winner}; now executing held-out cases",flush=True)
        for profile in profiles:
            if profile[0]!=split: continue
            for count in operations:
                results.append(run_case(directory,profile,count))
    summary=summarize(results); emit_csv(directory/"summary.csv",summary)
    raw=[r for c in results for r in c["records"]]; emit_csv(directory/"raw_results.csv",raw)
    audit=dict(passed=all(c["semantic_checks"] for c in results) and all(r["correctness"] for r in raw),cases=len(results),queries=len(raw),measured=sum(r["trial_kind"]=="measured" for r in raw),source_hashes_current=hashes)
    (directory/"audit.json").write_text(json.dumps(audit,indent=2))
    print(json.dumps(audit),flush=True)

if __name__=="__main__": main()
