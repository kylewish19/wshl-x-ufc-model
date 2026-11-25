"""WSHL_X Finish v1: independent, matchup-specific, research-only method learners.

Data: strictly as-of feature matrix; labels join by bout_id only for fitting
and scoring. Winner head is externally fixed to a past-only rate baseline;
at forecast time we evaluate KO/SUB/DEC for BOTH potential winning fighters.
This never alters Stage A/B, FanDuel markets or the Reference champion.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from math import log
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

METHODS=("KO_TKO","SUB","DEC")

def numeric(x,default=np.nan):
    if x is None or x=="" or x=="nan":return default
    try:
        v=float(x)
        return v if np.isfinite(v) else default
    except (TypeError,ValueError):
        return default

def rate(row,side,name):
    return numeric(row.get(side+"_"+name))

def safe(value,default=0.,bound=None):
    if not np.isfinite(value):return float(default)
    return float(np.clip(value,-bound,bound)) if bound else float(value)

def log_count(v):return float(np.log1p(max(0.,safe(v))))

def method_features(f:dict,side:str)->np.ndarray:
    """Independent predicted-fighter-relative pre-fight features.

    No actual-winner identity, target method, future opponent success,
    fabricated get-ups or present-day unlagged fighter stats can enter here.
    Numeric default encoding has explicit missingness and UFC sample flags.
    """
    if side not in ("a","b"):raise ValueError("side")
    opp="b" if side=="a" else "a"
    own=lambda field:rate(f,side,field)
    rival=lambda field:rate(f,opp,field)
    n,m=safe(own("prior_ufc_bouts")),safe(rival("prior_ufc_bouts"))
    wins,oppwins=safe(own("ufc_prior_wins")),safe(rival("ufc_prior_wins"))
    sub=safe(own("own_sub_attempts_per15"),bound=8)
    td=safe(own("own_takedowns_landed_per15"),bound=10)
    control=safe(own("own_control_generated_sec_per15"),bound=1200)
    kd=safe(own("own_knockdowns_per15"),bound=5)
    tdef=safe(rival("takedown_defense_rate_shrunk"),.58)
    sdef=safe(rival("submission_threat_nonloss_rate"),.75)
    koloss=safe(rival("ko_loss_rate_shrunk"),.12)
    subloss=safe(rival("sub_loss_rate_shrunk"),.09)
    elo=safe(own("ufc_elo_pre"),1500)
    oppelo=safe(rival("ufc_elo_pre"),1500)
    v=[
        log_count(n),log_count(m),(wins+2)/(n+4),(oppwins+2)/(m+4),
        safe(own("stats_coverage")),safe(rival("stats_coverage")),
        (elo-oppelo)/400,
        (safe(own("ufc_avg_opponent_elo_at_meeting_shrunk"),1500)-1500)/400,
        (safe(rival("ufc_avg_opponent_elo_at_meeting_shrunk"),1500)-1500)/400,
        np.log1p(sub),np.log1p(td),np.log1p(control/60),np.log1p(kd),
        np.log1p(safe(rival("knockdowns_absorbed_per15"),bound=10)),
        np.log1p(safe(rival("control_absorbed_sec_per15"),bound=1200)/60),
        tdef,sdef,koloss,subloss,
        safe(own("knockdown_nonko_survival_rate"),.5),
        safe(own("dangerous_opponent_finish_survival"),.55),
        safe(rival("dangerous_opponent_finish_survival"),.55),
        safe(rival("control_60s_nonsub_rate"),.75),
        safe(own("sub_loss_rate_shrunk"),.09),
        safe(own("takedown_defense_rate_shrunk"),.58),
        # Fighter-specific finishing-access x opponent-vulnerability interactions
        sub*(1-sdef),td*(1-tdef),control/60*(1-sdef),
        kd*koloss,sub*subloss,
        float(n<3),float(m<3),float(n==0),float(m==0),
        float(not np.isfinite(own("own_sub_attempts_per15"))),
        float(not np.isfinite(rival("own_sub_attempts_per15"))),
        float(not np.isfinite(own("own_knockdowns_per15"))),
        float(not np.isfinite(rival("knockdowns_absorbed_per15"))),
    ]
    arr=np.asarray(v,float)
    if not np.all(np.isfinite(arr)):raise ValueError("Non-finite feature vector")
    return arr

def training_rows(features:list[dict],labels:list[dict],before:str):
    byid={r["bout_id"]:r for r in labels}
    if len(byid)!=len(labels):raise ValueError("Duplicated labels")
    X,y=[],[]
    for f in features:
        if not "2021-01-01"<=f["event_date"]<before:continue
        if f["feature_as_of_exclusive"]!=f["event_date"]:raise ValueError("Not as-of")
        l=byid[f["bout_id"]]
        if l["result_status"]!="DECISIVE":continue
        if l["label_method"] not in METHODS:raise ValueError("Invalid label")
        side="a" if int(l["label_a_win"])==1 else "b"
        X.append(method_features(f,side));y.append(l["label_method"])
    return np.asarray(X),np.asarray(y)

def prior_win_probability(f:dict):
    def wr(side):
        n=safe(rate(f,side,"ufc_prior_bouts"))
        wins=safe(rate(f,side,"ufc_prior_wins"))
        return (wins+2)/(n+4)
    a,b=wr("a"),wr("b")
    return float(a/(a+b))

def elo_win_probability(f:dict):
    a=safe(rate(f,"a","ufc_elo_pre"),1500)
    b=safe(rate(f,"b","ufc_elo_pre"),1500)
    return float(1/(1+10**((b-a)/400)))

class HierarchicalFinish:
    """Method v1: P(finish|winner,x) and P(SUB|finish,winner,x).

    Training uses known winners to construct conditional outcomes. Prediction
    computes BOTH possible fighter-winner directions, never actual-winner oracle.
    """
    def fit(self,X,labels):
        y=np.asarray(labels)
        if len(y)<100:raise ValueError("Insufficient causal historical labels")
        finish=(y!="DEC").astype(int)
        sub=(y[finish==1]=="SUB").astype(int)
        if len(np.unique(finish))!=2 or len(np.unique(sub))!=2:
            raise ValueError("Both finish and submission classes required")
        pipe=lambda:make_pipeline(StandardScaler(),LogisticRegression(C=.20,max_iter=1500))
        self.finish=pipe().fit(X,finish)
        self.sub=pipe().fit(X[finish==1],sub)
        self.train_n=len(y)
        return self
    def predict(self,X):
        x=np.asarray(X,float)
        f=self.finish.predict_proba(x)[:,1]
        s=self.sub.predict_proba(x)[:,1]
        return np.column_stack([f*(1-s),f*s,1-f])

class MultinomialFinish:
    """Independent one-stage KO/SUB/DEC regularized method comparator."""
    def fit(self,X,labels):
        self.model=make_pipeline(StandardScaler(),LogisticRegression(C=.20,max_iter=1500))
        self.model.fit(X,labels)
        return self
    def predict(self,X):
        p=self.model.predict_proba(X)
        labels=list(self.model[-1].classes_)
        return p[:,[labels.index(k) for k in METHODS]]

class NonlinearFinish:
    """Small prespecified regularized nonlinear challenger; no parameter search."""
    def fit(self,X,labels):
        y=np.asarray(labels);finish=(y!="DEC").astype(int)
        sub=(y[finish==1]=="SUB").astype(int)
        if len(np.unique(finish))!=2 or len(np.unique(sub))!=2:
            raise ValueError("Insufficient method classes")
        clf=lambda leaf:HistGradientBoostingClassifier(
            max_iter=180,max_depth=3,max_leaf_nodes=7,learning_rate=.04,
            l2_regularization=15,min_samples_leaf=leaf,random_state=19)
        self.finish=clf(55).fit(X,finish)
        self.sub=clf(40).fit(X[finish==1],sub)
        return self
    def predict(self,X):
        x=np.asarray(X,float)
        f=self.finish.predict_proba(x)[:,1]
        s=self.sub.predict_proba(x)[:,1]
        return np.column_stack([f*(1-s),f*s,1-f])

def coherent_six(p_a:float,conditional)->np.ndarray:
    p=float(p_a)
    c=np.asarray(conditional,float)
    if not np.isfinite(p) or not 0<=p<=1 or c.shape!=(2,3):
        raise ValueError("Invalid winner/method forecast")
    if not np.all(np.isfinite(c)) or np.any(c<0) or np.max(np.abs(c.sum(axis=1)-1))>1e-8:
        raise ValueError("Conditional probabilities must sum to one")
    return np.r_[p*c[0],(1-p)*c[1]]

def score_six(q,true_side:int,method:str,*,p_a:float|None=None)->dict:
    """Own-selected-fighter scoring; ties go to A, never to hindsight winner."""
    probs=np.asarray(q,float)
    if probs.shape!=(6,) or method not in METHODS or true_side not in (0,1):
        raise ValueError("Invalid truth or six states")
    idx=3*true_side+METHODS.index(method)
    if abs(probs.sum()-1)>1e-8:raise ValueError("Not six-state simplex")
    p=float(probs[:3].sum()) if p_a is None else float(p_a)
    selected=0 if p>=.5 else 1
    predicted=METHODS[int(np.argmax(probs[3*selected:3*selected+3]))]
    return {
        "six_log_loss":-log(max(1e-12,float(probs[idx]))),
        "six_brier":float(np.sum((probs-np.eye(6)[idx])**2)),
        "exact":int(selected==true_side and predicted==method),
        "winner_correct":int(selected==true_side),
        "method_class_correct":int(predicted==method),
        "pred_method":predicted,"true_method":method,
        "winner_brier":(p-float(true_side==0))**2,
    }

def train_candidate_family(features,labels,before:str):
    X,y=training_rows(features,labels,before)
    counts=Counter(y)
    prior=np.array([(counts[m]+1)/(len(y)+3) for m in METHODS])
    if len(X)<100:raise ValueError("Insufficient training window")
    return {
        "prior":prior,
        "hierarchical":HierarchicalFinish().fit(X,y),
        "multinomial":MultinomialFinish().fit(X,y),
        "nonlinear":NonlinearFinish().fit(X,y),
        "train_n":len(y),
        "train_counts":dict(counts),
    }

def predict_family(f:dict,bundle:dict,*,p_a:float|None=None):
    if p_a is None:p_a=prior_win_probability(f)
    X=np.vstack([method_features(f,"a"),method_features(f,"b")])
    prior=np.stack([bundle["prior"],bundle["prior"]])
    conditional={"global_prior":prior}
    for name in ("hierarchical","multinomial","nonlinear"):
        conditional[name]=bundle[name].predict(X)
    return {name:coherent_six(p_a,cond) for name,cond in conditional.items()}

def aggregate(scored:list[dict])->dict:
    if not scored:raise ValueError("Empty evaluation cohort")
    n=len(scored)
    metrics={
        k:sum(r[k] for r in scored)/n for k in
        ("six_log_loss","six_brier","exact","winner_correct","method_class_correct","winner_brier")
    }
    metrics.update({"fights":n,"exact_hits":sum(r["exact"] for r in scored),
                    "winner_hits":sum(r["winner_correct"] for r in scored)})
    metrics["methods"]={
        method:{"actual":sum(x["true_method"]==method for x in scored),
                "predicted":sum(x["pred_method"]==method for x in scored),
                "class_hits":sum(x["true_method"]==x["pred_method"]==method for x in scored),
                "exact_hits":sum(x["true_method"]==x["pred_method"]==method and x["exact"] for x in scored)}
        for method in METHODS
    }
    return metrics
