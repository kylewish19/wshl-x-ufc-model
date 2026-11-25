"""Print full event-fold quality/defense ablation summary; research, no model writes."""
from __future__ import annotations
import json
from wshlx_ufc.quality_aware_method_shadow import study


def main():
    result=study()
    concise={
        "status":result["status"],
        "coverage":result["quality_match_coverage"],
        "per_event":[{
            "event_date":x["event_date"],"train":x["train_n"],"test":x["test_n"],
            "methods":{name:{
                "hits":stat["correct"],
                "brier":round(stat["brier"],6),
                "logloss":round(stat["logloss"],6)}
                for name,stat in x["metrics"].items()}
            } for x in result["folds"]],
        "overall":{name:{
            "n":score["n"],"hits":score["correct"],
            "brier":round(score["brier"],7),
            "logloss":round(score["logloss"],7)}
            for name,score in result["overall"].items()},
        "incremental":result["incremental_quality_vs_intercept"],
        "quality_only":result["quality_only_vs_intercept"],
        "not_promoted":True,
    }
    print("WSHLX_QUALITY_REPORT_START")
    print(json.dumps(concise,sort_keys=True))
    print("WSHLX_QUALITY_REPORT_END")


if __name__=="__main__":
    main()
