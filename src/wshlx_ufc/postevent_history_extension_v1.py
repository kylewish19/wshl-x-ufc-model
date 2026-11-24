"""Explicit future-only research extension; never rewrite the historical archive.

Nov 14: verified results, no provisional statistics.
Nov 21: verified results, optional secondary totals (round cross-check on
sig strikes, TD, KD, CTRL; sub attempts/total strikes/reversals single mirror).
Default is results-only. No old forecasts or production model changes.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import date
from pathlib import Path
import csv,hashlib,json,re,unicodedata
from .prefight_finish_resistance import ARCHIVE,_load_records,build_from_records
from .historical_feature_matrix import build_matrix
from .winner_recent_form_v3 import construct_record_history

ROOT=Path(__file__).resolve().parents[2]
PINS={
 "data/results/ufc334_2026-11-14_verified_outcomes.json":"8701827433539ea281f9c990be060ef03f7a6a8b",
 "data/locks/ufc334_2026-11-14/stage_a_final_selection.json":"564b8dbf2147f7a1cc839917ca3a4eb2d42ed63e",
 "data/results/ufcqatar_2026-11-21/verified_event_results_2026-11-24.json":"21cce01e16cd23c06d7f115c9c5cea26d9d75150",
 "data/results/ufcqatar_2026-11-21/ufcstats_derived_postevent_fight_totals_2026-11-24.json":"3c29ccb7efa3520fd8d7b587d1ee4b1343a57046",
 "data/results/ufcqatar_2026-11-21/fightingdata_round_stats_secondary_2026-11-24.csv":"864d97067cd97fe42e7a4e42b1db5bbe72da615d",
 "data/shadow_locks/ufcqatar_2026-11-21/worldwide_direct_six_v7_prospective_shadow.json":"f0372a7c3b2ba962a5a5b3f97fafb6863a101dee",
}
KEYS=list(PINS)
# Require a future event after the actual date on which the extension was
# gathered. This API cannot generate purported Nov21 prospective forecasts.
MIN_ASOF=date(2026,11,25)

def pinned(key):
    b=(ROOT/key).read_bytes()
    blob=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
    if blob!=PINS[key]:raise ValueError("Post-event source blob changed: "+key)
    return b

def seconds(clock):
    m=re.fullmatch(r"(\d+):([0-5]\d)",str(clock))
    if not m:raise ValueError("Invalid clock")
    return int(m[1])*60+int(m[2])

def namekey(s):
    return re.sub("[^a-z0-9]","",unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode().lower())

def verify_qatar_round_totals(totals,rounds,results):
    """Cross-check 64 round-fighter records against 24 full-fight rows."""
    byfight={int(x["fight_no"]):x for x in results["fights"]}
    expected={}
    for f in totals["fights"]:
        n=int(f["fight_no"]);r=byfight[n]
        names={r["winner"],r["loser"]}
        if {x["name"] for x in f["fighter_stats"]}!=names or len(f["fighter_stats"])!=2:
            raise ValueError("Qatar stats/result identity mismatch")
        for x in f["fighter_stats"]:
            key=(n,x["name"])
            if key in expected or x["result"]!=("W" if x["name"]==r["winner"] else "L"):
                raise ValueError("Duplicate or contradictory fighter total")
            expected[key]=(int(x["significant_strikes_landed"]),int(x["significant_strikes_attempted"]),
                       int(x["takedowns_landed"]),int(x["takedowns_attempted"]),
                       seconds(x["control_time_mmss"]),int(x["knockdowns"]))
    sums=defaultdict(lambda:[0]*6);seen=set()
    for x in rounds:
        n=int(x["fight_no"]);rnd=int(x["round"]);key=(n,x["fighter"])
        k=(*key,rnd)
        if k in seen or key not in expected or not 1<=rnd<=byfight[n]["round"]:
            raise ValueError("Unexpected duplicate round or fighter")
        seen.add(k)
        vals=[int(x[z]) for z in ("sig_landed","sig_attempted","td_landed","td_attempted","control_seconds","knockdowns")]
        duration=300 if rnd<byfight[n]["round"] else seconds(byfight[n]["round_clock"])
        if min(vals)<0 or vals[0]>vals[1] or vals[2]>vals[3] or vals[4]>duration:
            raise ValueError("Invalid round statistics")
        for i,v in enumerate(vals):sums[key][i]+=v
    if len(seen)!=64 or len(expected)!=24 or len(byfight)!=12:
        raise ValueError("Incomplete Qatar verification")
    for key,values in expected.items():
        if tuple(sums[key])!=values or any((*key,r) not in seen for r in range(1,byfight[key[0]]["round"]+1)):
            raise ValueError("Round sums do not match fighter total: "+str(key))
    return {"matched_fighter_totals":24,"matched_round_fighter_rows":64,
            "crosschecked_stat_fields":6,
            "not_independent_primary_UFCStats":True,
            "single_mirror_fields":["total_strikes","submission_attempts","reversals"]}

def stat_record(x,elapsed):
    y={
      "sig_landed":x["significant_strikes_landed"],"sig_attempted":x["significant_strikes_attempted"],
      "total_landed":x["total_strikes_landed"],"total_attempted":x["total_strikes_attempted"],
      "td_landed":x["takedowns_landed"],"td_attempted":x["takedowns_attempted"],
      "kd":x["knockdowns"],"sub_att":x["submission_attempts"],"ctrl_sec":seconds(x["control_time_mmss"]),
    }
    if any(type(v) is not int or v<0 for v in y.values()):
        raise ValueError("Missing/invalid source total")
    if any(y[a]>y[b] for a,b in (("sig_landed","sig_attempted"),("total_landed","total_attempted"),("td_landed","td_attempted"),("sig_landed","total_landed"),("sig_attempted","total_attempted"))) or y["ctrl_sec"]>elapsed:
        raise ValueError("Contradictory fighter stats")
    return y

def load_extended_records(*,as_of_exclusive:str,allow_secondary_qatar_stats:bool=False):
    cutoff=date.fromisoformat(as_of_exclusive)
    if cutoff<MIN_ASOF:
        raise ValueError("Extension observed Nov24; only future dates from Nov25 are eligible")
    manifest=json.loads((ARCHIVE/"availability.json").read_text())
    for filename in ("ufc_event_details.csv","ufc_fight_results.csv","ufc_fight_stats.csv"):
        b=(ARCHIVE/filename).read_bytes();p=manifest["source_csv_files"][filename]
        if len(b)!=p["bytes"] or hashlib.sha256(b).hexdigest()!=p["sha256"]:
            raise ValueError("Original pinned archive altered")
    records=_load_records(ARCHIVE,cutoff)
    if len(records)!=8871 or max(x["date"] for x in records)!=date(2026,11,7):
        raise ValueError("Base archive cohort changed")
    base_count=len(records)
    source={k:pinned(k) for k in KEYS}
    r14=json.loads(source[KEYS[0]]);l14=json.loads(source[KEYS[1]])
    r21=json.loads(source[KEYS[2]]);s21=json.loads(source[KEYS[3]])
    rounds=list(csv.DictReader(source[KEYS[4]].decode().splitlines()))
    l21=json.loads(source[KEYS[5]])
    audit=verify_qatar_round_totals(s21,rounds,r21)
    stats={int(f["fight_no"]):{x["name"]:x for x in f["fighter_stats"]} for f in s21["fights"]}
    idx=defaultdict(set)
    for rec in records:
        for n in (rec["a"],rec["b"]):idx[namekey(n)].add(n)
    def resolve(name,known_prior=None):
        match=idx.get(namekey(name),set())
        if len(match)>1:raise ValueError("Ambiguous prior-source name: "+name)
        if not match and known_prior and known_prior>0:
            raise ValueError("Veteran unmatched to base archive: "+name)
        return next(iter(match)) if match else name
    existing={(x["date"],*sorted((namekey(x["a"]),namekey(x["b"])))) for x in records}
    rows=[]
    def add(day,event,a,b,winner,method,rnd,clock,scheduled,sa,sb):
        elapsed=(rnd-1)*300+seconds(clock)
        if not 1<=rnd<=scheduled or not 0<elapsed<=scheduled*300:
            raise ValueError("Invalid observed fight duration")
        key=(day,*sorted((namekey(a),namekey(b))))
        if a==b or key in existing:raise ValueError("Duplicate extension bout")
        existing.add(key)
        if method=="DRAW" and winner is None:
            res=("D","D")
        elif winner==a:res=("W","L")
        elif winner==b:res=("L","W")
        else:raise ValueError("Result winner not in source pair")
        rows.append({"date":day,"event":event,"a":a,"b":b,"result":res,
            "method":"KO_TKO" if method=="KO" else method,
            "elapsed_seconds":elapsed,"round_format_mismatch":False,
            "stats_a":sa,"stats_b":sb})
    for f,l in zip(r14["fights"],l14["fights"],strict=True):
        if (f["fight_no"],f["a"],f["b"])!=(l["fight_no"],l["a"],l["b"]) or not f["model_fight_identity_verified"]:
            raise ValueError("UFC334 lock/outcome mismatch")
        a,b=(resolve(l[z],l["evidence_density"][z+"_prior_ufc_bouts"]) for z in ("a","b"))
        winner=a if f["winner"]==l["a"] else b if f["winner"]==l["b"] else None
        if winner is None and f["method"]!="DRAW":raise ValueError("UFC334 winner mismatch")
        add(date(2026,11,14),r14["event"],a,b,winner,f["method"],f["round"],f["time"],f["scheduled_rounds"],None,None)
    for f,l in zip(r21["fights"],l21["research_fights"],strict=True):
        if f["fight_no"]!=l["fight_no"] or {f["winner"],f["loser"]}!={l["a"],l["b"]} or not f["winning_fighter_and_method_verified"]:
            raise ValueError("Qatar lock/outcome mismatch")
        a,b=(resolve(l["source_"+z],l[z+"_prior_ufc_bouts"]) for z in ("a","b"))
        winner=a if f["winner"]==l["a"] else b
        elapsed=(f["round"]-1)*300+seconds(f["round_clock"])
        sa,sb=(stat_record(stats[f["fight_no"]][l[z]],elapsed) if allow_secondary_qatar_stats else None for z in ("a","b"))
        add(date(2026,11,21),r21["event"],a,b,winner,f["method"],f["round"],f["round_clock"],5 if f["fight_no"]==11 else 3,sa,sb)
    if len(rows)!=25 or sum(x["method"]=="DRAW" for x in rows)!=1:
        raise ValueError("Expected 24 decisive bouts plus one draw")
    records.extend(rows)
    return records,{
        "schema":"WSHLX_EXPLICIT_FUTURE_HISTORY_EXTENSION_V1",
        "research_only":True,"original_archive_unmodified":True,
        "base_bouts":base_count,"added_bouts":25,"added_decisive":24,"added_draws":1,
        "extended_bouts":len(records),"UFC334_provisional_stats_excluded":True,
        "Qatar_secondary_stats_enabled":bool(allow_secondary_qatar_stats),
        "Qatar_stats_crosscheck":audit,"source_git_blob_ids":PINS,
        "source_sha256":{k:hashlib.sha256(v).hexdigest() for k,v in source.items()},
        "earliest_future_use":MIN_ASOF.isoformat(),
        "data_as_of_exclusive":as_of_exclusive,"not_a_model_promotion":True,
    }

def future_research_matrix(*,as_of_exclusive:str,allow_secondary_qatar_stats:bool=False):
    records,audit=load_extended_records(as_of_exclusive=as_of_exclusive,allow_secondary_qatar_stats=allow_secondary_qatar_stats)
    snaps,_=build_from_records(records,as_of_exclusive=as_of_exclusive)
    features,labels=build_matrix(records,snaps)
    # Legacy build_matrix cutoff is November14. Explicitly label additions as
    # postevent extension, never as pristine prospective test observations.
    for row in features:
        if row["event_date"]>="2026-11-14":
            row["source_class"]="POSTEVENT_EXTENSION_RESEARCH_ONLY"
            row["data_partition"]="postevent_extension_research"
    return features,labels,audit

def future_research_snapshots(*,as_of_exclusive:str,query_bouts,allow_secondary_qatar_stats:bool=False):
    records,audit=load_extended_records(as_of_exclusive=as_of_exclusive,allow_secondary_qatar_stats=allow_secondary_qatar_stats)
    snapshots,_=build_from_records(records,as_of_exclusive=as_of_exclusive,query_bouts=query_bouts)
    form=construct_record_history(records,cutoff=as_of_exclusive,query_date=as_of_exclusive,query_bouts=tuple(query_bouts))
    return [s for s in snapshots if s.get("query_only")],{k:v for k,v in form.items() if v.get("query_only")},audit
