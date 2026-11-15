"""Regression tests for UFC334 scoring and repeated finish class bias."""
import hashlib
import json
from pathlib import Path

from wshlx_ufc.finish_class_diagnostics import compare_cards, inspect_card

ROOT = Path(__file__).resolve().parents[1]
GRADE = ROOT / "data/results/ufc334_2026-11-14_all_models_grading.json"
PREV = ROOT / "data/results/ufcvegas124_2026-11-07_all_models_grading.json"
A = ROOT / "data/locks/ufc334_2026-11-14/stage_a_final_selection.json"
RAW = ROOT / "data/locks/ufc334_2026-11-14/stage_a_model_raw_three_view.json"
PRICES = ROOT / "data/locks/ufc334_2026-11-14/stage_b_all_334_fanduel_prices_audit.json"
RESULTS = ROOT / "data/results/ufc334_2026-11-14_verified_outcomes.json"
WATCH = ROOT / "data/locks/ufc334_2026-11-14/stage_b_top5_ranked_research_review_compatible_cross_tier.json"


def data(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_ufc334_results_still_link_to_original_odds_blind_locks():
    a, raw, grade, outcomes = [data(x) for x in (A, RAW, GRADE, RESULTS)]
    assert a["stage_a_frozen"] is True and a["odds_used"] is False
    assert raw["odds_used"] is False
    assert a["raw_model_sha256"] == sha(RAW) == grade["original_raw_sha256"]
    assert sha(A) == grade["original_stage_a_sha256"]
    assert sha(PRICES) == grade["original_stage_b_sha256"]
    assert sha(WATCH) == grade["original_frozen_research_watchlist_sha256"]
    assert outcomes["status"] == "VERIFIED_POST_EVENT_OUTCOMES"
    assert grade["model_or_stage_a_b_changed"] is False
    assert len(grade["fights"]) == len(outcomes["fights"]) == 13
    assert len({f["fight_no"] for f in outcomes["fights"]}) == 13
    assert grade["stage_b_research_only"]["official_approved_stakes"] == 0
    assert grade["stage_b_research_only"]["official_betting_roi"] is None
    assert grade["post_card_official_full_fight_stats_imported"] is False


def test_ufc334_regrade_every_winner_method_and_primary_timing():
    grade, a, outcomes = data(GRADE), data(A), data(RESULTS)
    index = {r["fight_no"]: r for r in outcomes["fights"]}
    correct_winners = correct_exact = correct_timing = 0
    decisive = 0
    for f, frozen in zip(grade["fights"], a["fights"]):
        y = index[f["fight_no"]]
        assert f["fight_no"] == frozen["fight_no"] and y["a"] == frozen["a"]
        assert f["actual"]["method"] == y["method"]
        assert f["models"]["reference"]["fighter"] == frozen["official_reference_pick"]
        ref_method = frozen["method"]["primary_method_forecast_for_grade"]["reference"].replace("/TKO", "")
        assert f["models"]["reference"]["method"] == ref_method
        if y["method"] != "DRAW":
            decisive += 1
            side_correct = f["models"]["reference"]["fighter"] == y["winner"]
            exact = side_correct and ref_method == y["method"]
            assert (f["models"]["reference"]["winner_result"] == "W") == side_correct
            assert f["models"]["reference"]["exact_fighter_method_correct"] == exact
            correct_winners += side_correct
            correct_exact += exact
        else:
            assert y["winner"] is None
            assert f["models"]["reference"]["winner_result"] == "D"
            assert f["models"]["reference"]["exact_fighter_method_correct"] is None
        assert f["timing"]["original"]["market"] == frozen["primary_timing_forecast"]["market_key"]
        if f["timing"]["original"]["result"] == "W":
            correct_timing += 1
    assert (decisive, correct_winners, correct_exact, correct_timing) == (12,8,1,9)


def test_no_wagers_in_fanduel_original_and_hypothetical_units_are_correct():
    audit, grade = data(PRICES), data(GRADE)
    assert audit["completeness"]["quotes"] == 334
    assert audit["completeness"]["modeled_quotes"] == 310
    assert audit["official_approved_card"]["number_official_wagers"] == 0
    shadow = grade["stage_b_research_only"]
    best = shadow["categories"]["top_5_best_bets"]
    longshots = shadow["categories"]["top_5_longshots"]
    assert (best["W"],best["L"]) == (3,2)
    assert (longshots["W"],longshots["L"]) == (1,4)
    assert abs(best["units_virtual_net"]-1.449672)<1e-5
    assert abs(longshots["units_virtual_net"]-(-1.15))<1e-7
    assert abs(shadow["combined"]["virtual_net_units"]-0.299672)<1e-5
    assert all(not r["official_bet"] for tier in shadow["categories"].values()
               for r in tier["selections"])


def test_two_cards_expose_repeated_top_method_label_finish_bias():
    old, current = data(PREV), data(GRADE)
    one, two = inspect_card(old), inspect_card(current)
    assert one["decisive_fights"] == 14
    assert two["decisive_fights"] == 12
    assert one["predicted_leading_methods"] == {"KO":10,"SUB":1,"DEC":3}
    assert one["actual_methods"] == {"KO":6,"SUB":1,"DEC":7}
    assert two["predicted_leading_methods"] == {"KO":11,"SUB":1,"DEC":0}
    assert two["actual_methods"] == {"KO":3,"SUB":2,"DEC":7}
    both = compare_cards(old,current)
    assert both["combined_decisive_fights"] == 26
    assert both["combined_reference_winner_correct"] == 17
    assert both["combined_reference_exact_fighter_method_correct"] == 6
    assert both["combined_predicted_method_counts"] == {"KO":21,"SUB":2,"DEC":3}
    assert both["combined_actual_method_counts"] == {"KO":9,"SUB":3,"DEC":14}
    assert both["repeat_KO_leading_method_excess"]
    assert both["repeat_decision_leading_method_shortfall"]
    assert both["model_version_changed"] is False



def test_full_334_quote_shadow_audit_never_counts_unmodeled_draw_or_placed_bets():
    all_quotes = data(ROOT / "data/results/ufc334_2026-11-14_all_334_fanduel_markets_settlement_diagnostic.json")
    assert all_quotes["quotes"] == 334
    assert all_quotes["original_modeled_quotes"] == 310
    assert all_quotes["original_unmodeled_draw_quotes"] == 24
    assert all_quotes["settlements"] == {
        "W": 108, "L": 185, "UNMODELED_DRAW_QUOTE": 24,
        "UNRESOLVED_DRAW_BOOK_RULE": 17,
    }
    assert sum(all_quotes["settlements"].values()) == 334
    assert sum(x["settled"] for x in all_quotes["family_diagnostics"].values()) == 293
    assert all_quotes["governance"]["all_334_markets_were_unapproved"] is True
    assert all_quotes["governance"]["real_money_staked"] == 0
    assert all_quotes["governance"]["official_roi"] is None
    assert len(all_quotes["per_quote_diagnostic"]) == 334
    assert all(not row["approved_official"] for row in all_quotes["per_quote_diagnostic"])
    positive_ev = all_quotes["raw_positive_EV_candidate_summaries"]
    assert (positive_ev["n"], positive_ev["W"], positive_ev["L"]) == (127, 43, 84)
    assert abs(positive_ev["mean_model_p"] - 0.443782) < 1e-6
