"""Nov7 challenger investigation with OLDER heldout evidence, not winner cherry-picking.

After a 14-fight card, sample-specific 11-3 or 8-6 cannot justify replacing
the v0.27 reference; historical winner 112-bout OOF/61-bout walkforward and
method 88-bout OOF must be reported in separate populations alongside
genuinely frozen Nov7 prospective comparisons.

No chance of retraining or tuning against Nov7 in this diagnostic. The
future-only model refit is a separate artifact. No market approvals made.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/"reports/contextual_unified_through_2026-10-17/diagnostic.json"
METHOD_DEV=ROOT/"reports/post_ufc333_method_finish_access/diagnostic.json"
WINNER_DEV=ROOT/"reports/v034_winner_interactions_clean112/benchmark.json"
NOV7=ROOT/"data/results/ufcvegas124_2026-11-07_all_models_grading.json"
SAVE=ROOT/"reports/ufcvegas124_2026-11-07/challenger_generalization_audit.json"


def read(path):
    return json.loads(path.read_text())


def mcnemar(a,b):
    """Two-sided exact paired sign test on discordant correctness (not odds)."""
    if len(a)!=len(b):raise ValueError("Must compare identical fights")
    b_better=sum(not x and y for x,y in zip(a,b))
    a_better=sum(x and not y for x,y in zip(a,b))
    n=b_better+a_better
    if not n:return {"candidate_better":0,"reference_better":0,"discordant":0,"exact_p_value":1.0}
    k=min(a_better,b_better)
    p=min(1.0,2*sum(math.comb(n,i) for i in range(k+1))/2**n)
    return {"candidate_better":b_better,"reference_better":a_better,
            "discordant":n,"exact_p_value":p}


def main():
    old=read(OLD)
    dev=read(METHOD_DEV)
    wdev=read(WINNER_DEV)
    g=read(NOV7)
    a=g["scoreboards"]
    if g["all_fights"]!=14 or len(g["fights"])!=14:
        raise RuntimeError("Missing 14 frozen results")
    if old["trained_through"]!="2026-10-17":
        raise RuntimeError("Older model diagnostic changed temporal scope")
    if old["winner"]["full_fit_metrics"]["current"]["n"]!=112 or old["method"]["full_fit_metrics"]["current"]["n"]!=88:
        raise RuntimeError("Historical heldout population mismatch")
    if old["winner"]["walk_forward"]["overall"]["current"]["n"]!=61:
        raise RuntimeError("Chronological winner eval sample changed")
    metric={}
    for task in ("winner","method"):
        cohorts=old[task]["full_fit_metrics"]
        keys=("current","historical","global_unified","contextual_unified")
        metric[task]={k:cohorts[k] for k in keys}
    winner_old=old["winner"]["full_fit_metrics"]
    # In the 112-fight historical OOF set, current model scores have smaller
    # Brier/log-loss. Nov7 better challenger hit rate is not a repeatable win.
    old_current=winner_old["current"]
    old_historical=winner_old["historical"]
    if not (old_historical["brier"]>old_current["brier"]
            and old_historical["log_loss"]>old_current["log_loss"]):
        raise RuntimeError("Development baseline claim changed")
    novel=[x["model_views"] for x in g["fights"]]
    paired_winner={
        k:mcnemar([x["reference"]["winner_correct"] for x in novel],
                  [x[k]["winner_correct"] for x in novel])
        for k in ("historical","unified")
    }
    paired_exact={
        k:mcnemar([x["reference"]["own_fighter_and_method_correct"] for x in novel],
                  [x[k]["own_fighter_and_method_correct"] for x in novel])
        for k in ("historical","unified")
    }
    if paired_winner["unified"]["candidate_better"]!=2 or paired_winner["unified"]["reference_better"]!=0:
        raise RuntimeError("Nov7 winner disagreement incorrect")
    if paired_exact["unified"]["candidate_better"]!=4 or paired_exact["unified"]["reference_better"]!=1:
        raise RuntimeError("Nov7 exact method disagreements incorrect")
    # Conditional method variant v0.35 was proposed after earlier card; its
    # retrospective OOF recalibration *did not* improve 115-fight proper scores.
    baseline=dev["evaluation"]["all_historical_dev"]["cal"]
    access=dev["evaluation"]["all_historical_dev"]["finish"]
    if not (baseline["n"]==access["n"]==115 and
            access["brier"]>baseline["brier"] and
            access["log_loss"]>baseline["log_loss"]):
        raise RuntimeError("v0.35 method development comparison changed")
    old_method=old["method"]["full_fit_metrics"]
    methods={}
    for key in ("reference","historical","unified"):
        top=[r["model_views"][key]["own_selected_fighter_conditional_method"] for r in g["fights"]]
        methods[key]=dict(Counter(top))
    actual=dict(Counter(x["method"] for x in g["fights"]))
    if actual!={"KO":6,"DEC":7,"SUB":1}:
        raise RuntimeError("Actual method mix differs from postevent grading")
    report={
        "status":"NOV7_CHALLENGER_GENERALIZATION_PROSPECTIVE_AND_OLDER_OOF_AUDIT",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "development_historical_data_through":"2026-10-17",
        "frozen_nov7_fights":14,
        "model_promotion_allowed":False,
        "older_winner_112_retrospective_comparison":metric["winner"],
        "older_winner_61_strict_walk_forward":old["winner"]["walk_forward"]["overall"],
        "older_method_88_retrospective_comparison":metric["method"],
        "historical_winner_112_diff_vs_reference":{
            "historical_minus_reference_brier":old_historical["brier"]-old_current["brier"],
            "historical_minus_reference_logloss":old_historical["log_loss"]-old_current["log_loss"],
        },
        "nov7_frozen_winner_accuracy":{k:{"correct":a[k]["winner_W"],"n":14,
                                         "accuracy":a[k]["winner_rate"],
                                         "brier":a[k]["mean_winner_multiclass_brier"],
                                         "log_loss":a[k]["mean_winner_logloss"]}
                                       for k in ("reference","historical","unified")},
        "nov7_frozen_joint_fighter_method_accuracy":{k:{"correct":a[k]["own_fighter_and_method_W"],
                                                       "n":14,
                                                       "accuracy":a[k]["exact_winner_method_rate"],
                                                       "six_class_brier":a[k]["mean_joint_method_six_class_brier"],
                                                       "six_class_log_loss":a[k]["mean_joint_method_six_class_logloss"]}
                                                     for k in ("reference","historical","unified")},
        "prospective_paired_winner_mcnemar":paired_winner,
        "prospective_paired_exact_method_mcnemar":paired_exact,
        "nov7_top_method_call_distribution_per_own_fighter":methods,
        "nov7_actual_method_distribution":actual,
        "existing_finish_access_variant_115_historical_dev":{
            "calibrated":baseline,
            "finish_access":access,
            "brier_access_minus_calibrated":access["brier"]-baseline["brier"],
            "logloss_access_minus_calibrated":access["log_loss"]-baseline["log_loss"],
            "promote_finish_access":False,
        },
        "existing_winner_interaction_benchmark":{
            "sample_fights":wdev["n"],
            "reference":wdev["base"],
            "best_candidate_variant":wdev["best_retrospective_brier_variant"],
            "best_candidate_retrospective_gate_pass":wdev["best_variant_passes_metric_gate"],
            "promotion_status":"HISTORICAL_DEV_ONLY_NOT_PROSPECTIVE_APPROVED",
        },
        "diagnostic_issues":[
            "Two winner disagreements Petersen and Walker favored both shadows on Nov7; exact paired p=0.5 (two discordant fights) insufficient to switch champion.",
            "Longer 112-fight historical winner OOF favored reference (lower Brier/log loss) over historical conditional model, contradicting Nov7 winner ranking.",
            "On older 88-fight fighter+method OOF, reference 36/88 exact vs unified 35/88 and historical 23/88. This contradicts Nov7 8/14 unified vs 5/14 reference advantage.",
            "Reference's own predicted methods tilted KO; actual 6 KO, 1 submission and 7 decisions. Seven decisions challenge finish-vs-decision model. But a single event cannot calibrate a classifier.",
            "v0.35 finish-access method candidate WORSENED older 115-fight log loss and Brier relative to calibrated baseline, so retain shadow only.",
            "Bashi SUB and Raposo DEC are genuinely useful method-error investigations; Smith KO and Magomedov DEC illustrate residual method failure.",
        ],
        "candidate_promotion_gate":{
            "minimum_prospective_fights":300,
            "newly_logged_nov7_prospective_fights":14,
            "sufficient_prospective_evidence":False,
            "must_improve_multiple_heldout_fight_probabilistic_metrics":True,
            "must_pass_consistency_and_price_calibration_gates":True,
            "champion_promoted":False,
            "reference_model_code_or_coefficients_modified":False,
        },
        "no_lookahead_policy":"Nov7 historical grades derived solely from archived pre-Nov7 outputs. Refitting future-only shadows AFTER Nov7 never counts as a Nov7 model win.",
    }
    SAVE.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "status":report["status"],
        "prior_112_reference_win_logloss":old_current["log_loss"],
        "prior_112_historical_win_logloss":old_historical["log_loss"],
        "nov7":report["nov7_frozen_joint_fighter_method_accuracy"],
        "method_candidate_115_brier_delta":report["existing_finish_access_variant_115_historical_dev"]["brier_access_minus_calibrated"],
        "winner_paired":paired_winner,"exact_paired":paired_exact,
        "promoted":False,
    },indent=2))


if __name__=="__main__":
    main()
