"""Leakage-safe UFC conditional win-rate tables and historical-rate features."""
from __future__ import annotations
from dataclasses import dataclass
from math import sqrt
from typing import Sequence
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class SplitSpec:
    name: str; column: str; edges: tuple[float, ...]; labels: tuple[str, ...]; description: str = ""
    def bucket(self, s: pd.Series) -> pd.Series:
        if len(self.labels) != len(self.edges)-1: raise ValueError(f"{self.name}: bad labels")
        return pd.cut(pd.to_numeric(s,errors="coerce"),list(self.edges),labels=list(self.labels),include_lowest=True,right=False).astype("string")

def S(n,c,e,l,d=""): return SplitSpec(n,c,tuple(e),tuple(l),d or n.replace("_"," "))
I=np.inf
DEFAULT_SPLITS: tuple[SplitSpec,...] = (
 S("age_gap","age_diff",[-I,-10,-8,-6,-4,-2,2,4,6,8,10,I],["younger_10+","younger_8_10","younger_6_8","younger_4_6","younger_2_4","within_2","older_2_4","older_4_6","older_6_8","older_8_10","older_10+"]),
 S("reach_gap","reach_diff",[-I,-7,-5,-3,-1,1,3,5,7,I],["shorter_7+","shorter_5_7","shorter_3_5","shorter_1_3","within_1","longer_1_3","longer_3_5","longer_5_7","longer_7+"]),
 S("height_gap","height_diff",[-I,-5,-3,-1,1,3,5,I],["shorter_5+","shorter_3_5","shorter_1_3","within_1","taller_1_3","taller_3_5","taller_5+"]),
 S("ufc_experience_gap","ufc_fights_diff",[-I,-10,-5,-2,0,1,3,6,11,I],["10+_fewer","5_9_fewer","2_4_fewer","1_fewer","equal","1_2_more","3_5_more","6_10_more","11+_more"]),
 S("ufc_win_pct_gap","ufc_win_pct_diff",[-I,-.30,-.15,-.05,.05,.15,.30,I],["30pp+_worse","15_30pp_worse","5_15pp_worse","within_5pp","5_15pp_better","15_30pp_better","30pp+_better"]),
 S("recent5_gap","recent5_win_pct_diff",[-I,-.50,-.25,-.05,.05,.25,.50,I],["50pp+_worse","25_50pp_worse","5_25pp_worse","within_5pp","5_25pp_better","25_50pp_better","50pp+_better"]),
 S("layoff_gap","layoff_days_diff",[-I,-365,-180,-60,60,180,365,I],["365d+_more_active","180_365d_more_active","60_180d_more_active","within_60d","60_180d_longer","180_365d_longer","365d+_longer"]),
 S("sig_strike_diff_gap","sig_str_diff_diff",[-I,-2,-1,-.5,.5,1,2,I],["2+_worse","1_2_worse","0.5_1_worse","within_0.5","0.5_1_better","1_2_better","2+_better"]),
 S("sig_accuracy_gap","sig_accuracy_diff",[-I,-.15,-.08,-.03,.03,.08,.15,I],["15pp+_worse","8_15pp_worse","3_8pp_worse","within_3pp","3_8pp_better","8_15pp_better","15pp+_better"]),
 S("sig_defense_gap","sig_defense_diff",[-I,-.15,-.08,-.03,.03,.08,.15,I],["15pp+_worse","8_15pp_worse","3_8pp_worse","within_3pp","3_8pp_better","8_15pp_better","15pp+_better"]),
 S("td_rate_gap","td_per15_diff",[-I,-3,-1.5,-.5,.5,1.5,3,I],["3+_worse","1.5_3_worse","0.5_1.5_worse","within_0.5","0.5_1.5_better","1.5_3_better","3+_better"]),
 S("td_accuracy_gap","td_accuracy_diff",[-I,-.20,-.10,-.04,.04,.10,.20,I],["20pp+_worse","10_20pp_worse","4_10pp_worse","within_4pp","4_10pp_better","10_20pp_better","20pp+_better"]),
 S("td_defense_gap","td_defense_diff",[-I,-.20,-.10,-.04,.04,.10,.20,I],["20pp+_worse","10_20pp_worse","4_10pp_worse","within_4pp","4_10pp_better","10_20pp_better","20pp+_better"]),
 S("control_gap","ctrl_sec_per_min_diff",[-I,-30,-15,-5,5,15,30,I],["30s+_worse","15_30s_worse","5_15s_worse","within_5s","5_15s_better","15_30s_better","30s+_better"]),
 S("knockdown_gap","kd_per15_diff",[-I,-1,-.5,-.15,.15,.5,1,I],["1+_worse","0.5_1_worse","0.15_0.5_worse","within_0.15","0.15_0.5_better","0.5_1_better","1+_better"]),
 S("finish_win_rate_gap","finish_win_rate_diff",[-I,-.40,-.20,-.05,.05,.20,.40,I],["40pp+_lower","20_40pp_lower","5_20pp_lower","within_5pp","5_20pp_higher","20_40pp_higher","40pp+_higher"]),
 S("ko_loss_rate_gap","ko_loss_rate_diff",[-I,-.30,-.15,-.05,.05,.15,.30,I],["30pp+_less_vulnerable","15_30pp_less","5_15pp_less","within_5pp","5_15pp_more","15_30pp_more","30pp+_more"]),
 S("age_level","age",[-I,26,29,31,33,35,40,I],["under_26","26_28","29_30","31_32","33_34","35_39","40+"]),
 S("ufc_experience_level","ufc_fights",[-.5,.5,3,6,11,21,I],["debut","1_2","3_5","6_10","11_20","21+"]),
 S("streak_level","streak",[-I,-2.5,-.5,.5,2.5,3.5,5.5,I],["losing_3+","losing_1_2","no_streak","winning_1_2","winning_3","winning_4_5","winning_6+"]),
 S("layoff_level","layoff_days",[-I,90,180,365,450,540,730,1095,I],["under_90d","90_179d","180_364d","12_14mo","15_17mo","18_23mo","2_3yr","3yr+"]),
 S("slpm_level","slpm",[-I,2,3,4,5,6,I],["under_2","2_3","3_4","4_5","5_6","6+"]),
 S("sapm_level","sapm",[-I,2.3,2.9,3.3,3.8,4.5,I],["under_2.3","2.3_2.9","2.9_3.3","3.3_3.8","3.8_4.5","4.5+"]),
 S("sig_accuracy_level","sig_accuracy",[-I,.38,.42,.45,.48,.52,I],["under_38","38_42","42_45","45_48","48_52","52+"]),
 S("sig_defense_level","sig_defense",[-I,.45,.52,.58,.64,.70,I],["under_45","45_52","52_58","58_64","64_70","70+"]),
 S("td_per15_level","td_per15",[-I,.4,.8,1.2,1.8,2.7,I],["under_0.4","0.4_0.8","0.8_1.2","1.2_1.8","1.8_2.7","2.7+"]),
 S("td_accuracy_level","td_accuracy",[-I,.20,.30,.40,.50,.60,I],["under_20","20_30","30_40","40_50","50_60","60+"]),
 S("td_defense_level","td_defense",[-I,.44,.55,.63,.70,.78,I],["under_44","44_55","55_63","63_70","70_78","78+"]),
 S("sub_att_level","sub_att_per15",[-I,.1,.4,.8,1.5,I],["under_0.1","0.1_0.4","0.4_0.8","0.8_1.5","1.5+"]),
 S("kd_level","kd_per15",[-I,.1,.3,.6,1,I],["under_0.1","0.1_0.3","0.3_0.6","0.6_1.0","1.0+"]),
 S("control_level","ctrl_sec_per_min",[-I,5,15,30,45,I],["under_5s","5_15s","15_30s","30_45s","45s+"]),
 S("finish_win_rate_level","finish_win_rate",[-I,1/3,.5,2/3,.85,I],["decision_heavy","33_50","50_67","67_85","85+"]),
 S("ko_loss_rate_level","ko_loss_rate",[-I,.1,.25,.5,.75,I],["under_10","10_25","25_50","50_75","75+"]),
 S("sub_loss_rate_level","sub_loss_rate",[-I,.1,.25,.5,.75,I],["under_10","10_25","25_50","50_75","75+"]),
 S("five_round_experience_level","five_round_fights",[-.5,.5,1.5,3.5,6.5,I],["0","1","2_3","4_6","7+"]),
 S("title_experience_level","title_fights",[-.5,.5,1.5,3.5,6.5,I],["0","1","2_3","4_6","7+"]),
)
DEFAULT_CATEGORICAL_SPLITS=("debut_status","previous_meeting_result","five_round_exp_status","title_exp_status","stance_matchup","finish_profile_matchup","weight_class","scheduled_rounds","title_fight","rematch_number")
DEFAULT_INTERACTIONS=(("age_gap","ufc_experience_gap"),("age_gap","layoff_gap"),("age_gap","ko_loss_rate_gap"),("reach_gap","sig_strike_diff_gap"),("td_rate_gap","td_defense_gap"),("finish_win_rate_gap","ko_loss_rate_gap"),("stance_matchup","reach_gap"),("weight_class","finish_profile_matchup"),("scheduled_rounds","five_round_exp_status"),("title_fight","title_exp_status"),("previous_meeting_result","rematch_number"))

