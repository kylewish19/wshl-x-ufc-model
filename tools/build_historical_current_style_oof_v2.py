#!/usr/bin/env python3
"""Run the historical current-style OOF study with symmetric winner orientation.

UFCStats result exports normally place the winner first in BOUT, so the raw reconstructed
winner rows can have winner_is_a=1 for every fight. The production winner architecture
expects matchup A/B orientation, not "winner first" orientation. For this historical
OOF diagnostic we therefore mirror every training matchup, assign the inverse target to
the mirrored row, and pair-normalize original/mirrored predictions at inference.

The large OOF builder normalizes source dates to UTC. Historical timing's normal
production path uses tz-naive dates, so this wrapper also makes its fixed model-start
cutoff UTC-aware for this diagnostic only. This changes no outcome information and is
strictly a datetime compatibility fix.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from wshlx_ufc.models import WinnerModel as CoreWinnerModel
import wshlx_ufc.historical_timing_model as historical_timing_model


def _load_base():
    path = ROOT / "tools/build_historical_current_style_oof.py"
    spec = importlib.util.spec_from_file_location("historical_oof_base", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["historical_oof_base"] = module
    spec.loader.exec_module(module)
    return module


base = _load_base()
# OOF source dates are UTC-aware; keep the timing model's fixed 2001 start cutoff
# compatible with that representation without changing the cutoff date itself.
historical_timing_model.MODEL_START_DATE = pd.Timestamp("2001-01-01", tz="UTC")


def _swap_winner_features(x: pd.DataFrame) -> pd.DataFrame:
    out = x.copy()
    src = x.copy()
    for field in base.rb.SIDE_RATE_FIELDS:
        ac, bc = f"a_{field}", f"b_{field}"
        if ac in src and bc in src:
            out[ac] = src[bc].to_numpy()
            out[bc] = src[ac].to_numpy()
        dc = f"diff_{field}"
        if dc in src:
            out[dc] = -pd.to_numeric(src[dc], errors="coerce")
    return out


def _pair_normalized_first(p_first: np.ndarray, p_mirrored_first: np.ndarray) -> np.ndarray:
    pa = np.clip(np.asarray(p_first, dtype=float), 1e-7, 1 - 1e-7)
    pb = np.clip(np.asarray(p_mirrored_first, dtype=float), 1e-7, 1 - 1e-7)
    za = np.log(pa / (1.0 - pa))
    zb = np.log(pb / (1.0 - pb))
    m = np.maximum(za, zb)
    ea, eb = np.exp(za - m), np.exp(zb - m)
    return ea / (ea + eb)


class SymmetricWinnerModel:
    """Thin adapter around the exact current WinnerModel with mirrored matchup rows."""

    def __init__(self, c: float = 0.25):
        self.c = c
        self.core = CoreWinnerModel(c=c)

    def fit(self, x: pd.DataFrame, y):
        yy = np.asarray(y, dtype=int)
        mirrored = _swap_winner_features(x)
        xx = pd.concat([x.reset_index(drop=True), mirrored.reset_index(drop=True)], ignore_index=True)
        y2 = np.concatenate([yy, 1 - yy])
        if len(np.unique(y2)) != 2:
            raise ValueError("Symmetric winner construction failed to create both target classes")
        self.core.fit(xx, y2)
        return self

    def predict_proba(self, x: pd.DataFrame) -> np.ndarray:
        pa_raw = self.core.predict_proba(x)[:, 0]
        pb_raw = self.core.predict_proba(_swap_winner_features(x))[:, 0]
        pa = _pair_normalized_first(pa_raw, pb_raw)
        return np.column_stack([pa, 1.0 - pa])


base.WinnerModel = SymmetricWinnerModel

if __name__ == "__main__":
    raise SystemExit(base.main())
