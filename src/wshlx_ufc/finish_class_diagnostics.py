"""Post-event two-card finish-class diagnostic. NOT a predictive model refit.

Use only locked pre-fight picks paired to evidence-verified results. The
frequency of winning-method argmax labels is not the same as probability
calibration. Do not promote/fix champion based on one or two event samples.
"""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

METHODS = ("KO", "SUB", "DEC")


def inspect_card(card: dict) -> dict:
    if not isinstance(card.get("fights"), list):
        raise ValueError("Missing fight-level locked grade")
    rows = []
    for f in card["fights"]:
        if "model_views" in f:  # November 7 grading schema
            observed = f["method"]
            reference = f["model_views"]["reference"]
            method = reference["own_selected_fighter_conditional_method"]
            predicted = reference["pick"]
            winner = f["winner"]
            exact = reference["own_fighter_and_method_correct"]
        else:  # November 14 grading schema
            observed = f["actual"]["method"]
            reference = f["models"]["reference"]
            method = reference["method"]
            predicted = reference["fighter"]
            winner = f["actual"]["winner"]
            exact = reference["exact_fighter_method_correct"]
        method = "KO" if method in ("KO/TKO", "KO_TKO") else method
        if observed == "DRAW":
            if winner is not None or exact is not None:
                raise ValueError("Draw cannot be scored as an exact fighter-method hit")
            continue
        if method not in METHODS or observed not in METHODS:
            raise ValueError("Unknown actual or predicted finish method")
        if exact is not (predicted == winner and method == observed):
            raise ValueError("Locked exact method grade inconsistent with selected fighter")
        rows.append({"predicted_winner": predicted, "actual_winner": winner,
                     "predicted_method": method, "actual_method": observed,
                     "winner_correct": predicted == winner,
                     "exact_winner_method": bool(exact)})
    if not rows:
        raise ValueError("No decisive fights to compare")
    predicted = Counter(r["predicted_method"] for r in rows)
    observed = Counter(r["actual_method"] for r in rows)
    n = len(rows)
    return {"event": card["event"], "event_date": card["event_date"],
            "decisive_fights": n,
            "predicted_leading_methods": {m:predicted[m] for m in METHODS},
            "actual_methods": {m:observed[m] for m in METHODS},
            "winner_correct": sum(r["winner_correct"] for r in rows),
            "exact_winner_method_correct": sum(r["exact_winner_method"] for r in rows),
            "predicted_KO_share": predicted["KO"]/n,
            "actual_KO_share": observed["KO"]/n,
            "predicted_DEC_share": predicted["DEC"]/n,
            "actual_DEC_share": observed["DEC"]/n,
            "leading_method_KO_excess": predicted["KO"]-observed["KO"],
            "leading_method_DEC_shortfall": observed["DEC"]-predicted["DEC"]}


def compare_cards(*cards: dict) -> dict:
    if len(cards)<2:
        raise ValueError("Multiple historical event dates are required to flag a repeated issue")
    items=[inspect_card(c) for c in cards]
    if len(set(x["event_date"] for x in items))!=len(items):
        raise ValueError("Cannot count an event twice")
    chronological=sorted(items,key=lambda x:x["event_date"])
    if chronological!=items:
        raise ValueError("Input cards must be in chronological order")
    n=sum(x["decisive_fights"] for x in items)
    summed=lambda field:sum(x[field] for x in items)
    return {
        "status":"POST_EVENT_RESEARCH_DIAGNOSTIC_NOT_NEW_PREDICTIONS",
        "model_version_changed":False,
        "source_events":items,
        "combined_decisive_fights":n,
        "combined_reference_winner_correct":summed("winner_correct"),
        "combined_reference_exact_fighter_method_correct":summed("exact_winner_method_correct"),
        "combined_predicted_method_counts":{m:sum(x["predicted_leading_methods"][m] for x in items) for m in METHODS},
        "combined_actual_method_counts":{m:sum(x["actual_methods"][m] for x in items) for m in METHODS},
        "repeat_KO_leading_method_excess":all(x["leading_method_KO_excess"]>0 for x in items),
        "repeat_decision_leading_method_shortfall":all(x["leading_method_DEC_shortfall"]>0 for x in items),
        "critical_interpretation":"Top-1 class frequency is not a model calibration test; validate per-method probabilities with a time-ordered held-out backtest before promotion.",
        "requires_verified_ufcstats_and_walk_forward_before_predictive_retraining":True,
    }


def main():
    root=Path(__file__).resolve().parents[2]
    older=json.loads((root/"data/results/ufcvegas124_2026-11-07_all_models_grading.json").read_text())
    latest=json.loads((root/"data/results/ufc334_2026-11-14_all_models_grading.json").read_text())
    print(json.dumps(compare_cards(older,latest), indent=2))


if __name__=="__main__":
    main()
