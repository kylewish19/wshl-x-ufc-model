"""Odds-blind prospective research runner. No production or betting authorization.
Actual CLI requires caller-attested verified roster, identities, schedules, and
freshness. CI exercises hypothetical 14-bout input only; never writes real picks.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
from urllib.parse import urlparse
from collections import defaultdict
import argparse,hashlib,json,tempfile,re
import numpy as np
import pandas as pd
import rebuild_v027 as rb
import audit_worldwide_mma_history_v4 as a
from audit_ufc_identity_overlay import DB,SHA
from refit_reference_identity_corrected import source,rebuild,FILES,summarize
from smoke_refreshed_three_view import checked_load,REFERENCE,OFFSETS,HISTORICAL,reference_view
from wshlx_ufc.historical_data import build_prefight_perspective_rows,col,txt,bout
from wshlx_ufc.historical_timing_model import symmetric_timing_frame,_encode_transform
from wshlx_ufc.refreshed_unified import compose
from wshlx_ufc.models import fighter_double_chance
from wshlx_ufc.simulation import simulate_joint_outcomes

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="WSHLX_VERIFIED_REFRESHED_LINEUP_V1"
EVENT="__ODDS_BLIND_PREFIGHT_QUERY__"
CUTOFF="2026-11-21"
METHODS=("KO","SUB","DEC")
BASE_SEED=112526

def require(condition,message):
    if not condition:raise ValueError(message)
def dt(v):
    x=datetime.fromisoformat(v.replace("Z","+00:00"))
    require(x.tzinfo is not None,"Explicit UTC offset required")
    return x.astimezone(timezone.utc)
def trusted(url,hosts):
    p=urlparse(url)
    return p.scheme=="https" and p.hostname in hosts and not p.username and not p.password
def gate(d,now):
    allowed={"schema","event","event_date","first_fight_utc","lineup_source_url","lineup_verified_by_caller","identity_verification_complete","verified_at_utc","UFC_history_current_through_last_completed_event_verified","last_completed_event_date","fights"}
    require(set(d)==allowed and d["schema"]==SCHEMA,"Exact verified lineup schema required; draft rejected")
    require(now.tzinfo is not None,"Aware clock required")
    first,verified=dt(d["first_fight_utc"]),dt(d["verified_at_utc"])
    require(first>now and first.date().isoformat()==d["event_date"] and d["event_date"]>CUTOFF,"Must be a future event after source cutoff")
    require(timedelta(0)<=now-verified<=timedelta(hours=72),"Caller verification must be recent, not future dated")
    require(all(d[k] is True for k in ("lineup_verified_by_caller","identity_verification_complete","UFC_history_current_through_last_completed_event_verified")),"Caller verification incomplete")
    require(d["last_completed_event_date"]==CUTOFF,"Refit required for new completed event")
    require(trusted(d["lineup_source_url"],{"www.ufc.com","ufc.com"}) and urlparse(d["lineup_source_url"]).path.startswith("/event/"),"Official UFC event URL required")
    require(isinstance(d["event"],str) and d["event"].strip(),"Event name required")
    fights=d["fights"]
    require(isinstance(fights,list) and 1<=len(fights)<=20,"Invalid fight count")
    seen=set()
    for f in fights:
        require(set(f)=={"a","b","scheduled_rounds","weight_class"},"Unexpected fight fields (including odds or results)")
        require(type(f["scheduled_rounds"]) is int and f["scheduled_rounds"] in (3,5),"Invalid scheduled rounds")
        require(isinstance(f["weight_class"],str) and re.fullmatch(r"(?:UFC )?(?:Women's )?(?:Strawweight|Flyweight|Bantamweight|Featherweight|Lightweight|Welterweight|Middleweight|Light Heavyweight|Heavyweight|Catch Weight|Catchweight)(?: Title)? Bout",f["weight_class"]),"Invalid division")
        require("Title" not in f["weight_class"] or f["scheduled_rounds"]==5,"Title must be five rounds")
        for side in ("a","b"):
            z=f[side]
            require(set(z)=={"name","regional_id","ufcstats_profile_id","identity_source_url"},"Exact fighter identity fields required")
            require(isinstance(z["name"],str) and z["name"].strip() and type(z["regional_id"]) is int and z["regional_id"]>0,"Invalid fighter identity")
            require(z["regional_id"] not in seen,"Repeated fighter")
            require(z["ufcstats_profile_id"] is None or isinstance(z["ufcstats_profile_id"],str) and re.fullmatch(r"[0-9a-f]{16}",z["ufcstats_profile_id"]),"Invalid profile id")
            require(trusted(z["identity_source_url"],{"www.ufc.com","ufc.com","ufcstats.com","www.ufcstats.com","www.sherdog.com","www.tapology.com"}),"Identity evidence URL required")
            seen.add(z["regional_id"])
    return first

def prepare(t):
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)
        for k,v in FILES.items():t[k].to_csv(p/v,index=False)
        rb.TRAINING_CUTOFF=pd.Timestamp("2026-11-22",tz="UTC")
        fights,stats,static=rb.load_fights(p)
    _,history,coverage=rebuild(fights,rb.aggregate_fight_stats(fights,stats),static)
    require(len(fights)==8831 and coverage=={"paired":8786,"missing":45},"Source drift")
    return fights,static,history,coverage

def resolve(t,fights,con):
    profiles=defaultdict(set)
    for x in t["fighters"].to_dict("records"):
        url=txt(x["URL"]);name=txt(x["FIGHTER"])
        if url:profiles[url.rstrip("/").split("/")[-1]].add(name)
    # A debut without a raw profile must not accidentally inherit a same-name history.
    raw_names={txt(x) for x in t["fighters"]["FIGHTER"]}
    for label in t["results"]["BOUT"]:
        raw_names.update(bout(label) or ())
    aliases=a.aliases(con);ret=[];used=set()
    for f in fights:
        pair=[]
        for side in ("a","b"):
            z=f[side];fid=z["regional_id"];sid=z["ufcstats_profile_id"]
            require(a.namekey(z["name"]) in aliases.get(fid,set()),"Regional name/ID conflict")
            mapped={x[0] for x in con.execute("SELECT source_id FROM fighter_aliases WHERE fighter_id=? AND source='ufcstats'",(fid,))}
            if sid is not None:
                owners={x[0] for x in con.execute("SELECT fighter_id FROM fighter_aliases WHERE source='ufcstats' AND source_id=?",(sid,))}
                require(sid in mapped and owners=={fid} and len(profiles[sid])==1,"UFCStats identity not uniquely verified in raw source")
                name=next(iter(profiles[sid]))
                identity_status="PROFILE_ID_MATCH"
            else:
                require(not mapped,"Known UFCStats ID cannot be omitted")
                require(not any(a.namekey(n) in aliases[fid] or rb.norm_name(n)==rb.norm_name(z["name"]) for n in raw_names),"Unresolved possible historical collision")
                name=z["name"];identity_status="REGIONAL_ONLY_NO_UFC_SOURCE_MATCH"
            require(rb.norm_name(name) not in used,"Repeated or colliding source identity")
            used.add(rb.norm_name(name))
            pair.append({"display_name":z["name"],"source_name":name,"regional_id":fid,"ufcstats_profile_id":sid,"identity_status":identity_status})
        ret.append(pair)
    return ret

def batch_historical(t,rows,day,models):
    ev=pd.concat([t["events"],pd.DataFrame([{"EVENT":EVENT,"DATE":str(day.date())}])],ignore_index=True)
    rr=[]
    for x in rows:
        rr.append({"EVENT":EVENT,"BOUT":" vs. ".join(x["names"]),"OUTCOME":"W/L","METHOD":"Decision - Unanimous","ROUND":x["rounds"],"TIME":"5:00","WEIGHTCLASS":x["weight_class"],col(t["results"],"TIME FORMAT","TIME_FORMAT"):str(x["rounds"])+" Rnd"})
    def make(reversed_targets):
        query=pd.DataFrame(rr)
        if reversed_targets:query=query.assign(OUTCOME="L/W",METHOD="KO/TKO",ROUND=1,TIME="0:30")
        result=pd.concat([t["results"],query],ignore_index=True)
        f=build_prefight_perspective_rows(ev,result,t["stats"],t["fighters"])
        f=f[f.event==EVENT].copy()
        require(len(f)==len(rows)*2 and f.fight_id.nunique()==len(rows),"Query cardinality error")
        return f
    f,g=make(False),make(True)
    def predict(frame):
        w=pd.Series(models["winner"].predict_proba(frame),index=frame.index)
        m=models["method"].predict_joint_probabilities(frame)
        tim=models["timing"]
        tf=symmetric_timing_frame(frame);tf["scheduled_seconds"]=tf["scheduled_rounds"]*300
        tx=_encode_transform(tf,tim.rate_encoders).set_index("fight_id",drop=False)
        out=[]
        for x in rows:
            aa,bb=x["names"]
            q=frame[(frame.fighter==aa)&(frame.opponent==bb)]
            require(len(q)==1,"Historical A row identity error")
            i=q.index[0];fid=q.iloc[0].fight_id
            j={side+"_"+z:float(m.loc[i,prefix+"_"+("KO_TKO" if z=="KO" else z)]) for side,prefix in (("A","WIN"),("B","LOSS")) for z in METHODS}
            require(tim.hazard_model.bin_seconds==30,"Timing bin mismatch")
            hz=tim._hazards(tx.loc[fid],x["rounds"]*300)
            out.append({"winner_p_a":float(w.loc[i]),"joint_method":j,"hazards_30s":hz})
        return out
    v,u=predict(f),predict(g)
    for x,y in zip(v,u,strict=True):
        np.testing.assert_allclose(x["winner_p_a"],y["winner_p_a"],atol=1e-12,rtol=0)
        np.testing.assert_allclose(list(x["joint_method"].values()),list(y["joint_method"].values()),atol=1e-12,rtol=0)
        np.testing.assert_allclose(x["hazards_30s"],y["hazards_30s"],atol=1e-12,rtol=0)
    return v

def timing_sim(h,seconds,seed):
    h=np.asarray(h,float);s=np.r_[1.,np.cumprod(1-h)]
    mass=np.r_[s[:-1]*h,s[-1]]
    draws=np.random.default_rng(seed).choice(len(mass),10000,p=mass/mass.sum())
    finish=draws<len(h);duration=np.minimum((draws+1)*30,seconds)
    out={"GTD_YES":float(np.mean(~finish))}
    out["GTD_NO"]=1-out["GTD_YES"]
    for r in range(1,seconds//300+1):
        p=float(np.mean(finish & (duration>(r-1)*300)&(duration<=r*300)))
        out[f"FINISH_ROUND_{r}"]=p;out[f"FINISH_ROUND_{r}_NO"]=1-p
        if r>1:
            p=float(np.mean(duration>(r-1)*300))
            out[f"ROUND_{r}_STARTS_YES"]=p;out[f"ROUND_{r}_STARTS_NO"]=1-p
        threshold=r-.5;p=float(np.mean(duration>threshold*300))
        out[f"OVER_{threshold}"]=p;out[f"UNDER_{threshold}"]=1-p
    return out

def evaluate(t,rows,day,static,history,reference,historical):
    hv=batch_historical(t,rows,day,historical)
    results=[]
    for i,(x,h) in enumerate(zip(rows,hv,strict=True),1):
        aa,bb=x["names"];seconds=x["rounds"]*300
        r=reference_view(summarize(aa,history,static,day),summarize(bb,history,static,day),x["weight_class"],seconds,reference)
        views=compose(r,h,scheduled_seconds=seconds)
        out={}
        for k in ("reference","historical","unified"):
            v=views[k];side="A" if v["winner_p_a"]>=.5 else "B"
            sims={};variants={}
            for variant,j in v["coherence"].items():
                sims[variant]=simulate_joint_outcomes(j,trials=10000,seed=BASE_SEED+i)
                variants[variant]={"selected_winner_side":side,"method_given_selected_winner":max(METHODS,key=lambda m:j[side+"_"+m]),"double_chance":fighter_double_chance(j)}
                require(np.isclose(sum(sims[variant].values()),1),"Simulation mass")
            direct=v["timing_direct"]
            for rnd in range(1,x["rounds"]+1):direct[f"FINISH_ROUND_{rnd}_NO"]=1-direct[f"FINISH_ROUND_{rnd}"]
            out[k]={**v,"variants":variants,"joint_simulations_10000":sims,"timing_simulation_10000":timing_sim(v["hazards_30s"],seconds,BASE_SEED+100+i)}
        coverage=[]
        for n in (aa,bb):
            key=rb.norm_name(n);st=static.get(key,{});hist=history.get(key,[])
            coverage.append({"source_name":n,"prior_reference_decisive_bouts":len(hist),"paired_stats_bouts":sum(z["paired_stats_available"] for z in hist),"height_known":bool(pd.notna(st.get("height_inches"))),"reach_known":bool(pd.notna(st.get("reach_inches"))),"dob_known":bool(pd.notna(st.get("dob")))})
        results.append({"fight_no":i,"source_names":list(x["names"]),"scheduled_rounds":x["rounds"],"weight_class":x["weight_class"],"source_coverage":coverage,"models":out,"bet_authorized":False})
    return results

def main():
    ap=argparse.ArgumentParser()
    for name in ("reference","offsets","historical"):ap.add_argument("--"+name,type=Path,required=True)
    ap.add_argument("--lineup",type=Path);ap.add_argument("--output",type=Path);ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    now=datetime.now(timezone.utc)
    if args.self_test:
        require(args.lineup is None and args.output is None,"Self test cannot publish forecasts")
        draft=json.loads((ROOT/"research/lineups/ufcriyadh_2026-12-05_draft_2026-11-24.json").read_text())
        try:gate(draft,now)
        except ValueError:pass
        else:raise AssertionError("Unverified draft passed gate")
    else:
        require(args.lineup is not None and args.output is not None and not args.output.exists(),"Verified lineup and new output required")
        raw=args.lineup.read_bytes();d=json.loads(raw);first=gate(d,now)
    reference={**{n:checked_load(args.reference,n,s) for n,s in REFERENCE.items()},**{n:checked_load(args.offsets,n,s) for n,s in OFFSETS.items()}}
    historical={n:checked_load(args.historical,"historical_"+n,s) for n,s in HISTORICAL.items()}
    t=source();fights,static,history,coverage=prepare(t)
    if args.self_test:
        # Build a deliberately hypothetical card by rotating historical opponents,
        # with 28 distinct fighters and a five-round fixture, no publication.
        fixtures=[];used=set()
        for x in fights.iloc[::-1].itertuples(index=False):
            names=(x.fighter_a,x.fighter_b)
            keys={rb.norm_name(n) for n in names}
            if len(keys)!=2 or keys&used or not all(k in static for k in keys):continue
            fixtures.append((names,x.weight_class));used.update(keys)
            if len(fixtures)==14:break
        require(len(fixtures)==14,"Fixture shortage")
        rows=[{"names":(z[0][0],fixtures[(i+1)%14][0][1]),"rounds":5 if i==0 else 3,"weight_class":z[1].replace("Title ","")} for i,z in enumerate(fixtures)]
        day=pd.Timestamp("2026-12-05",tz="UTC")
    else:
        with a.get_tables(DB) as con:identities=resolve(t,d["fights"],con)
        rows=[{"names":tuple(z["source_name"] for z in pair),"rounds":f["scheduled_rounds"],"weight_class":f["weight_class"]} for f,pair in zip(d["fights"],identities,strict=True)]
        day=pd.Timestamp(d["event_date"],tz="UTC")
    result=evaluate(t,rows,day,static,history,reference,historical)
    json.dumps(result,allow_nan=False)
    if args.self_test:
        print(json.dumps({"hypothetical_fights":len(result),"model_views":3*len(result),"coherence_variants":9*len(result),"simulation_trials_per_distribution":10000,"draft_rejected":True,"target_reversal_verified":True,"real_card_predictions":0,"production_migrated":False}))
        return
    require(datetime.now(timezone.utc)<first,"Event started during inference")
    for row,pair in zip(result,identities,strict=True):row["identities"]=pair
    report={"schema":"WSHLX_REFRESHED_THREE_VIEW_RESEARCH_LOCK_V1","event":d["event"],"event_date":d["event_date"],"first_fight_utc":first.isoformat(),"generated_at_utc":datetime.now(timezone.utc).isoformat(),"lineup_sha256":hashlib.sha256(raw).hexdigest(),"lineup_source_url":d["lineup_source_url"],"history_through":CUTOFF,"worldwide_source_sha256":SHA,"artifact_hashes":{"reference":REFERENCE,"offsets":OFFSETS,"historical":HISTORICAL},"source_coverage":coverage,"research_only":True,"odds_used":False,"bet_authorized":False,"production_migrated":False,"fights":result}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x") as fp:json.dump(report,fp,indent=2,allow_nan=False)
if __name__=="__main__":main()
