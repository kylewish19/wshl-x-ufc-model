"""WSHL_X forward-only exact fighter+method and FanDuel decision audit.

Independent of legacy Stage A/B and RESEARCH ONLY until prospective promotion.
The model must make the correct fighter AND KO/SUB/DEC forecast to score exact.
An observed 100% 2-5-group record is tracked but NEVER promised.

- Six-class simplex is strictly checked; no normalization that conceals bugs.
- Same fighter-side tie rule as the corrected direct-six v7 research.
- Research eligibility is conditioned on dated, actually-graded PREVIOUS
  events from the SAME registered model and same exact-probability bucket.
- Conservative Wilson lower bound is used for price edge, not a raw model P.
- No outcome, late price, unknown source, wrong book, or unvalidated sample
  can be turned into an official bet.
- This does NOT edit frozen Nov21 models or the existing Stage B grader.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime,timezone
from math import isfinite,log,sqrt
from typing import Mapping,Sequence

SIX=("A_KO","A_SUB","A_DEC","B_KO","B_SUB","B_DEC")
METHODS=("KO","SUB","DEC")
BUCKETS=((0.0,0.25),(0.25,0.35),(0.35,0.45),(0.45,0.60),(0.60,1.0000001))

@dataclass(frozen=True)
class SelectionGuard:
    # Research thresholds predeclared to be measured, NOT calibrated claims.
    min_prior_prospective_fights: int=300
    min_bucket_settlements: int=50
    min_wilson_lower_bound: float=0.55
    max_exact_picks_per_card: int=5
    min_edge_vs_fanduel: float=0.05
    min_ev_units_per_unit_staked: float=0.05

def _prob(v):
    x=float(v)
    if not isfinite(x) or x<0.0 or x>1.0:
        raise ValueError("Probability outside 0..1 or non-finite")
    return x

def six_probabilities(cells: Mapping[str,float])->tuple[float,...]:
    if set(cells)!=set(SIX):
        raise ValueError("Six fighter/method cells must exist exactly once")
    p=tuple(_prob(cells[k]) for k in SIX)
    if abs(sum(p)-1.0)>1e-8:
        raise ValueError("Six outcome probabilities do not sum to 1")
    return p

def pick_six(p:Sequence[float])->int:
    if len(p)!=6 or abs(sum(_prob(x) for x in p)-1)>1e-8:
        raise ValueError("Expected coherent six-cell vector")
    # A 50/50 numerical tie selects A, as in legacy score_six.
    side=0 if sum(p[:3])>=0.5-1e-12 else 1
    return 3*side+max(range(3),key=lambda i:p[3*side+i])

def bucket(p:float)->str:
    value=_prob(p)
    for low,high in BUCKETS:
        if low<=value<high:
            return f"[{low:.2f},{min(high,1.0):.2f})"
    raise ValueError("Probability bucket invalid")

def wilson_lower(successes:int,total:int,z:float=1.959963984540054)->float:
    if total<0 or successes<0 or successes>total:
        raise ValueError("Impossible pre-fight calibration record")
    if total==0:return 0.0
    p=successes/total
    denom=1+z*z/total
    low=(p+z*z/(2*total)-z*sqrt((p*(1-p)+z*z/(4*total))/total))/denom
    return max(0.0,low)

def grade_one(cells:Mapping[str,float],actual_state:str)->dict:
    p=six_probabilities(cells)
    if actual_state not in SIX:raise ValueError("Only verified decisive six outcomes can be graded")
    idx=SIX.index(actual_state)
    selection=pick_six(p)
    observed=1.0 if idx<3 else 0.0
    return {
        "prediction":SIX[selection],
        "actual":actual_state,
        "winner_hit":int((selection<3)==(idx<3)),
        "method_class_hit":int(selection%3==idx%3),
        "exact_hit":int(selection==idx),
        "p_selected_exact":float(p[selection]),
        "p_observed_exact":float(p[idx]),
        "winner_brier":(sum(p[:3])-observed)**2,
        "six_logloss":-log(max(1e-12,p[idx])),
        "six_brier":sum((x-(1.0 if i==idx else 0.0))**2 for i,x in enumerate(p)),
    }

def prospective_calibration_history(
    prior_settled:Sequence[Mapping],
    *,
    model_id:str,
    before_event_date:str,
)->dict:
    """Only PREVIOUS, actually prospectively locked + verified results count.

    Expected record fields:
      model_id, event_date ISO, event_id, bout_id, locked_before_event,
      independently_verified, selected_exact_probability, exact_hit.
    Any future-date row is rejected, never silently counted.
    """
    hist={}
    count=0
    seen=set()
    events=set()
    for row in prior_settled:
        if row.get("model_id")!=model_id:continue
        d=str(row["event_date"])
        if d>=before_event_date:raise ValueError("Future or target event in calibration history")
        if not row.get("locked_before_event") or not row.get("independently_verified"):
            raise ValueError("Unverified or post-fight label in purported prospective calibration")
        key=(d,str(row["event_id"]),str(row["bout_id"]))
        if key in seen:raise ValueError("Repeated prior prospective fight")
        seen.add(key);events.add(key[:2])
        hit=row.get("exact_hit")
        if type(hit) is not int or hit not in (0,1):
            raise ValueError("Only genuine binary exact method grade accepted")
        k=bucket(row["selected_exact_probability"])
        wins,n=hist.get(k,(0,0))
        hist[k]=(wins+hit,n+1)
        count+=1
    return {"model_id":model_id,"prospective_fights":count,
            "independent_events":len(events),
            "by_probability_bucket":{k:{"hits":w,"n":n,"wilson_lower":wilson_lower(w,n)}
                                     for k,(w,n) in sorted(hist.items())}}

def research_selection(
    bouts:Sequence[Mapping], *,
    model_id:str,
    history:Mapping,
    event_date:str,
    guard:SelectionGuard=SelectionGuard(),
)->dict:
    """Zero-to-five (never forcibly 2-to-5) independently eligible exact leans.

    All candidate inputs must be frozen for THIS future event; caller must
    verify cryptographic source hashes. The last mile betting gate is NOT here.
    """
    if history.get("model_id")!=model_id:raise ValueError("Calibration model identity differs")
    count=int(history.get("prospective_fights",0))
    seen=set();review=[]
    for row in bouts:
        if row.get("event_date")!=event_date:raise ValueError("Mixed-date event review")
        key=str(row["bout_id"])
        if not key or key in seen:raise ValueError("Blank or repeated fight identity")
        seen.add(key)
        if row.get("model_id")!=model_id:raise ValueError("Mixed-model probabilities")
        p=six_probabilities(row["six_joint"])
        idx=pick_six(p)
        prob=p[idx];bk=bucket(prob)
        sample=history.get("by_probability_bucket",{}).get(bk,{"hits":0,"n":0,"wilson_lower":0.0})
        n=int(sample["n"])
        lower=wilson_lower(int(sample["hits"]),n)
        reasons=[]
        if row.get("not_an_approved_wager") is not True:reasons.append("not_originally_research_only")
        if row.get("source_identity_verified_both") is not True:
            reasons.append("unverified_cross_promotion_fighter_identity")
        if row.get("original_provisional"):reasons.append("provisional_bout")
        if count<guard.min_prior_prospective_fights:
            reasons.append("insufficient_prior_prospective_model_grades")
        if n<guard.min_bucket_settlements:
            reasons.append("insufficient_prior_same_probability_bucket")
        if lower<guard.min_wilson_lower_bound:
            reasons.append("prior_bin_reliability_lower_bound_below_gate")
        review.append({
            "bout_id":key,"model_id":model_id,"selected_outcome":SIX[idx],
            "raw_model_p_exact_UNCALIBRATED":prob,
            "source_qa_verified":row.get("source_identity_verified_both") is True,
            "bucket":bk,"previous_bin_fights":n,
            "prior_exact_reliability_wilson_lower":lower,
            "independent_eligibility":not reasons,
            "reasons":reasons,
        })
    eligible=sorted((r for r in review if r["independent_eligibility"]),
                    key=lambda x:(-x["prior_exact_reliability_wilson_lower"],
                                  -x["raw_model_p_exact_UNCALIBRATED"],x["bout_id"]))
    selected=eligible[:guard.max_exact_picks_per_card]
    return {
        "status":"RESEARCH_SELECTION_ONLY_NEVER_OFFICIAL_STAGE_B",
        "model_id":model_id,"event_date":event_date,
        "prospective_history_fights":count,
        "num_candidates":len(review),"num_selected":len(selected),
        "selection_not_forced":True,
        "eligible_outcome_list":[x["selected_outcome"] for x in selected],
        "selected":selected,"all_reviews":review,
        "will_not_promise_100_percent_exact":True,
    }

def american_decimal(odds:int)->float:
    if isinstance(odds,bool) or type(odds) is not int or (-100<odds<100):
        raise ValueError("Invalid American price")
    return 1.0+(odds/100.0 if odds>0 else 100.0/abs(odds))

def fanduel_price_audit(
    *,
    selected:Mapping,
    quote:Mapping,
    before_event_utc:str,
    guard:SelectionGuard=SelectionGuard(),
)->dict:
    """Separate price audit only; NEVER promotes unverified research wagers.

    A valid quoted FanDuel market must MATCH exact selected fighter and
    KO/SUB/DEC, have a pre-first-fight quote timestamp and a real source SHA.
    Negative outcome on any requirement => PASS, without EV calculations.
    """
    reasons=[]
    if selected.get("independent_eligibility") is not True:
        reasons.append("research_exact_reliability_gate_not_cleared")
    if quote.get("sportsbook")!="FanDuel":reasons.append("not_FanDuel")
    if quote.get("outcome")!=selected.get("selected_outcome"):
        reasons.append("different_fighter_or_victory_method_market")
    if quote.get("bout_id")!=selected.get("bout_id"):
        reasons.append("wrong_fight_quote")
    source=str(quote.get("source_sha256",""))
    if len(source)!=64 or any(x not in "0123456789abcdef" for x in source.lower()):
        reasons.append("unverified_FanDuel_quote_source_SHA")
    try:
        quoted=datetime.fromisoformat(str(quote["quoted_at_utc"]).replace("Z","+00:00"))
        first=datetime.fromisoformat(before_event_utc.replace("Z","+00:00"))
        if quoted.tzinfo is None or first.tzinfo is None or quoted>=first:
            reasons.append("missing_timezone_or_late_price")
    except (KeyError,ValueError,TypeError):
        reasons.append("unparseable_price_time")
    odds=quote.get("american_odds")
    try:decimal=american_decimal(odds)
    except (ValueError,TypeError):
        decimal=None;reasons.append("invalid_FanDuel_american_odds")
    lower=float(selected.get("prior_exact_reliability_wilson_lower",0.0))
    if not isfinite(lower) or lower<0 or lower>1:
        reasons.append("invalid_prospective_calibration_lower_bound")
        lower=0.
    if reasons or decimal is None:
        return {"status":"PASS_NO_VERIFIED_BET_PRICE","reasons":reasons,
                "official_bet_approved":False,"research_only":True}
    implied=1/decimal
    conservative_ev=lower*(decimal-1)-(1-lower)
    edge=lower-implied
    if edge<guard.min_edge_vs_fanduel:reasons.append("conservative_probability_edge_below_gate")
    if conservative_ev<guard.min_ev_units_per_unit_staked:
        reasons.append("conservative_expected_return_below_gate")
    # The research-only shadow is never allowed to produce a live bet.
    return {
        "status":"RESEARCH_PRICE_DIAGNOSTIC_ONLY" if not reasons else "PASS_NO_VERIFIED_BET_PRICE",
        "reasons":reasons,"official_bet_approved":False,"research_only":True,
        "american_odds":odds,"implied_probability":implied,
        "verified_historical_lower_bound_used":lower,
        "conservative_edge":edge,"conservative_EV_per_1u":conservative_ev,
    }

def grade_selected_card(selected:Sequence[Mapping],settled:Mapping[str,str])->dict:
    """Prospective selection strategy grade: 'all picks right' is explicit.

    NO inferred settlements and NO unresolved fight treated as a win.
    This does not grade fighters not in the previously frozen selected list.
    """
    ids=[str(s["bout_id"]) for s in selected]
    if len(ids)!=len(set(ids)):raise ValueError("Repeated research bet")
    statuses={}
    for s in selected:
        bout=str(s["bout_id"])
        actual=settled.get(bout)
        if actual is None:
            statuses[bout]="PENDING"
        elif actual=="VOID":
            statuses[bout]="VOID"
        elif actual in SIX:
            statuses[bout]="W" if s["selected_outcome"]==actual else "L"
        else:raise ValueError("Unverified non-six market settlement")
    wins=sum(v=="W" for v in statuses.values())
    losses=sum(v=="L" for v in statuses.values())
    void=sum(v=="VOID" for v in statuses.values())
    pending=sum(v=="PENDING" for v in statuses.values())
    all_resolved=pending==0
    valid=wins+losses
    return {"picks_prelocked":len(ids),"wins":wins,"losses":losses,
            "void":void,"pending":pending,
            "resolved_decisive_picks":valid,
            "exact_selection_hit_rate":wins/valid if valid else None,
            "perfect_group":bool(valid>=2 and losses==0 and all_resolved and void==0),
            "perfect_group_eligible":bool(len(ids)>=2 and all_resolved and void==0),
            "never_counts_pending_as_win":True,"settlements":statuses}
