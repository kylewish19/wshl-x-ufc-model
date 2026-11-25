"""Future-only Reference backbone refit; old residual/calibrator untouched.
Explicitly separate results-only history from measured performance exposure.
"""
from pathlib import Path
import json,hashlib,tempfile
import numpy as np
import pandas as pd
import joblib
import rebuild_v027 as rb
from audit_identity_safe_csv import corrected_tables,FILES
from audit_ufc_identity_overlay import mapping
from refit_historical_identity_corrected import append_recent
from refit_ufcvegas124_historical_shadow import clean_name,map_bout
from wshlx_ufc.historical_data import load_source_files
from wshlx_ufc.prefight_finish_resistance import ARCHIVE
from wshlx_ufc.models import WinnerModel,ConditionalMethodModel
from wshlx_ufc.timing import DiscreteTimeHazardModel

OUT=Path("research_outputs/reference_identity_refit_2026-11-25")
STAT_FIELDS=("kd_for","sig_landed","sig_attempted","ground_landed","ground_attempted","td_landed","td_attempted","sub_att","ctrl_seconds","r1_sig_landed","r1_seconds","r3_sig_landed","r3_seconds")

def summarize(name,history,static,day):
    # Preserve result counts, last activity, recent W/L and method history.
    # Missing stats must not add performance exposure or round-retention time.
    key=rb.norm_name(name)
    items=[]
    for item in history.get(key,[]):
        r=dict(item)
        if not r["paired_stats_available"]:
            r["duration_seconds"]=0.
            for f in STAT_FIELDS:
                r[f]=r["opp_"+f]=0.
        items.append(r)
    return rb.summarize_history(name,{key:items},static,day)

def rebuild(fights,stats,static):
    history={};rows=[[],[],[]];coverage={"paired":0,"missing":0}
    for day,group in fights.groupby("event_date",sort=True):
        pending=[]
        for f in group.itertuples(index=False):
            a,b=(summarize(n,history,static,day) for n in (f.fighter_a,f.fighter_b))
            w=int(rb.norm_name(f.winner)==rb.norm_name(f.fighter_a))
            win,opp=(a,b) if w else (b,a)
            wf=rb.winner_features(a,b,f.weight_class,f.scheduled_seconds)
            mf=rb.method_features(win,opp,f.weight_class,f.scheduled_seconds)
            meta={"fight_key":f.fight_key,"event":f.event,"event_date":day.isoformat(),"bout":f.bout,"fighter_a":f.fighter_a,"fighter_b":f.fighter_b,"winner":f.winner,"method":f.method,"winner_is_a":w,"weight_class":f.weight_class,"scheduled_seconds":int(f.scheduled_seconds),"duration_seconds":float(f.duration_seconds)}
            rows[0].append({**meta,**wf})
            rows[1].append({**meta,**mf,**rb.residual_features(win,opp)})
            rows[2].append({**meta,**wf})
            ka,kb=map(rb.norm_name,(f.fighter_a,f.fighter_b))
            sa,sb=(stats.get((rb.norm_text(f.event),rb.norm_text(f.bout),k),{}) for k in (ka,kb))
            valid=bool(sa and sb)
            coverage["paired" if valid else "missing"]+=1
            for key,own,other in ((ka,sa,sb),(kb,sb,sa)):
                item={"event_date":day,"duration_seconds":float(f.duration_seconds),"win":rb.norm_name(f.winner)==key,"method":f.method,"paired_stats_available":valid}
                for z in STAT_FIELDS:
                    item[z]=float(own.get(z,0.));item["opp_"+z]=float(other.get(z,0.))
                pending.append((key,item))
        for key,item in pending:history.setdefault(key,[]).append(item)
    return [pd.DataFrame(r) for r in rows],history,coverage

