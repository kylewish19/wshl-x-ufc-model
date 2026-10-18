"""Historical conditional-rate timing challenger for UFC round/distance markets.

One orientation-invariant row is created per fight. Historical finish/survival rates are
encoded strictly from earlier event dates, then fed into the existing 30-second discrete
hazard model. All O/U, goes-distance, and round-start prices come from one survival curve.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from .calibration import TemperatureCalibrator, fit_temperature_calibrator
from .historical_data import METRICS
from .historical_model import chronological_split
from .historical_outcomes import add_timing_targets
from .historical_rates import PastOnlyRateEncoder, SplitSpec
from .timing import DiscreteTimeHazardModel

I = np.inf
TIMING_SPLITS = (
    SplitSpec("pair_age_mean", "pair_mean_age", (-I, 27, 30, 33, 36, I), ("u27", "27_29", "30_32", "33_35", "36+")),
    SplitSpec("pair_age_max", "pair_max_age", (-I, 30, 33, 36, 40, I), ("u30", "30_32", "33_35", "36_39", "40+")),
    SplitSpec("age_gap_abs", "gap_abs_age", (-I, 2, 4, 6, 9, I), ("u2", "2_4", "4_6", "6_9", "9+")),
    SplitSpec("reach_gap_abs", "gap_abs_reach", (-I, 2, 4, 6, 8, I), ("u2", "2_4", "4_6", "6_8", "8+")),
    SplitSpec("finish_mean", "pair_mean_finish_win_rate", (-I, .25, .45, .60, .75, I), ("u25", "25_45", "45_60", "60_75", "75+")),
    SplitSpec("finish_max", "pair_max_finish_win_rate", (-I, .35, .55, .70, .85, I), ("u35", "35_55", "55_70", "70_85", "85+")),
    SplitSpec("ko_vulnerability_max", "pair_max_ko_loss_rate", (-I, .10, .25, .50, .75, I), ("u10", "10_25", "25_50", "50_75", "75+")),
    SplitSpec("sub_vulnerability_max", "pair_max_sub_loss_rate", (-I, .10, .25, .50, .75, I), ("u10", "10_25", "25_50", "50_75", "75+")),
    SplitSpec("kd_mean", "pair_mean_kd_per15", (-I, .10, .30, .60, 1.0, I), ("u.1", ".1_.3", ".3_.6", ".6_1", "1+")),
    SplitSpec("sub_att_mean", "pair_mean_sub_att_per15", (-I, .10, .40, .80, 1.5, I), ("u.1", ".1_.4", ".4_.8", ".8_1.5", "1.5+")),
    SplitSpec("slpm_mean", "pair_mean_slpm", (-I, 2.5, 3.5, 4.5, 5.5, I), ("u2.5", "2.5_3.5", "3.5_4.5", "4.5_5.5", "5.5+")),
    SplitSpec("sapm_mean", "pair_mean_sapm", (-I, 2.5, 3.5, 4.5, 5.5, I), ("u2.5", "2.5_3.5", "3.5_4.5", "4.5_5.5", "5.5+")),
    SplitSpec("td_mean", "pair_mean_td_per15", (-I, .5, 1.25, 2.25, 3.5, I), ("u.5", ".5_1.25", "1.25_2.25", "2.25_3.5", "3.5+")),
    SplitSpec("layoff_max", "pair_max_layoff_days", (-I, 120, 240, 365, 540, I), ("u120", "120_240", "240_365", "365_540", "540+")),
    SplitSpec("experience_total", "pair_total_ufc_fights", (-I, 3, 8, 16, 30, I), ("u3", "3_8", "8_16", "16_30", "30+")),
)
TIMING_TARGETS = ("finish_observed", "finish_r1", "survive_450", "survive_750", "goes_distance")


def _weight_context(weight_class: pd.Series) -> tuple[pd.Series, pd.Series]:
    s = weight_class.astype(str).str.lower()
    pounds = pd.Series(np.nan, index=s.index, dtype=float)
    # Order matters: light heavyweight must be assigned before heavyweight.
    mapping = [
        ("strawweight", 115), ("flyweight", 125), ("bantamweight", 135),
        ("featherweight", 145), ("lightweight", 155), ("welterweight", 170),
        ("middleweight", 185), ("light heavyweight", 205), ("heavyweight", 265),
    ]
    for name, value in mapping:
        mask = s.str.contains(name, regex=False)
        pounds.loc[mask] = value
    women = s.str.contains("women", regex=False).astype(float)
    return pounds, women


def symmetric_timing_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Collapse mirrored fighter rows to orientation-invariant matchup features."""
    if frame.empty:
        return frame.copy()
    base = frame.loc[~frame["fight_id"].astype(str).duplicated(keep="first")].copy()
    out = pd.DataFrame(index=base.index)
    for c in ("fight_id", "date", "event", "weight_class", "scheduled_rounds", "title_fight", "rematch_number"):
        if c in base:
            out[c] = base[c]
    for target in ("finish_seconds", "scheduled_seconds", "finish_observed", "finish_r1", "survive_450", "survive_750", "goes_distance"):
        if target in base:
            out[target] = base[target]
    for metric in METRICS:
        opp = f"opp_{metric}"
        if metric not in base or opp not in base:
            continue
        a = pd.to_numeric(base[metric], errors="coerce")
        b = pd.to_numeric(base[opp], errors="coerce")
        out[f"pair_mean_{metric}"] = pd.concat([a, b], axis=1).mean(axis=1)
        out[f"pair_min_{metric}"] = pd.concat([a, b], axis=1).min(axis=1)
        out[f"pair_max_{metric}"] = pd.concat([a, b], axis=1).max(axis=1)
        out[f"gap_abs_{metric}"] = (a - b).abs()
    if "ufc_fights" in base and "opp_ufc_fights" in base:
        out["pair_total_ufc_fights"] = pd.to_numeric(base["ufc_fights"], errors="coerce") + pd.to_numeric(base["opp_ufc_fights"], errors="coerce")
    if "date" in out:
        out["event_year"] = pd.to_datetime(out["date"], errors="coerce").dt.year.astype(float)
    if "weight_class" in out:
        out["weight_class_lbs"], out["women_division"] = _weight_context(out["weight_class"])
    if "pair_mean_finish_win_rate" in out and "pair_max_ko_loss_rate" in out:
        out["finish_pressure_x_ko_vulnerability"] = out["pair_mean_finish_win_rate"] * out["pair_max_ko_loss_rate"]
    if "pair_mean_kd_per15" in out and "pair_mean_sapm" in out:
        out["power_x_damage_absorbed"] = out["pair_mean_kd_per15"] * out["pair_mean_sapm"]
    if "pair_mean_sub_att_per15" in out and "pair_max_sub_loss_rate" in out:
        out["sub_pressure_x_sub_vulnerability"] = out["pair_mean_sub_att_per15"] * out["pair_max_sub_loss_rate"]
    return out.reset_index(drop=True)


