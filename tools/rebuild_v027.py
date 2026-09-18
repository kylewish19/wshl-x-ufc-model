from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, log_loss

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from wshlx_ufc.grading import multiclass_brier
from wshlx_ufc.method_residual_v027 import V027MethodResidualChallenger, V027_FEATURES
from wshlx_ufc.models import ConditionalMethodModel, WinnerModel
from wshlx_ufc.timing import DiscreteTimeHazardModel

UPSTREAM_REPO = "Greco1899/scrape_ufc_stats"
UPSTREAM_COMMIT = "cb4ecb64dd62324a7a51a378f6b5bbb0fc99bc65"
TRAINING_CUTOFF = pd.Timestamp("2026-09-13", tz="UTC")
CLEAN_LEDGER = ROOT / "data/results/clean_ufc_64_2026-09-05.csv"

RAW_FILES = {
    "events": "ufc_event_details.csv",
    "results": "ufc_fight_results.csv",
    "stats": "ufc_fight_stats.csv",
    "tott": "ufc_fighter_tott.csv",
}

KNOWN_UPSTREAM_BLOB_SHAS = {
    "ufc_event_details.csv": "27f416337b93d523357a29e57a2660126e27eb44",
    "ufc_fight_results.csv": "395f46ba4a4811f0a6b15ed0d4003df51b164704",
    "ufc_fight_stats.csv": "6763ee38bea2edc63ae341d84adbbeb3a2a0eb2b",
    "ufc_fighter_tott.csv": "a4e17fa437c361eb74eb94c98dcb17470f09bb28",
}

SIDE_RATE_FIELDS = [
    "prior_bouts",
    "win_rate",
    "finish_win_rate",
    "ko_win_rate",
    "sub_win_rate",
    "ko_loss_rate",
    "sub_loss_rate",
    "kd_for_per15",
    "kd_against_per15",
    "sig_landed_per_min",
    "sig_absorbed_per_min",
    "sig_accuracy",
    "sig_defense",
    "ground_for_per15",
    "ground_against_per15",
    "td_landed_per15",
    "td_attempts_per15",
    "td_accuracy",
    "td_defense",
    "sub_att_per15",
    "sub_att_against_per15",
    "ctrl_for_per15",
    "ctrl_against_per15",
    "r3_retention",
    "recent5_win_rate",
    "recent5_finish_rate",
    "recent5_sig_diff_per_min",
    "recent5_kd_for_per15",
    "recent5_td_landed_per15",
    "recent5_sub_att_per15",
    "days_since_last",
    "age_years",
    "height_inches",
    "reach_inches",
    "southpaw",
]

WINNER_FEATURES = (
    [f"a_{x}" for x in SIDE_RATE_FIELDS]
    + [f"b_{x}" for x in SIDE_RATE_FIELDS]
    + [f"diff_{x}" for x in SIDE_RATE_FIELDS if x not in {"days_since_last", "southpaw"}]
    + [
        "scheduled_five_round",
        "is_heavyweight",
        "is_womens",
        "same_stance",
    ]
)

METHOD_BASE_FEATURES = (
    [f"winner_{x}" for x in SIDE_RATE_FIELDS]
    + [f"opponent_{x}" for x in SIDE_RATE_FIELDS]
    + [f"diff_{x}" for x in SIDE_RATE_FIELDS if x not in {"days_since_last", "southpaw"}]
    + [
        "scheduled_five_round",
        "is_heavyweight",
        "is_womens",
        "same_stance",
    ]
)

TIMING_FEATURES = WINNER_FEATURES


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def download_sources(raw_dir: Path) -> dict[str, dict[str, str | int]]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, dict[str, str | int]] = {}
    for logical, filename in RAW_FILES.items():
        url = (
            "https://raw.githubusercontent.com/"
            f"{UPSTREAM_REPO}/{UPSTREAM_COMMIT}/{filename}"
        )
        path = raw_dir / filename
        urllib.request.urlretrieve(url, path)
        receipt[logical] = {
            "filename": filename,
            "url": url,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "upstream_git_blob_sha": KNOWN_UPSTREAM_BLOB_SHAS[filename],
        }
    return receipt


def norm_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def norm_name(value: object) -> str:
    s = norm_text(value).lower()
    s = s.replace("’", "'")
    s = re.sub(r"[^a-z0-9]+", "", s)
    aliases = {
        "stanleydorsainvil": "standorsainvil",
        "marquelmederos": "marquelmederos",
    }
    return aliases.get(s, s)


def parse_count(value: object) -> tuple[float, float]:
    s = norm_text(value)
    if not s or s in {"--", "---"}:
        return 0.0, 0.0
    m = re.match(r"^\s*(\d+)\s+of\s+(\d+)\s*$", s)
    if not m:
        return 0.0, 0.0
    return float(m.group(1)), float(m.group(2))


def parse_clock(value: object) -> float:
    s = norm_text(value)
    m = re.match(r"^(\d+):(\d{2})$", s)
    if not m:
        return 0.0
    return float(int(m.group(1)) * 60 + int(m.group(2)))


def parse_height(value: object) -> float:
    s = norm_text(value)
    m = re.match(r"^(\d+)'\s*(\d+)\"?$", s)
    if not m:
        return np.nan
    return float(int(m.group(1)) * 12 + int(m.group(2)))


