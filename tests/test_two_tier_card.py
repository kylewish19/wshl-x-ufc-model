"""Non-negotiable WSHL_X Top5 +200 and Top5 -150..+190 regressions."""
from __future__ import annotations

from copy import deepcopy

import pytest

from wshlx_ufc.two_tier_card import (
    LONGSHOTS, BEST_BETS, break_even, expected_value, fight_key, grade_two_tier,
    select_two_tier, tier_for_odds,
)

EVENT = "UFC Fight Night: Example"
DATE = "2026-11-07"
SHA = "a" * 64
NOW = "2026-11-06T17:00:00Z"
QUOTE = "2026-11-06T15:00:00-00:00"


def frozen_fights(n=14):
    return [{"a": f"Fighter A{i}", "b": f"Fighter B{i}"} for i in range(n)]


def candidate(i, odds, cid=None, prob=.75, conservative=.65, gates=None):
    return {
        "candidate_id": cid or f"cand-{i}-{odds}",
        "fighter_a": f"Fighter A{i}",
        "fighter_b": f"Fighter B{i}",
        "market": f"Fighter A{i} ML",
        "market_family": "moneyline",
        "american_odds": odds,
        "model_probability": prob,
        "conservative_probability": conservative,
        "evidence_quality": .80,
        "stake_units": .25,
        "sportsbook": "FanDuel",
        "quoted_at_utc": QUOTE,
        "researched_before_start": True,
        "gates": gates or {
            "stage_a_supported": True,
            "research": True,
            "price": True,
            "calibration": True,
            "market_family": True,
        }
    }


def select(candidates, fights=None):
    return select_two_tier(
        event=EVENT, event_date=DATE, stage_a_sha256=SHA,
        candidates=candidates,
        verified_stage_a_fights=fights if fights is not None else frozen_fights(),
        generated_at_utc=NOW,
    )


@pytest.mark.parametrize("odds,category", [
    (-500, None), (-151, None), (-150, BEST_BETS), (-140, BEST_BETS),
    (-100, BEST_BETS), (100, BEST_BETS), (190, BEST_BETS),
    (191, None), (195, None), (199, None),
    (200, LONGSHOTS), (201, LONGSHOTS), (800, LONGSHOTS)
])
def test_exact_requested_american_odds_bands(odds, category):
    assert tier_for_odds(odds) == category


@pytest.mark.parametrize("bad", [-99, 0, 99, 190.5, "200", None, True])
def test_invalid_american_odds_fail_closed(bad):
    with pytest.raises(ValueError):
        tier_for_odds(bad)


def test_breakeven_and_profit_arithmetic():
    assert break_even(200) == pytest.approx(1/3)
    assert break_even(-150) == pytest.approx(.6)
    assert expected_value(200, .40) == pytest.approx(.20)
    assert expected_value(-150, .65) == pytest.approx(1/12)


def test_max_five_each_and_no_fight_in_both_categories():
    candidates = [candidate(i, 200, conservative=.65) for i in range(7)]
    candidates += [candidate(i, 150, cid=f"best-{i}", conservative=.65) for i in range(7)]
    # Seven different longshots plus seven competing best bets from SAME fights
    # cannot yield 14 rows or both categories for any one fighter pair.
    candidates += [candidate(7+i, -110, cid=f"extra-{i}", conservative=.70) for i in range(7)]
    card = select(candidates)
    a, b = card["selected"][LONGSHOTS], card["selected"][BEST_BETS]
    assert len(a) <= 5 and len(b) <= 5
    assert len(a) == 5
    assert len(b) == 5
    keys = [x["fight_key"] for x in a+b]
    assert len(keys) == len(set(keys)) == 10
    assert sum(x["fight_key"] in {z["fight_key"] for z in b} for x in a) == 0
    assert card["no_overlap"]
    assert card["selected_total"] == 10
    assert len(card["rejected"]) == len(candidates)-10


def test_one_fight_across_tiers_global_value_ranking_not_alphabetical():
    long = candidate(0, 200, cid="long", conservative=.40, prob=.55)
    best = candidate(0, 190, cid="best", conservative=.70, prob=.75)
    card = select([long, best])
    # +190 at 70% conservative probability has much higher EV than +200 at 40%.
    assert card["selected"][LONGSHOTS] == []
    assert [x["candidate_id"] for x in card["selected"][BEST_BETS]] == ["best"]
    assert card["rejected"][0]["reasons"] == ["fight_already_selected_in_a_top5_tier"]


def test_both_categories_may_have_fewer_than_five_or_zero():
    card = select([candidate(0, 200, conservative=.50), candidate(1, -140, conservative=.70)])
    assert card["counts"] == {LONGSHOTS: 1, BEST_BETS: 1}
    assert select([])["counts"] == {LONGSHOTS: 0, BEST_BETS: 0}


