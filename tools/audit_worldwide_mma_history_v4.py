"""Research-only UFC-to-worldwide-MMA fighter identity and history audit.

Uses a separately downloaded SHA-recorded Fight Canon SQLite release, NOT
the user's original pinned UFCStats source, no model fitting and no odds.

Fighter IDs are accepted only when an EXACT fight-day two-participant UFC
match from the original pinned UFC fight register corroborates the mapping.
Names alone NEVER authorize historical-record transfer, especially for
same-name athletes. Pro bouts are strictly DATE BEFORE prospective fight,
and source date/absence are never used as a proxy for the current outcome.

Third-party cross-promotion history is incomplete and retrospectively
updated, so pre-date filters are essential but not sufficient for perfectly
point-in-time source availability. Regional missingness is UNKNOWN, not zero.
"""
from __future__ import annotations

from collections import defaultdict,Counter
from datetime import date,datetime,timezone
import hashlib,json,re,sqlite3,sys,unicodedata
from pathlib import Path

import pandas as pd

from wshlx_ufc.historical_data import bout,col,normalize_events,txt
from wshlx_ufc.prefight_profile_context import checked_file
from wshlx_ufc.historical_feature_matrix import load_matrix

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/model_health/2026-11-19_worldwide_mma_identity_audit"
DB=ROOT/".research_cache/fightcanon/canon.db"
DATE_CUTOFF="2026-11-08"

def namekey(x):
    return re.sub(r"[^a-z0-9]","",
        unicodedata.normalize("NFKD",str(x)).encode("ascii","ignore")
        .decode("ascii").casefold())

def clean_day(x):
    if not x:return None
    try:return date.fromisoformat(str(x)[:10]).isoformat()
    except ValueError:return None

def load_source_pairs():
    event=pd.read_csv(checked_file("ufc_event_details.csv"),low_memory=False)
    results=pd.read_csv(checked_file("ufc_fight_results.csv"),low_memory=False)
    event_dates={
        str(z.event).strip():z.date.date().isoformat()
        for z in normalize_events(event).itertuples(index=False)
        if pd.notna(z.date)
    }
    e,b=(col(results,k) for k in ("EVENT","BOUT"))
    if not e or not b:raise ValueError("UFC source lacks event/fight key")
    ret=[];seen=set()
    for row in results.to_dict("records"):
        event=txt(row[e]);when=event_dates.get(event)
        if not when or not "2021-01-01"<=when<DATE_CUTOFF:continue
        pair=bout(row[b])
        if pair is None:continue
        a,bname=pair
        key=(when,*sorted((namekey(a),namekey(bname))))
        if key in seen:raise ValueError("Repeated modern same-day opponent pair source")
        seen.add(key);ret.append({"date":when,"event":event,"a":a,"b":bname,"key":key})
    return ret

