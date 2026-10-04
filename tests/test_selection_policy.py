from wshlx_ufc.selection_policy import (
    evidence_adjusted_confidence,
    method_bet_gate,
    research_override_gate,
    timing_bet_gate,
    timing_stake_cap,
)


def test_sparse_sample_caps_lock_level_confidence():
    # Gable Steveson entered UFC 331 with only one prior UFC bout.
    assert evidence_adjusted_confidence(8.6, 1, 2) == 7.5
    # Gandra/Diaz had small samples, but the original 7.4 does not need a cut.
    assert evidence_adjusted_confidence(7.4, 2, 3) == 7.4


def test_research_override_requires_coinflip_or_missing_data():
    # Aswell 59% -> Yoo flip should be blocked; research can downgrade/pass.
    d = research_override_gate(
        flips_raw_model_side=True,
        raw_favorite_probability=0.5903,
        material_data_omission=False,
    )
    assert not d.eligible

    # Menifield 53.9% -> Iwo flip is no longer treated as a coinflip.
    d = research_override_gate(
        flips_raw_model_side=True,
        raw_favorite_probability=0.5388,
        material_data_omission=False,
    )
    assert not d.eligible

    # Tuivasa/Despaigne was essentially 50/50 and also had verified omitted
    # post-UFC evidence, so the override remains allowed.
    d = research_override_gate(
        flips_raw_model_side=True,
        raw_favorite_probability=0.5037,
        material_data_omission=True,
    )
    assert d.eligible


def test_method_gate_keeps_gandra_but_blocks_despaigne_and_sparse_steveson():
    gandra = method_bet_gate(
        winner_probability=0.7240,
        exact_joint_method_probability=0.4015,
        conditional_method_probability=0.5546,
        baseline_top_method="KO",
        shadow_top_method="KO",
        fighter_a_prior_ufc_bouts=2,
        fighter_b_prior_ufc_bouts=3,
    )
    assert gandra.eligible

    despaigne = method_bet_gate(
        winner_probability=0.4963,
        exact_joint_method_probability=0.2822,
        conditional_method_probability=0.5686,
        baseline_top_method="KO",
        shadow_top_method="KO",
        fighter_a_prior_ufc_bouts=18,
        fighter_b_prior_ufc_bouts=3,
    )
    assert not despaigne.eligible

    steveson = method_bet_gate(
        winner_probability=0.8987,
        exact_joint_method_probability=0.608,
        conditional_method_probability=0.6763,
        baseline_top_method="KO",
        shadow_top_method="KO",
        fighter_a_prior_ufc_bouts=1,
        fighter_b_prior_ufc_bouts=2,
    )
    assert not steveson.eligible


def test_timing_gate_rejects_ufc331_small_edges():
    # Arman/Ruffy O2.5: 60.0% model vs 51.9% break-even.
    assert not timing_bet_gate(
        model_probability=0.6000,
        market_break_even_probability=0.5192,
    ).eligible

    # Brito/Chikadze R3 starts: 61.6% vs 51.0%.
    assert not timing_bet_gate(
        model_probability=0.6160,
        market_break_even_probability=0.5098,
    ).eligible

    # A materially larger edge can still qualify with adequate UFC evidence.
    assert timing_bet_gate(
        model_probability=0.70,
        market_break_even_probability=0.55,
        fighter_a_prior_ufc_bouts=5,
        fighter_b_prior_ufc_bouts=6,
    ).eligible


def test_timing_gate_blocks_sparse_ufc332_false_edges():
    # Wint/Armand O1.5 showed a huge mechanical edge but the matchup was
    # one prior UFC bout versus a debutant. It remains model-only.
    d = timing_bet_gate(
        model_probability=0.7045,
        market_break_even_probability=0.3571,
        fighter_a_prior_ufc_bouts=1,
        fighter_b_prior_ufc_bouts=0,
    )
    assert not d.eligible
    assert "sparse_ufc_sample_blocks_timing_promotion" in d.reasons

    # Normal evidence density can still pass the same 12-point gate.
    d = timing_bet_gate(
        model_probability=0.6380,
        market_break_even_probability=0.4673,
        fighter_a_prior_ufc_bouts=24,
        fighter_b_prior_ufc_bouts=7,
    )
    assert d.eligible


def test_timing_stake_probation_caps_exposure():
    # Official timing wagers are 0-4 across UFC 331 and UFC 332.
    assert timing_stake_cap(
        requested_units=0.75,
        graded_official_timing_bets=4,
        timing_pnl_units=-2.75,
    ) == 0.25

    # Once the probation sample is reached and cumulative timing P/L is no
    # longer negative, the requested stake is allowed.
    assert timing_stake_cap(
        requested_units=0.75,
        graded_official_timing_bets=20,
        timing_pnl_units=1.0,
    ) == 0.75
