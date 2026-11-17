"""Research-only, time-safe UFC bout matrix with separated post-fight labels.

The archive is a pinned SECONDARY UFCStats-compatible source. These features are
frozen strictly before the event's calendar date; no same-day results enter.
This module has no access to production model promotion or betting selections.
"""
from __future__ import annotations

from datetime import date
import hashlib
from pathlib import Path
import csv
import json

from .prefight_finish_resistance import ARCHIVE, _load_records, load_and_build
from .prefight_opponent_quality import build_historical_opponent_quality

BEGIN = "2021-01-01"
TRAIN_END = "2025-12-31"
CUTOFF = "2026-11-14"

# Only documented prior-fight features. Missing rate measurements remain null;
# debut fighters are not assigned fictional performance statistics.
RESISTANCE = (
    "prior_ufc_bouts", "prior_stats_bouts", "stats_coverage",
    "ko_loss_rate_shrunk", "sub_loss_rate_shrunk",
    "own_knockdowns_per15", "own_sub_attempts_per15",
    "own_takedowns_landed_per15", "own_control_generated_sec_per15",
    "knockdowns_absorbed_per15", "knockdown_nonko_survival_rate",
    "submission_threat_nonloss_rate", "control_60s_nonsub_rate",
    "dangerous_opponent_finish_survival", "takedown_defense_rate_shrunk",
    "control_absorbed_sec_per15", "prior_knockdown_bouts",
    "prior_submission_threat_bouts", "prior_takedowns_faced",
    "prior_dangerous_opponent_bouts", "history_under_5_ufc_bouts",
    "prior_stats_missing_not_zero_filled",
)
QUALITY = (
    "ufc_prior_bouts", "ufc_prior_wins", "ufc_prior_losses", "ufc_prior_draws",
    "ufc_elo_pre", "ufc_avg_opponent_elo_at_meeting_shrunk",
    "ufc_avg_beaten_opponent_elo_at_meeting_shrunk", "ufc_strength_uncertain",
    "ufc_debutant",
)


def bout_key(when: str, event: str, a: str, b: str) -> tuple[str, str, str, str]:
    if not a or not b or a == b:
        raise ValueError("Invalid fighter identity")
    return (when, event, *sorted((a, b)))