def parse_reach(value: object) -> float:
    s = norm_text(value).replace('"', "")
    try:
        return float(s)
    except Exception:
        return np.nan


def method3(value: object) -> str | None:
    s = norm_text(value).upper()
    if "KO/TKO" in s or s.startswith("TKO") or s.startswith("KO"):
        return "KO"
    if "SUBMISSION" in s:
        return "SUB"
    if "DECISION" in s:
        return "DEC"
    return None


def parse_event_date(value: object) -> pd.Timestamp:
    return pd.Timestamp(pd.to_datetime(value, errors="raise"), tz="UTC")


def build_static(tott: pd.DataFrame) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for _, r in tott.iterrows():
        name = norm_name(r["FIGHTER"])
        dob = pd.to_datetime(r.get("DOB"), errors="coerce", utc=True)
        out[name] = {
            "name": norm_text(r["FIGHTER"]),
            "height_inches": parse_height(r.get("HEIGHT")),
            "reach_inches": parse_reach(r.get("REACH")),
            "stance": norm_text(r.get("STANCE")).lower(),
            "dob": dob,
        }
    return out


def load_fights(raw_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, dict[str, object]]]:
    events = pd.read_csv(raw_dir / RAW_FILES["events"])
    results = pd.read_csv(raw_dir / RAW_FILES["results"])
    stats = pd.read_csv(raw_dir / RAW_FILES["stats"])
    tott = pd.read_csv(raw_dir / RAW_FILES["tott"])

    for frame in (events, results, stats, tott):
        frame.columns = [norm_text(c) for c in frame.columns]

    events["EVENT_KEY"] = events["EVENT"].map(norm_text)
    events["EVENT_DATE"] = pd.to_datetime(events["DATE"], errors="coerce", utc=True)
    event_dates = dict(zip(events["EVENT_KEY"], events["EVENT_DATE"]))

    results["EVENT_KEY"] = results["EVENT"].map(norm_text)
    results["BOUT_KEY"] = results["BOUT"].map(norm_text)
    results["EVENT_DATE"] = results["EVENT_KEY"].map(event_dates)
    results = results.loc[results["EVENT_DATE"].notna()].copy()
    results = results.loc[results["EVENT_DATE"] < TRAINING_CUTOFF].copy()

    records = []
    for _, r in results.iterrows():
        bout = norm_text(r["BOUT"])
        if " vs. " not in bout:
            continue
        a, b = bout.split(" vs. ", 1)
        outcome = norm_text(r["OUTCOME"]).upper()
        if outcome == "W/L":
            winner = a
        elif outcome == "L/W":
            winner = b
        else:
            continue
        m3 = method3(r["METHOD"])
        if m3 is None:
            continue
        try:
            finish_round = int(r["ROUND"])
        except Exception:
            continue
        finish_sec = parse_clock(r["TIME"])
        duration = (finish_round - 1) * 300 + finish_sec
        fmt = norm_text(r["TIME FORMAT"])
        scheduled_rounds = 5 if fmt.startswith("5") else 3
        scheduled_seconds = scheduled_rounds * 300
        duration = min(float(duration), float(scheduled_seconds))
        records.append(
            {
                "event": norm_text(r["EVENT"]),
                "bout": bout,
                "event_date": r["EVENT_DATE"],
                "fighter_a": a,
                "fighter_b": b,
                "winner": winner,
                "method": m3,
                "finish_round": finish_round,
                "duration_seconds": duration,
                "scheduled_seconds": scheduled_seconds,
                "weight_class": norm_text(r["WEIGHTCLASS"]),
                "fight_url": norm_text(r["URL"]),
            }
        )
    fights = pd.DataFrame(records)
    fights["fight_key"] = (
        fights["event_date"].dt.strftime("%Y-%m-%d")
        + "|"
        + fights["bout"].map(norm_text)
    )

    stats["EVENT_KEY"] = stats["EVENT"].map(norm_text)
    stats["BOUT_KEY"] = stats["BOUT"].map(norm_text)
    stats["FIGHTER_KEY"] = stats["FIGHTER"].map(norm_name)
    return fights.sort_values(["event_date", "event", "bout"]).reset_index(drop=True), stats, build_static(tott)


