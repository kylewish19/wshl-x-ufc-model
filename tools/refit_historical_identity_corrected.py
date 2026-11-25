"""Isolated future-only refit of the original Historical winner/method/timing heads.
No odds, no real card forecast, no production artifact replacement.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import pandas as pd
import joblib
from audit_identity_safe_csv import corrected_tables,frame
from audit_ufc_identity_overlay import mapping,DB
from refit_ufcvegas124_historical_shadow import clean_name,map_bout
import audit_worldwide_mma_history_v4 as a
from wshlx_ufc.historical_data import load_source_files,col,method,secs,outcome
from wshlx_ufc.prefight_finish_resistance import ARCHIVE
from wshlx_ufc.postevent_history_extension_v1 import load_extended_records
from wshlx_ufc.historical_model import fit_historical_winner_model
from wshlx_ufc.historical_method_model import fit_historical_method_model
from wshlx_ufc.historical_timing_model import fit_historical_timing_model

OUT=Path("research_outputs/historical_identity_refit_2026-11-25")
def verified_method(res,raw_method,expected_res,expected_method):
    if tuple(res)!=tuple(expected_res):
        raise ValueError(f"Result disagreement: {res!r} versus {expected_res!r}")
    normalized=method(raw_method)
    # A judged draw may be stored under Decision - Majority/Split/Unanimous.
    # Require D/D on BOTH sources; never relabel a decisive decision as a draw.
    if tuple(res)==("D","D") and normalized in ("DEC","DRAW"):
        normalized="DRAW"
    if normalized!=expected_method:
        raise ValueError(f"Method disagreement: {raw_method!r} -> {normalized!r} versus {expected_method!r}")
    return "DRAW" if normalized=="DRAW" else raw_method

def selfcheck_recent():
    assert verified_method(("D","D"),"Decision - Majority",("D","D"),"DRAW")=="DRAW"
    assert verified_method(("W","L"),"Decision - Split",("W","L"),"DEC")=="Decision - Split"
    for args in [(("W","L"),"Decision - Majority",("D","D"),"DRAW"),(("W","L"),"Submission",("W","L"),"KO_TKO"),(("D","D"),"KO/TKO",("D","D"),"DRAW")]:
        try:verified_method(*args)
        except ValueError:pass
        else:raise AssertionError("Invalid source agreement accepted")

def append_recent(t):
    selfcheck_recent()
    records,_=load_extended_records(as_of_exclusive="2026-12-05")
    extra=[r for r in records if r["date"].isoformat()>="2026-11-14"]
    assert len(extra)==25
    con=a.get_tables(DB)
    try:
        alias=a.aliases(con)
        rows=[];events={}
        for r in extra:
            day=r["date"].isoformat()
            hits=[]
            for x in con.execute("""SELECT f.fight_id,p.fighter_id,q.fighter_id,p.result,q.result,f.method,f.end_round,f.end_time,f.scheduled_rounds,f.weight_class
            FROM fights f JOIN events e ON e.event_id=f.event_id
            JOIN fight_participants p ON p.fight_id=f.fight_id AND p.corner=0
            JOIN fight_participants q ON q.fight_id=f.fight_id AND q.corner=1
            WHERE e.date=? AND EXISTS(SELECT 1 FROM fight_aliases z WHERE z.fight_id=f.fight_id AND z.source='ufcstats')""",(day,)):
                _,i,j,*rest=x
                ka,kb=a.namekey(r["a"]),a.namekey(r["b"])
                if ka in alias[i] and kb in alias[j]:hits.append((x,False))
                elif ka in alias[j] and kb in alias[i]:hits.append((x,True))
            if len(hits)!=1:raise ValueError("Unmatched recent bout "+str((day,r["a"],r["b"])))
            x,reverse=hits[0]
            _,_,_,ra,rb,m,rnd,clock,scheduled,wc=x
            res=(rb,ra) if reverse else (ra,rb)
            try:
                normalized_method=verified_method(res,m,r["result"],r["method"])
                if scheduled not in (3,5) or not wc or not rnd or not clock:
                    raise ValueError(f"Incomplete schedule metadata: {x!r}")
                if (rnd-1)*300+secs(clock)!=r["elapsed_seconds"]:
                    raise ValueError(f"Duration disagreement: {rnd}, {clock} versus {r['elapsed_seconds']}")
            except ValueError as exc:
                raise ValueError(f"{day} {r['a']} vs {r['b']}: {exc}") from exc
            print("VERIFIED_RECENT",day,r["a"],r["b"],res,repr(m),normalized_method,flush=True)
            events[r["event"]]={"EVENT":r["event"],"DATE":day}
            rows.append({"EVENT":r["event"],"BOUT":r["a"]+" vs. "+r["b"],"OUTCOME":"/".join(res),"METHOD":normalized_method,"ROUND":rnd,"TIME":clock,"WEIGHTCLASS":wc,"TIME FORMAT":str(scheduled)+" Rnd"})
        t["events"]=pd.concat([t["events"],pd.DataFrame(events.values())],ignore_index=True)
        df=pd.DataFrame(rows)
        # Use one date representation for both legacy date parsers.
        t["events"]["DATE"]=pd.to_datetime(t["events"]["DATE"],format="mixed",errors="raise").dt.strftime("%Y-%m-%d")
        tf=col(t["results"],"TIME FORMAT","TIME_FORMAT")
        if tf!="TIME FORMAT":df=df.rename(columns={"TIME FORMAT":tf})
        t["results"]=pd.concat([t["results"],df],ignore_index=True)
        return t,len(rows)
    finally:con.close()

def main():
    if OUT.exists():raise FileExistsError("Never overwrite research output")
    t,_=corrected_tables(load_source_files(ARCHIVE),mapping())
    t,n=append_recent(t)
    # Preserve earlier Historical refit's known identity policies.
    for k in ("results","stats"):
        df=t[k]
        df["BOUT"]=[map_bout(b,e) for b,e in zip(df["BOUT"],df["EVENT"])]
        if k=="stats":df["FIGHTER"]=[clean_name(f,e) for f,e in zip(df["FIGHTER"],df["EVENT"])]
    t["fighters"]["FIGHTER"]=t["fighters"]["FIGHTER"].replace({"Kai Kamaka":"Kai Kamaka III","Zach Reese":"Zachary Reese"})
    t["fighters"]=t["fighters"][t["fighters"]["FIGHTER"]!="Anthony Romero (The Genius)"]
    f=frame(t)
    f["date"]=pd.to_datetime(f["date"])
    assert str(f["date"].max().date())=="2026-11-21"
    for day in ("2026-11-14","2026-11-21"):
        x=f[f["date"].dt.strftime("%Y-%m-%d")==day]
        assert len(x)==24 and x["fight_id"].nunique()==12
    # Unsupported outcomes do not train any of these heads.
    f=f[f["fight_method"].isin(["KO_TKO","SUB","DEC"])].copy()
    assert f.groupby("fight_id")["win"].agg(["count","sum"]).eq([2,1]).all(axis=None)
    OUT.mkdir(parents=True)
    report={"history_through":"2026-11-21","added_result_rows":n,"recent_stats_policy":"Results-only Nov14 and Nov21; no invented fight statistics. Secondary totals not included in this controlled arm.","training_perspectives":len(f),"training_fights":f["fight_id"].nunique(),"research_only":True,"new_prospective_observations":0,"production_migrated":False,"models":{}}
    for name,fit in (("winner",lambda:fit_historical_winner_model(f)),("method",lambda:fit_historical_method_model(f)),("timing",lambda:fit_historical_timing_model(f,t["results"]))):
        bundle,metrics=fit()
        assert str(pd.Timestamp(bundle.history_end).date())=="2026-11-21"
        p=OUT/("historical_"+name+".joblib")
        joblib.dump(bundle,p,compress=3)
        report["models"][name]={"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"history_end":str(bundle.history_end),"feature_count":len(bundle.feature_columns),"metrics":metrics}
        print("REFIT_HEAD",name,str(bundle.history_end),len(bundle.feature_columns),flush=True)
    (OUT/"manifest.json").write_text(json.dumps(report,indent=2,default=str))
    print(json.dumps(report,default=str))
if __name__=="__main__":main()
