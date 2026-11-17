"""Produce restricted diagnostic summaries; never change frozen model or wager."""
from __future__ import annotations
import json
from wshlx_ufc.resistance_method_shadow import evaluate

def main():
    result=evaluate()
    limited={
        k:result[k] for k in (
            "schema","status","historical_dated_stats","feature_training_rows",
            "event_evaluations","decisive_fights","draws","summary",
            "by_event","model_promoted",
        )
    }
    print("RESISTANCE_METHOD_BENCHMARK_START")
    print(json.dumps(limited,sort_keys=True,allow_nan=False))
    print("RESISTANCE_METHOD_BENCHMARK_END")

if __name__=="__main__":
    main()