def aggregate_fight_stats(fights: pd.DataFrame, stats: pd.DataFrame) -> dict[tuple[str, str, str], dict[str, float]]:
    bykey: dict[tuple[str, str, str], dict[str, float]] = {}
    duration_lookup = {
        (norm_text(r.event), norm_text(r.bout)): float(r.duration_seconds)
        for r in fights.itertuples(index=False)
    }
    grouped = stats.groupby(["EVENT_KEY", "BOUT_KEY", "FIGHTER_KEY"], sort=False)
    for (event, bout, fighter), g in grouped:
        duration = duration_lookup.get((event, bout))
        if duration is None or duration <= 0:
            continue
        totals = {
            "kd_for": 0.0,
            "sig_landed": 0.0,
            "sig_attempted": 0.0,
            "ground_landed": 0.0,
            "ground_attempted": 0.0,
            "td_landed": 0.0,
            "td_attempted": 0.0,
            "sub_att": 0.0,
            "ctrl_seconds": 0.0,
            "r1_sig_landed": 0.0,
            "r1_seconds": min(300.0, duration),
            "r3_sig_landed": 0.0,
            "r3_seconds": max(0.0, min(300.0, duration - 600.0)),
        }
        for _, row in g.iterrows():
            round_s = norm_text(row["ROUND"])
            m = re.search(r"(\d+)", round_s)
            round_no = int(m.group(1)) if m else 0
            kd = pd.to_numeric(row.get("KD"), errors="coerce")
            totals["kd_for"] += 0.0 if pd.isna(kd) else float(kd)
            sl, sa = parse_count(row.get("SIG.STR."))
            gl, ga = parse_count(row.get("GROUND"))
            tl, ta = parse_count(row.get("TD"))
            totals["sig_landed"] += sl
            totals["sig_attempted"] += sa
            totals["ground_landed"] += gl
            totals["ground_attempted"] += ga
            totals["td_landed"] += tl
            totals["td_attempted"] += ta
            sub = pd.to_numeric(row.get("SUB.ATT"), errors="coerce")
            totals["sub_att"] += 0.0 if pd.isna(sub) else float(sub)
            totals["ctrl_seconds"] += parse_clock(row.get("CTRL"))
            if round_no == 1:
                totals["r1_sig_landed"] += sl
            if round_no == 3:
                totals["r3_sig_landed"] += sl
        totals["duration_seconds"] = duration
        bykey[(event, bout, fighter)] = totals
    return bykey


def safe_rate(num: float, den: float, scale: float = 1.0) -> float:
    return float(num / den * scale) if den > 0 else np.nan


def summarize_history(
    name: str,
    history: dict[str, list[dict[str, object]]],
    static: dict[str, dict[str, object]],
    asof: pd.Timestamp,
) -> dict[str, float]:
    key = norm_name(name)
    items = history.get(key, [])
    st = static.get(key, {})
    n = len(items)

    total_sec = sum(float(x["duration_seconds"]) for x in items)
    prior_bouts = float(n)
    wins = sum(int(x["win"]) for x in items)
    finishes_w = sum(int(x["win"] and x["method"] != "DEC") for x in items)
    ko_w = sum(int(x["win"] and x["method"] == "KO") for x in items)
    sub_w = sum(int(x["win"] and x["method"] == "SUB") for x in items)
    ko_l = sum(int((not x["win"]) and x["method"] == "KO") for x in items)
    sub_l = sum(int((not x["win"]) and x["method"] == "SUB") for x in items)

    def s(field: str) -> float:
        return float(sum(float(x.get(field, 0.0)) for x in items))

    sig_attempted = s("sig_attempted")
    opp_sig_attempted = s("opp_sig_attempted")
    td_attempted = s("td_attempted")
    opp_td_attempted = s("opp_td_attempted")

    r1_landed = s("r1_sig_landed")
    r1_sec = s("r1_seconds")
    r3_landed = s("r3_sig_landed")
    r3_sec = s("r3_seconds")
    r1_lpm = safe_rate(r1_landed, r1_sec, 60.0)
    r3_lpm = safe_rate(r3_landed, r3_sec, 60.0)
    r3_appearances = sum(float(x.get("r3_seconds", 0.0)) > 0 for x in items)
    retention = (
        r3_lpm / r1_lpm
        if r3_appearances >= 2
        and np.isfinite(r1_lpm)
        and np.isfinite(r3_lpm)
        and r1_lpm > 0.05
        else np.nan
    )

    recent = items[-5:]
    recent_sec = sum(float(x["duration_seconds"]) for x in recent)
    recent_sig_diff = sum(
        float(x.get("sig_landed", 0.0)) - float(x.get("opp_sig_landed", 0.0))
        for x in recent
    )

    last_date = pd.Timestamp(items[-1]["event_date"]) if items else pd.NaT
    days_since_last = (
        float((asof - last_date).days)
        if items and pd.notna(last_date)
        else np.nan
    )

    dob = st.get("dob", pd.NaT)
    age = (
        float((asof - pd.Timestamp(dob)).days / 365.2425)
        if pd.notna(dob)
        else np.nan
    )
    stance = str(st.get("stance", "")).lower()

    return {
        "prior_bouts": prior_bouts,
        "win_rate": safe_rate(wins, n),
        "finish_win_rate": safe_rate(finishes_w, n),
        "ko_win_rate": safe_rate(ko_w, n),
        "sub_win_rate": safe_rate(sub_w, n),
        "ko_loss_rate": safe_rate(ko_l, n),
        "sub_loss_rate": safe_rate(sub_l, n),
        "kd_for_per15": safe_rate(s("kd_for"), total_sec, 900.0),
        "kd_against_per15": safe_rate(s("opp_kd_for"), total_sec, 900.0),
        "sig_landed_per_min": safe_rate(s("sig_landed"), total_sec, 60.0),
        "sig_absorbed_per_min": safe_rate(s("opp_sig_landed"), total_sec, 60.0),
        "sig_accuracy": safe_rate(s("sig_landed"), sig_attempted),
        "sig_defense": (
            1.0 - safe_rate(s("opp_sig_landed"), opp_sig_attempted)
            if opp_sig_attempted > 0 else np.nan
        ),
        "ground_for_per15": safe_rate(s("ground_landed"), total_sec, 900.0),
        "ground_against_per15": safe_rate(s("opp_ground_landed"), total_sec, 900.0),
        "td_landed_per15": safe_rate(s("td_landed"), total_sec, 900.0),
        "td_attempts_per15": safe_rate(td_attempted, total_sec, 900.0),
        "td_accuracy": safe_rate(s("td_landed"), td_attempted),
        "td_defense": (
            1.0 - safe_rate(s("opp_td_landed"), opp_td_attempted)
            if opp_td_attempted > 0 else np.nan
        ),
        "sub_att_per15": safe_rate(s("sub_att"), total_sec, 900.0),
        "sub_att_against_per15": safe_rate(s("opp_sub_att"), total_sec, 900.0),
        "ctrl_for_per15": safe_rate(s("ctrl_seconds"), total_sec, 900.0),
        "ctrl_against_per15": safe_rate(s("opp_ctrl_seconds"), total_sec, 900.0),
        "r3_retention": retention,
        "recent5_win_rate": safe_rate(sum(int(x["win"]) for x in recent), len(recent)),
        "recent5_finish_rate": safe_rate(
            sum(int(x["win"] and x["method"] != "DEC") for x in recent),
            len(recent),
        ),
        "recent5_sig_diff_per_min": safe_rate(recent_sig_diff, recent_sec, 60.0),
        "recent5_kd_for_per15": safe_rate(
            sum(float(x.get("kd_for", 0.0)) for x in recent), recent_sec, 900.0
        ),
        "recent5_td_landed_per15": safe_rate(
            sum(float(x.get("td_landed", 0.0)) for x in recent), recent_sec, 900.0
        ),
        "recent5_sub_att_per15": safe_rate(
            sum(float(x.get("sub_att", 0.0)) for x in recent), recent_sec, 900.0
        ),
        "days_since_last": days_since_last,
        "age_years": age,
        "height_inches": float(st.get("height_inches", np.nan)),
        "reach_inches": float(st.get("reach_inches", np.nan)),
        "southpaw": float("southpaw" in stance),
        "_stance": stance,
    }


