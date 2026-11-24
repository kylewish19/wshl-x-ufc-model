"""UFC Qatar official result identity, outcome and distinct frozen score tests."""
import importlib.util
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("ufcqatar_grade_runner",ROOT/"tools/grade_ufcqatar_2026_11_21_frozen_models.py")
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

def source():
    sources=[g.read(z) for z in (g.LOCK,g.COH,g.V3,g.V4,g.V5,g.V7)]
    result=g.read(g.SOURCE)
    return sources,result

def test_exact_original_and_all_later_immutable_shas_valid():
    (o,c,v3,v4,v5,v7),res=source()
    checks=g.valid_card(o,c,v3,v4,v5,v7)
    assert all(checks.values())
    assert len(res["fights"])==12
    assert res["fights"][0]["winner"]=="Diyar Nurgozhay"
    assert res["fights"][3]["method"]=="SUB"
    assert res["fights"][7]["winner"]=="Kyoji Horiguchi"
    assert res["fights"][11]["winner"]=="John Mitchell"

def test_six_state_fighter_and_method_must_both_match():
    p={"winner":"Athlete A","method":"DEC","cohort":"TEST","joint":None}
    actual={"winner":"Athlete A","method":"SUB"}
    a=g.grade_prediction(p,actual,"Athlete A")
    assert a["winner_hit"]==1 and a["method_class_hit"]==0 and a["exact_hit"]==0
    wrong=g.grade_prediction(p,{"winner":"Athlete B","method":"DEC"},"Athlete A")
    assert wrong["winner_hit"]==0 and wrong["method_class_hit"]==1 and wrong["exact_hit"]==0
    with pytest.raises(ValueError,match="Incoherent"):
        g.probs({"A_KO":1.1,"A_SUB":0,"A_DEC":0,"B_KO":0,"B_SUB":0,"B_DEC":0})

def test_same_verified_matches_original_and_coherent_research_variants():
    (o,c,v3,v4,v5,v7),truth=source()
    rows=[]
    for i,(f,actual) in enumerate(zip(o["fights"],truth["fights"])):
        assert {actual["winner"],actual["loser"]}=={f["a"],f["b"]}
        pred=g.get_pred(i,o,c,v3,v4,v5,v7)
        grades={k:g.grade_prediction(x,actual,f["a"]) for k,x in pred.items()}
        rows.append({"models":grades})
    out=g.summarize(rows)
    expected={
        "reference":(11,4),
        "historical":(10,5),
        "unified":(11,3),
        "coherent_reference_aligned":(11,7),
        "coherent_historical_aligned":(10,5),
        "coherent_unified_aligned":(11,7),
        "winner_v3_primary":(8,3),
        "winner_v4_primary":(9,4),
        "method_v5_primary":(8,5),
        "direct_six_v7_primary":(8,5),
    }
    assert len(expected)==10
    assert {k:(v["winner_hits"],v["exact_hits"]) for k,v in out.items()}==expected
    assert all(v["exact_hits"]<=v["winner_hits"]<=12 for v in out.values())
    # Coherent is a 6-state method postprocessor, not another independent
    # vote for the winner: original winner accuracy must remain the same.
    assert out["reference"]["winner_hits"]==out["coherent_reference_aligned"]["winner_hits"]
    assert out["unified"]["winner_hits"]==out["coherent_unified_aligned"]["winner_hits"]

def test_public_double_chance_distance_and_timing_are_not_exact_single_methods():
    (o,*_),res=source()
    hits=sum(g.public_grade(i,x)["hit"] for i,x in enumerate(res["fights"]))
    assert hits==6
    assert g.public_grade(1,res["fights"][1])["hit"]==1  # Mar Fan DEC in KO/DEC
    assert g.public_grade(5,res["fights"][5])["hit"]==1  # fight goes distance
    assert g.public_grade(8,res["fights"][8])["hit"]==1  # Hooker DEC in KO/DEC
    assert g.public_grade(3,res["fights"][3])["hit"]==0  # Albazi submission
    assert all(g.timing_grade(o["fights"][i],res["fights"][i])["hit"] in (0,1) for i in range(12))
