"""Forward-only six-way UFC grade and research/price gate regression tests."""
from datetime import datetime,timezone
import math
import pytest

from wshlx_ufc.forward_validation_v1 import (
    SIX,SelectionGuard,american_decimal,bucket,fanduel_price_audit,grade_one,
    grade_selected_card,pick_six,prospective_calibration_history,
    research_selection,six_probabilities,wilson_lower,
)

def six(q=(.31,.04,.05,.30,.10,.20)):
    return dict(zip(SIX,q))

def candidate(bout="a",p=(.31,.04,.05,.30,.10,.20),verified=True,provisional=False):
    return {"bout_id":bout,"model_id":"direct_paired230_v7",
        "event_date":"2026-11-21","six_joint":six(p),
        "source_identity_verified_both":verified,
        "not_an_approved_wager":True,"original_provisional":provisional}

def history(hits=0,misses=0,p=.31):
    return prospective_calibration_history([
        {"model_id":"direct_paired230_v7","event_date":"2026-11-01",
         "event_id":"older","bout_id":f"historic_{i}",
         "locked_before_event":True,"independently_verified":True,
         "selected_exact_probability":p,
         "exact_hit":int(i<hits)}
        for i in range(hits+misses)],
        model_id="direct_paired230_v7",before_event_date="2026-11-21")

def test_six_cell_probabilities_must_be_true_one_of_six():
    assert six_probabilities(six())==( .31,.04,.05,.30,.10,.20 )
    with pytest.raises(ValueError,match="exactly once"):
        six_probabilities({"A_KO":1})
    with pytest.raises(ValueError,match="sum to 1"):
        six_probabilities(six((.5,.04,.05,.30,.10,.20)))
    with pytest.raises(ValueError,match="non-finite"):
        six_probabilities(six((math.nan,.04,.05,.30,.10,.20)))

def test_winner_marginal_and_true_exact_differ_from_highest_cell():
    # B wins by sum despite A having largest individual cell.
    p=six((.31,.01,.03,.30,.21,.14))
    assert pick_six(six_probabilities(p))==3
    exact=grade_one(p,"B_SUB")
    assert exact["winner_hit"]==1
    assert exact["method_class_hit"]==0
    assert exact["exact_hit"]==0
    assert exact["six_logloss"]==pytest.approx(-math.log(.21))
    exact2=grade_one(p,"B_KO")
    assert exact2["exact_hit"]==1
    assert exact2["winner_brier"]==pytest.approx(.35**2)
    assert pick_six(six_probabilities(six((.20,.20,.10,.20,.20,.10))))<3

def test_wilson_calibration_unverified_zero_and_future_rows_rejected():
    assert wilson_lower(0,0)==0
    assert wilson_lower(50,50)<1.0
    assert wilson_lower(30,50)<.6
    with pytest.raises(ValueError,match="Impossible"):
        wilson_lower(3,2)
    with pytest.raises(ValueError,match="Future"):
        prospective_calibration_history([
            {"model_id":"direct_paired230_v7","event_date":"2026-11-22",
             "event_id":"future","bout_id":"x","locked_before_event":True,
             "independently_verified":True,"selected_exact_probability":.31,"exact_hit":1}
        ],model_id="direct_paired230_v7",before_event_date="2026-11-21")
    with pytest.raises(ValueError,match="Unverified"):
        prospective_calibration_history([
            {"model_id":"direct_paired230_v7","event_date":"2026-11-01",
             "event_id":"prior","bout_id":"x","locked_before_event":False,
             "independently_verified":True,"selected_exact_probability":.31,"exact_hit":1}
        ],model_id="direct_paired230_v7",before_event_date="2026-11-21")

def test_no_future_results_means_no_forced_two_or_five_bets():
    r=research_selection([candidate("a"),candidate("b",verified=False),
       candidate("c",provisional=True)],
       model_id="direct_paired230_v7",history=history(),event_date="2026-11-21")
    assert r["num_selected"]==0
    assert "insufficient_prior_prospective_model_grades" in r["all_reviews"][0]["reasons"]
    assert "unverified_cross_promotion_fighter_identity" in r["all_reviews"][1]["reasons"]
    assert "provisional_bout" in r["all_reviews"][2]["reasons"]
    assert r["will_not_promise_100_percent_exact"]

