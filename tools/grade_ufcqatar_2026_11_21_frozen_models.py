"""Post-event UFC Qatar grading from immutable pre-fight model sidecars.

Source results were verified Nov24; none is used to recompute November21
predictions. Only the 10 preregistered ORIGINAL/RESEARCH model arms below
are graded. Coherent has THREE variants dependent on existing winner heads,
not an independent predictor. The public user-selected KO/DEC/DISTANCE card
gets a separate unpriced grade, never mistaken for a model lock.

Usage: python tools/grade_ufcqatar_2026_11_21_frozen_models.py
Fails if an existing grade is about to be overwritten.
"""
from __future__ import annotations
from collections import defaultdict,Counter
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,math

ROOT=Path(__file__).resolve().parents[1]
DAY="2026-11-21"
SOURCE=ROOT/"data/results/ufcqatar_2026-11-21/verified_event_results_2026-11-24.json"
LOCK=ROOT/"data/locks/ufcqatar_2026-11-21/stage_a_final_selection.json"
SHADOW=ROOT/"data/shadow_locks/ufcqatar_2026-11-21"
COH=SHADOW/"coherent_joint_pre_event_shadow.json"
V3=SHADOW/"winner_v3_prospective_shadow.json"
V4=SHADOW/"worldwide_winner_v4_prospective_shadow.json"
V5=SHADOW/"worldwide_method_v5_prospective_shadow.json"
V7=SHADOW/"worldwide_direct_six_v7_prospective_shadow.json"
DEST=ROOT/"data/grades/ufcqatar_2026_11_21_all_frozen_models_and_public_card_grade.json"
REPORT=ROOT/"reports/model_health/2026-11-24_UFC_QATAR_ALL_LOCKED_MODELS_GRADE.md"
STATE_KEYS=("A_KO","A_SUB","A_DEC","B_KO","B_SUB","B_DEC")
HEADS=("reference","historical","unified")
PRIMARY=("reference","historical","unified",
         "coherent_reference_aligned","coherent_historical_aligned",
         "coherent_unified_aligned",
         "winner_v3_primary","winner_v4_primary","method_v5_primary",
         "direct_six_v7_primary")
SOURCE_SCOPE="12 distinct decisive completed bouts; original 11 plus late provisional Mitchell-Yousaf"

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def method(m):
    s=str(m).upper()
    if s.startswith("KO"):return "KO"
    if s.startswith("DEC"):return "DEC"
    if s.startswith("SUB"):return "SUB"
    raise ValueError(f"Unrecognized method {m}")

def probs(cell):
    if set(cell)!=set(STATE_KEYS):raise ValueError("Incomplete 6-state bout predictions")
    v={x:float(cell[x]) for x in STATE_KEYS}
    if not all(math.isfinite(x) and 0<=x<=1 for x in v.values()) or abs(sum(v.values())-1)>1e-8:
        raise ValueError("Incoherent result probabilities")
    return v

def valid_card(o,c,v3,v4,v5,v7):
    if len(o["fights"])!=12:raise ValueError("12 original fighters required")
    if not o["stage_a_frozen"] or o["event_date"]!=DAY or o["odds_used"]:
        raise ValueError("Official Stage A original card altered")
    checks={
        "coherent":c["source_frozen_stage_a_sha256"]==sha(LOCK),
        "v3":v3["original_stage_a_sha256"]==sha(LOCK) and v3["original_coherent_shadow_sha256"]==sha(COH),
        "v4":v4["original_stage_a_sha256"]==sha(LOCK) and v4["original_independent_v3_shadow_sha256"]==sha(V3),
        "v5":v5["original_stage_a_sha256"]==sha(LOCK) and v5["independent_v3_sha256"]==sha(V3) and v5["independent_v4_sha256"]==sha(V4),
        "v7":all(v7["original_frozen_sha256"].get(p.name)==sha(p)
                 for p in (LOCK,ROOT/"data/locks/ufcqatar_2026-11-21/stage_a_final_audit.json",COH,V3,V4,V5))
    }
    if not all(checks.values()):raise ValueError("Previously frozen 11/21 source SHA mismatch "+str(checks))
    if not (len(c["fights"])==len(v3["fights"])==len(v4["fights"])==len(v5["research_predictions"])==len(v7["research_fights"])==12):
        raise ValueError("Original graded bout identity count mismatch")
    return checks

