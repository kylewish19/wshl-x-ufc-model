"""Reconstruct UFC pre-fight state from UFCStats-compatible CSV exports."""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Mapping
import numpy as np
import pandas as pd
import requests

SOURCE_URLS={
 "events":"https://raw.githubusercontent.com/Greco1899/scrape_ufc_stats/main/ufc_event_details.csv",
 "results":"https://raw.githubusercontent.com/Greco1899/scrape_ufc_stats/main/ufc_fight_results.csv",
 "stats":"https://raw.githubusercontent.com/Greco1899/scrape_ufc_stats/main/ufc_fight_stats.csv",
 "fighters":"https://raw.githubusercontent.com/Greco1899/scrape_ufc_stats/main/ufc_fighter_tott.csv"}
SOURCE_FILENAMES={"events":"ufc_event_details.csv","results":"ufc_fight_results.csv","stats":"ufc_fight_stats.csv","fighters":"ufc_fighter_tott.csv"}

def download_source_files(out_dir,timeout=60):
    root=Path(out_dir);root.mkdir(parents=True,exist_ok=True);out={}
    for n,u in SOURCE_URLS.items():
        r=requests.get(u,timeout=timeout,headers={"User-Agent":"wshlx-ufc-historical-model/1.0"});r.raise_for_status();p=root/SOURCE_FILENAMES[n];p.write_bytes(r.content);out[n]=p
    return out

def load_source_files(root):
    root=Path(root);return {n:pd.read_csv(root/f,low_memory=False) for n,f in SOURCE_FILENAMES.items()}

def txt(x): return "" if pd.isna(x) else re.sub(r"\s+"," ",str(x)).strip()
def col(df,*names):
    # Prefer an exact header first. Only use punctuation/spacing normalization when
    # it maps to exactly one source column. This prevents collisions such as
    # SIG.STR. vs SIG.STR. % and TD vs TD % while still accepting TIME_FORMAT vs
    # TIME FORMAT and SUB ATT vs SUB.ATT variants.
    exact={str(c).strip().upper():c for c in df.columns}
    for n in names:
        key=str(n).strip().upper()
        if key in exact:return exact[key]
    norm=lambda x: re.sub(r"[^A-Z0-9]+","",str(x).upper())
    by_norm=defaultdict(list)
    for c in df.columns:by_norm[norm(c)].append(c)
    for n in names:
        matches=by_norm.get(norm(n),[])
        if len(matches)==1:return matches[0]
    return None
def bout(x):
    s=txt(x)
    for t in (" vs. "," vs "," v. "," v "):
        if t in s:
            a,b=s.split(t,1);return (a.strip(),b.strip()) if a.strip() and b.strip() else None
    return None
def outcome(x):
    p=[q for q in re.split(r"[/|,-]",txt(x).upper().replace(" ","")) if q]
    if len(p)<2:return None
    def n(q): return "W" if q.startswith("W") else "L" if q.startswith("L") else "D" if q.startswith("D") else "NC" if "NC" in q else q
    return n(p[0]),n(p[1])
def num(x):
    s=txt(x).replace("%","")
    try:return float(s)
    except ValueError:
        m=re.search(r"-?\d+(?:\.\d+)?",s);return float(m.group()) if m else 0.
def of(x):
    m=re.search(r"(-?\d+(?:\.\d+)?)\s+of\s+(-?\d+(?:\.\d+)?)",txt(x).lower())
    return (float(m.group(1)),float(m.group(2))) if m else (num(x),num(x)) if txt(x) not in {"","--"} else (0.,0.)
def secs(x):
    m=re.fullmatch(r"(\d+):(\d{1,2})",txt(x));return float(int(m.group(1))*60+int(m.group(2))) if m else num(x)
def height(x):
    s=txt(x);m=re.search(r"(\d+)\s*'\s*(\d+)",s)
    if m:return float(int(m.group(1))*12+int(m.group(2)))
    m=re.search(r"\d+(?:\.\d+)?",s);return float(m.group()) if m else np.nan
def inches(x):
    m=re.search(r"\d+(?:\.\d+)?",txt(x));return float(m.group()) if m else np.nan
