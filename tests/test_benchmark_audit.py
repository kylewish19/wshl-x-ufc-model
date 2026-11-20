import pandas as pd

from wshlx_ufc.benchmark_audit import (
    BenchmarkAuditConfig,
    audit_summary,
    compare_rate_tables,
)


def test_compare_rate_tables_flags_material_mismatch():
    reproduced = pd.DataFrame(
        {
            "split": ["age_gap", "reach_gap"],
            "bucket": ["10_plus_years", "8_inches"],
            "n": [500, 90],
            "win_rate": [0.69, 0.55],
        }
    )
    published = pd.DataFrame(
        {
            "family": ["age_gap", "reach_gap"],
            "bucket": ["10_plus_years", "8_inches"],
            "target": ["win", "win"],
            "subject": ["younger_fighter", "longer_reach"],
            "rate": [0.695, 0.641],
            "n": [508, 92],
            "source_url": ["a", "b"],
            "as_of": ["2026-10-10", "2026-10-10"],
        }
    )
    audit = compare_rate_tables(
        reproduced,
        published,
        config=BenchmarkAuditConfig(absolute_tolerance=0.03, minimum_n=30),
    )
    by_family = audit.set_index("family")
    assert bool(by_family.loc["age_gap", "audit_pass"])
    assert not bool(by_family.loc["reach_gap", "audit_pass"])
    summary = audit_summary(audit)
    assert summary["matched_rows"] == 2.0
    assert summary["pass_rows"] == 1.0