def test_no_qualifying_edge_means_pass_not_forced_pick():
    weak = candidate(0, 200, conservative=.20, prob=.51)
    gap = candidate(1, 195, conservative=.80, prob=.90)
    gates = candidate(2, -110, conservative=.70, gates={
        "stage_a_supported": True, "research": True, "price": True,
        "calibration": True, "market_family": False,
    })
    card = select([weak, gap, gates])
    assert card["selected_total"] == 0
    assert any("no_positive_conservative_value" in x["reasons"] for x in card["rejected"])
    assert any("outside_requested_odds_tiers" in x["reasons"] for x in card["rejected"])
    assert any("failed_market_family_gate" in x["reasons"] for x in card["rejected"])


@pytest.mark.parametrize("change", [
    {"sportsbook": "BetMGM"},
    {"conservative_probability": .95},
    {"quoted_at_utc": "2026-11-06T20:00:00Z"},
    {"quoted_at_utc": "2026-11-06T15:00:00"},
    {"researched_before_start": False},
    {"gates": {"research": True}},
    {"model_probability": float("nan")},
    {"evidence_quality": -1},
    {"market_family": "fantasy"},
    {"stake_units": 0},
])
def test_unverified_or_malformed_market_refused(change):
    c = candidate(0, 200)
    c.update(change)
    with pytest.raises(ValueError):
        select([c])


def test_forbid_missing_or_duplicate_ids_or_unknown_bouts():
    with pytest.raises(ValueError):
        select([candidate(0, 200, cid="same"), candidate(1, 200, cid="same")])
    with pytest.raises(ValueError):
        select([candidate(15, 200)])
    with pytest.raises(ValueError):
        select([candidate(0, 200)], fights=[])


def test_one_bet_per_fight_even_with_two_longshots():
    a = candidate(0, 200, cid="ko", conservative=.52)
    a["market_family"] = "method"
    a["market"] = "Fighter A0 by KO/TKO"
    b = candidate(0, 300, cid="ml", conservative=.65)
    card = select([a, b])
    assert card["selected_total"] == 1
    assert len(card["rejected"]) == 1


def test_grade_each_category_separately_with_correct_pnl_and_roi():
    long = candidate(0, 200, cid="long", conservative=.40, prob=.75)
    best = candidate(1, -150, cid="best", conservative=.70)
    other = candidate(2, 300, cid="pending", conservative=.40, prob=.75)
    card = select([long, best, other])
    grade = grade_two_tier(card, {"long": "W", "best": "L"})
    assert grade["combined"]["W"] == 1
    assert grade["combined"]["L"] == 1
    assert grade["combined"]["PENDING"] == 1
    l = grade["categories"][LONGSHOTS]
    b = grade["categories"][BEST_BETS]
    assert l["record"] == {"W": 1, "L": 0, "PUSH": 0, "VOID": 0, "PENDING": 1}
    assert b["record"] == {"W": 0, "L": 1, "PUSH": 0, "VOID": 0, "PENDING": 0}
    assert l["pnl_units"] == pytest.approx(.5)
    assert b["pnl_units"] == pytest.approx(-.25)
    assert l["settled_risk_units"] == pytest.approx(.25)
    assert b["settled_risk_units"] == pytest.approx(.25)
    assert grade["combined"]["pnl_units"] == pytest.approx(.25)
    assert grade["combined"]["settled_risk_units"] == pytest.approx(.5)
    assert grade["combined"]["roi"] == pytest.approx(.5)


def test_push_void_and_pending_not_counted_as_losses_or_exposure():
    card = select([
        candidate(0, 200, cid="push"), candidate(1, -110, cid="void"),
        candidate(2, 300, cid="pending")
    ])
    g = grade_two_tier(card, {"push": "PUSH", "void": "VOID"})
    assert g["combined"]["settled_risk_units"] == 0
    assert g["combined"]["pnl_units"] == 0
    assert g["combined"]["roi"] is None
    assert g["combined"]["PENDING"] == 1


def test_cannot_add_unselected_grade_or_reuse_a_fight_by_tampering():
    card = select([candidate(0, 200)])
    with pytest.raises(ValueError):
        grade_two_tier(card, {"not_selected": "W"})
    hacked = deepcopy(card)
    hacked["selected"][BEST_BETS].append(deepcopy(hacked["selected"][LONGSHOTS][0]))
    with pytest.raises(ValueError):
        grade_two_tier(hacked, {})


def test_fighter_key_ignores_order_and_minor_punctuation():
    assert fight_key("José Souza", "Jonny Parsons") == fight_key("Jonny Parsons", "Jose Souza")
    with pytest.raises(ValueError):
        fight_key("X", "X")