def _encode_fit(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, PastOnlyRateEncoder]]:
    out = frame.copy()
    encoders: dict[str, PastOnlyRateEncoder] = {}
    for target in TIMING_TARGETS:
        prior = float(pd.to_numeric(frame[target], errors="coerce").mean())
        enc = PastOnlyRateEncoder(specs=TIMING_SPLITS, alpha=20.0, prior=prior)
        z = enc.fit_transform(frame, target=target)
        for c in [c for c in z.columns if c.startswith("hist_") and c.endswith("_wr")]:
            out[c.replace("_wr", f"_{target}_rate")] = z[c]
        for c in [c for c in z.columns if c.startswith("hist_") and c.endswith("_n")]:
            if c not in out:
                out[c] = z[c]
        encoders[target] = enc
    return out, encoders


def _fit_encoders(frame: pd.DataFrame) -> dict[str, PastOnlyRateEncoder]:
    out: dict[str, PastOnlyRateEncoder] = {}
    for target in TIMING_TARGETS:
        prior = float(pd.to_numeric(frame[target], errors="coerce").mean())
        out[target] = PastOnlyRateEncoder(specs=TIMING_SPLITS, alpha=20.0, prior=prior).fit(frame, target=target)
    return out


def _encode_transform(frame: pd.DataFrame, encoders: dict[str, PastOnlyRateEncoder]) -> pd.DataFrame:
    out = frame.copy()
    for target, enc in encoders.items():
        z = enc.transform(frame)
        for c in [c for c in z.columns if c.startswith("hist_") and c.endswith("_wr")]:
            out[c.replace("_wr", f"_{target}_rate")] = z[c]
        for c in [c for c in z.columns if c.startswith("hist_") and c.endswith("_n")]:
            if c not in out:
                out[c] = z[c]
    return out


TARGET_COLS = {"finish_seconds", "scheduled_seconds", "finish_observed", "finish_r1", "survive_450", "survive_750", "goes_distance"}
META_COLS = {"fight_id", "date", "event", "weight_class"}


def _numeric_features(frame: pd.DataFrame) -> list[str]:
    return [c for c in frame.columns if c not in TARGET_COLS | META_COLS and pd.api.types.is_numeric_dtype(frame[c])]