def get_tables(db):
    if not db.exists() or db.stat().st_size<10_000_000:
        raise FileNotFoundError("Missing canonical source SQLite. Download its release separately.")
    con=sqlite3.connect(f"file:{db}?mode=ro",uri=True)
    con.row_factory=sqlite3.Row
    con.execute("PRAGMA query_only=ON")
    required={"fighters","fighter_aliases","fights","fight_participants","events"}
    names={x[0] for x in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if required-names:raise ValueError("FightCanon schema missing "+str(required-names))
    return con

def aliases(con):
    m=defaultdict(set)
    for fighter_id,name in con.execute("SELECT fighter_id,name FROM fighters"):
        if name:m[int(fighter_id)].add(namekey(name))
    for fighter_id,name in con.execute(
        "SELECT fighter_id,name FROM fighter_aliases WHERE source IN ('ufcstats','sherdog')"):
        if name:m[int(fighter_id)].add(namekey(name))
    return m

def source_matched_fights(con,alias):
    # UFCStats source ID and promotion both corroborate the fighter ID.
    rows=con.execute("""
    SELECT e.date AS day, f.fight_id,
           x.fighter_id AS aid, y.fighter_id AS bid
    FROM fights f
    JOIN events e ON e.event_id=f.event_id
    JOIN fight_aliases fa ON fa.fight_id=f.fight_id
       AND fa.source='ufcstats'
    JOIN fight_participants x ON x.fight_id=f.fight_id AND x.corner=0
    JOIN fight_participants y ON y.fight_id=f.fight_id AND y.corner=1
    WHERE e.date >= '2021-01-01' AND e.date < ?
    """,(DATE_CUTOFF,)).fetchall()
    index=defaultdict(set)
    for d, fightid,a,b in rows:
        day=clean_day(d)
        if not day:continue
        ids=(int(a),int(b))
        aa=alias.get(ids[0],set());bb=alias.get(ids[1],set())
        for an in aa:
            for bn in bb:
                if an!=bn:index[(day,*sorted((an,bn)))].add((fightid,ids[0],ids[1]))
    return index,len(rows)

def build_verified_map(source,index,alias):
    candidate=defaultdict(set)
    matches=[];missed=[];ambiguous=[]
    for r in source:
        candidates=index.get(r["key"],set())
        # Identical dated fight + BOTH named opponents must match aliases.
        if len(candidates)!=1:
            example={"date":r["date"],"a":r["a"],"b":r["b"],"candidates":len(candidates)}
            (missed if len(candidates)==0 else ambiguous).append(example)
            continue
        fightid,id0,id1=next(iter(candidates))
        ka,kb=namekey(r["a"]),namekey(r["b"])
        options=[]
        if ka in alias[id0] and kb in alias[id1]:options.append((id0,id1))
        if ka in alias[id1] and kb in alias[id0]:options.append((id1,id0))
        if len(options)!=1:
            ambiguous.append({"date":r["date"],"a":r["a"],"b":r["b"],"why":"Ambiguous UFC corner-to-name orientation"})
            continue
        ida,idb=options[0]
        candidate[ka].add(ida);candidate[kb].add(idb)
        matches.append({"date":r["date"],"event":r["event"],
                        "a":r["a"],"b":r["b"],"a_id":ida,"b_id":idb,
                        "fightcanon_fight_id":int(fightid)})
    disputed={name:ids for name,ids in candidate.items() if len(ids)!=1}
    vetted={name:next(iter(ids)) for name,ids in candidate.items() if len(ids)==1}
    for x in list(vetted):
        if x in disputed:del vetted[x]
    return vetted,matches,missed,ambiguous,{
       "multiple_FightCanon_fighterIDs_same_UFC_normalized_name":{
           k:sorted(x) for k,x in sorted(disputed.items())},
       "identity_verified_with_exact_day_and_TWO_opponents":True,
       "name_only_links":0,
    }

def history_for_ids(con,ids):
    # Historical per fighter all pro bouts (outside the UFC included).
    # Filter source as-of per EVENT DATE, never per modern current record.
    histories=defaultdict(list)
    ids=sorted(set(int(x) for x in ids))
    for offset in range(0,len(ids),350):
        batch=ids[offset:offset+350]
        keys=",".join("?" for _ in batch)
        # Query-only connection stays immutable: no temp tables or cached
        # post-event records are created or used.
        query=f"""
          SELECT p.fighter_id AS athlete_id, e.date AS day,
                 e.promotion, p.result, f.method, f.fight_id, f.bout_type
          FROM fight_participants p
          JOIN fights f ON f.fight_id=p.fight_id
          JOIN events e ON e.event_id=f.event_id
          WHERE p.fighter_id IN ({keys}) AND e.date IS NOT NULL AND e.date < ?
          ORDER BY p.fighter_id,e.date,f.fight_id
        """
        for fid,d,promotion,result,method,fightid,kind in con.execute(
            query,(*batch,DATE_CUTOFF)):
            when=clean_day(d)
            if not when or (kind and str(kind).lower() in ("amateur","exhibition")):
                continue
            histories[int(fid)].append({
                "date":when,"promotion":str(promotion or "").strip(),
                "result":str(result or "").upper().strip(),"method":str(method or "").lower(),
                "fight_id":int(fightid),
            })
    return histories

def victory_class(text):
    s=str(text or "").strip().lower()
    if "submission" in s or s in ("sub","tapout","technical submission"):
        return "SUB"
    if "ko" in s or "tko" in s or "knockout" in s:
        return "KO"
    if "decision" in s or s.startswith(("ud ","sd ","md ")):
        return "DEC"
    return "UNREPORTED"

def prior(history,when):
    # Date strictly earlier; same-day outcomes excluded from all queries.
    data=[x for x in history if x["date"]<when]
    nonufc=[x for x in data if x["promotion"].upper()!="UFC" and x["result"] in ("W","L","D")]
    completed=[x for x in nonufc if x["result"] in ("W","L")]
    recent5=completed[-5:]
    recent3=completed[-3:]
    def win_stats(seq):return sum(x["result"]=="W" for x in seq)
    result={
        "known_nonUFC_bouts_prior":len(nonufc),
        "known_nonUFC_wins_prior":sum(x["result"]=="W" for x in nonufc),
        "known_nonUFC_losses_prior":sum(x["result"]=="L" for x in nonufc),
        "known_nonUFC_decisive_prior":len(completed),
        "known_nonUFC_bouts_prior_365d":sum((date.fromisoformat(when)-date.fromisoformat(x["date"])).days<=365 for x in nonufc),
        "known_pro_mma_bouts_any_org_prior":sum(x["result"] in ("W","L","D") for x in data),
        "known_nonUFC_recent3_decisive":len(recent3),
        "known_nonUFC_recent3_wins":win_stats(recent3),
        "known_nonUFC_recent5_decisive":len(recent5),
        "known_nonUFC_recent5_wins":win_stats(recent5),
        "known_nonUFC_method_recorded":sum(victory_class(x["method"])!="UNREPORTED" for x in completed),
    }
    for method in ("KO","SUB","DEC"):
        result[f"known_nonUFC_{method}_wins_prior"]=sum(
            x["result"]=="W" and victory_class(x["method"])==method for x in completed)
        result[f"known_nonUFC_{method}_losses_prior"]=sum(
            x["result"]=="L" and victory_class(x["method"])==method for x in completed)
    if any(q<0 for q in result.values()):raise ValueError("Negative historical fight count")
    return result

def run():
    source=load_source_pairs()
    if not 2900<=len(source)<=3500:
        raise ValueError(f"Unexpected 2021–Nov7 UFC source fight count: {len(source)}")
    # Source result rows can include NCs and other metadata not represented by
    # the strict decisive/draw training matrix. Join on identical verified
    # pre-fight source names/dates rather than inventing a 3,036 raw-row count.
    con=get_tables(DB)
    alias=aliases(con)
    index,available=source_matched_fights(con,alias)
    vetted,matched,unmatched,ambiguous,audit=build_verified_map(source,index,alias)
    histories=history_for_ids(con,vetted.values())
    matrices,labels,_=load_matrix()
    byid={x["bout_id"]:x for x in matrices}
    result=[]
    matchmap={(r["date"],namekey(r["a"]),namekey(r["b"])):r for r in matched}
    # Same fight source may have fighter corners reversed; matches canonical.
    identity_per_year=Counter()
    for f in matrices:
        if not "2021-01-01"<=f["event_date"]<DATE_CUTOFF:continue
        a,b=namekey(f["fighter_a"]),namekey(f["fighter_b"])
        match=matchmap.get((f["event_date"],a,b)) or matchmap.get((f["event_date"],b,a))
        if not match or a not in vetted or b not in vetted:continue
        aa=prior(histories[vetted[a]],f["event_date"])
        bb=prior(histories[vetted[b]],f["event_date"])
        ida=vetted[a];idb=vetted[b]
        if ida==idb:raise ValueError("Same person on opposite sides")
        row={
            "date":f["event_date"],"bout_id":f["bout_id"],
            "fighter_a":f["fighter_a"],"fighter_b":f["fighter_b"],
            "a_verified_id":ida,"b_verified_id":idb,
            "a":aa,"b":bb,
            "a_prior_ufc_bouts":int(f["a_ufc_prior_bouts"]),
            "b_prior_ufc_bouts":int(f["b_ufc_prior_bouts"]),
        }
        result.append(row)
        identity_per_year[f["event_date"][:4]]+=1
    year_summary={}
    for year in ("2024","2025","2026"):
        subset=[r for r in result if r["date"].startswith(year)]
        debut=[r for r in subset if min(r["a_prior_ufc_bouts"],r["b_prior_ufc_bouts"])==0]
        bothnew=[r for r in subset if r["a_prior_ufc_bouts"]==r["b_prior_ufc_bouts"]==0]
        withregional=sum(
            r["a"]["known_nonUFC_bouts_prior"]>=3 and r["b"]["known_nonUFC_bouts_prior"]>=3 for r in subset)
        rookie_has_history=sum(
            (r["a_prior_ufc_bouts"]==0 and r["a"]["known_nonUFC_bouts_prior"]>=3) or
            (r["b_prior_ufc_bouts"]==0 and r["b"]["known_nonUFC_bouts_prior"]>=3) for r in debut)
        year_summary[year]={
            "date_verified_source_fights":len(subset),
            "verified_pairs_with_both_3plus_nonUFC_bouts":withregional,
            "with_one_or_more_UFC_debutant":len(debut),
            "UFC_debutant_matchups_with_3plus_known_regional_fights":rookie_has_history,
            "two_debutants_matchups":len(bothnew),
        }
    OUT.mkdir(parents=True,exist_ok=True)
    manifest={
        "schema":"WSHLX_FIGHTCANON_CROSS_PROMOTION_EVIDENCE_AUDIT_V1",
        "db_size_bytes":DB.stat().st_size,
        "db_sha256":hashlib.sha256(DB.read_bytes()).hexdigest(),
        "db_download_url":"https://github.com/Jadevit/fight-canon-db/releases/download/db-2026-11-19-1934/canon.db",
        "db_release_final_asset_url_transient_UNTRUSTED":(DB.parent/"download_url.txt").read_text().strip()
             if (DB.parent/"download_url.txt").exists() else None,
        "inspected_utc":datetime.now(timezone.utc).isoformat(),
        "source_class":"SECONDARY_CROSS_PROMOTION_AGGREGATE_UFCSTATS_SHERDOG_ET_AL",
        "matches_use_UFC_fight_date_and_BOTH_fighter_aliases":True,
        "no_naive_name_only_identity_linkage":True,
        "no_current_bout_or_future_bouts_for_features":True,
        "vintage_caveat":"2026 retrospective dataset, earlier fight histories may be backfilled after fight date",
        "no_betting_odds_used":True,"no_model_weights_retrained":True,
        "nov21_original_stage_a_and_coherent_locked_unchanged":True,
        "available_ufcstats_id_fights_in_db":available,
        "pinned_ufc_modern_source_fights":len(source),
        "ufc_fights_exact_two_opponent_match":len(matched),
        "ufc_fights_no_crosswalk":len(unmatched),
        "ufc_fights_ambiguous_crosswalk":len(ambiguous),
        "unique_fighters_vetted":len(vetted),
        "modern_feature_rows_with_both_vetted":len(result),
        "identity_ambiguity_audit":audit,
        "unmatched_examples":unmatched[:12],
        "ambiguous_examples":ambiguous[:12],
        "yearwise_verified_regional_evidence":year_summary,
    }
    (OUT/"identity_and_regional_data_coverage.json").write_text(
        json.dumps(manifest,indent=2,sort_keys=True,allow_nan=False)+"\n")
    (OUT/"verified_bout_prior_pro_history.json").write_text(
        json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({
        "model_promotion":False,
        "coverage":{k:manifest[k] for k in ("ufc_fights_exact_two_opponent_match",
                 "pinned_ufc_modern_source_fights","modern_feature_rows_with_both_vetted",
                 "unique_fighters_vetted","ufc_fights_ambiguous_crosswalk")},
        "regional_2026":year_summary["2026"],
        "source_db_sha256":manifest["db_sha256"],
        "status":"SOURCE_ONLY_NO_NEW_WINNER_ACCURACY_CLAIM",
    },sort_keys=True))

if __name__=="__main__":run()
