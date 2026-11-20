"""Generate SHA-checked pre-Nov21 exact-selection READINESS report.

Not a grade, not a recommended bet, never rewrites a frozen Stage A or
independent research model. A future independently verified prospective
calibration ledger may be passed ONLY if earlier event dates and independently
verified prospectively locked results exist. Otherwise everything is PASS.

Usage:
  PYTHONPATH=src python tools/audit_ufcqatar_forward_selection_readiness.py
      --output reports/model_health/2026-11-20_qatar_selection_readiness.json

Optional external source:
  --prior-ledger path/to/independently_verified_prior_settled_bouts.json
The prior-ledger input is intentionally absent for Nov21 until the user
actually collects enough genuinely future, frozen-and-graded bouts.
"""
from __future__ import annotations
from argparse import ArgumentParser
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json

from wshlx_ufc.forward_validation_v1 import (
    SelectionGuard,prospective_calibration_history,research_selection
)

ROOT=Path(__file__).resolve().parents[1]
SLUG="ufcqatar_2026-11-21"
ORIGINAL=ROOT/"data/locks"/SLUG/"stage_a_final_selection.json"
SHADOW=ROOT/"data/shadow_locks"/SLUG/"worldwide_direct_six_v7_prospective_shadow.json"
PRIMARY="wshlx_direct_six_v7_paired230_winner_marginal"

def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()

def build(original:dict,shadow:dict,original_hash:str,shadow_hash:str,
          prior:list[dict],now:str)->dict:
    if not original.get("stage_a_frozen") or original.get("odds_used") is not False:
        raise ValueError("Must use immutable, genuine odds-blind original Stage A")
    if original.get("event_date")!="2026-11-21" or shadow.get("event_date")!=original["event_date"]:
        raise ValueError("Wrong fight event")
    if shadow.get("primary_architecture_locked_before_results")!="direct_paired230":
        raise ValueError("Cannot switch winner-method challenger after locking")
    if shadow.get("primary_selection_policy_locked_before_results")!="winner_marginal_method":
        raise ValueError("Cannot choose direct-six policy after seeing outcomes")
    if shadow.get("original_frozen_sha256",{}).get(ORIGINAL.name)!=original_hash:
        raise ValueError("V7 future research sidecar not linked to frozen original SHA")
    if shadow.get("betting_picks_approved")!=0 or shadow.get("FanDuel_odds_used") is not False:
        raise ValueError("Selected research cannot quietly authorize bets")
    if not shadow.get("all_prior_official_research_predictions_UNCHANGED"):
        raise ValueError("Earlier original locks were not verified")
    if shadow.get("fights_predicted")!=len(shadow.get("research_fights",[]))!=12:
        raise ValueError("Original expected 12-fight research panel must remain complete")
    if len(original.get("fights",[]))!=12:raise ValueError("12 original ordered bouts required")
    lock_time=datetime.fromisoformat(shadow["created_and_locked_utc"].replace("Z","+00:00"))
    first=datetime.fromisoformat(shadow["earliest_fight_utc"].replace("Z","+00:00"))
    check=datetime.fromisoformat(now.replace("Z","+00:00"))
    if (lock_time.tzinfo is None or check.tzinfo is None or
        lock_time>=first or check>=first):
        raise ValueError("Cannot create first claimed pre-event readiness after opening fight")
    normalized=[]
    for i,(f,og) in enumerate(zip(shadow["research_fights"],original["fights"]),1):
        if (f.get("fight_no")!=og.get("fight_no")!=i or
            f.get("a")!=og.get("a") or f.get("b")!=og.get("b")):
            raise ValueError(f"Changed fighter/date/number identity at row {i}")
        if f.get("original_Stage_A_posture_unchanged")!=og.get("stage_a_posture"):
            raise ValueError("Original Stage A PASS/winner posture has changed")
        normalized.append({
            "bout_id":f"{SLUG}_{i:02d}",
            "model_id":PRIMARY,
            "event_date":original["event_date"],
            "six_joint":f["six_joint"],
            "source_identity_verified_both":f.get("independent_external_source_ids_both_verified") is True,
            "not_an_approved_wager":f.get("not_an_approved_wager") is True,
            "original_provisional":f.get("original_provisional_12th") is True,
        })
    reg=prospective_calibration_history(prior,
             model_id=PRIMARY,before_event_date=original["event_date"])
    selection=research_selection(normalized,model_id=PRIMARY,
               history=reg,event_date=original["event_date"])
    return {
        "schema":"WSHLX_QATAR_FORWARD_RESEARCH_ONLY_SELECTION_READINESS_V1",
        "created_utc":now,
        "original_stage_a_sha256":original_hash,
        "direct_six_v7_research_lock_sha256":shadow_hash,
        "source_lock_created_utc":shadow["created_and_locked_utc"],
        "original_stage_a_and_all_research_locks_UNMODIFIED":True,
        "no_results_seen":True,
        "FanDuel_quotes_verified":False,
        "new_official_betting_picks":0,
        "paper_model_is_NOT_promoted":True,
        "research_calibration":reg,
        "eligibility_rules":{
            "min_prior_genuinely_prospective_exact_fights":SelectionGuard().min_prior_prospective_fights,
            "min_verified_same_exact_probability_bucket":SelectionGuard().min_bucket_settlements,
            "min_95pct_Wilson_lower_bound":SelectionGuard().min_wilson_lower_bound,
            "maximum_not_forced_exact_predictions":SelectionGuard().max_exact_picks_per_card,
            "independent_fighter_identity_required":True,
            "late_provisional_bouts_pass":True,
            "pricing_only_from_verified_pre_event_FanDuel_not_present":True,
        },
        "reviewed_bouts":len(normalized),
        "candidate_selection":selection,
        "note":"Raw v7 six-state probabilities are uncalibrated. No historical "
               "period 2024-2026 is relabeled as new independently prospective "
               "observations; no 2-5 bets forced without verified edge.",
    }

def main():
    ap=ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--prior-ledger",type=Path,default=None)
    args=ap.parse_args()
    if args.output.exists():raise FileExistsError("Never overwrite the original pre-event readiness assessment")
    prior=[]
    if args.prior_ledger is not None:
        ledger=json.loads(args.prior_ledger.read_text())
        if ledger.get("schema")!="WSHLX_VERIFIED_PREVIOUS_EVENT_MODEL_GRADES_V1":
            raise ValueError("Prior ledger must declare required grading provenance schema")
        if ledger.get("results_verified") is not True or not ledger.get("evidence"):
            raise ValueError("Prior ledger requires independently verifiable result sources")
        prior=ledger["prior_fights"]
    result=build(
        json.loads(ORIGINAL.read_text()),json.loads(SHADOW.read_text()),
        sha(ORIGINAL),sha(SHADOW),prior,datetime.now(timezone.utc).isoformat())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "status":result["schema"],"eligible_exact_research_picks":result["candidate_selection"]["num_selected"],
        "prior_real_prospective_fights":result["research_calibration"]["prospective_fights"],
        "needs_FanDuel_quotes":True,"official_approved_bets":0,
        "data_unverified_count":sum(not x["source_qa_verified"] for x in result["candidate_selection"]["all_reviews"]),
    },sort_keys=True))
if __name__=="__main__":main()