def dates(s): return pd.to_datetime(s,errors="coerce",format="mixed")
def rounds(tf,wc):
    m=re.search(r"([1-9])\s*rnd",txt(tf).lower()) or re.match(r"([1-9])",txt(tf));return int(m.group(1)) if m else 5 if "title" in txt(wc).lower() else 3
def duration(r,t): return max(1/60,((int(num(r) or 1)-1)*300+secs(t))/60)
def method(x):
    s=txt(x).upper();return "KO_TKO" if "KO" in s else "SUB" if "SUB" in s else "DEC" if "DEC" in s else "DRAW" if "DRAW" in s else "NC" if "NC" in s else "OTHER"

def normalize_events(df):
    e,d,l=col(df,"EVENT"),col(df,"DATE"),col(df,"LOCATION")
    if e is None or d is None:raise ValueError("events CSV needs EVENT and DATE")
    return pd.DataFrame({"event":df[e].map(txt),"date":dates(df[d]),"location":df[l].map(txt) if l else ""}).drop_duplicates("event",keep="last")
def normalize_fighters(df):
    f=col(df,"FIGHTER");h=col(df,"HEIGHT");r=col(df,"REACH");s=col(df,"STANCE");d=col(df,"DOB")
    if f is None:raise ValueError("fighter CSV needs FIGHTER")
    o=pd.DataFrame({"fighter":df[f].map(txt)});o["height"]=df[h].map(height) if h else np.nan;o["reach"]=df[r].map(inches) if r else np.nan;o["stance"]=df[s].map(txt) if s else "";o["dob"]=dates(df[d]) if d else pd.NaT
    return o.drop_duplicates("fighter",keep="last")

def aggregate_fight_stats(df):
    e,b,f=col(df,"EVENT"),col(df,"BOUT"),col(df,"FIGHTER")
    if None in (e,b,f):return {}
    C={n:col(df,n) for n in ("KD","SIG.STR.","TOTAL STR.","TD","SUB ATT","SUB.ATT","CTRL")};sub=C["SUB ATT"] or C["SUB.ATT"];out={}
    for _,r in df.iterrows():
        k=(txt(r[e]),txt(r[b]),txt(r[f]));a=out.setdefault(k,defaultdict(float))
        if C["KD"]:a["kd"]+=num(r[C["KD"]])
        for src,x,y in (("SIG.STR.","sig_landed","sig_attempted"),("TOTAL STR.","total_landed","total_attempted"),("TD","td_landed","td_attempted")):
            if C[src]:u,v=of(r[C[src]]);a[x]+=u;a[y]+=v
        if sub:a["sub_att"]+=num(r[sub])
        if C["CTRL"]:a["ctrl_sec"]+=secs(r[C["CTRL"]])
    return out

@dataclass
class State:
    fights:int=0;wins:int=0;losses:int=0;draws:int=0;streak:int=0;last_date:pd.Timestamp|None=None
    recent:list[int]=field(default_factory=list);t:dict[str,float]=field(default_factory=lambda:defaultdict(float))
    five:int=0;title:int=0;stat_fights:int=0;finish_wins:int=0;ko_wins:int=0;sub_wins:int=0;dec_wins:int=0;ko_losses:int=0;sub_losses:int=0;dec_losses:int=0
    def snap(self,date):
        t=self.t;m=t["minutes"];dec=self.wins+self.losses+self.draws;r3=self.recent[-3:];r5=self.recent[-5:]
        q=lambda a,b: a/b if b else np.nan
        return {"ufc_fights":float(self.fights),"ufc_win_pct":q(self.wins,dec),"recent3_win_pct":q(sum(r3),len(r3)),"recent5_win_pct":q(sum(r5),len(r5)),"streak":float(self.streak),"layoff_days":float((date-self.last_date).days) if self.last_date is not None else np.nan,
         "slpm":q(t["sig_landed"],m),"sapm":q(t["sig_absorbed"],m),"sig_accuracy":q(t["sig_landed"],t["sig_attempted"]),"sig_defense":1-q(t["sig_absorbed"],t["sig_faced"]) if t["sig_faced"] else np.nan,
         "td_per15":15*q(t["td_landed"],m) if m else np.nan,"td_accuracy":q(t["td_landed"],t["td_attempted"]),"td_defense":1-q(t["td_absorbed"],t["td_faced"]) if t["td_faced"] else np.nan,
         "sub_att_per15":15*q(t["sub_att"],m) if m else np.nan,"kd_per15":15*q(t["kd"],m) if m else np.nan,"ctrl_sec_per_min":q(t["ctrl_sec"],m),"finish_win_rate":q(self.finish_wins,self.wins),"ko_win_rate":q(self.ko_wins,self.wins),"sub_win_rate":q(self.sub_wins,self.wins),"decision_win_rate":q(self.dec_wins,self.wins),"ko_loss_rate":q(self.ko_losses,self.losses),"sub_loss_rate":q(self.sub_losses,self.losses),"decision_loss_rate":q(self.dec_losses,self.losses),"five_round_fights":float(self.five),"title_fights":float(self.title),"stat_fights":float(self.stat_fights),"stats_coverage":q(self.stat_fights,self.fights)}

