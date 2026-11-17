"""Summarize selected-fighter historical research. Does not write to Stage A/B."""
from __future__ import annotations
import json
from wshlx_ufc.predicted_side_method_shadow import evaluate


def main():
    study=evaluate()
    concise={
        key:study[key] for key in (
            "schema", "status", "all_bouts", "outcome_views",
            "draw_event_count", "evaluation_events", "summary",
            "per_event", "model_promoted"
        )
    }
    print("SELECTED_FIGHTER_METHOD_SUMMARY_START")
    print(json.dumps(concise,sort_keys=True))
    print("SELECTED_FIGHTER_METHOD_SUMMARY_END")


if __name__ == "__main__":
    main()