def wilson_interval(wins,n,z=1.96):
    if n<=0:return np.nan,np.nan
    p=wins/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return max(0,c-h),min(1,c+h)

def _finish_table(g,split,desc):
    g=g.rename(columns={"count":"n","sum":"wins"}); g["win_rate"]=g.wins/g.n
    ci=[wilson_interval(float(w),float(n)) for w,n in zip(g.wins,g.n)]; g["ci_low"]=[x[0] for x in ci]; g["ci_high"]=[x[1] for x in ci]
    g.insert(0,"split",split); g["description"]=desc
    return g[["split","bucket","n","wins","win_rate","ci_low","ci_high","description"]]

def conditional_rate_table(frame,spec,target="win",min_n=1):
    if spec.column not in frame:return pd.DataFrame()
    w=pd.DataFrame({"bucket":spec.bucket(frame[spec.column]),"win":pd.to_numeric(frame[target],errors="coerce")}).dropna()
    g=w.groupby("bucket",observed=True).win.agg(["count","sum"]).reset_index(); g=g[g["count"]>=min_n]
    return _finish_table(g,spec.name,spec.description) if len(g) else pd.DataFrame()

def all_conditional_rate_tables(frame,specs=DEFAULT_SPLITS,target="win",min_n=20):
    t=[conditional_rate_table(frame,s,target,min_n) for s in specs]; t=[x for x in t if len(x)]
    return pd.concat(t,ignore_index=True) if t else pd.DataFrame()