def physical(p,date):
    if p is None:return {"age":np.nan,"height":np.nan,"reach":np.nan,"stance":"Unknown"}
    dob=p.get("dob",pd.NaT);return {"age":float((date-dob).days/365.2425) if pd.notna(dob) else np.nan,"height":p.get("height",np.nan),"reach":p.get("reach",np.nan),"stance":txt(p.get("stance")) or "Unknown"}
def diff(a,b):
    a,b=pd.to_numeric(pd.Series([a,b]),errors="coerce");return float(a-b) if pd.notna(a) and pd.notna(b) else np.nan
METRICS=("age","height","reach","ufc_fights","ufc_win_pct","recent3_win_pct","recent5_win_pct","streak","layoff_days","slpm","sapm","sig_accuracy","sig_defense","td_per15","td_accuracy","td_defense","sub_att_per15","kd_per15","ctrl_sec_per_min","finish_win_rate","ko_win_rate","sub_win_rate","decision_win_rate","ko_loss_rate","sub_loss_rate","decision_loss_rate","five_round_fights","title_fights","stat_fights","stats_coverage")
def perspective(base,f,o,A,B,w,prev):
    r=dict(base,fighter=f,opponent=o,win=int(w),stance=A.get("stance","Unknown"),opp_stance=B.get("stance","Unknown"),previous_meeting_result=prev);r["stance_matchup"]=f"{r['stance'].title()}_vs_{r['opp_stance'].title()}"
    for n in METRICS:r[n]=A.get(n,np.nan);r[f"opp_{n}"]=B.get(n,np.nan);r[f"{n}_diff"]=diff(A.get(n),B.get(n))
    r["sig_str_diff"]=diff(r["slpm"],r["sapm"]);r["sig_str_diff_diff"]=diff(r["sig_str_diff"],diff(r["opp_slpm"],r["opp_sapm"]))
    r["debut_status"]="debutant_vs_veteran" if r["ufc_fights"]==0<r["opp_ufc_fights"] else "veteran_vs_debutant" if r["opp_ufc_fights"]==0<r["ufc_fights"] else "both_debutants" if r["ufc_fights"]==r["opp_ufc_fights"]==0 else "both_veterans"
    def status(x,y):return "experienced_vs_first_timer" if x>0==y else "first_timer_vs_experienced" if y>0==x else "both_experienced" if x>0 and y>0 else "both_first_timers"
    r["five_round_exp_status"]=status(r["five_round_fights"],r["opp_five_round_fights"]);r["title_exp_status"]=status(r["title_fights"],r["opp_title_fights"])
    def prof(x):return "unknown" if pd.isna(x) else "finish_heavy" if x>=2/3 else "decision_heavy" if x<=1/3 else "mixed"
    r["finish_profile_matchup"]=f"{prof(r['finish_win_rate'])}_vs_{prof(r['opp_finish_win_rate'])}";return r

