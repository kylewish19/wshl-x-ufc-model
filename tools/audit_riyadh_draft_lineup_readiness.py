"""Readiness-only draft lineup audit; no prediction or wager generation."""
from collections import defaultdict,Counter
from pathlib import Path
import json
from wshlx_ufc.postevent_history_extension_v1 import load_extended_records
from lock_ufcqatar_winner_v3_research import namekey
from lock_ufcqatar_worldwide_winner_v4_research import historic_verified_id_map

ROOT=Path(__file__).resolve().parents[1]
DRAFT=ROOT/"research/lineups/ufcriyadh_2026-12-05_draft_2026-11-24.json"
def main():
    draft=json.loads(DRAFT.read_text())
    assert not draft["lineup_verified_by_caller"]
    records,_=load_extended_records(as_of_exclusive=draft["event_date"])
    names=defaultdict(set);counts=Counter()
    for r in records:
        for s in ("a","b"):
            name=r[s];names[namekey(name)].add(name);counts[name]+=1
    ids=historic_verified_id_map()
    rows=[]
    for f in draft["fights"]:
        for s in ("a","b"):
            n=f[s];k=namekey(n);c=sorted(names[k])
            manual=(k=="brunosilva")
            status="manual_same_name_identity_check" if manual else "candidate_exact_normalized_UFC_name" if len(c)==1 else "unmatched_or_ambiguous_name"
            rows.append({"listed_name":n,"UFC_source_candidates":c,"status":status,
                 "prior_UFC_bouts_if_candidate_correct":counts[c[0]] if len(c)==1 and not manual else None,
                 "prior_dated_crosswalk_candidate":k in ids and not manual,
                 "identity_verified_for_Dec5":False})
    result={"schema":"WSHLX_DRAFT_LINEUP_IDENTITY_READINESS_NOT_FORECAST","event_date":draft["event_date"],
      "listed_fights":len(draft["fights"]),"fighter_rows":rows,
      "candidate_exact_normalized_UFC_names":sum(x["status"]=="candidate_exact_normalized_UFC_name" for x in rows),
      "prior_dated_crosswalk_candidates":sum(x["prior_dated_crosswalk_candidate"] for x in rows),
      "manual_review_required_all":True,"predictions_generated":0,"approved_bets":0}
    out=ROOT/"reports/model_health/2026-11-24_riyadh_readiness"
    out.mkdir(parents=True,exist_ok=True)
    (out/"identity_readiness.json").write_text(json.dumps(result,indent=2)+"\n")
    print("RIYADH_READINESS",json.dumps(result))
if __name__=="__main__":main()