def matchup_flags(weight_class: str, scheduled_seconds: int, a_stance: str, b_stance: str) -> dict[str, float]:
    wc = weight_class.lower()
    return {
        "scheduled_five_round": float(scheduled_seconds == 1500),
        "is_heavyweight": float("heavyweight" in wc and "light heavyweight" not in wc),
        "is_womens": float("women" in wc),
        "same_stance": float(bool(a_stance) and a_stance == b_stance),
    }


def winner_features(
    a: dict[str, float], b: dict[str, float], weight_class: str, scheduled_seconds: int
) -> dict[str, float]:
    out: dict[str, float] = {}
    for f in SIDE_RATE_FIELDS:
        out[f"a_{f}"] = a.get(f, np.nan)
        out[f"b_{f}"] = b.get(f, np.nan)
        if f not in {"days_since_last", "southpaw"}:
            av = a.get(f, np.nan)
            bv = b.get(f, np.nan)
            out[f"diff_{f}"] = av - bv if np.isfinite(av) and np.isfinite(bv) else np.nan
    out.update(matchup_flags(weight_class, scheduled_seconds, a.get("_stance", ""), b.get("_stance", "")))
    return out


def method_features(
    winner: dict[str, float], opponent: dict[str, float], weight_class: str, scheduled_seconds: int
) -> dict[str, float]:
    out: dict[str, float] = {}
    for f in SIDE_RATE_FIELDS:
        out[f"winner_{f}"] = winner.get(f, np.nan)
        out[f"opponent_{f}"] = opponent.get(f, np.nan)
        if f not in {"days_since_last", "southpaw"}:
            wv = winner.get(f, np.nan)
            ov = opponent.get(f, np.nan)
            out[f"diff_{f}"] = wv - ov if np.isfinite(wv) and np.isfinite(ov) else np.nan
    out.update(
        matchup_flags(
            weight_class,
            scheduled_seconds,
            winner.get("_stance", ""),
            opponent.get("_stance", ""),
        )
    )
    return out