def build_prefight_perspective_rows(events,results,stats,fighters):
    E=normalize_events(events).set_index("event");P=normalize_fighters(fighters).set_index("fighter").to_dict("index");FS=aggregate_fight_stats(stats)
    ec,bc,oc=col(results,"EVENT"),col(results,"BOUT"),col(results,"OUTCOME")
    if None in (ec,bc,oc):raise ValueError("results CSV needs EVENT BOUT OUTCOME")
    wc,mc,rc,tc,tfc=col(results,"WEIGHTCLASS"),col(results,"METHOD"),col(results,"ROUND"),col(results,"TIME"),col(results,"TIME_FORMAT","TIME FORMAT");F=[]
    for i,x in results.iterrows():
        ev,b=txt(x[ec]),txt(x[bc]);p,q=bout(b),outcome(x[oc])
        if p is None or q is None or ev not in E.index:continue
        d=pd.to_datetime(E.at[ev,"date"],errors="coerce")
        if pd.isna(d):continue
        F.append({"i":i,"event":ev,"bout":b,"date":d,"a":p[0],"b":p[1],"oa":q[0],"ob":q[1],"wc":txt(x[wc]) if wc else "","method":txt(x[mc]) if mc else "","round":x[rc] if rc else 1,"time":x[tc] if tc else "0:00","tf":txt(x[tfc]) if tfc else ""})
    states=defaultdict(State);pairs=defaultdict(list);rows=[]
    for x in sorted(F,key=lambda z:(z["date"],z["i"])):
        d,a,b=x["date"],x["a"],x["b"];sa,sb=states[a],states[b];A={**physical(P.get(a),d),**sa.snap(d)};B={**physical(P.get(b),d),**sb.snap(d)};pk=tuple(sorted((a,b)));hist=pairs[pk];prev=hist[-1] if hist else None
        pa="win" if prev==a else "loss" if prev==b else "none" if prev is None else "draw_or_nc";pb="loss" if pa=="win" else "win" if pa=="loss" else pa
        R=rounds(x["tf"],x["wc"]);title=int("title" in x["wc"].lower());fid=f"{d.date()}::{x['event']}::{a}::{b}";base={"fight_id":fid,"date":d,"event":x["event"],"weight_class":x["wc"],"scheduled_rounds":R,"title_fight":title,"rematch_number":len(hist),"fight_method":method(x["method"])};dec={x["oa"],x["ob"]}=={"W","L"}
        if dec:
            aw=int(x["oa"]=="W");rows += [perspective(base,a,b,A,B,aw,pa),perspective(base,b,a,B,A,1-aw,pb)]
        dur=duration(x["round"],x["time"]);AS=FS.get((x["event"],x["bout"],a),{});BS=FS.get((x["event"],x["bout"],b),{});mg=method(x["method"])
        def upd(s,res,own,opp):
            s.fights+=1;s.last_date=d;s.five+=int(R>=5);s.title+=title;t=s.t
            if own or opp:
                s.stat_fights+=1;t["minutes"]+=dur
            for k in ("sig_landed","sig_attempted","td_landed","td_attempted","kd","sub_att","ctrl_sec"):t[k]+=own.get(k,0.)
            t["sig_absorbed"]+=opp.get("sig_landed",0.);t["sig_faced"]+=opp.get("sig_attempted",0.);t["td_absorbed"]+=opp.get("td_landed",0.);t["td_faced"]+=opp.get("td_attempted",0.)
            if res=="W":
                s.wins+=1;s.recent.append(1);s.streak=s.streak+1 if s.streak>0 else 1;s.finish_wins+=mg in {"KO_TKO","SUB"};s.ko_wins+=mg=="KO_TKO";s.sub_wins+=mg=="SUB";s.dec_wins+=mg=="DEC"
            elif res=="L":
                s.losses+=1;s.recent.append(0);s.streak=s.streak-1 if s.streak<0 else -1;s.ko_losses+=mg=="KO_TKO";s.sub_losses+=mg=="SUB";s.dec_losses+=mg=="DEC"
            elif res in {"D","NC"}:
                if res=="D":s.draws+=1
                s.streak=0
            s.recent=s.recent[-10:]
        upd(sa,x["oa"],AS,BS);upd(sb,x["ob"],BS,AS);pairs[pk].append(a if dec and x["oa"]=="W" else b if dec else "draw_or_nc")
    return pd.DataFrame(rows).sort_values(["date","fight_id","fighter"],kind="stable").reset_index(drop=True) if rows else pd.DataFrame()

def build_from_directory(root):
    s=load_source_files(root);return build_prefight_perspective_rows(s["events"],s["results"],s["stats"],s["fighters"])
