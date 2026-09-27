from __future__ import annotations

import hashlib, json, urllib.request
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
UPSTREAM_REPO="Greco1899/scrape_ufc_stats"
UPSTREAM_COMMIT="b93901a2ab58d7c9880797451c7ef0ef5e03ce1a"
EVENT="UFC Fight Night: Rosas Jr. vs. Barcelos"
OUT=ROOT/"data/raw/ufcvegas121_2026-09-26"
FILES=["ufc_event_details.csv","ufc_fight_results.csv","ufc_fight_stats.csv","ufc_fighter_tott.csv"]

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    receipt={}
    for name in FILES:
        url=f"https://raw.githubusercontent.com/{UPSTREAM_REPO}/{UPSTREAM_COMMIT}/{name}"
        path=OUT/name
        urllib.request.urlretrieve(url,path)
        receipt[name]={"bytes":path.stat().st_size,"sha256":sha256(path)}
    events=pd.read_csv(OUT/"ufc_event_details.csv")
    results=pd.read_csv(OUT/"ufc_fight_results.csv")
    stats=pd.read_csv(OUT/"ufc_fight_stats.csv")
    er=events.loc[events["EVENT"].astype(str).str.strip()==EVENT].copy()
    rr=results.loc[results["EVENT"].astype(str).str.strip()==EVENT].copy()
    sr=stats.loc[stats["EVENT"].astype(str).str.strip()==EVENT].copy()
    er.to_csv(OUT/"ufcvegas121_event_details.csv",index=False)
    rr.to_csv(OUT/"ufcvegas121_fight_results.csv",index=False)
    sr.to_csv(OUT/"ufcvegas121_fight_stats.csv",index=False)
    rb=set(rr["BOUT"].astype(str).str.strip())
    sb=set(sr["BOUT"].astype(str).str.strip())
    payload={
      "checked_at_utc":datetime.now(timezone.utc).isoformat(),
      "upstream_commit":UPSTREAM_COMMIT,
      "event":EVENT,
      "event_rows":int(len(er)),
      "result_rows":int(len(rr)),
      "unique_result_bouts":int(len(rb)),
      "fight_stat_rows":int(len(sr)),
      "unique_stat_bouts":int(len(sb)),
      "missing_stat_bouts":sorted(rb-sb),
      "full_card_stats_available":len(er)==1 and len(rb)==12 and len(sb)==12 and not (rb-sb),
      "receipt":receipt
    }
    (OUT/"availability.json").write_text(json.dumps(payload,indent=2,sort_keys=True))
    print(json.dumps(payload,indent=2,sort_keys=True))

if __name__=="__main__": main()
