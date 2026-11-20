"""Research-only trained selective exact winner+method reliability gate.

Trains on earlier OUT-OF-YEAR, pre-fight source probabilities and past label
correctness; predicts NEXT YEAR's correctness. No fit on target year's
outcomes, fighter name, or sportsbook odds. Compare against exact-probability
ranked picks on identical 11-14 fight cards. Arbitrary 2-5 bets never forced.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter
import csv,json,hashlib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

BASE=Path("reports/model_health/2026-11-19_exact_outcome_phase2")
INPUT=BASE/"out_of_year_six_predictions.csv"
OUTPUT=BASE/"trained_selective_gate_2025_2026.json"
FEATURES=(
    "exact_probability","global_exact_probability","own_gap","global_gap",
    "winner_confidence","min_prior_ufc","min_stats_coverage",
    "direct_for_own","agree_global","global_gap_direct"
)

def joined():
    df=pd.read_csv(INPUT,low_memory=False)
    df=df.loc[df["variant"]=="all_features"].copy()
    fact=df.loc[df["model"]=="factorized6"].copy()
    direct=df.loc[df["model"]=="direct6"].copy()
    if len(fact)!=1512 or len(direct)!=1512:raise ValueError("1,512 original fights per model expected")
    fields=["bout_id","global_pick","global_gap","a_ko","a_sub","a_dec","b_ko","b_sub","b_dec"]
    merged=fact.merge(direct[fields],on="bout_id",suffixes=("","_direct"),
                      validate="one_to_one")
    if len(merged)!=1512:raise ValueError("Matched forecast identity drift")
    same=np.arange(len(merged))
    columns=np.asarray([x+"_direct" for x in ("a_ko","a_sub","a_dec","b_ko","b_sub","b_dec")])
    merged["direct_for_own"]=merged[columns].to_numpy()[same,merged["picked_exact_state"].astype(int)]
    merged["agree_global"]=(merged["picked_exact_state"]==merged["global_pick_direct"]).astype(int)
    merged["winner_confidence"]=np.maximum(merged["prob_a"],1-merged["prob_a"])
    if merged[list(FEATURES)].isna().any().any():raise ValueError("Missing pre-result training feature")
    return merged

def evaluate_cards(t,rank):
    subsets=[g for _,g in t.groupby(["date","event"])
             if 11<=len(g)<=14]
    if not subsets:raise ValueError("No full-card cohort")
    result={"full_11_14_fight_cards":len(subsets),"rank_by":rank}
    for k in (2,3,5):
        selected=[g.sort_values([rank,"bout_id"],ascending=[False,True]).head(k)
                  for g in subsets]
        p=pd.concat(selected,ignore_index=True)
        result["top_"+str(k)]={
            "picks":len(p),"exact_hits":int(p["exact"].sum()),
            "hit_rate":float(p["exact"].mean()),
            "perfect_selected_cards":sum(bool(s["exact"].all()) for s in selected),
            "perfect_selected_card_rate":sum(bool(s["exact"].all()) for s in selected)/len(selected),
        }
    return result

def cut_gate(t,*,threshold=.60):
    g=[s for _,s in t.groupby(["date","event"]) if 11<=len(s)<=14]
    chosen=[]
    for x in g:
        q=x.loc[(x["score_reliability"]>=threshold)&(x["min_prior_ufc"]>=5)]
        q=q.sort_values(["score_reliability","bout_id"],ascending=[False,True]).head(5)
        chosen.append(q)
    allselected=pd.concat(chosen,ignore_index=True)
    sizes=Counter(len(q) for q in chosen)
    full=[q for q in chosen if 2<=len(q)<=5]
    return {
        "gate":"estimated correctness >=60%, both >=5 prior UFC bouts, up to five",
        "cards":len(g),"selection_size_counts":dict(sizes),
        "zero_pick_cards":sizes[0],
        "picks":len(allselected),
        "exact_hits":int(allselected["exact"].sum()),
        "hit_rate":float(allselected["exact"].mean()) if len(allselected) else None,
        "cards_with_two_to_five":len(full),
        "all_two_to_five_hit_count":sum(bool(q["exact"].all()) for q in full),
        "forced_bets":0,
    }

def run():
    f=joined()
    result={"schema":"WSHLX_PREVIOUS_YEAR_ONLY_SELECTIVE_EXACT_RELIABILITY_GATE",
        "source_predictions_sha256":hashlib.sha256(INPUT.read_bytes()).hexdigest(),
        "no_current_year_result_columns_as_model_inputs":True,
        "predicts_selected_fighter_plus_method_exact_NOT_WINNER":True,
        "years_used_to_train_frozen_base_models_are_exclusive":True,
        "future_test_dates_not_training_or_threshold_tuning":True,
        "not_prospective":True,"not_a_production_or_FanDuel_bet_gate":True,
        "no_original_nov21_lock_changes":True,
        "fixed_logistic_regularization":.2,
        "predeclared_features":FEATURES,"folds":{}}
    for y in (2025,2026):
        training=f.loc[f["year"]<y]
        test=f.loc[f["year"]==y].copy()
        if (y==2025 and (len(training),len(test))!=(511,513)) or (
            y==2026 and (len(training),len(test))!=(1024,488)):
            raise ValueError("Date fold cohort drift")
        clf=make_pipeline(StandardScaler(),
            LogisticRegression(C=.2,max_iter=3000))
        clf.fit(training[list(FEATURES)],training["exact"].astype(int))
        test["score_reliability"]=clf.predict_proba(test[list(FEATURES)])[:,1]
        result["folds"][str(y)]={
            "training_fights":len(training),"evaluation_fights":len(test),
            "max_score":float(test["score_reliability"].max()),
            "number_scored_above60pct":int((test["score_reliability"]>=.60).sum()),
            "rank_by_trained_reliability":evaluate_cards(test,"score_reliability"),
            "rank_by_existing_exact_probability":evaluate_cards(test,"exact_probability"),
            "abstain_if_no_60pct_support":cut_gate(test),
        }
    OUTPUT.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({"status":"RESEARCH_ONLY_NO_SELECTIVE_MODEL_PROMOTION","folds":result["folds"]},sort_keys=True))

if __name__=="__main__":
    run()
