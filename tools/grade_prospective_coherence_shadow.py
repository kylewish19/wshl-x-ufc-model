"""Post-event grade of a REAL previously saved three-view shadow lock.

Requires verified results for the original bout identities. No new
predictions are generated here. Zero FanDuel odds and no original grades
or official selections are modified. Writes to NEW research ledger only.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from wshlx_ufc.prospective_coherence_grade import grade_prospective_shadow

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--event-slug",required=True)
    p.add_argument("--verified-results",required=True,type=Path)
    x=p.parse_args()
    slug=x.event_slug
    if "/" in slug or "\\" in slug or not slug.replace("-","").replace("_","").isalnum():
        raise ValueError("Invalid research event slug")
    raw=ROOT/"data/locks"/slug/"stage_a_model_raw_three_view.json"
    frozen=ROOT/"data/locks"/slug/"stage_a_final_selection.json"
    source=ROOT/"research/events"/(slug+".json")
    locked=ROOT/"data/shadow_locks"/slug/"coherent_joint_pre_event_shadow.json"
    out=ROOT/"data/shadow_grades"/slug/"coherent_joint_post_event_grade.json"
    if out.exists():
        raise FileExistsError("Never overwrite a published research grading ledger")
    for f in (raw,frozen,source,locked,x.verified_results):
        if not f.is_file():
            raise FileNotFoundError(f"Missing required Stage A/shadow/results source: {f}")
    score=grade_prospective_shadow(
        lock_bytes=locked.read_bytes(),
        raw_bytes=raw.read_bytes(),frozen_bytes=frozen.read_bytes(),
        schedule_bytes=source.read_bytes(),
        results_bytes=x.verified_results.read_bytes(),
        as_of_utc=datetime.now(timezone.utc),
    )
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("x",encoding="utf-8") as f:
        json.dump(score,f,indent=2,sort_keys=True,ensure_ascii=False)
        f.write("\n")
    print("SHADOW_GRADE_WRITTEN",out.relative_to(ROOT))
    for model,m in score["summary"].items():
        print(model,{
            v:{"exact":m[v]["exact_fighter_method_correct"],
               "Brier":round(m[v]["six_way_brier"],5),
               "logloss":round(m[v]["six_way_logloss"],5)}
            for v in ("raw_archived","winner_aligned","winner_and_timing_aligned")
        })
    print("Original Stage A/B unchanged; no new official picks or bets")

if __name__=="__main__":
    main()
