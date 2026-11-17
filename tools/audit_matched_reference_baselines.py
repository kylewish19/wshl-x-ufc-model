"""Match unchanged WSHL_X original Reference selections with simple as-of baselines.

Strict date + normalized-pair identity; no fuzzy guess, no post-hoc tuning,
no original pick or betting record updates. Only existing grade-153 subset.
"""
from __future__ import annotations

from collections import defaultdict
import json
import random
import re
import unicodedata

from wshlx_ufc.historical_baselines import _winner_probabilities
from wshlx_ufc.historical_feature_matrix import load_matrix
from wshlx_ufc.longitudinal_audit import ROOT, _clean153, _load as read_json

AUDIT = "reports/model_health/2026-11-17_FULL_HISTORY_BASELINE_AUDIT.json"
OUT = ROOT / "reports/model_health/2026-11-17_MATCHED_REFERENCE_BASELINES.json"


def normalize_name(name: str) -> str:
    value = unicodedata.normalize("NFKD", str(name))
    ascii_name = value.encode("ascii", errors="ignore").decode("ascii").casefold()
    return re.sub("[^a-z0-9]", "", ascii_name)


def matchup_key(when: str, a: str, b: str):
    names = (normalize_name(a), normalize_name(b))
    if not names[0] or not names[1] or names[0] == names[1]:
        raise ValueError("Ambiguous fighter identity")
    return (when, *sorted(names))


def align_rows(features, labels, grade_rows):
    lab = {x["bout_id"]: x for x in labels}
    if len(lab) != len(labels):
        raise ValueError("Duplicate model label IDs")
    index = {}
    for f in features:
        key = matchup_key(f["event_date"], f["fighter_a"], f["fighter_b"])
        if key in index:
            raise ValueError("Potential historical name-identity collision")
        index[key] = f
    matched, missing = [], []
    for g in grade_rows:
        a, b = g["fight"].split(" vs ")
        key = matchup_key(g["event_date"], a, b)
        f = index.get(key)
        if f is None:
            missing.append({"event_date": g["event_date"], "fight": g["fight"], "reason": "NO_EXACT_NORMALIZED_PAIR"})
            continue
        label = lab[f["bout_id"]]
        if label["result_status"] != "DECISIVE":
            raise ValueError("Archived reference result matched to source draw")
        truth = normalize_name(g["actual_winner"])
        pick = normalize_name(g["locked_pick"])
        fa, fb = normalize_name(f["fighter_a"]), normalize_name(f["fighter_b"])
        if truth not in (fa, fb) or pick not in (fa, fb):
            raise ValueError("Names matched bout, but winner or pick did not")
        actual_a = int(truth == fa)
        chosen_a = int(pick == fa)
        if actual_a != int(label["label_a_win"]):
            raise ValueError("Grade and independent UFCStats-compatible outcome disagree")
        expected_method = {"KO": "KO_TKO", "SUB": "SUB", "DEC": "DEC"}[g["actual_method"]]
        if label["label_method"] != expected_method:
            raise ValueError("Method mismatch between archives")
        if bool(chosen_a == actual_a) != bool(g["winner_correct"]):
            raise ValueError("Grade's winner correctness was rewritten")
        if bool(g["joint_correct"]) != bool(g["winner_correct"] and g["method_correct"]):
            raise ValueError("Grade's exact correctness was rewritten")
        p = _winner_probabilities(f)
        matched.append({
            "date": f["event_date"], "fight": g["fight"],
            "bout_id": f["bout_id"], "actual_method": expected_method,
            "reference_winner_hit": int(g["winner_correct"]),
            "reference_method_hit": int(g["method_correct"]),
            "reference_exact_hit": int(g["joint_correct"]),
            "reference_fighter_plus_fixed_dec_exact_hit": int(g["winner_correct"] and expected_method == "DEC"),
            "ufc_elo_winner_hit": int((p["past_only_ufc_elo"] >= .5) == bool(actual_a)),
            "ufc_winrate_winner_hit": int((p["prior_ufc_win_rate"] >= .5) == bool(actual_a)),
            "ufc_elo_fighter_plus_fixed_dec_exact_hit": int(((p["past_only_ufc_elo"] >= .5) == bool(actual_a)) and expected_method == "DEC"),
            "ufc_winrate_fighter_plus_fixed_dec_exact_hit": int(((p["prior_ufc_win_rate"] >= .5) == bool(actual_a)) and expected_method == "DEC"),
        })
    return matched, missing


