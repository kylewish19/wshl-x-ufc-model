"""Lock a coherent three-view UFC research sidecar BEFORE the first bout.

Run only after the standard full three-view Stage A has been formally frozen.
No manual clock override: actual UTC clock is used. Stage A/B unchanged.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from wshlx_ufc.prospective_coherence import create_lock, check_lock_against_source

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--event-slug",required=True,help="GitHub research event slug")
    args=parser.parse_args()
    slug=args.event_slug
    if slug.count("/") or slug.count("\\") or not slug.replace("-","").replace("_","").isalnum():
        raise ValueError("Invalid directory-safe event slug")
    parent=ROOT/"data/locks"/slug
    raw_path=parent/"stage_a_model_raw_three_view.json"
    frozen_path=parent/"stage_a_final_selection.json"
    manifest_path=ROOT/"research/events"/(slug+".json")
    output=ROOT/"data/shadow_locks"/slug/"coherent_joint_pre_event_shadow.json"
    if output.exists():
        raise FileExistsError("Research shadow lock already exists: cannot regenerate or overwrite")
    if not raw_path.is_file() or not frozen_path.is_file():
        raise FileNotFoundError(
            "No complete original frozen Stage A available for "+slug+
            ". Do NOT create or label prospective predictions before Stage A."
        )
    if not manifest_path.is_file():
        raise FileNotFoundError("No official source-checked event timing manifest")
    raw_bytes=raw_path.read_bytes()
    frozen_bytes=frozen_path.read_bytes()
    event_bytes=manifest_path.read_bytes()
    manifest=json.loads(event_bytes)
    if manifest["event_slug"]!=slug:
        raise ValueError("Schedule manifest slug differs from original lock directory")
    # Use actual runtime clock, never caller supplied, to prevent a completed
    # event replay from being falsely represented as a prospective prediction.
    now=datetime.now(timezone.utc)
    payload=create_lock(
        raw_bytes=raw_bytes,frozen_bytes=frozen_bytes,
        schedule_bytes=event_bytes,as_of_utc=now,
    )
    check_lock_against_source(payload,raw_bytes,frozen_bytes,event_bytes)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("x",encoding="utf-8") as f:
        json.dump(payload,f,sort_keys=True,indent=2,ensure_ascii=False)
        f.write("\n")
    print("PROSPECTIVE_COHERENCE_LOCK_CREATED",str(output.relative_to(ROOT)))
    print("EVENT",payload["event"],"FIGHTS",len(payload["fights"]))
    print("REAL_GENERATION_UTC",payload["generated_at_utc"])
    print("EARLIEST_BOUT_UTC",payload["utc_event_earliest_start"])
    print("ORIGINAL_FROZEN_SOURCE_SHA",payload["source_raw_sha256"])
    print("NO BETS APPROVED; NO CHAMPION MODEL PROMOTED; ORIGINAL STAGE A/B UNCHANGED")


if __name__=="__main__":
    main()
