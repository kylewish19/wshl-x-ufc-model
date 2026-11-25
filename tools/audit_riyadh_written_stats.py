"""Compare written-source claims to frozen corrected UFC input, read-only."""
import json,tempfile
from pathlib import Path
import pandas as pd
import rebuild_v027 as rb
from refit_reference_identity_corrected import source,FILES
def main():
    t=source()
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)
        for k,v in FILES.items():t[k].to_csv(p/v,index=False)
        rb.TRAINING_CUTOFF=pd.Timestamp("2026-11-22",tz="UTC")
        fights,stats,_=rb.load_fights(p)
    agg=rb.aggregate_fight_stats(fights,stats)
    targets=[
      ("2026-09-05","Pavel Andrusca","Nathaniel Wood",{"sig_landed":50,"sig_attempted":105,"opp_sig_landed":28,"td_landed":4,"td_attempted":19,"ctrl_seconds":366}),
      ("2026-07-25","Magomed Tuchalov","Brendson Ribeiro",{"sig_landed":35,"sig_attempted":80,"opp_sig_landed":39,"td_landed":8,"td_attempted":14,"ctrl_seconds":260}),
      ("2026-08-15","Islam Makhachev","Ian Machado Garry",{})]
    out=[]
    for date,name,opp,claims in targets:
        keys={rb.norm_name(name),rb.norm_name(opp)}
        rows=[f for f in fights.itertuples(index=False) if abs((f.event_date-pd.Timestamp(date,tz="UTC")).days)<=1 and {rb.norm_name(f.fighter_a),rb.norm_name(f.fighter_b)}==keys]
        if len(rows)!=1:
            out.append({"fighters":[name,opp],"status":"REVIEW_MISSING_OR_AMBIGUOUS","matches":len(rows)});continue
        f=rows[0];key=(rb.norm_text(f.event),rb.norm_text(f.bout))
        own=agg.get((*key,rb.norm_name(name)));other=agg.get((*key,rb.norm_name(opp)))
        if not own or not other:
            out.append({"fighters":[name,opp],"date":str(f.event_date.date()),"status":"UNAVAILABLE_PAIRED_STATS"});continue
        data={**own,**{"opp_"+k:v for k,v in other.items()}}
        comparisons={k:{"written":v,"archive":data[k],"match":data[k]==v} for k,v in claims.items()}
        out.append({"fighters":[name,opp],"date":str(f.event_date.date()),"status":"COMPARED","archive_stats":{k:data[k] for k in ("sig_landed","sig_attempted","opp_sig_landed","td_landed","td_attempted","ctrl_seconds","kd_for","opp_kd_for","sub_att","duration_seconds")},"comparisons":comparisons})
    print("WRITTEN_STAT_AUDIT",json.dumps({"fights":out,"archive_changed":False,"actual_predictions":0},allow_nan=False))
if __name__=="__main__":main()