def residual_features(w: dict[str, float], o: dict[str, float]) -> dict[str, float]:
    def v(d: dict[str, float], key: str) -> float:
        x = d.get(key, np.nan)
        return float(x) if np.isfinite(x) else np.nan

    def product(a: float, b: float) -> float:
        return a * b if np.isfinite(a) and np.isfinite(b) else np.nan

    kd = product(v(w, "kd_for_per15"), 1.0 + v(o, "kd_against_per15"))
    ground = product(v(w, "ground_for_per15"), 1.0 + v(o, "ground_against_per15"))
    sub = product(v(w, "sub_att_per15"), 1.0 + v(o, "sub_att_against_per15"))
    td_def_weak = 1.0 - v(o, "td_defense") if np.isfinite(v(o, "td_defense")) else np.nan
    td_access = product(v(w, "td_landed_per15"), td_def_weak)
    control = product(v(w, "ctrl_for_per15") / 900.0, 1.0 + v(o, "ctrl_against_per15") / 900.0)

    td_acc = v(w, "td_accuracy")
    failed_share = 1.0 - td_acc if np.isfinite(td_acc) else np.nan
    wrestle_exposure = product(
        product(v(w, "td_attempts_per15"), failed_share),
        1.0 + v(o, "sub_att_per15"),
    )

    return {
        "knockdown_interaction": kd,
        "ground_strike_interaction": ground,
        "submission_attempt_interaction": sub,
        "td_access_interaction": td_access,
        "control_interaction": control,
        "offensive_wrestling_exposure_interaction": wrestle_exposure,
        "winner_round3_retention": v(w, "r3_retention"),
        "opponent_round3_retention": v(o, "r3_retention"),
        "winner_log_ufc_bouts": math.log1p(max(v(w, "prior_bouts"), 0.0)),
        "opponent_log_ufc_bouts": math.log1p(max(v(o, "prior_bouts"), 0.0)),
    }