def test_validated_earlier_data_and_qa_can_qualify_some_not_forced_five():
    # 300+ historical independently logged exact picks in SAME probability
    # bucket, 90% correct, yields Wilson lower bound > 0.55. This is a
    # synthetic TEST ONLY, not historical UFC performance.
    h=history(300,50,p=.31)
    assert h["prospective_fights"]==350
    r=research_selection([candidate("yes"),candidate("unverified",verified=False)],
       model_id="direct_paired230_v7",history=h,event_date="2026-11-21")
    assert r["num_selected"]==1
    assert r["selected"][0]["bout_id"]=="yes"
    assert r["selected"][0]["prior_exact_reliability_wilson_lower"]>.55
    with pytest.raises(ValueError,match="Mixed-model"):
        research_selection([{**candidate(), "model_id":"different"}],
            model_id="direct_paired230_v7",history=h,event_date="2026-11-21")

def quote(odds=200,book="FanDuel",source="a"*64,
          at="2026-11-21T12:00:00+00:00",outcome="B_KO",fight="yes"):
    return {"sportsbook":book,"american_odds":odds,
            "source_sha256":source,"quoted_at_utc":at,
            "source_verified_pre_event":True,
            "evidence":"verified FanDuel screenshot archival reference",
            "outcome":outcome,"bout_id":fight}

def test_straight_price_math_breakeven_profit_and_refusal_without_independent_history():
    assert american_decimal(200)==3
    assert american_decimal(-150)==pytest.approx(1+100/150)
    with pytest.raises(ValueError):american_decimal(-50)
    h=history(300,50,p=.31)
    r=research_selection([candidate("yes")],
        model_id="direct_paired230_v7",history=h,event_date="2026-11-21")
    bet=r["selected"][0]
    # .31-sized top A cell, A winner side 40%, B side 60% -> B_KO.
    assert bet["selected_outcome"]=="B_KO"
    price=fanduel_price_audit(selected=bet,quote=quote(),
        before_event_utc="2026-11-21T15:00:00+00:00")
    assert price["status"]=="RESEARCH_PRICE_DIAGNOSTIC_ONLY"
    assert price["conservative_edge"]>0
    assert price["conservative_EV_per_1u"]>0
    assert price["official_bet_approved"] is False
    assert fanduel_price_audit(selected={**bet,"independent_eligibility":False},
        quote=quote(),before_event_utc="2026-11-21T15:00:00+00:00")["official_bet_approved"] is False

def test_prices_not_fanduel_late_or_no_match_are_rejected():
    h=history(300,50,p=.31)
    bet=research_selection([candidate("yes")],model_id="direct_paired230_v7",
        history=h,event_date="2026-11-21")["selected"][0]
    for q in (quote(book="DraftKings"),quote(source="unverified"),
              {**quote(),"source_verified_pre_event":False},
              {**quote(),"evidence":""},
              quote(at="2026-11-21T16:00:00+00:00"),
              quote(outcome="A_KO"),quote(fight="wrong")):
        p=fanduel_price_audit(selected=bet,quote=q,
                             before_event_utc="2026-11-21T15:00:00+00:00")
        assert p["status"]=="PASS_NO_VERIFIED_BET_PRICE"
        assert p["official_bet_approved"] is False

def test_selected_2_to_5_all_hit_only_when_every_decisive_result_verified():
    picks=[{"bout_id":"x","selected_outcome":"B_KO"},
           {"bout_id":"y","selected_outcome":"A_DEC"}]
    pending=grade_selected_card(picks,{"x":"B_KO"})
    assert pending["perfect_group"] is False and pending["pending"]==1
    perfect=grade_selected_card(picks,{"x":"B_KO","y":"A_DEC"})
    assert perfect["perfect_group"] is True and perfect["wins"]==2
    lost=grade_selected_card(picks,{"x":"B_KO","y":"B_DEC"})
    assert lost["perfect_group"] is False and lost["losses"]==1
    void=grade_selected_card(picks,{"x":"B_KO","y":"VOID"})
    assert void["perfect_group"] is False
    with pytest.raises(ValueError):grade_selected_card(picks,{"x":"not verified"})


def test_cannot_count_six_bet_group_as_two_to_five_perfect():
    bets=[{"bout_id":str(i),"selected_outcome":"A_KO"} for i in range(6)]
    with pytest.raises(ValueError,match="exceeds five"):
        grade_selected_card(bets,{str(i):"A_KO" for i in range(6)})