def selfcheck():
    day=pd.Timestamp("2026-11-25",tz="UTC")
    p={"event_date":day-pd.Timedelta(days=30),"duration_seconds":300.,"win":True,"method":"KO","paired_stats_available":True}
    for f in STAT_FIELDS:p[f]=p["opp_"+f]=0.
    p["sig_landed"]=25.;p["r1_seconds"]=300.
    q={**p,"event_date":day-pd.Timedelta(days=4),"duration_seconds":900.,"win":False,"method":"DEC","paired_stats_available":False}
    old=summarize("Test",{"test":[p]}, {},day)
    new=summarize("Test",{"test":[p,q]}, {},day)
    assert old["sig_landed_per_min"]==new["sig_landed_per_min"]==5.
    assert new["prior_bouts"]==2 and new["win_rate"]==.5 and new["days_since_last"]==4.

def source():
    t,_=corrected_tables(load_source_files(ARCHIVE),mapping())
    t,n=append_recent(t)
    for k in ("results","stats"):
        df=t[k]
        df["BOUT"]=[map_bout(b,e) for b,e in zip(df["BOUT"],df["EVENT"])]
        if k=="stats":df["FIGHTER"]=[clean_name(f,e) for f,e in zip(df["FIGHTER"],df["EVENT"])]
    t["fighters"]["FIGHTER"]=t["fighters"]["FIGHTER"].replace({"Kai Kamaka":"Kai Kamaka III","Zach Reese":"Zachary Reese"})
    t["fighters"]=t["fighters"][t["fighters"]["FIGHTER"]!="Anthony Romero (The Genius)"]
    return t

def main():
    selfcheck()
    if OUT.exists():raise FileExistsError("Do not overwrite refit")
    t=source()
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)
        for k,v in FILES.items():t[k].to_csv(path/v,index=False)
        rb.TRAINING_CUTOFF=pd.Timestamp("2026-11-22",tz="UTC")
        fights,stats,static=rb.load_fights(path)
    assert str(fights.event_date.max().date())=="2026-11-21"
    assert all(sum(fights.event_date.dt.strftime("%Y-%m-%d")==d)==12 for d in ("2026-11-14","2026-11-21"))
    agg=rb.aggregate_fight_stats(fights,stats)
    (w,m,t),history,coverage=rebuild(fights,agg,static)
    assert len(w)==len(m)==len(t)==len(fights)
    assert static[rb.norm_name("Bruno Silva [Bulldog]")]["height_inches"]==64.
    assert static[rb.norm_name("Bruno Silva [Blindado]")]["height_inches"]==72.
    assert all(len(history[rb.norm_name(n)])==11 for n in ("Bruno Silva [Bulldog]","Bruno Silva [Blindado]"))
    models={
      "winner":WinnerModel(c=.25).fit(w[list(rb.WINNER_FEATURES)],w["winner_is_a"]),
      "method_baseline":ConditionalMethodModel(finish_c=.1,sub_c=.1).fit(m[list(rb.METHOD_BASE_FEATURES)],m["method"]),
      "timing_30s":DiscreteTimeHazardModel(bin_seconds=30,c=.1).fit(t[list(rb.TIMING_FEATURES)],t["duration_seconds"].to_numpy(float),t["scheduled_seconds"].to_numpy(int),((t["method"]!="DEC")|(t["duration_seconds"]<t["scheduled_seconds"])).astype(int).to_numpy())}
    OUT.mkdir(parents=True)
    manifest={"history_through":"2026-11-21","training_fights":len(w),"coverage":coverage,"missing_stats_exposure_policy":"Zero measured time, retain actual outcome and recency; legacy partial source fields not repaired","residual_and_calibrator":"Existing versions preserved; compatibility with new baseline not yet established","research_only":True,"production_migrated":False,"live_predictions":0,"models":{}}
    for name,model in models.items():
        p=OUT/(name+".joblib");joblib.dump(model,p,compress=3)
        manifest["models"][name]={"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2))
    print(json.dumps(manifest))
if __name__=="__main__":main()