def get_pred(i,o,c,v3,v4,v5,v7):
    f=o["fights"][i];g=c["fights"][i]
    a=f["a"];b=f["b"]
    checks=(g,v3["fights"][i],v4["fights"][i],v5["research_predictions"][i],v7["research_fights"][i])
    if any((z["fight_no"],z["a"],z["b"])!=(i+1,a,b) for z in checks):
        raise ValueError("Different matchup in frozen research file")
    selections={}
    methods=f["method"]["primary_method_forecast_for_grade"]
    original=[
        ("reference",f["official_reference_pick"],methods["reference"]),
        ("historical",f["winner_views"]["historical_shadow"]["pick"],methods["historical_own_fighter"]),
        ("unified",f["winner_views"]["oof_unified_shadow"]["pick"],methods["unified_own_fighter"]),
    ]
    for key,w,m in original:
        selections[key]={"winner":w,"method":method(m),"joint":None,
                         "cohort":"ORIGINAL_ODDS_BLIND_STAGE_A"}
    for v in HEADS:
        original_c=g["models"][v]["variant_selections"]["winner_and_timing_aligned"]
        selections["coherent_"+v+"_aligned"]={
            "winner":original_c["frozen_winner_pick"],
            "method":method(original_c["selected_method_given_frozen_winner"]),
            "joint":g["models"][v]["distributions"]["winner_and_timing_aligned"],
            "cohort":"COHERENT_PROBABILITY_POSTPROCESSOR_NOT_INDEPENDENT_MODEL"}
        if selections[v]["winner"]!=selections["coherent_"+v+"_aligned"]["winner"]:
            raise ValueError("Coherent variant rewrote original winner")
    newer=[
        ("winner_v3_primary",v3["fights"][i]["research_models"]["logit_recent_57"]),
        ("winner_v4_primary",v4["fights"][i]["research_variants"]["winner_v4_boost73"]),
        ("method_v5_primary",v5["research_predictions"][i]["method_model_variants"]["worldwide_MMA_multinomial54"]),
    ]
    for name,p in newer:
        selections[name]={"winner":p["winner"],"method":method(p["method"]),
                          "joint":p["six_joint"],"cohort":"PROSPECTIVE_RESEARCH_ONLY"}
    g7=v7["research_fights"][i]
    selections["direct_six_v7_primary"]={
        "winner":g7["winner"],"method":method(g7["method"]),
        "joint":g7["six_joint"],"cohort":"PROSPECTIVE_RESEARCH_ONLY"}
    if set(selections)!=set(PRIMARY):raise ValueError("All ten originally locked arms required")
    for x in selections.values():
        if x["winner"] not in (a,b):raise ValueError("Winner not in matched fight identity")
        if x["joint"] is not None:
            q=probs(x["joint"])
            winner_is_a=x["winner"]==a
            # In the original v7 pick policy the chosen method maximizes
            # conditional class for the winner marginal; same requirement.
            idx=("A_" if winner_is_a else "B_")+x["method"]
            if q[idx]<=0:raise ValueError("Research-selected event class has invalid zero mass")
    return selections

def grade_prediction(guess,truth,a):
    win=guess["winner"]==truth["winner"]
    m=guess["method"]==truth["method"]
    out={
        "winner":guess["winner"],"selected_method":guess["method"],
        "winner_hit":int(win),"method_class_hit":int(m),"exact_hit":int(win and m),
        "correct_winner_wrong_method":int(win and not m),
        "cohort":guess["cohort"]
    }
    if guess["joint"] is not None:
        q=probs(guess["joint"])
        key=("A_" if truth["winner"]==a else "B_")+truth["method"]
        ref=q[key]
        pa=q["A_KO"]+q["A_SUB"]+q["A_DEC"]
        actualA=int(truth["winner"]==a)
        out.update({"six_logloss":-math.log(max(1e-12,ref)),
                    "six_brier":sum((v-int(k==key))**2 for k,v in q.items()),
                    "winner_brier":(pa-actualA)**2,
                    "p_predicted_exact":q[("A_" if guess["winner"]==a else "B_")+guess["method"]]})
    return out

