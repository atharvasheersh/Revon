"""Derive reviewer-revision summaries from retained case records, without timing."""
from __future__ import annotations
import argparse,csv,json,statistics,hashlib
from pathlib import Path
from collections import defaultdict

def load(path):return json.loads(Path(path).read_text(encoding='utf8'))
def save(path,value):Path(path).write_text(json.dumps(value,indent=2),encoding='utf8')
def median(xs):return statistics.median(list(xs))
def quantile(xs,q):
    xs=sorted(xs);at=(len(xs)-1)*q;i=int(at);j=min(i+1,len(xs)-1)
    return xs[i]*(1-(at-i))+xs[j]*(at-i)
def csv_write(path,rows):
    with Path(path).open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for row in rows for k in row)));w.writeheader();w.writerows(rows)
def measured(result):return [r for r in result['records'] if r['trial_kind']=='measured']
def grouped_medians(result):
    groups=defaultdict(list)
    for row in measured(result):groups[(row['strategy'],row['threshold'])].append(row)
    return {key:median(r['diff_ms'] for r in rows) for key,rows in groups.items()}

def analyze(output,allow_incomplete=False):
    audit=load(output/'audit.json')
    if not allow_incomplete and not audit['passed']:raise ValueError('full audited campaign required for final analysis')
    protocol=load(output/'protocol.json');frozen=load(output/'frozen_selection.json')
    cases=[load(p) for p in sorted((output/'cases').glob('*/result.json'))]
    raw=[r for c in cases for r in c['records']];summary=[]
    for case in cases:
        grouped=defaultdict(list)
        for row in measured(case):grouped[(row['strategy'],row['threshold'])].append(row)
        telemetry=load(output/'cases'/case['case']['name']/'telemetry.json')
        for (strategy,threshold),rows in grouped.items():
            values=[r['diff_ms'] for r in rows]
            rec={'case':case['case']['name'],'suite':case['case']['suite'],'strategy':strategy,'threshold':threshold,
              'n':len(values),'median_ms':median(values),'p25_ms':quantile(values,.25),'p75_ms':quantile(values,.75),
              'selected':rows[0]['selected'],'operations':case['operations'],'rows':case['initial_rows'],'commits':case['commits'],
              'import_ms':case['import_ms'],'commit_median_ms':median(case['commit_ms']),'checkout_ms':case['checkout_ms'],
              'storage_bytes':case['storage_bytes'],'peak_worker_rss_bytes':telemetry['peak_rss_bytes'],
              'worker_cpu_seconds':telemetry['cpu_seconds'],'worker_os_read_bytes':telemetry['os_read_bytes'],'worker_os_write_bytes':telemetry['os_write_bytes']}
            for key in ['decision_probe_ms','command_ms','parse_ms','canonical_ms']:
                values=[r[key] for r in rows if r.get(key) is not None]
                rec[key+'_median']=median(values) if values else None
            summary.append(rec)
    selected=frozen['threshold'];selector=[]
    for case in cases:
        if case['case']['suite'] not in ['calibration','validation','sensitivity']:continue
        m=grouped_medians(case);best=min(m[('log',0)],m[('merkle',0)])
        faster='log' if m[('log',0)]<=m[('merkle',0)] else 'merkle'
        oldpath='log' if case['operations']<=4096 else 'merkle';newpath='log' if case['operations']<=selected else 'merkle'
        selector.append({'case':case['case']['name'],'suite':case['case']['suite'],**case['case']['spec'],
          'operations':case['operations'],'log_ms':m[('log',0)],'merkle_ms':m[('merkle',0)],'hybrid4096_ms':m[('hybrid',4096)],
          'calibrated_ms':m[('hybrid',selected)],'faster_forced_median':faster,'old_selected':oldpath,'calibrated_selected':newpath,
          'old_agreement':oldpath==faster,'calibrated_agreement':newpath==faster,
          'old_normalized_ms':m[('hybrid',4096)]/best,'calibrated_normalized_ms':m[('hybrid',selected)]/best,
          'merkle_over_hybrid4096':m[('merkle',0)]/m[('hybrid',4096)]})
    aggregate=[]
    for dataset in ['co2-observed','wine-generated',100000,1000000]:
        for model in ['revon-m','revon-h','dolt']:
            matching=[c for c in cases if c['case'].get('model')==model and (c['case'].get('dataset')==dataset if isinstance(dataset,str) else c['case']['suite']=='scale' and c['initial_rows']==dataset)]
            if not matching:continue
            medians=[median(r['diff_ms'] for r in measured(c)) for c in matching]
            telemetry=[load(output/'cases'/c['case']['name']/'telemetry.json') for c in matching]
            row={'dataset':str(dataset),'model':model,'repositories':len(matching),'initial_rows':matching[0]['initial_rows'],
              'history_unit':'same observed history' if dataset=='co2-observed' else 'distinct generated seeds',
              'diff_median_ms':median(medians),'diff_min_ms':min(medians),'diff_max_ms':max(medians),
              'import_median_s':median(c['import_ms']/1000 for c in matching),
              'commit_median_ms':median(median(c['commit_ms']) for c in matching),
              'checkout_median_s':median(c['checkout_ms']/1000 for c in matching),
              'storage_median_mib':median(c['storage_bytes']/2**20 for c in matching),
              'rss_median_gib':median(t['peak_rss_bytes']/2**30 for t in telemetry)}
            if model=='dolt':
                for key in ['command_ms','parse_ms','canonical_ms']:
                    row[key]=median(median(r[key] for r in measured(c)) for c in matching)
                row['command_fraction']=row['command_ms']/row['diff_median_ms']
            aggregate.append(row)
    monitor=[]
    for repeat in range(1,4):
        selected_cases=[c for c in cases if c['case']['suite']=='monitor' and c['case']['replicate']==repeat]
        if len(selected_cases)==2:
            by={c['case']['monitor']:grouped_medians(c) for c in selected_cases}
            for strategy,threshold in by[False]:
                monitor.append({'replicate':repeat,'strategy':strategy,'threshold':threshold,'off_ms':by[False][(strategy,threshold)],'on_ms':by[True][(strategy,threshold)],'on_over_off':by[True][(strategy,threshold)]/by[False][(strategy,threshold)]})
    val=[r for r in selector if r['suite']=='validation']
    findings={'audit':audit,'threshold':selected,'calibration_scores':frozen['scores'],
      'validation':{'cases':len(val),'old_agreement':sum(r['old_agreement'] for r in val),'calibrated_agreement':sum(r['calibrated_agreement'] for r in val),
        'old_normalized_mean':statistics.mean(r['old_normalized_ms'] for r in val) if val else None,
        'calibrated_normalized_mean':statistics.mean(r['calibrated_normalized_ms'] for r in val) if val else None,
        'calibrated_slowest_normalized':max((r['calibrated_normalized_ms'] for r in val),default=None)},
      'public_and_scale':aggregate,'monitor_diagnostic':monitor,
      'scope':'descriptive matched fixed-host histories; medians/ranges are not population confidence intervals; all cross-system comparisons include API/CLI costs'}
    for name,rows in [('raw_results.csv',raw),('summary.csv',summary),('selector.csv',selector),('public_scale.csv',aggregate),('monitor.csv',monitor)]:
        if rows:csv_write(output/name,rows)
    save(output/'analysis.json',findings)
    return findings