def _binary_metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    yy = np.asarray(y, dtype=int)
    pp = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    out = {
        "n": float(len(yy)),
        "accuracy": float(np.mean((pp >= 0.5) == yy)),
        "brier": float(brier_score_loss(yy, pp)),
        "log_loss": float(log_loss(yy, pp, labels=[0, 1])),
    }
    out["roc_auc"] = float(roc_auc_score(yy, pp)) if len(np.unique(yy)) == 2 else np.nan
    return out


def _market_predictions(bundle: "HistoricalTimingBundle", encoded: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in encoded.iterrows():
        scheduled = int(row["scheduled_seconds"])
        probs = bundle.market_probabilities_from_encoded(row, scheduled)
        probs["fight_id"] = row["fight_id"]
        rows.append(probs)
    return pd.DataFrame(rows).set_index("fight_id")


def evaluate_timing_markets(bundle: "HistoricalTimingBundle", encoded: pd.DataFrame) -> dict[str, dict[str, float]]:
    pred = _market_predictions(bundle, encoded)
    actual = encoded.set_index("fight_id")
    definitions: dict[str, tuple[str, np.ndarray]] = {
        "GTD_YES": ("goes_distance", actual["goes_distance"].to_numpy()),
        "OVER_1.5": ("survive_450", actual["survive_450"].to_numpy()),
        "OVER_2.5": ("survive_750", actual["survive_750"].to_numpy()),
        "ROUND_2_STARTS_YES": ("r2", (actual["finish_seconds"] > 300).astype(int).to_numpy()),
        "ROUND_3_STARTS_YES": ("r3", (actual["finish_seconds"] > 600).astype(int).to_numpy()),
    }
    out: dict[str, dict[str, float]] = {}
    for market, (_, y) in definitions.items():
        if market in pred:
            out[market] = _binary_metrics(y, pred[market].to_numpy())
    five = actual["scheduled_seconds"].eq(1500)
    for market, seconds in (("ROUND_4_STARTS_YES", 900), ("ROUND_5_STARTS_YES", 1200)):
        if market in pred and five.any():
            out[market] = _binary_metrics((actual.loc[five, "finish_seconds"] > seconds).astype(int).to_numpy(), pred.loc[five, market].to_numpy())
    return out


@dataclass
class HistoricalTimingBundle:
    hazard_model: DiscreteTimeHazardModel
    rate_encoders: dict[str, PastOnlyRateEncoder]
    feature_columns: list[str]
    history_end: pd.Timestamp
    hazard_temperature: float = 1.0

    def _hazards(self, x_row: pd.Series, scheduled_seconds: int) -> np.ndarray:
        raw = self.hazard_model._hazards_for_one(x_row[self.feature_columns], scheduled_seconds)
        return TemperatureCalibrator(self.hazard_temperature).transform(raw)

    def market_probabilities_from_encoded(self, row: pd.Series, scheduled_seconds: int) -> dict[str, float]:
        hazards = np.clip(self._hazards(row, scheduled_seconds), 1e-9, 1 - 1e-9)
        survival = np.cumprod(1.0 - hazards)
        endpoints = np.arange(1, len(survival) + 1) * self.hazard_model.bin_seconds
        def survive(seconds: int) -> float:
            if seconds <= 0:
                return 1.0
            if seconds > scheduled_seconds:
                return 0.0
            eligible = np.flatnonzero(endpoints <= seconds)
            return 1.0 if not len(eligible) else float(survival[eligible[-1]])
        rounds = scheduled_seconds // 300
        out: dict[str, float] = {}
        thresholds = [0.5, 1.5, 2.5] + ([3.5, 4.5] if rounds == 5 else [])
        for r in thresholds:
            sec = int(round(r * 300))
            p = survive(sec)
            out[f"OVER_{r}"] = p
            out[f"UNDER_{r}"] = 1.0 - p
        gtd = survive(scheduled_seconds)
        out["GTD_YES"], out["GTD_NO"] = gtd, 1.0 - gtd
        for r in range(2, rounds + 1):
            p = survive((r - 1) * 300)
            out[f"ROUND_{r}_STARTS_YES"] = p
            out[f"ROUND_{r}_STARTS_NO"] = 1.0 - p
        return out

    def market_probabilities(self, perspective_frame: pd.DataFrame) -> pd.DataFrame:
        x = symmetric_timing_frame(perspective_frame)
        x = _encode_transform(x, self.rate_encoders)
        rows = []
        for _, row in x.iterrows():
            scheduled = int(pd.to_numeric(row.get("scheduled_rounds"), errors="coerce") * 300)
            probs = self.market_probabilities_from_encoded(row, scheduled)
            probs["fight_id"] = row["fight_id"]
            rows.append(probs)
        return pd.DataFrame(rows).set_index("fight_id")


def _fit_hazard(frame: pd.DataFrame) -> tuple[DiscreteTimeHazardModel, list[str]]:
    features = _numeric_features(frame)
    model = DiscreteTimeHazardModel(bin_seconds=30, c=0.10)
    model.fit(frame[features], frame["finish_seconds"], frame["scheduled_seconds"], frame["finish_observed"])
    return model, features


def fit_historical_timing_model(perspective_frame: pd.DataFrame, results: pd.DataFrame) -> tuple[HistoricalTimingBundle, dict[str, object]]:
    targeted = add_timing_targets(perspective_frame, results)
    work = symmetric_timing_frame(targeted)
    work = work.dropna(subset=["finish_seconds", "scheduled_seconds", "finish_observed"]).copy()
    work = work[work["scheduled_seconds"].isin([900.0, 1500.0])].copy()
    train, val, test = chronological_split(work)

    train_e, train_enc = _encode_fit(train)
    val_e = _encode_transform(val, train_enc)
    hazard_eval, features = _fit_hazard(train_e)

    # Calibrate interval hazards on validation only. Positive temperature preserves the
    # ordering of interval hazards while the survival construction keeps all props coherent.
    expanded_val, y_val = hazard_eval._expanded_rows(
        val_e[features], val_e["finish_seconds"].to_numpy(), val_e["scheduled_seconds"].to_numpy(), val_e["finish_observed"].to_numpy()
    )
    raw_hazard_val = hazard_eval.pipeline.predict_proba(expanded_val)[:, 1]
    calibrator, cal_report = fit_temperature_calibrator(y_val, raw_hazard_val)

    raw_bundle = HistoricalTimingBundle(hazard_eval, train_enc, features, pd.to_datetime(train["date"]).max(), 1.0)
    calibrated_bundle = HistoricalTimingBundle(hazard_eval, train_enc, features, pd.to_datetime(train["date"]).max(), calibrator.temperature)

    test_enc = _fit_encoders(pd.concat([train, val], ignore_index=True))
    test_e = _encode_transform(test, test_enc)
    # Evaluation model remains the train-era hazard learner; only historical rate state is
    # allowed to advance for the final test era, matching the winner-model protocol.
    raw_test_bundle = HistoricalTimingBundle(hazard_eval, test_enc, features, pd.to_datetime(test["date"]).max(), 1.0)
    cal_test_bundle = HistoricalTimingBundle(hazard_eval, test_enc, features, pd.to_datetime(test["date"]).max(), calibrator.temperature)

    metrics: dict[str, object] = {
        "validation": evaluate_timing_markets(calibrated_bundle, val_e),
        "test": evaluate_timing_markets(cal_test_bundle, test_e),
        "raw_validation": evaluate_timing_markets(raw_bundle, val_e),
        "raw_test": evaluate_timing_markets(raw_test_bundle, test_e),
        "hazard_calibration": cal_report,
        "n_train_fights": int(len(train)),
        "n_validation_fights": int(len(val)),
        "n_test_fights": int(len(test)),
    }

    full_e, final_enc = _encode_fit(work)
    final_hazard, final_features = _fit_hazard(full_e)
    bundle = HistoricalTimingBundle(
        hazard_model=final_hazard,
        rate_encoders=final_enc,
        feature_columns=final_features,
        history_end=pd.to_datetime(work["date"]).max(),
        hazard_temperature=calibrator.temperature,
    )
    return bundle, metrics


def timing_conditional_rate_tables(perspective_frame: pd.DataFrame, results: pd.DataFrame, min_n: int = 30) -> pd.DataFrame:
    from .historical_rates import all_conditional_rate_tables
    targeted = add_timing_targets(perspective_frame, results)
    work = symmetric_timing_frame(targeted).dropna(subset=["finish_observed"])
    parts = []
    for target in TIMING_TARGETS:
        t = all_conditional_rate_tables(work, specs=TIMING_SPLITS, target=target, min_n=min_n)
        if len(t):
            z = t.copy().rename(columns={"wins": "events", "win_rate": "event_rate"})
            z["outcome"] = target
            parts.append(z)
    if not parts:
        return pd.DataFrame()
    cols = ["outcome", "split", "bucket", "n", "events", "event_rate", "ci_low", "ci_high", "description"]
    return pd.concat(parts, ignore_index=True)[cols]