def enrich_and_snapshot(
    fights: pd.DataFrame,
    fight_stats: dict[tuple[str, str, str], dict[str, float]],
    static: dict[str, dict[str, object]],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    history: dict[str, list[dict[str, object]]] = {}
    winner_rows = []
    method_rows = []
    timing_rows = []

    for date, group in fights.groupby("event_date", sort=True):
        pending_updates: list[tuple[str, dict[str, object]]] = []
        for fight in group.itertuples(index=False):
            a = summarize_history(fight.fighter_a, history, static, date)
            b = summarize_history(fight.fighter_b, history, static, date)
            wf = winner_features(a, b, fight.weight_class, fight.scheduled_seconds)

            winner_is_a = int(norm_name(fight.winner) == norm_name(fight.fighter_a))
            w_side, o_side = (a, b) if winner_is_a else (b, a)
            mf = method_features(w_side, o_side, fight.weight_class, fight.scheduled_seconds)
            rf = residual_features(w_side, o_side)

            base_meta = {
                "fight_key": fight.fight_key,
                "event": fight.event,
                "event_date": date.isoformat(),
                "bout": fight.bout,
                "fighter_a": fight.fighter_a,
                "fighter_b": fight.fighter_b,
                "winner": fight.winner,
                "method": fight.method,
                "winner_is_a": winner_is_a,
                "weight_class": fight.weight_class,
                "scheduled_seconds": int(fight.scheduled_seconds),
                "duration_seconds": float(fight.duration_seconds),
            }
            winner_rows.append({**base_meta, **wf})
            method_rows.append({**base_meta, **mf, **rf})
            timing_rows.append({**base_meta, **wf})

            event_key = norm_text(fight.event)
            bout_key = norm_text(fight.bout)
            sa = fight_stats.get((event_key, bout_key, norm_name(fight.fighter_a)), {})
            sb = fight_stats.get((event_key, bout_key, norm_name(fight.fighter_b)), {})
            for fighter_name, own, opp in [
                (fight.fighter_a, sa, sb),
                (fight.fighter_b, sb, sa),
            ]:
                key = norm_name(fighter_name)
                item = {
                    "event_date": date,
                    "duration_seconds": float(fight.duration_seconds),
                    "win": norm_name(fight.winner) == key,
                    "method": fight.method,
                }
                for f in [
                    "kd_for",
                    "sig_landed",
                    "sig_attempted",
                    "ground_landed",
                    "ground_attempted",
                    "td_landed",
                    "td_attempted",
                    "sub_att",
                    "ctrl_seconds",
                    "r1_sig_landed",
                    "r1_seconds",
                    "r3_sig_landed",
                    "r3_seconds",
                ]:
                    item[f] = float(own.get(f, 0.0))
                    item[f"opp_{f}"] = float(opp.get(f, 0.0))
                pending_updates.append((key, item))

        # Same-day outcomes become history only after all same-day prefight rows are frozen.
        for key, item in pending_updates:
            history.setdefault(key, []).append(item)

    return pd.DataFrame(winner_rows), pd.DataFrame(method_rows), pd.DataFrame(timing_rows)


def find_clean_rows(clean: pd.DataFrame, method_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    used = set()
    for c in clean.itertuples(index=False):
        date = str(c.event_date)
        f1, f2 = [x.strip() for x in str(c.fight).split(" vs ", 1)]
        nset = {norm_name(f1), norm_name(f2)}
        cand = method_df.loc[method_df["event_date"].str.startswith(date)].copy()
        best_i = None
        best_score = -1
        for i, r in cand.iterrows():
            rset = {norm_name(r["fighter_a"]), norm_name(r["fighter_b"])}
            score = len(nset & rset)
            if score > best_score and int(i) not in used:
                best_score = score
                best_i = i
        if best_i is None or best_score < 2:
            raise RuntimeError(f"Could not uniquely match clean fight: {date} {c.fight}")
        used.add(int(best_i))
        r = method_df.loc[best_i].to_dict()
        r["clean_displayed_method"] = str(c.displayed_method)
        r["clean_actual_method"] = str(c.actual_method)
        r["clean_winner_correct"] = int(c.winner_correct)
        rows.append(r)
    out = pd.DataFrame(rows)
    if len(out) != 64:
        raise RuntimeError(f"Expected 64 clean fights, matched {len(out)}")
    return out.sort_values(["event_date", "bout"]).reset_index(drop=True)


def fit_baseline_for_cutoff(method_df: pd.DataFrame, cutoff: str) -> ConditionalMethodModel:
    train = method_df.loc[method_df["event_date"] < cutoff]
    if len(train) < 1000:
        raise RuntimeError("Too few historical rows before clean-card cutoff")
    model = ConditionalMethodModel(finish_c=0.10, sub_c=0.10)
    model.fit(train[METHOD_BASE_FEATURES], train["method"])
    return model


def add_clean_oof_baselines(clean_rows: pd.DataFrame, method_df: pd.DataFrame) -> pd.DataFrame:
    out = clean_rows.copy()
    out[["base_KO", "base_SUB", "base_DEC"]] = np.nan
    for cutoff in sorted(out["event_date"].unique()):
        model = fit_baseline_for_cutoff(method_df, cutoff)
        mask = out["event_date"] == cutoff
        p = model.predict_proba(out.loc[mask, METHOD_BASE_FEATURES])
        out.loc[mask, "base_KO"] = p["KO"].to_numpy()
        out.loc[mask, "base_SUB"] = p["SUB"].to_numpy()
        out.loc[mask, "base_DEC"] = p["DEC"].to_numpy()
    return out


def grade_methods(y: np.ndarray, p: np.ndarray) -> dict[str, object]:
    classes = ["KO", "SUB", "DEC"]
    pred = np.asarray(classes)[np.argmax(p, axis=1)]
    return {
        "n": int(len(y)),
        "accuracy": float(accuracy_score(y, pred)),
        "log_loss": float(log_loss(y, p, labels=classes)),
        "multiclass_brier": float(multiclass_brier(y, p, classes)),
        "calls": {c: int(np.sum(pred == c)) for c in classes},
        "actual": {c: int(np.sum(y == c)) for c in classes},
        "recall": {
            c: (
                float(np.mean(pred[y == c] == c))
                if np.any(y == c)
                else None
            )
            for c in classes
        },
    }


def chronology_residual_benchmark(clean_oof: pd.DataFrame) -> dict[str, object]:
    classes = ["KO", "SUB", "DEC"]
    baseline_probs = clean_oof[["base_KO", "base_SUB", "base_DEC"]].to_numpy(float)
    baseline_y = clean_oof["clean_actual_method"].to_numpy(str)
    base_grade = grade_methods(baseline_y, baseline_probs)

    all_y = []
    all_base = []
    all_candidate = []
    fold_receipts = []
    dates = sorted(clean_oof["event_date"].unique())

    for test_date in dates[1:]:
        train = clean_oof.loc[clean_oof["event_date"] < test_date].copy()
        test = clean_oof.loc[clean_oof["event_date"] == test_date].copy()
        if len(train) < 12:
            continue
        try:
            model = V027MethodResidualChallenger(ridge=10.0, clip_z=5.0).fit(
                train[list(V027_FEATURES)],
                actual_method=train["clean_actual_method"],
                baseline_ko=train["base_KO"],
                baseline_sub=train["base_SUB"],
                baseline_dec=train["base_DEC"],
            )
        except ValueError:
            continue
        cand = model.predict_proba(
            test[list(V027_FEATURES)],
            baseline_ko=test["base_KO"],
            baseline_sub=test["base_SUB"],
            baseline_dec=test["base_DEC"],
        )
        all_y.extend(test["clean_actual_method"].tolist())
        all_base.append(test[["base_KO", "base_SUB", "base_DEC"]].to_numpy(float))
        all_candidate.append(cand[["KO", "SUB", "DEC"]].to_numpy(float))
        fold_receipts.append(
            {
                "test_date": test_date,
                "train_clean_fights": int(len(train)),
                "test_fights": int(len(test)),
            }
        )

    if not all_y:
        return {"baseline_all_64": base_grade, "chronology_candidate": None}

    y = np.asarray(all_y, dtype=str)
    bp = np.vstack(all_base)
    cp = np.vstack(all_candidate)
    return {
        "baseline_all_64": base_grade,
        "chronology_evaluation_fights": int(len(y)),
        "chronology_baseline": grade_methods(y, bp),
        "chronology_candidate": grade_methods(y, cp),
        "folds": fold_receipts,
        "note": (
            "Retrospective reconstruction only. Architecture and feature formulas were "
            "defined after historical results were known; this is not prospective proof."
        ),
    }


def winner_clean_benchmark(clean: pd.DataFrame, winner_df: pd.DataFrame) -> dict[str, object]:
    rows = []
    used = set()
    for c in clean.itertuples(index=False):
        date = str(c.event_date)
        f1, f2 = [x.strip() for x in str(c.fight).split(" vs ", 1)]
        nset = {norm_name(f1), norm_name(f2)}
        cand = winner_df.loc[winner_df["event_date"].str.startswith(date)]
        best_i = None
        best_score = -1
        for i, r in cand.iterrows():
            rset = {norm_name(r["fighter_a"]), norm_name(r["fighter_b"])}
            score = len(nset & rset)
            if score > best_score and int(i) not in used:
                best_score = score
                best_i = i
        if best_i is None or best_score < 2:
            raise RuntimeError(f"Winner benchmark match failed: {c.fight}")
        used.add(int(best_i))
        rows.append(winner_df.loc[best_i].to_dict())
    clean_w = pd.DataFrame(rows)

    probs = np.full(len(clean_w), np.nan)
    for cutoff in sorted(clean_w["event_date"].unique()):
        train = winner_df.loc[winner_df["event_date"] < cutoff]
        test_mask = clean_w["event_date"] == cutoff
        model = WinnerModel(c=0.25).fit(train[WINNER_FEATURES], train["winner_is_a"])
        probs[test_mask] = model.predict_proba(clean_w.loc[test_mask, WINNER_FEATURES])[:, 0]

    y = clean_w["winner_is_a"].to_numpy(int)
    pred = (probs >= 0.5).astype(int)
    return {
        "n": int(len(y)),
        "accuracy": float(np.mean(pred == y)),
        "brier": float(np.mean((probs - y) ** 2)),
        "log_loss": float(log_loss(y, np.column_stack([1 - probs, probs]), labels=[0, 1])),
        "note": "New reconstruction benchmark, not the historical official v0.3.1 score.",
    }


def save_final_models(
    winner_df: pd.DataFrame,
    method_df: pd.DataFrame,
    timing_df: pd.DataFrame,
    clean_oof: pd.DataFrame,
    artifact_dir: Path,
) -> dict[str, str]:
    artifact_dir.mkdir(parents=True, exist_ok=True)

    winner = WinnerModel(c=0.25).fit(winner_df[WINNER_FEATURES], winner_df["winner_is_a"])
    method = ConditionalMethodModel(finish_c=0.10, sub_c=0.10).fit(
        method_df[METHOD_BASE_FEATURES], method_df["method"]
    )
    residual = V027MethodResidualChallenger(ridge=10.0, clip_z=5.0).fit(
        clean_oof[list(V027_FEATURES)],
        actual_method=clean_oof["clean_actual_method"],
        baseline_ko=clean_oof["base_KO"],
        baseline_sub=clean_oof["base_SUB"],
        baseline_dec=clean_oof["base_DEC"],
    )

    timing = DiscreteTimeHazardModel(bin_seconds=60, c=0.10).fit(
        timing_df[TIMING_FEATURES],
        timing_df["duration_seconds"].to_numpy(float),
        timing_df["scheduled_seconds"].to_numpy(int),
        (timing_df["method"] != "DEC").astype(int).to_numpy(),
    )

    paths = {
        "winner": artifact_dir / "winner_reconstruction.joblib",
        "method_baseline": artifact_dir / "method_baseline_reconstruction.joblib",
        "method_residual_v027": artifact_dir / "method_residual_v027.joblib",
        "timing": artifact_dir / "timing_reconstruction.joblib",
    }
    joblib.dump(winner, paths["winner"])
    joblib.dump(method, paths["method_baseline"])
    joblib.dump(residual, paths["method_residual_v027"])
    joblib.dump(timing, paths["timing"])
    return {k: sha256_file(v) for k, v in paths.items()}


def write_post_august_delta(
    winner_df: pd.DataFrame,
    method_df: pd.DataFrame,
    out_dir: Path,
) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cutoff = "2026-08-02"
    w = winner_df.loc[winner_df["event_date"] >= cutoff].copy()
    m = method_df.loc[method_df["event_date"] >= cutoff].copy()
    keep_meta = [
        "fight_key", "event", "event_date", "bout", "fighter_a", "fighter_b",
        "winner", "method", "winner_is_a", "weight_class",
        "scheduled_seconds", "duration_seconds",
    ]
    w_cols = keep_meta + list(WINNER_FEATURES)
    m_cols = keep_meta + list(METHOD_BASE_FEATURES) + list(V027_FEATURES)
    w.to_csv(out_dir / "prefight_winner_features_2026-08-02_to_cutoff.csv", index=False, columns=w_cols)
    m.to_csv(out_dir / "prefight_method_features_2026-08-02_to_cutoff.csv", index=False, columns=m_cols)
    return {
        "winner_rows": int(len(w)),
        "method_rows": int(len(m)),
        "first_event_date": str(w["event_date"].min()) if len(w) else None,
        "last_event_date": str(w["event_date"].max()) if len(w) else None,
        "winner_delta_sha256": sha256_file(out_dir / "prefight_winner_features_2026-08-02_to_cutoff.csv"),
        "method_delta_sha256": sha256_file(out_dir / "prefight_method_features_2026-08-02_to_cutoff.csv"),
    }


def main() -> None:
    raw_dir = ROOT / "build/rebuild_v027/raw"
    artifact_dir = ROOT / "artifacts/v027_reconstruction"
    report_dir = ROOT / "reports/v027_reconstruction"
    feature_dir = ROOT / "data/features/reconstructed"
    for d in (artifact_dir, report_dir, feature_dir):
        d.mkdir(parents=True, exist_ok=True)

    source_receipt = download_sources(raw_dir)
    fights, stats, static = load_fights(raw_dir)
    fight_stats = aggregate_fight_stats(fights, stats)
    winner_df, method_df, timing_df = enrich_and_snapshot(fights, fight_stats, static)

    clean = pd.read_csv(CLEAN_LEDGER)
    clean_oof = add_clean_oof_baselines(find_clean_rows(clean, method_df), method_df)

    method_benchmark = chronology_residual_benchmark(clean_oof)
    winner_benchmark = winner_clean_benchmark(clean, winner_df)
    artifact_hashes = save_final_models(
        winner_df, method_df, timing_df, clean_oof, artifact_dir
    )
    delta = write_post_august_delta(winner_df, method_df, feature_dir)

    clean_export_cols = [
        "fight_key", "event", "event_date", "bout", "winner", "clean_actual_method",
        "base_KO", "base_SUB", "base_DEC", *V027_FEATURES
    ]
    clean_oof.to_csv(
        report_dir / "clean64_reconstructed_oof_method_inputs.csv",
        index=False,
        columns=clean_export_cols,
    )

    manifest = {
        "status": "V0.27_RECONSTRUCTION_TRAINED_SHADOW",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "upstream": {
            "repository": UPSTREAM_REPO,
            "commit": UPSTREAM_COMMIT,
            "files": source_receipt,
        },
        "cutoff_exclusive": TRAINING_CUTOFF.isoformat(),
        "population": {
            "decisive_fights": int(len(fights)),
            "first_event_date": fights["event_date"].min().isoformat(),
            "last_event_date": fights["event_date"].max().isoformat(),
            "winner_training_rows": int(len(winner_df)),
            "conditional_method_training_rows": int(len(method_df)),
            "timing_training_rows": int(len(timing_df)),
            "clean_feedback_rows": int(len(clean_oof)),
        },
        "feature_contract": {
            "same_day_leakage_rule": "same-day fights frozen before any same-day outcome update",
            "winner_feature_count": len(WINNER_FEATURES),
            "method_baseline_feature_count": len(METHOD_BASE_FEATURES),
            "residual_features": list(V027_FEATURES),
            "residual_formula_status": (
                "new v0.27 reconstruction formulas; not claimed byte-identical to lost v0.26"
            ),
        },
        "winner_clean64_reconstruction_benchmark": winner_benchmark,
        "method_clean64_reconstruction_benchmark": method_benchmark,
        "post_august_feature_delta": delta,
        "artifact_sha256": artifact_hashes,
        "promotion": {
            "authorized": False,
            "role": "shadow/reconstruction",
            "prospective_fights_since_rebuild": 0,
        },
        "integrity_note": (
            "This rebuild uses public UFCStats-derived fight/round data pinned to an "
            "upstream Git commit. It reconstructs current causal fighter histories "
            "through the latest completed event before the cutoff. It does not claim "
            "to reproduce the lost v0.26 binaries or its exact coefficients."
        ),
    }
    (artifact_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    (report_dir / "benchmark.json").write_text(
        json.dumps(
            {
                "winner": winner_benchmark,
                "method": method_benchmark,
                "population": manifest["population"],
                "delta": delta,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    summary = [
        "# v0.27 reconstruction build report",
        "",
        f"- Status: **{manifest['status']}**",
        f"- Upstream: \`{UPSTREAM_REPO}@{UPSTREAM_COMMIT}\`",
        f"- Training cutoff (exclusive): **{TRAINING_CUTOFF.isoformat()}**",
        f"- Decisive UFC fights reconstructed: **{len(fights):,}**",
        f"- Latest completed event in feed: **{fights['event_date'].max().date()}**",
        f"- Clean WSHL_X feedback rows: **{len(clean_oof)}**",
        f"- Post-Aug-1 prefight rows restored: **{delta['winner_rows']}**",
        "",
        "## Clean-64 winner reconstruction benchmark",
        "",
        f"- Accuracy: {winner_benchmark['accuracy']:.4f}",
        f"- Brier: {winner_benchmark['brier']:.6f}",
        f"- Log loss: {winner_benchmark['log_loss']:.6f}",
        "",
        "## Clean-card conditional method reconstruction",
        "",
        f"- Chronology evaluation fights: {method_benchmark.get('chronology_evaluation_fights', 0)}",
    ]
    c = method_benchmark.get("chronology_candidate")
    b = method_benchmark.get("chronology_baseline")
    if c and b:
        summary += [
            f"- Baseline accuracy / candidate accuracy: {b['accuracy']:.4f} / {c['accuracy']:.4f}",
            f"- Baseline Brier / candidate Brier: {b['multiclass_brier']:.6f} / {c['multiclass_brier']:.6f}",
            f"- Baseline log loss / candidate log loss: {b['log_loss']:.6f} / {c['log_loss']:.6f}",
            f"- Baseline SUB recall / candidate SUB recall: {b['recall']['SUB']} / {c['recall']['SUB']}",
        ]
    summary += [
        "",
        "## Interpretation",
        "",
        "This is a verified **reconstruction shadow**, not a promotion and not the lost v0.26 binary.",
        "All historical matchup features are frozen from fights dated strictly earlier than the target event.",
        "Same-day fights are frozen together before any same-day result updates the histories.",
    ]
    (report_dir / "BUILD_REPORT.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