def plots(output,destination):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    destination.mkdir(parents=True,exist_ok=True)
    rows=list(csv.DictReader((output/'selector.csv').open()));data=load(output/'analysis.json');colors={'log':'#555555','merkle':'#b45530','hybrid4096':'#00838a','calibrated':'#6b4d9c'}
    plt.rcParams.update({'font.size':8.5,'axes.spines.top':False,'axes.spines.right':False,'savefig.bbox':'tight'})
    fig,axs=plt.subplots(1,2,figsize=(5.6,3.0),sharey=True)
    for ax,loc in zip(axs,['spread','repeated-key']):
        for system in colors:
            xs=[512,4096,32768];centers=[];low=[];high=[]
            for count in xs:
                values=[float(r[system+'_ms']) for r in rows if r['suite']=='validation' and r['locality']==loc and int(r['operations'])==count]
                centers.append(median(values));low.append(min(values));high.append(max(values))
            label={'log':'Forced log','merkle':'Forced Merkle','hybrid4096':'Hybrid T=4096','calibrated':f"Calibrated T={data['threshold']}"}[system]
            style={'log':'o-','merkle':'s-','hybrid4096':'^--','calibrated':'D:'}[system]
            ax.plot(xs,centers,style,label=label,color=colors[system],markersize=3);ax.fill_between(xs,low,high,color=colors[system],alpha=.09)
        ax.set_xscale('log',base=2);ax.set_yscale('log');ax.set_xticks([512,4096,32768],['512','4096','32768']);ax.set_title(loc);ax.set_xlabel('Operations across 8 commits');ax.grid(axis='y',alpha=.15)
    axs[0].set_ylabel('Diff latency (ms, log scale)')
    handles,labels=axs[1].get_legend_handles_labels();fig.legend(handles,labels,loc='upper center',ncol=2,fontsize=7,frameon=False)
    fig.tight_layout(rect=(0,0,1,.84));fig.savefig(destination/'Fig8.png',dpi=300);fig.savefig(destination/'Fig8.pdf');plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(5.6,2.7))
    for ax,dataset,title in zip(axs,['co2-observed','wine-generated'],['CO2: observed','Wine: generated']):
        for i,model in enumerate(['revon-m','revon-h','dolt']):
            r=next(x for x in data['public_and_scale'] if x['dataset']==dataset and x['model']==model)
            ax.errorbar(i,r['diff_median_ms'],yerr=[[r['diff_median_ms']-r['diff_min_ms']],[r['diff_max_ms']-r['diff_median_ms']]],fmt='o',capsize=4,color=['#b45530','#00838a','#555555'][i])
        ax.set_xticks(range(3),['Revon-M','Revon-H','Dolt CLI']);ax.set_yscale('log');ax.set_title(title);ax.grid(axis='y',alpha=.15)
    axs[0].set_ylabel('Median diff latency (ms, log scale)');fig.tight_layout();fig.savefig(destination/'Fig9.png',dpi=300);fig.savefig(destination/'Fig9.pdf');plt.close(fig)
    scale=[x for x in data['public_and_scale'] if x['dataset'] in ['100000','1000000']]
    if len(scale)==6:
        fig,axs=plt.subplots(1,3,figsize=(5.6,2.6))
        for ax,key,label in zip(axs,['import_median_s','diff_median_ms','rss_median_gib'],['Initial import (s)','Cached diff (ms)','Worker RSS (GiB)']):
            for model,color in zip(['revon-m','revon-h','dolt'],['#b45530','#00838a','#555555']):
                subset=sorted([x for x in scale if x['model']==model],key=lambda x:int(x['dataset']))
                ax.plot([1,2],[x[key] for x in subset],'o-',color=color,label=model)
            ax.set_xticks([1,2],['100k','1M']);ax.set_ylabel(label);ax.grid(axis='y',alpha=.15)
            if key!='rss_median_gib':ax.set_yscale('log')
        axs[2].legend(fontsize=6);fig.tight_layout();fig.savefig(destination/'Fig10.png',dpi=300);fig.savefig(destination/'Fig10.pdf');plt.close(fig)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--figures',type=Path);parser.add_argument('--allow-incomplete',action='store_true');args=parser.parse_args()
    findings=analyze(args.output,args.allow_incomplete)
    if args.figures:plots(args.output,args.figures)
    print(json.dumps({'threshold':findings['threshold'],'audit':findings['audit'],'validation':findings['validation']},indent=2))

if __name__=='__main__':main()
