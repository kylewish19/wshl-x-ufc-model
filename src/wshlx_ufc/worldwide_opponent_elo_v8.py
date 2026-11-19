"""Time-safe global professional MMA Elo opponent-strength history (research).

Cross-promotion fight results from the EXACT external Fight Canon release
already pinned in worldwide MMA research (not independently event-stamped
in 2021-25). Every fight on the same date is first snapshot before ANY
same-date outcomes update Elo. All pro fighters (including non-UFC opponents)
contribute to Elo, not just eventual UFC roster members. No future records
are input to a fighter's historical prediction-day features.

Uses only verified FightCanon fighter IDs matched to original UFC event date
AND both named fighters, NOT fuzzy fighter names. Ambiguous UFC pairs stay
missing/neutral with explicit audit. Elo strength of previous regional
opponents and prior beaten opponents is approximated, not calibrated to
sportsbook odds or professional MMA ground truth.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import date
import math,sqlite3

from .historical_feature_matrix import load_matrix

SOURCE_CUTOFF="2026-11-08"
K_FACTOR=24.
INITIAL=1500.
BASELINE_PSEUDO_BOUTS=4.
FIELDS=(
    "global_pro_mma_elo_scaled",
    "log_prior_global_pro_mma_decisive",
    "mean_prior_opp_elo_scaled_shrunk",
    "mean_beaten_opp_elo_scaled_shrunk",
)

def state():
    return {"elo":INITIAL,"n":0,"opponents":0.,
            "wins":0,"beaten":0.}

def score(s):
    return (
      (s["elo"]-INITIAL)/400.,
      math.log1p(s["n"]),
      ((s["opponents"]+BASELINE_PSEUDO_BOUTS*INITIAL)/(s["n"]+BASELINE_PSEUDO_BOUTS)-INITIAL)/400.,
      ((s["beaten"]+BASELINE_PSEUDO_BOUTS*INITIAL)/(s["wins"]+BASELINE_PSEUDO_BOUTS)-INITIAL)/400.,
    )

def day_updates(day_fights,ratings):
    """Build all updates using ratings frozen at start of this date."""
    increments=defaultdict(float);count=defaultdict(int)
    opponents=defaultdict(float);beaten=defaultdict(float);wins=defaultdict(int)
    used=set()
    for r in day_fights:
        aid,bid=int(r["a"]),int(r["b"])
        if aid==bid or r["fight_id"] in used:
            raise ValueError("Source professional fight identity duplicate")
        used.add(r["fight_id"])
        ar,br=ratings[aid]["elo"],ratings[bid]["elo"]
        outcome=float(r["p_a_win"])
        expected=1/(1+10**((br-ar)/400))
        diff=K_FACTOR*(outcome-expected)
        increments[aid]+=diff;increments[bid]-=diff
        count[aid]+=1;count[bid]+=1
        opponents[aid]+=br;opponents[bid]+=ar
        if outcome==1.:wins[aid]+=1;beaten[aid]+=br
        if outcome==0.:wins[bid]+=1;beaten[bid]+=ar
    for athlete in count:
        s=ratings[athlete]
        s["elo"]+=increments[athlete]
        s["n"]+=count[athlete]
        s["opponents"]+=opponents[athlete]
        s["beaten"]+=beaten[athlete]
        s["wins"]+=wins[athlete]
        if not math.isfinite(s["elo"]):raise ValueError("Nonfinite world professional Elo")

def build(query,source_con,cutoff=SOURCE_CUTOFF):
    """query: dict[ISO event date] -> set[int verified fighter ids].

    Reconstruct from all decisive professional fights in original canonical
    pro source through CUTOFF. Same-day labels are never consumed for
    same-date target predictions.
    """
    requested=defaultdict(set)
    for day,ids in query.items():
        date.fromisoformat(day)
        if day>=cutoff:raise ValueError("Future source Elo query not available")
        requested[day].update(int(fid) for fid in ids if fid is not None)
    sql="""
      SELECT e.date,f.fight_id,a.fighter_id,b.fighter_id,
             a.result,b.result,f.bout_type
      FROM fights f
      JOIN events e ON e.event_id=f.event_id
      JOIN fight_participants a ON a.fight_id=f.fight_id AND a.corner=0
      JOIN fight_participants b ON b.fight_id=f.fight_id AND b.corner=1
      WHERE e.date IS NOT NULL AND e.date < ?
      ORDER BY e.date,f.fight_id
    """
    source=[]
    invalid_date=0;nonpro=0;excluded_result=0
    for record in source_con.execute(sql,(cutoff,)):
        rawday,fid,a,b,ra,rb,kind=record
        day=str(rawday)[:10]
        try:date.fromisoformat(day)
        except ValueError:
            invalid_date+=1;continue
        if kind and any(t in str(kind).casefold() for t in ("amateur","exhibition")):
            nonpro+=1;continue
        ra,rb=str(ra or "").upper().strip(),str(rb or "").upper().strip()
        if ra=="W" and rb=="L":result=1.
        elif ra=="L" and rb=="W":result=0.
        elif ra=="D" and rb=="D":result=.5
        else:
            excluded_result+=1;continue
        if a is None or b is None:raise ValueError("No canonical source fighter pair")
        source.append({"date":day,"fight_id":int(fid),"a":int(a),"b":int(b),
                       "p_a_win":result})
    source.sort(key=lambda x:(x["date"],x["fight_id"]))
    if len(source)<100_000:
        raise ValueError("Source contains far too few historical pro MMA fights")

    rating=defaultdict(state)
    snapshots={};i=0
    all_dates=sorted(set(requested)|{x["date"] for x in source})
    fight_idx=0
    for when in all_dates:
        # Query BEFORE even first same-day fight has been updated.
        if when in requested:
            for fid in requested[when]:
                snapshots[(when,fid)]=score(rating[fid])
        batch=[]
        while fight_idx<len(source) and source[fight_idx]["date"]==when:
            batch.append(source[fight_idx]);fight_idx+=1
        day_updates(batch,rating)
    if fight_idx!=len(source):raise ValueError("Some pro fight histories not processed")
    if len(snapshots)!=sum(len(v) for v in requested.values()):
        raise ValueError("Missing verified dated fighter-strength snapshots")
    return snapshots,{
        "source":"FightCanon pinned pro MMA source; UFC+regional+other professional leagues",
        "raw_pro_bouts_used":len(source),
        "invalid_event_dates":invalid_date,
        "excluded_amateur_exhibition":nonpro,
        "excluded_unknown_or_nondecisive_outcomes":excluded_result,
        "rating_prior":"1500, K=24 and 4 pseudobouts strength shrinkage",
        "date_queries":len(requested),
        "fighter_date_snapshots":len(snapshots),
        "global_profighter_ids":len(rating),
        "exclude_same_date_and_future_fights":True,
        "unverified_name_only_fighter_join_forbidden":True,
        "vintage_not_historically_source_versioned":True,
    }