def categorical_conditional_rate_tables(frame,columns=DEFAULT_CATEGORICAL_SPLITS,target="win",min_n=20):
    out=[]
    for c in columns:
        if c not in frame:continue
        w=pd.DataFrame({"bucket":frame[c].astype("string"),"win":pd.to_numeric(frame[target],errors="coerce")}).dropna()
        g=w.groupby("bucket",observed=True).win.agg(["count","sum"]).reset_index(); g=g[g["count"]>=min_n]
        if len(g):out.append(_finish_table(g,c,f"Categorical conditional win rate for {c}."))
    return pd.concat(out,ignore_index=True) if out else pd.DataFrame()

def interaction_conditional_rate_tables(frame,interactions=DEFAULT_INTERACTIONS,target="win",min_n=30):
    sm={s.name:s for s in DEFAULT_SPLITS}; out=[]
    def vals(k):
        if k in sm and sm[k].column in frame:return sm[k].bucket(frame[sm[k].column])
        return frame[k].astype("string") if k in frame else None
    for a,b in interactions:
        av,bv=vals(a),vals(b)
        if av is None or bv is None:continue
        w=pd.DataFrame({"bucket":av.astype("string")+" | "+bv.astype("string"),"win":pd.to_numeric(frame[target],errors="coerce")}).dropna()
        g=w.groupby("bucket",observed=True).win.agg(["count","sum"]).reset_index(); g=g[g["count"]>=min_n]
        if len(g):out.append(_finish_table(g,f"{a}__x__{b}",f"Two-way conditional win rate: {a} x {b}."))
    return pd.concat(out,ignore_index=True) if out else pd.DataFrame()