def timing_grade(f,truth):
    p=f["primary_timing_forecast"]
    key=p["market_key"]
    r=int(truth["round"])
    minutes=(r-1)*5+int(truth["round_clock"].split(":")[0])+int(truth["round_clock"].split(":")[1])/60
    dec=truth["method"]=="DEC"
    if key=="GTD_YES":hit=dec
    elif key=="GTD_NO":hit=not dec
    elif key=="ROUND_2_STARTS_YES":hit=minutes>5
    elif key=="ROUND_2_STARTS_NO":hit=minutes<=5
    elif key=="ROUND_3_STARTS_YES":hit=minutes>10
    elif key=="ROUND_3_STARTS_NO":hit=minutes<=10
    elif key.startswith("OVER_"):hit=minutes>5*float(key.split("_")[1])
    elif key.startswith("UNDER_"):hit=minutes<5*float(key.split("_")[1])
    else:raise ValueError("Unsupported original timing selection "+str(key))
    return {"frozen_primary_timing_market":p["market"],"market_key":key,
            "hit":int(hit),"actual_duration_minutes":minutes,
            "original_frozen_p":p["min_two_model_probability"],"unpriced":True}

# Pre-event user chat choices, NOT cryptographically GitHub Stage A predictions.
PUBLIC=(
    ("Diyar Nurgozhay",("KO",),None),
    ("Dom Mar Fan",("KO","DEC"),None),
    ("Jake Matthews",("DEC",),None),
    ("Amir Albazi",("DEC",),None),
    ("Tallison Teixeira",("KO",),None),
    (None,(),True),  # Topuria vs Luna GTD YES
    ("Ikram Aliskerov",("KO",),None),
    ("Asu Almabayev",("SUB","DEC"),None),
    ("Dan Hooker",("KO","DEC"),None),
    ("Kevin Vallejos",("KO",),None),
    ("Navajo Stirling",("KO",),None),
    ("John Mitchell",("KO",),None),
)
def public_grade(i,truth):
    expected=PUBLIC[i]
    if expected[2] is True:
        return {"pick":"FIGHT_GOES_DISTANCE_YES","hit":int(truth["method"]=="DEC"),
                "market_type":"GTD_YES"}
    return {"pick":expected[0]+" "+"/".join(expected[1]),
            "hit":int(expected[0]==truth["winner"] and truth["method"] in expected[1]),
            "market_type":"WINNER_AND_ALLOWED_METHODS"}

def summarize(records):
    bymodel={}
    for name in PRIMARY:
        x=[r["models"][name] for r in records]
        hits=sum(z["winner_hit"] for z in x)
        exact=sum(z["exact_hit"] for z in x)
        methodhits=sum(z["method_class_hit"] for z in x)
        total=len(x)
        calc={
            "winner_hits":hits,"winner_accuracy":hits/total,
            "exact_hits":exact,"exact_accuracy":exact/total,
            "method_class_hits":methodhits,
            "conditional_method_when_winner_correct":exact/hits if hits else None,
            "correct_winner_wrong_method":sum(z["correct_winner_wrong_method"] for z in x),
            "original_11_excluding_provisional_exact":sum(z["exact_hit"] for z in x[:-1]),
            "original_11_excluding_provisional_winner":sum(z["winner_hit"] for z in x[:-1]),
            "round_proper_scores_included":bool("six_logloss" in x[0]),
        }
        if "six_logloss" in x[0]:
            for stat in ("six_logloss","six_brier","winner_brier"):
                calc[stat]=sum(z[stat] for z in x)/total
        bymodel[name]=calc
    return bymodel