def summarize(rows):
    if not rows:
        return {"fights": 0}
    out = {"fights": len(rows), "events": len({r["date"] for r in rows})}
    fields = [x for x in rows[0] if x.endswith("_hit")]
    for k in fields:
        out[k] = {"hits": sum(x[k] for x in rows),
                  "accuracy": sum(x[k] for x in rows) / len(rows)}
    out["actual_method_counts"] = {m: sum(x["actual_method"] == m for x in rows)
                                   for m in ("KO_TKO", "SUB", "DEC")}
    return out


def paired_bootstrap_by_event(rows, baseline: str, *, seed: int = 19, samples: int = 1000):
    if not rows:
        return None
    byday = defaultdict(list)
    for x in rows:
        byday[x["date"]].append(x)
    days = sorted(byday)
    rng = random.Random(seed)
    diffs = []
    for _ in range(samples):
        drawn = [days[rng.randrange(len(days))] for _ in days]
        sample = [x for d in drawn for x in byday[d]]
        diffs.append(sum(x["reference_winner_hit"] - x[baseline] for x in sample) / len(sample))
    diffs.sort()
    return [diffs[int((len(diffs)-1)*.025)], diffs[int((len(diffs)-1)*.975)]]


def main():
    features, labels, manifest = load_matrix()
    original = _clean153()
    matched, missing = align_rows(features, labels, original)
    audited = read_json(AUDIT)
    provenance = audited["original_stage_a_artifact_identity_verification"]
    all_later = {x["date"] for x in provenance}
    timestamped = {x["date"] for x in provenance if x["has_pre_fight_timestamp_evidence"]}
    last89 = [x for x in matched if x["date"] in all_later]
    timed = [x for x in matched if x["date"] in timestamped]
    report = {
        "schema": "WSHLX_REFERENCE_VS_SIMPLE_MATCHED_BOUTS_V1",
        "source_ledger": "data/results/clean_ufc_153_2026-11-07.csv",
        "source_baseline": manifest["schema"],
        "source_stats_sha256": manifest["source_stats_sha256"],
        "identity_policy": "EXACT_DATE_AND_PUNCTUATION_NORMALIZED_UNORDERED_FIGHTER_PAIR_NO_FUZZY_MATCH",
        "reference_grade_total": len(original), "matched_count": len(matched),
        "missing_count": len(missing), "missing": missing,
        "all_matched_reconstructed_grade": summarize(matched),
        "later_with_separate_original_stage_a_files": summarize(last89),
        "later_with_pre_fight_timestamp_evidence": summarize(timed),
        "reference_minus_prior_ufc_winrate_winner_accuracy_95pct_event_bootstrap": paired_bootstrap_by_event(matched, "ufc_winrate_winner_hit"),
        "method_baseline": "FIXED_TRAINING_2021_2025_DEC_PLURALITY_NO_FIGHT_TUNING",
        "reference_probabilities_missing_in_153_grade_no_proper_score_comparison": True,
        "earliest_64_are_reconstructed_not_verified_timestamped": True,
        "retrospective_not_pristine": True,
        "no_model_or_bet_promotion": True,
    }
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    print("NO AUTOMATIC ALIAS FIXES, MODEL PROMOTION, ODDS OR FROZEN PICK CHANGES")

if __name__ == "__main__":
    main()
