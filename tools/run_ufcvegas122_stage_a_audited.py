from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "ufcvegas122_stage_a_base", ROOT / "tools/run_ufcvegas122_stage_a.py"
)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["ufcvegas122_stage_a_base"] = mod
spec.loader.exec_module(mod)

# Current public UFC profile facts used only to repair verified missing/stale
# statics before the odds-blind lock. No sportsbook prices are used.
PROFILE_OVERRIDES = {
    "Allen Frye Jr.": {"height_inches": 77.0, "reach_inches": 80.5},
    "Felipe Franco": {"height_inches": 73.5, "reach_inches": 77.0},
    "Leon Shahbazyan": {"height_inches": 76.0, "reach_inches": 77.0},
    "Kai Kamaka III": {"age_years": 31.0, "height_inches": 67.0, "reach_inches": 69.0},
}

# Kai's current UFC display name carries the III suffix while older UFCStats
# history can be stored as Kai Kamaka. Merge the older/current identity before
# feature construction so his 2020-21 UFC bouts are not dropped.
mod.HISTORY_ALIASES["kaikamakaiii"] = "kaikamaka"

_original_summary = mod.rb.summarize_history


def audited_summary(name, history, static, asof):
    out = _original_summary(name, history, static, asof)
    for key, value in PROFILE_OVERRIDES.get(name, {}).items():
        out[key] = float(value)
    return out


mod.rb.summarize_history = audited_summary

if __name__ == "__main__":
    mod.main()