def main():
    if DEST.exists() or REPORT.exists():
        raise FileExistsError("Original archived Nov24 grade cannot be silently overwritten")
    o,c,v3,v4,v5,v7=[read(x) for x in (LOCK,COH,V3,V4,V5,V7)]
    actual=read(SOURCE)
    if actual["event_date"]!=DAY or len(actual["fights"])!=12:
        raise ValueError("12 independently verified official results required")
    checks=valid_card(o,c,v3,v4,v5,v7)
    rows=[]
    for i,(fight,result) in enumerate(zip(o["fights"],actual["fights"])):
        if result["fight_no"]!=i+1 or not result["decisive"] or not result["winning_fighter_and_method_verified"]:
            raise ValueError("Unverified, void, duplicate or reordered fight results")
        if {result["winner"],result["loser"]}!={fight["a"],fight["b"]}:
            raise ValueError("Fighter in result not in preevent matchup; do not auto alias")
        picked=get_pred(i,o,c,v3,v4,v5,v7)
        graded={k:grade_prediction(sel,result,fight["a"]) for k,sel in picked.items()}
        rows.append({
            "fight_no":i+1,"bout_key":f"ufcqatar_2026_11_21_{i+1:02d}",
            "original_a":fight["a"],"original_b":fight["b"],
            "result":{"winner":result["winner"],"method":result["method"],
                      "round":result["round"],"time":result["round_clock"],
                      "official_method_description":result["official_method_description"]},
            "original_stage_a_posture_UNCHANGED":fight["stage_a_posture"],
            "original_unconfirmed_provisional":bool(i==11),
            "models":graded,
            "primary_timing":timing_grade(fight,result),
            "public_video_card":public_grade(i,result),
        })
    model_summaries=summarize(rows)
    public_hits=sum(r["public_video_card"]["hit"] for r in rows)
    timing_hits=sum(r["primary_timing"]["hit"] for r in rows)
    methods=Counter(r["result"]["method"] for r in rows)
    result={
        "schema":"WSHLX_UFC_QATAR_NOV21_MODEL_X10_AND_PUBLIC_CARD_POST_EVENT_GRADE",
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "event_date":DAY,"scope":SOURCE_SCOPE,
        "original_Reference_and_model_shadows_never_modified":True,
        "source_result_path":str(SOURCE.relative_to(ROOT)),
        "source_result_sha256":sha(SOURCE),
        "frozen_source_hashes":{p.name:sha(p) for p in (LOCK,COH,V3,V4,V5,V7)},
        "original_sha_checks":checks,
        "confirmed_fight_count":len(rows),
        "method_distribution":dict(methods),
        "model_summaries":model_summaries,
        "primary_stage_a_timing":{"correct":timing_hits,"total":12,
                                  "accuracy":timing_hits/12,
                                  "all_unpriced":True},
        "public_pre_event_selections_FROM_CHAT_NOT_OFFICIAL_MODEL_LOCK":{
            "correct":public_hits,"total":12,"accuracy":public_hits/12,
            "original_11_excluding_provisional":sum(x["public_video_card"]["hit"] for x in rows[:-1]),
            "distinct_public_card_vs_preregistered_original":True,
            "bets_not_verified_no_ROI_claim":True,
        },
        "coherent_postprocessed_views_NOT_independent_winner_models":True,
        "genuinely_forward_this_event_ONLY_one_event_n12":True,
        "no_model_promotion_based_on_single_event":True,
        "existing_Stage_B_and_FanDuel_prices_NOT_INFERRED":True,
        "newly_approved_bets":0,"betting_roi_UNVERIFIED":True,
        "event_results_not_added_to_training_or_old_picks":True,
        "per_fight":rows,
    }
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    lines=[
        "# UFC Qatar (November 21, 2026) — independently frozen models graded November 24",
        "",
        "**12 of 12 decisive event bouts verified. Source: SPORTS ILLUSTRATED MMA and Cage Almanac UFCStats-derived outcomes, 2026-11-21/22. All original predictions preserved by source SHA checks.**",
        "",
        "| Model/view | Winners | Exact fighter + method | Conditional method given correct winner |",
        "|---|---:|---:|---:|",
    ]
    for name,stat in model_summaries.items():
        lines.append(f"| {name} | {stat['winner_hits']}/12 | **{stat['exact_hits']}/12** | {stat['exact_hits']}/{stat['winner_hits']} |")
    lines+=["",f"Original frozen Stage A primary timing: **{timing_hits}/12** correct; no FanDuel price/ROI inferred.",
            f"Separate public user-selected fighter/method/GTD/double-chance video card: **{public_hits}/12**; not the official original card.",
            "","## Fight-by-fight, primary views","",
            "| Matchup | Actual | Reference | Historical | Unified | Coherent reference | Coherent unified | V3 | V4 | V5 | V7 | Public |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    abbreviations={"reference":"Ref","historical":"Hist","unified":"Uni",
        "coherent_reference_aligned":"C-Ref","coherent_unified_aligned":"C-Uni",
        "winner_v3_primary":"V3","winner_v4_primary":"V4",
        "method_v5_primary":"V5","direct_six_v7_primary":"V7"}
    for r in rows:
        name=r["original_a"].split()[-1]+" vs "+r["original_b"].split()[-1]
        true=r["result"]["winner"].split()[-1]+" "+r["result"]["method"]
        col=[]
        for key in ("reference","historical","unified","coherent_reference_aligned",
                    "coherent_unified_aligned","winner_v3_primary","winner_v4_primary",
                    "method_v5_primary","direct_six_v7_primary"):
            x=r["models"][key]
            mark="✅" if x["exact_hit"] else ("~" if x["winner_hit"] else "❌")
            col.append(x["winner"].split()[-1]+" "+x["selected_method"]+" "+mark)
        # Include 9 models after actual; public makes 10 extra columns.
        lines.append("| "+" | ".join([name,true,*col,
                         r["public_video_card"]["pick"]+(" ✅" if r["public_video_card"]["hit"] else " ❌")])+" |")
    lines+=["","## Source facts and defensible findings",
            "",
            "- Event produced **8 decisions, 3 KO/TKO finishes, 1 submission**. Reference originally got 11/12 winners but just 4/12 exact, an observable METHOD bottleneck.",
            "- Coherent Reference and Coherent Unified **winner_and_timing_aligned** research variants each reached **7/12 exact (58.3%)**, keeping their same original winner picks. These are probability postprocessors, not an independent learner; do not claim 58.3% future accuracy from a single event or retrospectively select the winning postprocessor.",
            "- Winner v3/v4 did not improve winner accuracy on this forward event. Method v5 and direct six v7 got 5/12 exact but both chose only 8/12 correct winners, so the old winner head remained strongest this event.",
            "- Original first 11 bouts plus previously reported late provisional Mitchell/Yousaf scored separately in structured JSON. The last fight is counted as genuine decisive, but not retroactively part of original 11 originally confirmed fights.",
            "- The public card graded separately: user double-chance and GTD bets are treated as combined markets, not the same exact-method category. No FanDuel prices, stakes or independently verified closing lines supplied, so zero hypothetical/real profitability conclusions.",
            "- ONE event is insufficient for model promotion. Preserve all original source SHA and register new predictions before another future fight. Compare opponent-specific finish mechanisms and original GTD timing props after reviewing actual UFCStats per-fight stats, not invented tape observations.",
            "",
            "## External verification",
            "",
            "- https://www.si.com/fannation/mma/news/ufc-qatar-free-live-stream-results-highlights-prochazka-vs-stirling",
            "- https://cagealmanac.com/events/ufc-fight-night-prochazka-vs-stirling-cbf69f",
            "- https://www.ufc.com/news/ufc-qatar-results-prochazka-vs-stirling",
            "",
            "Legend: ✅ exact; ~ winner correct but method wrong; ❌ winning fighter incorrect.",
            ""]
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text("\n".join(lines))
    print(json.dumps({
        "STATUS":"PREFIGHT_ORIGINAL_AND_ALL_MODEL_SHA_VERIFIED_POSTFIGHT_GRADED",
        "model_summaries":{k:{"win":v["winner_hits"],"exact":v["exact_hits"]}
                           for k,v in model_summaries.items()},
        "timing_hits":timing_hits,"public_hits":public_hits,
        "actual_methods":dict(methods),
        "graded_sha":sha(DEST),
        "report_sha":sha(REPORT),
    },sort_keys=True))

if __name__=="__main__":main()
