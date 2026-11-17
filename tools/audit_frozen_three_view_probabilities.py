"""Audit original frozen UFC probabilities (research only; never refit or alter locks).

Main three-view cohort: Oct24, Nov7, Nov14. Known original forecast files
are digest-checked against the final Stage A freeze. Use the model's own
selected fighter, not the actual winner, when grading method picks.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import json
import math
import random
from pathlib import Path

from wshlx_ufc.historical_feature_matrix import load_matrix
from wshlx_ufc.historical_baselines import _winner_probabilities
from wshlx_ufc.longitudinal_audit import ROOT, _clean153, _sha, _load

CARDS = {
    "2026-10-24": "ufc333_2026-10-24",
    "2026-11-07": "ufcvegas124_2026-11-07",
    "2026-11-14": "ufc334_2026-11-14",
}
MODELS = ("reference", "historical", "unified")
METHODS = ("KO", "SUB", "DEC")
SIX = tuple(side + "_" + method for side in ("A", "B") for method in METHODS)
OUT = ROOT / "reports/model_health/2026-11-17_FROZEN_THREE_VIEW_PROBABILITY_AUDIT.json"


def checked(p):
    p = float(p)
    if not math.isfinite(p) or not 0 <= p <= 1:
        raise ValueError("Invalid archived probability")
    return p


def log_probability(p):
    return -math.log(max(1e-12, checked(p)))


def unique_map(rows, key):
    ans = {}
    for row in rows:
        k = key(row)
        if k in ans:
            raise ValueError("Duplicate identity: " + str(k))
        ans[k] = row
    return ans


def key(day, a, b):
    return (day, *sorted((a, b)))


def validate_joint(j):
    if set(j) != set(SIX):
        raise ValueError("Missing or unexpected joint outcome cells")
    out = {k: checked(j[k]) for k in SIX}
    if abs(sum(out.values()) - 1) > 1e-7:
        raise ValueError("Six-cell probabilities do not sum to one")
    return out


def model_values(f):
    return {
        "reference": (f["winner_reference_p_a"], f["joint_calibrated"], f["timing_v033_direct"]),
        "historical": (f["historical_shadow"]["winner_p_a"], f["historical_shadow"]["joint_method"], f["historical_shadow"]["timing_direct"]),
        "unified": (f["oof_unified_shadow"]["winner_p_a"], f["oof_unified_shadow"]["joint_method"], f["oof_unified_shadow"]["timing_direct"]),
    }


def score_row(p, joint, truth_side, truth_method, gtd_p, actual_gtd):
    p = checked(p)
    j = validate_joint(joint)
    # Keep native winner and native six-way forecasts separate. Their marginals
    # may differ in two shadow views; never silently repair the original.
    side = "A" if p >= .5 else "B"
    selected_method = max(METHODS, key=lambda m: j[side + "_" + m])
    best_cell = max(SIX, key=j.get)
    gap = abs(p - sum(j["A_" + m] for m in METHODS))
    obs = {"winner_p_a": p, "selected_side": side,
           "selected_method": selected_method, "global_joint_argmax": best_cell,
           "joint_p": j, "winner_joint_marginal_gap": gap,
           "gtd_p": checked(gtd_p), "actual_gtd": bool(actual_gtd),
           "gtd_brier": (gtd_p - int(actual_gtd))**2,
           "gtd_log_loss": log_probability(gtd_p if actual_gtd else 1-gtd_p)}
    if truth_side is None:
        return obs
    y = int(truth_side == "A")
    true_cell = truth_side + "_" + truth_method
    obs.update({
        "winner_correct": int(side == truth_side),
        "winner_brier": (p-y)**2,
        "winner_log_loss": log_probability(p if y else 1-p),
        "selected_fighter_method_exact": int(side == truth_side and selected_method == truth_method),
        "selected_fighter_method_class_correct": int(selected_method == truth_method),
        "global_joint_argmax_exact": int(best_cell == true_cell),
        "six_class_brier": sum((v-int(k==true_cell))**2 for k,v in j.items()),
        "six_class_log_loss": log_probability(j[true_cell]),
        "true_cell_probability": j[true_cell],
        "true_winner_probability": p if y else 1-p,
    })
    return obs


def summary(rows, name):
    allobs = [r["models"][name] for r in rows]
    decisive = [(r,r["models"][name]) for r in rows if r["truth_side"] is not None]
    obs = [x for _,x in decisive]
    n = len(obs)
    def avg(k): return sum(x[k] for x in obs)/n
    class_stats = {}
    for m in METHODS:
        actual = sum(r["truth_method"] == m for r,_ in decisive)
        pred = sum(x["selected_method"] == m for x in obs)
        correct = sum(r["truth_method"] == m and x["selected_method"] == m for r,x in decisive)
        exact = sum(r["truth_method"] == m and x["selected_method"] == m and x["winner_correct"] for r,x in decisive)
        class_stats[m] = {"actual":actual,"predicted":pred,"class_hits":correct,"exact_hits":exact,
                          "class_recall":correct/actual if actual else None}
    return {
        "decisive": n, "events": len({r["date"] for r,_ in decisive}),
        "winner_hits": sum(x["winner_correct"] for x in obs),
        "winner_accuracy": avg("winner_correct"), "winner_brier": avg("winner_brier"),
        "winner_log_loss":avg("winner_log_loss"),
        "own_selected_fighter_exact_hits":sum(x["selected_fighter_method_exact"] for x in obs),
        "own_selected_fighter_method_class_hits":sum(x["selected_fighter_method_class_correct"] for x in obs),
        "global_joint_top_cell_hits":sum(x["global_joint_argmax_exact"] for x in obs),
        "six_class_brier":avg("six_class_brier"), "six_class_log_loss":avg("six_class_log_loss"),
        "class_stats":class_stats,
        "joint_winner_marginal_gap_over_1pp":sum(x["winner_joint_marginal_gap"]>.01+1e-12 for x in allobs),
        "joint_winner_marginal_gap_max":max(x["winner_joint_marginal_gap"] for x in allobs),
        "gtd_n_including_draws":len(allobs),
        "gtd_brier":sum(x["gtd_brier"] for x in allobs)/len(allobs),
        "gtd_log_loss":sum(x["gtd_log_loss"] for x in allobs)/len(allobs),
        "gtd_expected":sum(x["gtd_p"] for x in allobs),
        "gtd_actual":sum(x["actual_gtd"] for x in allobs),
        "confidence_buckets":[{"range":f"{lo:.2f}-{hi:.2f}",
                               "n":len(bucket), "mean_confidence":sum(max(x["winner_p_a"],1-x["winner_p_a"]) for x in bucket)/len(bucket) if bucket else None,
                               "observed_accuracy":sum(x["winner_correct"] for x in bucket)/len(bucket) if bucket else None}
                              for lo,hi in ((.5,.6),(.6,.7),(.7,.8),(.8,1.000001))
                              for bucket in [[x for x in obs if lo<=max(x["winner_p_a"],1-x["winner_p_a"])<hi]]],
    }


def event_interval(rows, other, metric, samples=1000):
    groups = defaultdict(list)
    for r in rows:
        if r["truth_side"] is not None:
            groups[r["date"]].append(r["models"][other][metric]-r["models"]["reference"][metric])
    dates = sorted(groups)
    rng = random.Random(19)
    vals = []
    for _ in range(samples):
        draw = [dates[rng.randrange(len(dates))] for __ in dates]
        d = [v for day in draw for v in groups[day]]
        vals.append(sum(d)/len(d))
    vals.sort()
    return [vals[int(.025*(samples-1))], vals[int(.975*(samples-1))]]


def run():
    features, labels, manifest = load_matrix()
    label_by_id = unique_map(labels,lambda x:x["bout_id"])
    lookup = unique_map(features,lambda x:key(x["event_date"],x["fighter_a"],x["fighter_b"]))
    clean = unique_map(_clean153(),lambda x:key(x["event_date"],*x["fight"].split(" vs ")))
    train_counts = Counter(x["label_method"] for x in labels if "2021-01-01"<=x["event_date"]<"2026-01-01" and x["result_status"]=="DECISIVE")
    prior = {m:(train_counts["KO_TKO" if m=="KO" else m]+1)/(sum(train_counts.values())+3) for m in METHODS}
    results334 = _load("data/results/ufc334_2026-11-14_verified_outcomes.json")
    grade334 = _load("data/results/ufc334_2026-11-14_all_models_grading.json")
    outcomes334 = unique_map(results334["fights"],lambda f:f["fight_no"])
    rows, evidence, baseline_rows = [], [], []
    for day, folder in CARDS.items():
        path = f"data/locks/{folder}/stage_a_final_selection.json"
        final = _load(path)
        raw_path = final["raw_model_path"]
        raw = _load(raw_path)
        digest = _sha(raw_path)
        if digest != final["raw_model_sha256"] or not final["stage_a_frozen"] or final["odds_used"] or raw["odds_used"]:
            raise ValueError("Freeze/raw SHA/odds integrity failure")
        if final["event_date"] != day or raw["event_date"] != day:
            raise ValueError("Event date mismatch")
        if datetime.fromisoformat(final["frozen_at_utc"]).date().isoformat() >= day:
            raise ValueError("Final freeze not before event calendar date")
        if raw["event_date"] != day or datetime.fromisoformat(raw["generated_at_utc"]) > datetime.fromisoformat(final["frozen_at_utc"]):
            raise ValueError("Invalid model/final time order")
        if day=="2026-11-14":
            if grade334["original_raw_sha256"]!=digest or results334["original_stage_a_raw_sha256"]!=digest or grade334["original_stage_a_sha256"]!=_sha(path):
                raise ValueError("UFC334 grade/outcome source provenance mismatch")
        final_fights = unique_map(final["fights"],lambda x:x["fight_no"])
        if len(raw["fights"])!=len(final_fights):
            raise ValueError("Different raw and final fight counts")
        evidence.append({"date":day,"raw_path":raw_path,"raw_sha256":digest,"final_path":path,
                         "final_sha256":_sha(path),"frozen_at_utc":final["frozen_at_utc"],
                         "fights":len(final_fights)})
        for f in raw["fights"]:
            ff=final_fights[f["fight_no"]]
            a,b=f["a"],f["b"]
            if (a,b)!=(ff["a"],ff["b"]):
                raise ValueError("Raw-final identity mismatch")
            kk=key(day,a,b)
            if day=="2026-11-14":
                result=outcomes334[f["fight_no"]]
                if (a,b)!=(result["a"],result["b"]):
                    raise ValueError("Nov14 outcome identity mismatch")
                winner,method,elapsed=result["winner"],result["method"],result["elapsed_seconds"]
            else:
                hist, truth=lookup[kk],clean[kk]
                lab=label_by_id[hist["bout_id"]]
                method=truth["actual_method"]
                winner=truth["actual_winner"]
                elapsed=lab["label_elapsed_seconds"]
                lab_winner=hist["fighter_a"] if lab["label_a_win"]==1 else hist["fighter_b"]
                if lab["result_status"]!="DECISIVE" or lab_winner!=winner or lab["label_method"]!=("KO_TKO" if method=="KO" else method):
                    raise ValueError("Independent label mismatch")
            if method=="DRAW":
                if winner is not None: raise ValueError("Draw with winner")
                side=None
            else:
                if method not in METHODS or winner not in (a,b): raise ValueError("Invalid decisive outcome")
                side="A" if winner==a else "B"
            gtd = elapsed>=f["scheduled_seconds"]
            row={"date":day,"a":a,"b":b,"truth_side":side,"truth_method":method,
                 "winner":winner,"elapsed_seconds":elapsed,"scheduled_seconds":f["scheduled_seconds"],"models":{}}
            for name,(p,j,t) in model_values(f).items():
                view=ff["winner_views"][{"reference":"reference","historical":"historical_shadow","unified":"oof_unified_shadow"}[name]]
                selected=a if p>=.5 else b
                if view["pick"]!=selected or abs(view["probability"]-max(p,1-p))>1e-7:
                    raise ValueError("Final winner differs from frozen raw")
                row["models"][name]=score_row(p,j,side,method,t["GTD_YES"],gtd)
            rows.append(row)
            if day!="2026-11-14":
                # Baselines share precisely the original 28 matchups. Convert
                # source A/B orientation to original raw A/B orientation.
                for name,p0 in _winner_probabilities(hist).items():
                    p=p0 if hist["fighter_a"]==a else 1-p0
                    j={s+"_"+m:(p if s=="A" else 1-p)*prior[m] for s in ("A","B") for m in METHODS}
                    row["models"][name]=score_row(p,j,side,method,prior["DEC"],gtd)
                baseline_rows.append(row)
    if len(rows)!=41 or sum(r["truth_side"] is not None for r in rows)!=40 or len(baseline_rows)!=28:
        raise ValueError("Expected 41 scheduled / 40 decisive and 28 paired simple benchmark fights")
    report={
        "schema":"WSHLX_ORIGINAL_FROZEN_THREE_VIEW_AUDIT_V1",
        "research_status":"RETROSPECTIVE_PREVIOUSLY_INSPECTED_NO_PROMOTION",
        "source_evidence":evidence,
        "excluded_edmonton":"Reference-only native probabilities; no comparable three-view freeze. Do not pool.",
        "interesting_limitation":"Historical/Unified native six-class winner marginal may differ from independent winner head. No repair or substitution made.",
        "cohort_40_decisive":{m:summary(rows,m) for m in MODELS},
        "common_28_decisive":{m:summary(baseline_rows,m) for m in (*MODELS,"coinflip","prior_ufc_win_rate","past_only_ufc_elo")},
        "baseline_gtd_note":"For simple baselines, 2021-25 DEC prior is a proxy, not an independently validated duration model.",
        "per_event":{d:{m:summary([r for r in rows if r["date"]==d],m) for m in MODELS} for d in CARDS},
        "event_cluster_bootstrap_3_events_shadow_minus_reference_descriptive_only":{
            m:{k:event_interval(rows,m,k) for k in ("winner_brier","winner_log_loss","six_class_log_loss","selected_fighter_method_exact")}
            for m in ("historical","unified")},
        "row_evidence":rows,
        "no_model_trained_or_promoted":True,
        "stage_a_b_unchanged":True,
    }
    OUT.write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
    compact={k:v for k,v in report.items() if k!="row_evidence"}
    print(json.dumps(compact,sort_keys=True,allow_nan=False))
    return report


if __name__=="__main__":
    run()