def bout_id(key: tuple[str, str, str, str]) -> str:
    return hashlib.sha256(json.dumps(key, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def build_matrix(records: list[dict], snapshots: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return feature rows and labels in distinct tables keyed only by bout_id.

    `records` contains POST-fight results, used for labels and pre-event Elo
    updates only. Pre-event `snapshots` are computed by build_from_records,
    which freezes *every fight on the same calendar date* before updating.
    """
    originals = {}
    for record in records:
        when = record["date"].isoformat() if isinstance(record["date"], date) else str(record["date"])
        key = bout_key(when, record["event"], record["a"], record["b"])
        if key in originals:
            raise ValueError("Duplicate historical result bout")
        originals[key] = record
    # Readable pre-day opponent strength, including historical opponents' Elo
    # as of THEIR encounter (not their eventual career rating).
    elo_input = [
        {"date": k[0], "event": k[1], "a": r["a"], "b": r["b"],
         "outcome": "/".join(r["result"])}
        for k, r in originals.items()
    ]
    quality = {}
    for q in build_historical_opponent_quality(elo_input):
        key = bout_key(q["date"], q["event"], q["a"], q["b"])
        if key in quality:
            raise ValueError("Duplicate opponent quality snapshot")
        quality[key] = q
    if set(originals) != set(quality):
        raise ValueError("Opponent ratings and fight labels do not align")
    features, labels, seen = [], [], set()
    for snap in snapshots:
        if snap.get("query_only"):
            raise ValueError("Query-only bouts cannot be included in labeled dataset")
        when = snap["event_date"]
        key = bout_key(when, snap["event"], snap["a"], snap["b"])
        if key in seen or key not in originals:
            raise ValueError("Duplicate/missing timestamped pre-fight snapshot")
        seen.add(key)
        record = originals[key]
        q = quality[key]
        if (q["a"], q["b"]) != (snap["a"], snap["b"]):
            raise ValueError("Fighter order mismatch between independent snapshots")
        if not snap["current_fight_result_not_a_feature"]:
            raise ValueError("Future outcome feature found")
        row = {
            "bout_id": bout_id(key), "event_date": when, "event": snap["event"],
            "fighter_a": snap["a"], "fighter_b": snap["b"],
            "feature_as_of_exclusive": when,
            "source_class": "PINNED_SECONDARY_UFCSTATS_COMPATIBLE_RETROSPECTIVE",
            "data_partition": ("training_2021_2025" if BEGIN <= when <= TRAIN_END else
                               "retrospective_2026" if TRAIN_END < when < CUTOFF else "prior_context_only"),
        }
        for fields, aa, bb in (
            (RESISTANCE, snap["a_pre"], snap["b_pre"]),
            (QUALITY, q["a_pre"], q["b_pre"]),
        ):
            for field in fields:
                if field not in aa or field not in bb:
                    raise ValueError("Required feature missing: " + field)
                a, b = aa[field], bb[field]
                row["a_" + field] = a
                row["b_" + field] = b
                if isinstance(a, (int, float, bool)) and isinstance(b, (int, float, bool)):
                    row["diff_" + field] = float(a) - float(b)
                else:
                    row["diff_" + field] = None
        if row["a_prior_ufc_bouts"] != row["a_ufc_prior_bouts"] or row["b_prior_ufc_bouts"] != row["b_ufc_prior_bouts"]:
            raise ValueError("Independent past-only builders disagree on prior bouts")
        res = tuple(record["result"])
        method = record["method"]
        if res == ("D", "D"):
            label_a_win, label_method, state = None, None, "DRAW"
        elif res in (("W", "L"), ("L", "W")) and method in ("KO_TKO", "SUB", "DEC"):
            label_a_win, label_method, state = int(res[0] == "W"), method, "DECISIVE"
        else:
            raise ValueError("Unsupported/contradictory result label")
        labels.append({
            "bout_id": row["bout_id"], "event_date": when,
            "result_status": state, "label_a_win": label_a_win,
            "label_method": label_method, "label_elapsed_seconds": record["elapsed_seconds"],
        })
        features.append(row)
    if seen != set(originals):
        raise ValueError("Historical label row(s) lack pre-event features")
    if len({x["bout_id"] for x in features}) != len(features):
        raise ValueError("Fight ID collision")
    return features, labels


def load_matrix(*, as_of_exclusive: str = CUTOFF):
    snapshots, source = load_and_build(as_of_exclusive=as_of_exclusive)
    originals = _load_records(ARCHIVE, date.fromisoformat(as_of_exclusive))
    features, labels = build_matrix(originals, snapshots)
    manifest = {
        "schema": "WSHLX_ASOF_BOUT_FEATURES_V1",
        "as_of_exclusive": as_of_exclusive,
        "source_class": source["source_classification"],
        "source_stats_sha256": source["source_sha256"],
        "pre_event_snapshot_count": len(snapshots),
        "feature_rows": len(features), "label_rows": len(labels),
        "training_2021_2025": sum(x["data_partition"] == "training_2021_2025" for x in features),
        "retrospective_2026": sum(x["data_partition"] == "retrospective_2026" for x in features),
        "draws_in_modern_window": sum(x["result_status"] == "DRAW" and BEGIN <= x["event_date"] < as_of_exclusive for x in labels),
        "missing_numeric_features_are_null_not_zero": True,
        "method_labels_separate_from_feature_rows": True,
        "pre_event_only_same_date_results_excluded": True,
        "post_2025_not_pristine_holdout": True,
        "reach_and_age_deferred_until_asof_provenance_verified": True,
        "no_model_trained_or_promoted": True,
    }
    return features, labels, manifest


def export_matrix(destination: Path) -> dict:
    feature_rows, label_rows, report = load_matrix()
    destination.mkdir(parents=True, exist_ok=True)
    for name, rows in (("pre_event_features.csv", feature_rows), ("post_event_labels.csv", label_rows)):
        path = destination / name
        with path.open("w", encoding="utf-8", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=list(rows[0]), extrasaction="raise")
            writer.writeheader()
            writer.writerows(rows)
        report[name + "_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    (destination / "matrix_manifest.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report
