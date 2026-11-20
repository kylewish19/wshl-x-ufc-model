"""Audit coverage and 13 historically queried UFC334 pairs without changing picks.

NOTE: This is retrospective card replay. Do NOT label these new features as
the original Nov11 Stage A prediction inputs or as validated primary UFCStats.
"""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

from wshlx_ufc.prefight_finish_resistance import load_and_build

ROOT=Path(__file__).resolve().parents[1]
LOCK=ROOT/"data/locks/ufc334_2026-11-14/stage_a_final_selection.json"


def main():
    frozen=json.loads(LOCK.read_text())
    if frozen.get("stage_a_frozen") is not True or frozen.get("odds_used") is not False:
        raise RuntimeError("Original odds-blind Stage A freeze not verified")
    pairs=[(x["a"],x["b"]) for x in frozen["fights"]]
    snapshots,counts=load_and_build(
        as_of_exclusive=frozen["event_date"],query_bouts=pairs
    )
    queries=[s for s in snapshots if s.get("query_only")]
    if len(queries)!=13:
        raise RuntimeError("13 bout research query mismatch")
    record=[]
    for snap in queries:
        for side in ("a","b"):
            x=snap[side+"_pre"]
            record.append({
                "fighter":snap[side],
                "opponent":snap["b" if side=="a" else "a"],
                "prior_bouts":x["prior_ufc_bouts"],
                "prior_stats_bouts":x["prior_stats_bouts"],
                "ko_loss_rate":round(x["ko_loss_rate_shrunk"],5),
                "sub_loss_rate":round(x["sub_loss_rate_shrunk"],5),
                "kd_absorbed_per15":(
                    None if x["knockdowns_absorbed_per15"] is None else
                    round(x["knockdowns_absorbed_per15"],5)),
                "kd_nonko_survival_rate":round(
                    x["knockdown_nonko_survival_rate"],5),
                "sub_threat_nonloss_rate":round(
                    x["submission_threat_nonloss_rate"],5),
                "control_60s_nonsub_rate":round(
                    x["control_60s_nonsub_rate"],5),
                "td_defense_rate":round(x["takedown_defense_rate_shrunk"],5),
                "dangerous_opponent_bouts":x["prior_dangerous_opponent_bouts"],
                "dangerous_opponent_survival_rate":round(
                    x["dangerous_opponent_finish_survival"],5),
                "own_kd_per15":x["own_knockdowns_per15"],
                "own_sub_attempts_per15":x["own_sub_attempts_per15"],
                "direct_getups_recorded":False,
                "training_authorized":False,
            })
    report={
        "schema":"WSHL_X_UFC334_POST_EVENT_PREFIGHT_RESISTANCE_DATA_COVERAGE_V1",
        "status":"PROVISIONAL_SECONDARY_MIRROR_RESEARCH_NO_MODEL_CHANGE",
        "event":frozen["event"],"event_date":frozen["event_date"],
        "source_pinned_archive":str(
            Path("data/raw/ufcvegas124_2026-11-07/availability.json")
        ),
        "original_stage_a_not_modified":True,
        "post_event_replay_not_original_prediction_features":True,
        "fighter_count":len(record),
        "dated_historical_stats":counts,
        "fighter_prior_bouts_known":sum(x["prior_bouts"]>0 for x in record),
        "fighter_with_stats":sum(x["prior_stats_bouts"]>0 for x in record),
        "fighters_with_documented_dangerous_opponent_exposure":sum(
            x["dangerous_opponent_bouts"]>0 for x in record),
        "fighters_without_kd_observation":sum(x["kd_absorbed_per15"] is None for x in record),
        "one_to_one_original_fighter_identity_match":True,
        "not_model_trained_or_promoted":True,
        "no_fanduel_odds":True,
        "fighters":record,
    }
    print("RESISTANCE_COVERAGE_START")
    print(json.dumps(report,sort_keys=True,allow_nan=False))
    print("RESISTANCE_COVERAGE_END")


if __name__=="__main__":
    main()
