"""Create a real, immutable-intent *prospective* three-view research shadow.

This module is not in the production model and cannot authorize any wager.
- Requires existing FINAL odds-blind Stage A freeze, exact raw SHA and identities.
- Requires trusted event-start manifest with a named main event and date.
- Requires actual UTC run BEFORE advertised first-fight start (CLI supplies
  the real clock; injected clock parameter exists only for pure unit tests).
- Derives winner-only and winner+GTD probability projections; leaves the
  Reference/Historical/Unified winner picks, original method/timing markets,
  Stage A/B, 10K simulations and FanDuel price gates completely untouched.
- The file-writing CLI uses exclusive creation, never replaces a prior lock.
- An after-the-fact replay cannot pass this pre-event gating function.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math

from .joint_coherence_shadow import JOINT_KEYS, SIDES, FINISH_KEYS, METHODS, project
from .opponent_quality_join import canonical

MODEL_NAMES = ("reference", "historical", "unified")
VARIANTS = ("raw_archived", "winner_aligned", "winner_and_timing_aligned")


def _time(value: str) -> datetime:
    try:
        d = datetime.fromisoformat(value.replace("Z","+00:00"))
    except (TypeError, ValueError) as e:
        raise ValueError("Expected ISO8601 datetime with UTC offset") from e
    if d.tzinfo is None or d.utcoffset() is None:
        raise ValueError("Datetime must include an explicit UTC offset")
    return d.astimezone(timezone.utc)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_view(raw: dict, locked: dict, model: str):
    if model == "reference":
        q = raw["joint_calibrated"]
        pa = raw["winner_reference_p_a"]
        timing = raw["timing_v033_direct"]
        pick = raw["winner_reference_pick"]
        if pick != locked["official_reference_pick"]:
            raise ValueError("Reference pre-fight winner changed after freezing")
        saved_prob = locked["winner_views"]["reference"]["probability"]
    else:
        src = ("historical_shadow" if model == "historical" else
               "oof_unified_shadow")
        shadow = raw[src]
        q = shadow["joint_method"]
        pa = shadow["winner_p_a"]
        timing = shadow["timing_direct"]
        pick = shadow["winner_pick"]
        if pick != locked["winner_views"][src]["pick"]:
            raise ValueError("Shadow winner pick differs from official locked view")
        saved_prob = locked["winner_views"][src]["probability"]
    if pick not in (raw["a"], raw["b"]):
        raise ValueError("Winner does not match original fighter identities")
    pa = float(pa)
    if not 0 < pa < 1 or not math.isfinite(pa):
        raise ValueError("Invalid original probability")
    target = pa if pick == raw["a"] else 1-pa
    if abs(target-float(saved_prob)) > 1e-8:
        raise ValueError("Locked winner probability differs from original raw")
    if not set(JOINT_KEYS).issubset(q):
        raise ValueError("Missing one of six method probabilities")
    joint={key:float(q[key]) for key in JOINT_KEYS}
    if len(q)!=6 or any(not math.isfinite(x) or x<=0 for x in joint.values()):
        raise ValueError("Invalid original six-method joint")
    if abs(sum(joint.values())-1)>1e-5:
        raise ValueError("Original joint probability not normalized")
    gtd=float(timing["GTD_NO"])
    if not 0<gtd<1 or not math.isfinite(gtd):
        raise ValueError("Invalid original direct GTD_NO timing probability")
    if abs(float(timing["GTD_YES"])+gtd-1)>1e-8:
        raise ValueError("Original GTD outcomes do not sum to one")
    return joint,pa,gtd,pick,{str(k):float(v) for k,v in timing.items()}


def create_lock(*,raw_bytes:bytes,frozen_bytes:bytes,
                schedule_bytes:bytes,as_of_utc:datetime) -> dict:
    """Pure function. The production CLI calls this with real UTC clock only.

    IMPORTANT: A clock injected in a UNIT TEST does not make a historical
    replay prospective. Only the CI/CLI real-clock path can produce a live
    research lock, and its artifact must persist before the first fight.
    """
    as_of = as_of_utc.astimezone(timezone.utc) if (
        isinstance(as_of_utc,datetime) and as_of_utc.tzinfo is not None
    ) else None
    if as_of is None:
        raise ValueError("Real UTC timestamp must be timezone aware")
    raw=json.loads(raw_bytes)
    frozen=json.loads(frozen_bytes)
    schedule=json.loads(schedule_bytes)
    deadline=_time(schedule["first_fight_not_before_utc"])
    original_lock_time=_time(frozen["frozen_at_utc"])
    if (schedule.get("schema") != "WSHL_X_UFC_EVENT_START_MANIFEST_V1"
        or schedule.get("card_roster_complete") is not False
        or not str(schedule.get("source_url","")).startswith("https://www.ufc.com/")
        or schedule["event_date"] != deadline.date().isoformat()):
        raise ValueError("Invalid independent official event-time manifest")
    if as_of >= deadline:
        raise ValueError("Event already started: cannot issue a prospective shadow lock")
    if not (original_lock_time < as_of < deadline):
        raise ValueError("Stage A must have been frozen before the live research lock")
    if (raw.get("odds_used") is not False or
        frozen.get("odds_used") is not False or
        frozen.get("stage_a_frozen") is not True or
        not (frozen["event_date"] == raw["event_date"] == schedule["event_date"])
        or frozen["raw_model_sha256"]!=_sha(raw_bytes)):
        raise ValueError("Odds-blind Stage A freeze or original raw SHA invalid")
    if frozen.get("raw_model_sha256") != frozen.get("original_stage_a_raw_sha256"):
        raise ValueError("Frozen original raw digest inconsistency")
    rows=raw["fights"]
    locks=frozen["fights"]
    if not rows or len(rows)!=len(locks):
        raise ValueError("Missing or incomplete raw vs final frozen card")
    by_no={int(x["fight_no"]):x for x in locks}
    if len(by_no)!=len(locks):
        raise ValueError("Duplicate original locked fight numbers")
    seen=set()
    identity=set()
    result=[]
    for fight in rows:
        n=int(fight["fight_no"])
        if n not in by_no:
            raise ValueError("Raw fight number missing from original final Stage A")
        original=by_no[n]
        a,b=fight["a"],fight["b"]
        if (a,b)!=(original["a"],original["b"]):
            raise ValueError("Raw fighter pair does not match original Stage A")
        if n in seen:
            raise ValueError("Duplicate raw fight")
        seen.add(n)
        pair=(canonical(a),canonical(b))
        if not all(pair) or pair[0]==pair[1] or pair[0] in identity or pair[1] in identity:
            raise ValueError("Repeated or ambiguous fighter on same event card")
        identity.update(pair)
        views={}
        for model in MODEL_NAMES:
            original_joint,pa,fgtd,pick,markets=_source_view(fight,original,model)
            projected_winner=project(original_joint,winner_p_a=pa)
            projected_joint=project(original_joint,winner_p_a=pa,finish_p=fgtd)
            distributions={
                "raw_archived":original_joint,
                "winner_aligned":projected_winner,
                "winner_and_timing_aligned":projected_joint,
            }
            side="A" if pick==a else "B"
            selections={
                name:{
                    "frozen_winner_pick":pick,
                    "selected_method_given_frozen_winner":max(
                        METHODS,key=lambda m:dist[f"{side}_{m}"]),
                    "selected_method_conditional_probability":(
                        max(dist[f"{side}_{m}"] for m in METHODS) /
                        sum(dist[k] for k in SIDES[side])),
                    "frozen_winner_changed":False,
                    "bet_authorized":False,
                } for name,dist in distributions.items()
            }
            views[model]={
                "original_frozen_fighter_pick":pick,
                "original_frozen_winner_p_a":pa,
                "original_direct_gtd_no":fgtd,
                "original_direct_timing_markets_untouched":markets,
                "distributions":distributions,
                "variant_selections":selections,
                "wager_gate":"UNAPPROVED_SHADOW_ONLY",
            }
        result.append({
            "fight_no":n,"a":a,"b":b,
            "scheduled_rounds":original["scheduled_rounds"],
            "original_stage_a_posture":original["stage_a_posture"],
            "models":views,
            "bet_authorized":False,
        })
    if len(seen)!=len(locks):
        raise ValueError("Raw vs original frozen fight set differs")
    main_names={canonical(x) for x in schedule["main_event_fighters"]}
    if len(main_names)!=2 or not any(
        {canonical(f["a"]),canonical(f["b"])} == main_names for f in result
    ):
        raise ValueError("Original frozen event missing UFC-verified main event")
    generated=as_of.isoformat(timespec="microseconds")
    return {
        "schema":"WSHL_X_THREE_VIEW_PROSPECTIVE_COHERENCE_SHADOW_LOCK_V1",
        "status":"ODDS_BLIND_PROSPECTIVE_RESEARCH_UNPROMOTED",
        "event_slug":schedule["event_slug"],
        "event":frozen["event"],
        "event_date":frozen["event_date"],
        "utc_event_earliest_start":deadline.isoformat(),
        "generated_at_utc":generated,
        "original_frozen_at_utc":original_lock_time.isoformat(),
        "source_raw_sha256":_sha(raw_bytes),
        "source_frozen_stage_a_sha256":_sha(frozen_bytes),
        "source_event_manifest_sha256":_sha(schedule_bytes),
        "official_event_page":schedule["source_url"],
        "source_original_fight_count":len(rows),
        "models_present":list(MODEL_NAMES),
        "variants":list(VARIANTS),
        "timing_scope":"Direct GTD_NO only for joint finish-vs-decision alignment; other pre-fight timing props NOT changed",
        "original_winner_method_timing_picks_untouched":True,
        "original_stage_a_and_stage_b_unchanged":True,
        "original_10000_simulations_unchanged":True,
        "fanduel_odds_used":False,
        "new_model_trained":False,
        "video_consensus_overlay_changed":False,
        "shadow_is_frozen_probability_reconciliation_not_new_fighter_model":True,
        "bet_authorized":False,
        "model_promoted":False,
        "historical_results_seen":False,
        "fights":result,
    }


def check_lock_against_source(payload:dict,raw_bytes:bytes,frozen_bytes:bytes,
                              schedule_bytes:bytes)->None:
    if (payload["source_raw_sha256"]!=_sha(raw_bytes) or
        payload["source_frozen_stage_a_sha256"]!=_sha(frozen_bytes) or
        payload["source_event_manifest_sha256"]!=_sha(schedule_bytes)):
        raise ValueError("Source SHA mismatch: frozen shadow cannot be verified")
    if (payload.get("bet_authorized") is not False or
        payload.get("model_promoted") is not False or
        payload.get("fanduel_odds_used") is not False):
        raise ValueError("Research shadow must not approve bets or claim promotion")
    stamped=_time(payload["generated_at_utc"])
    first=_time(payload["utc_event_earliest_start"])
    if not _time(payload["original_frozen_at_utc"]) < stamped < first:
        raise ValueError("Research timestamp is after event or before Stage A freeze")
    if len(payload["fights"])!=len(json.loads(frozen_bytes)["fights"]):
        raise ValueError("Research lock fight count mutated")
    # Recalculate EVERY probability and source selection deterministically
    # from the original SHA-verified frozen card. A later edit to the saved
    # shadow forecasts must be rejected even if the three source SHAs match.
    # This timestamp is used ONLY for replay verification; the live locking
    # CLI never accepts a user-provided timestamp.
    expected = create_lock(
        raw_bytes=raw_bytes, frozen_bytes=frozen_bytes,
        schedule_bytes=schedule_bytes,
        as_of_utc=stamped,
    )
    if payload != expected:
        raise ValueError(
            "Saved shadow probabilities or metadata differ from original"
            " independently reconstructed frozen source"
        )
