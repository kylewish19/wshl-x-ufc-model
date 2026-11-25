import hashlib,json,copy
import pytest
from wshlx_ufc.combined_research_grade import grade,CORE,VARIANTS,CHALLENGERS
from wshlx_ufc.joint_coherence_shadow import JOINT_KEYS

def fixture():
    q=dict(zip(JOINT_KEYS,[.3,.1,.2,.1,.1,.2]))
    def row(n,ids,regional):
        return {"fight_no":n,"identities":[{"regional_id":i} for i in ids],"models":{k:{"winner_p_a":.6,"coherence":{v:q.copy() for v in VARIANTS},"timing_direct":{"GTD_YES":.4}} for k in CORE},"challengers":{k:{"p_a":.6,"six_joint":q.copy()} for k in CHALLENGERS[:4 if regional else 3]},"regional_status":"ELIGIBLE" if regional else "ABSTAIN_UNRESOLVED"}
    lock={"schema":"WSHLX_REFRESHED_COMBINED_RESEARCH_V1","research_only":True,"odds_used":False,"bet_authorized":False,"event":"Synthetic test","event_date":"2026-12-05","first_fight_utc":"2026-12-05T15:00:00Z","generated_at_utc":"2026-12-04T12:00:00Z","fights":[row(1,[1,2],True),row(2,[3,4],False),row(3,[5,6],True)]}
    b=json.dumps(lock).encode()
    evidence={"sha256":hashlib.sha256(b).hexdigest(),"published_at_utc":"2026-12-04T13:00:00Z","externally_verified_by_caller":True,"evidence_url":"https://example.invalid/synthetic-test"}
    actual={"event":lock["event"],"event_date":lock["event_date"],"verified_at_utc":"2026-12-06T00:00:00Z","results_verified_by_caller":True,"fights":[{"fight_no":1,"regional_ids":[2,1],"status":"DECISIVE","winner_id":1,"method":"KO_TKO","timing_eligible":True,"went_distance":False},{"fight_no":2,"regional_ids":[3,4],"status":"DECISIVE","winner_id":4,"method":"DEC","timing_eligible":True,"went_distance":True},{"fight_no":3,"regional_ids":[5,6],"status":"NC"}]}
    return b,actual,evidence

def test_grade_paired_counts():
    b,a,e=fixture();g=grade(b,a,e)
    assert g["unique_decisive_bouts"]==2
    assert g["models"]["reference:raw"]["exact_hits"]==1
    assert g["paired_vs_reference_raw"][CHALLENGERS[-1]]["paired_fights"]==1
    assert len(g["non_gradeable"])==1 and g["timing_gtd"]["reference"]["n"]==2
    assert g["paired_vs_own_raw"]["reference:winner_aligned"]["six_log_loss_delta"]==0
    assert not g["prospective_promotion_authorized"]
def test_reject_backdated_or_changed():
    b,a,e=fixture()
    with pytest.raises(ValueError,match="proof"):grade(b+b" ",a,e)
    e["published_at_utc"]="2026-12-05T15:00:00Z"
    with pytest.raises(ValueError,match="publication"):grade(b,a,e)
def test_reject_wrong_identity_or_missing_result():
    b,a,e=fixture();a["fights"][0]["regional_ids"]=[1,99]
    with pytest.raises(ValueError,match="identity"):grade(b,a,e)
    a["fights"].pop()
    with pytest.raises(ValueError,match="results"):grade(b,a,e)