def comprehensive_conditional_rate_tables(frame,min_n=20):
    parts=[all_conditional_rate_tables(frame,min_n=min_n),categorical_conditional_rate_tables(frame,min_n=min_n),interaction_conditional_rate_tables(frame,min_n=max(30,min_n))]
    parts=[p for p in parts if len(p)]; return pd.concat(parts,ignore_index=True) if parts else pd.DataFrame()

class PastOnlyRateEncoder:
    """Smoothed bucket rates using only history from earlier fight dates."""
    def __init__(self,specs=DEFAULT_SPLITS,alpha=10.,prior=.5): self.specs=tuple(specs);self.alpha=float(alpha);self.prior=float(prior);self._n={};self._w={}
    def _rate(self,name,b):
        if pd.isna(b):return self.prior,0.
        k=(name,str(b));n=self._n.get(k,0.);w=self._w.get(k,0.);d=n+self.alpha
        return (self.prior if d<=0 else (w+self.alpha*self.prior)/d),n
    def _buckets(self,f): return {s.name:s.bucket(f[s.column]) for s in self.specs if s.column in f}
    def fit_transform(self,frame,date_col="date",fight_id_col="fight_id",target="win"):
        o=frame.copy();o[date_col]=pd.to_datetime(o[date_col],errors="coerce");o=o.sort_values([date_col,fight_id_col],kind="stable");bs=self._buckets(o)
        vals={f"hist_{n}_wr":pd.Series(index=o.index,dtype=float) for n in bs}; ns={f"hist_{n}_n":pd.Series(index=o.index,dtype=float) for n in bs}
        # Score an entire event date before ingesting any outcomes from that date.
        # This matches our pre-card lock workflow and prevents same-card leakage.
        for _,idx in o.groupby(date_col,sort=False,dropna=False).groups.items():
            idx=list(idx)
            for n,s in bs.items():
                for i in idx: vals[f"hist_{n}_wr"].loc[i],ns[f"hist_{n}_n"].loc[i]=self._rate(n,s.loc[i])
            for n,s in bs.items():
                for i in idx:
                    b,y=s.loc[i],o.at[i,target]
                    if pd.isna(b) or pd.isna(y):continue
                    k=(n,str(b));self._n[k]=self._n.get(k,0)+1;self._w[k]=self._w.get(k,0)+float(y)
        for k,v in {**vals,**ns}.items():o[k]=v
        return o
    def fit(self,frame,target="win"):
        for n,s in self._buckets(frame).items():
            for b,y in zip(s,pd.to_numeric(frame[target],errors="coerce")):
                if pd.isna(b) or pd.isna(y):continue
                k=(n,str(b));self._n[k]=self._n.get(k,0)+1;self._w[k]=self._w.get(k,0)+float(y)
        return self
    def transform(self,frame):
        o=frame.copy()
        for n,s in self._buckets(o).items():
            x=[self._rate(n,b) for b in s];o[f"hist_{n}_wr"]=[v[0] for v in x];o[f"hist_{n}_n"]=[v[1] for v in x]
        return o

def add_interaction_features(frame):
    o=frame.copy()
    for new,a,b in (("age_x_layoff","age_diff","layoff_days_diff"),("age_x_ko_vulnerability","age_diff","ko_loss_rate_diff"),("reach_x_sig_str_diff","reach_diff","sig_str_diff_diff"),("td_offense_x_td_defense","td_per15_diff","td_defense_diff"),("control_x_td_defense","ctrl_sec_per_min_diff","td_defense_diff"),("experience_x_age","ufc_fights_diff","age_diff"),("finish_x_ko_vulnerability","finish_win_rate_diff","ko_loss_rate_diff")):
        if a in o and b in o:o[new]=pd.to_numeric(o[a],errors="coerce")*pd.to_numeric(o[b],errors="coerce")
    return o
