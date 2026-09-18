from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def rounds_to_seconds(rounds: float) -> int:
    """Convert sportsbook round threshold to elapsed fight seconds.

    Examples:
      O0.5 -> survive beyond 150 seconds
      O1.5 -> survive beyond 450 seconds
      O2.5 -> survive beyond 750 seconds
    """
    if rounds < 0:
        raise ValueError("rounds must be nonnegative")
    return int(round(rounds * 300))


@dataclass
class DiscreteTimeHazardModel:
    """Discrete-time survival model for UFC fight duration.

    The model estimates the conditional probability of a fight ending in each
    small time bin given that it has survived to the start of that bin. This
    yields a single coherent survival curve from which O/U rounds, GTD, and
    round-start probabilities are derived.

    Decisions are treated as right-censored at the scheduled fight duration,
    not as a special artificial finish at 15:00/25:00.
    """

    bin_seconds: int = 30
    c: float = 0.10

    def __post_init__(self) -> None:
        if self.bin_seconds <= 0 or 300 % self.bin_seconds != 0:
            raise ValueError("bin_seconds must be a positive divisor of 300")
        self.pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        C=self.c,
                        solver="lbfgs",
                        max_iter=5000,
                        class_weight=None,
                        random_state=19,
                    ),
                ),
            ]
        )
        self.base_feature_names_: list[str] | None = None

    def _expanded_rows(
        self,
        x: pd.DataFrame,
        durations_seconds: np.ndarray,
        scheduled_seconds: np.ndarray,
        event_observed: np.ndarray,
    ) -> tuple[pd.DataFrame, np.ndarray]:
        rows: list[dict[str, float]] = []
        labels: list[int] = []

        for row_i, (_, feature_row) in enumerate(x.iterrows()):
            duration = float(durations_seconds[row_i])
            scheduled = int(scheduled_seconds[row_i])
            observed = int(event_observed[row_i])

            if scheduled not in (900, 1500):
                raise ValueError("scheduled_seconds must be 900 or 1500")
            if not (0 < duration <= scheduled):
                raise ValueError("duration must be within (0, scheduled_seconds]")
            if observed not in (0, 1):
                raise ValueError("event_observed must contain only 0/1")
            if observed == 0 and duration < scheduled:
                raise ValueError("censored fights must extend to scheduled duration")

            n_bins = int(np.ceil(scheduled / self.bin_seconds))
            for bin_i in range(n_bins):
                start = bin_i * self.bin_seconds
                end = min((bin_i + 1) * self.bin_seconds, scheduled)
                if start >= duration:
                    break

                record = {k: float(v) if pd.notna(v) else np.nan for k, v in feature_row.items()}
                record["time_elapsed_fraction"] = start / scheduled
                record["time_elapsed_rounds"] = start / 300.0
                record["scheduled_five_round"] = float(scheduled == 1500)
                rows.append(record)

                ended_here = observed == 1 and start < duration <= end
                labels.append(int(ended_here))
                if ended_here:
                    break

        expanded = pd.DataFrame(rows)
        y = np.asarray(labels, dtype=int)
        return expanded, y

    def fit(
        self,
        x: pd.DataFrame,
        durations_seconds,
        scheduled_seconds,
        event_observed,
    ) -> "DiscreteTimeHazardModel":
        self.base_feature_names_ = list(x.columns)
        expanded, y = self._expanded_rows(
            x,
            np.asarray(durations_seconds, dtype=float),
            np.asarray(scheduled_seconds, dtype=int),
            np.asarray(event_observed, dtype=int),
        )
        if len(np.unique(y)) < 2:
            raise ValueError("Hazard model requires both finish and survival intervals.")
        self.pipeline.fit(expanded, y)
        return self

    def _hazards_for_one(self, x_row: pd.Series, scheduled_seconds: int) -> np.ndarray:
        if scheduled_seconds not in (900, 1500):
            raise ValueError("scheduled_seconds must be 900 or 1500")

        records = []
        n_bins = scheduled_seconds // self.bin_seconds
        for bin_i in range(n_bins):
            start = bin_i * self.bin_seconds
            record = {k: float(v) if pd.notna(v) else np.nan for k, v in x_row.items()}
            record["time_elapsed_fraction"] = start / scheduled_seconds
            record["time_elapsed_rounds"] = start / 300.0
            record["scheduled_five_round"] = float(scheduled_seconds == 1500)
            records.append(record)

        frame = pd.DataFrame(records)
        return self.pipeline.predict_proba(frame)[:, 1]

    def survival_curve(self, x_row: pd.Series, scheduled_seconds: int) -> pd.Series:
        hazards = np.clip(
            self._hazards_for_one(x_row, scheduled_seconds),
            1e-9,
            1 - 1e-9,
        )
        survival = np.cumprod(1.0 - hazards)
        endpoints = np.arange(1, len(survival) + 1) * self.bin_seconds
        return pd.Series(survival, index=endpoints, name="survival")

    def survival_at(self, x_row: pd.Series, scheduled_seconds: int, seconds: int) -> float:
        if seconds <= 0:
            return 1.0
        if seconds > scheduled_seconds:
            return 0.0
        curve = self.survival_curve(x_row, scheduled_seconds)
        eligible = curve.index[curve.index <= seconds]
        if len(eligible) == 0:
            return 1.0
        return float(curve.loc[eligible[-1]])

    def market_probabilities(
        self,
        x_row: pd.Series,
        scheduled_seconds: int,
    ) -> dict[str, float]:
        scheduled_rounds = scheduled_seconds // 300
        out: dict[str, float] = {}

        thresholds = [0.5, 1.5, 2.5]
        if scheduled_rounds == 5:
            thresholds += [3.5, 4.5]

        for r in thresholds:
            p_over = self.survival_at(x_row, scheduled_seconds, rounds_to_seconds(r))
            out[f"OVER_{r}"] = p_over
            out[f"UNDER_{r}"] = 1.0 - p_over

        p_gtd = self.survival_at(x_row, scheduled_seconds, scheduled_seconds)
        out["GTD_YES"] = p_gtd
        out["GTD_NO"] = 1.0 - p_gtd

        for round_no in range(2, scheduled_rounds + 1):
            start_seconds = (round_no - 1) * 300
            out[f"ROUND_{round_no}_STARTS_YES"] = self.survival_at(
                x_row, scheduled_seconds, start_seconds
            )
            out[f"ROUND_{round_no}_STARTS_NO"] = 1.0 - out[
                f"ROUND_{round_no}_STARTS_YES"
            ]

        return out
