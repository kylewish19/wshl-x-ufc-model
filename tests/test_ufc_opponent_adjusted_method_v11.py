from datetime import date
import numpy as np
from wshlx_ufc.opponent_adjusted_method_v11 import fresh,observed,update,rates,vec,build,PRIOR

def stats(kd=0,sub=0,td=0,ctrl=0):
    return {"kd":kd,"sub_att":sub,"td_landed":td,"ctrl_sec":ctrl}

def row(day,a,b,method="KO_TKO",res=("W","L")):
    return {"date":date.fromisoformat(day),"event":"test","a":a,"b":b,
            "method":method,"result":res,"stats_a":stats(kd=1),"stats_b":stats()}

def test_missing_stats_only_outcome_rates_updated():
    a=fresh();v=observed("W","SUB",None)
    update(a,v,observed("L","SUB",None),rates(fresh()),1500)
    assert a["n"][0].tolist()==[1,1,0,0,0]
    assert a["hits"][0,1]==1
    assert a["residual"][0,1]>0

def test_same_day_outcomes_frozen_and_two_directions():
    rows=[row("2025-01-01","A","B"),row("2025-01-01","A","C"),row("2025-01-02","A","D")]
    out,_=build(rows)
    a=out[("2025-01-01","test","A","B")][2]
    b=out[("2025-01-01","test","A","C")][2]
    c=out[("2025-01-02","test","A","D")][2]
    assert len(a)==45 and np.allclose(a,b)
    assert np.allclose(a[-5:],PRIOR)
    assert c[0]>0 and c[10]>0
    changed=rows[:2]+[row("2025-01-02","A","D","SUB",("L","W"))]
    assert np.array_equal(c,build(changed)[0][("2025-01-02","test","A","D")][2])

def test_opposition_weight_uses_prior_rating_and_defensive_exposure():
    a,b=fresh(),fresh()
    own=observed("W","KO_TKO",stats(kd=1))
    other=observed("L","KO_TKO",stats())
    update(a,own,other,rates(fresh()),1700)
    update(b,own,other,rates(fresh()),1300)
    assert vec(a)[0]>vec(b)[0]
    assert a["n"][0,0]==b["n"][0,0]==1
    # Opponent whose pre-bout history already shows KO vulnerability
    # yields a smaller positive KO residual for the same observed KO.
    vulnerable=rates(fresh());vulnerable[1,0]=.70
    c=fresh();update(c,own,other,vulnerable,1700)
    assert vec(c)[0]<vec(a)[0]

def test_strict_source_does_not_turn_unknown_or_duplicate_into_zero(tmp_path):
    from wshlx_ufc.opponent_adjusted_method_v11 import strict_access_totals
    # Fighter A has a missing submission count. Fighter B's duplicate
    # round rows are ambiguous and must be excluded, not summed.
    (tmp_path/"ufc_fight_stats.csv").write_text(
        "EVENT,BOUT,FIGHTER,ROUND,KD,SUB ATT,TD,CTRL\n"
        "test,A vs. B,A,Round 1,0,--,1 of 2,0:30\n"
        "test,A vs. B,B,Round 1,0,0,0 of 1,0:00\n"
        "test,A vs. B,B,Round 1,0,0,0 of 1,0:00\n")
    r=row("2025-01-01","A","B")
    r["elapsed_seconds"]=280.0
    output,audit=strict_access_totals([r],root=tmp_path)
    assert output[0]["stats_a"]["kd"]==0
    assert output[0]["stats_a"]["sub_att"] is None
    assert output[0]["stats_a"]["td_landed"]==1
    assert output[0]["stats_a"]["ctrl_sec"]==30
    assert all(v is None for v in output[0]["stats_b"].values())
    assert audit["raw_duplicate_round_keys_excluded"]==1
    assert audit["strict_missing_fighter_field_totals"]==5
