"""World MMA identity audit: reject name-only mapping, same-date leakage."""
from datetime import date
import importlib.util
from pathlib import Path
import sqlite3

spec=importlib.util.spec_from_file_location(
 "wshlx_external_mma_v4_test",
 Path(__file__).resolve().parents[1]/"tools/audit_worldwide_mma_history_v4.py")
subject=importlib.util.module_from_spec(spec);spec.loader.exec_module(subject)

def test_unicode_key_and_prior_region_only_uses_past():
    assert subject.namekey("Jiří Procházka")=="jiriprochazka"
    assert subject.namekey("Jon Jones")=="jonjones"
    history=[
      {"date":"2023-01-10","promotion":"Cage Warriors","result":"W","method":"Submission","fight_id":1},
      {"date":"2024-02-10","promotion":"UFC","result":"L","method":"KO/TKO","fight_id":2},
      {"date":"2025-02-10","promotion":"PFL","result":"W","method":"Decision","fight_id":3},
    ]
    a=subject.prior(history,"2024-02-10")
    assert a["known_nonUFC_bouts_prior"]==1
    assert a["known_pro_mma_bouts_any_org_prior"]==1
    b=subject.prior(history,"2026-01-01")
    assert b["known_nonUFC_bouts_prior"]==2
    assert b["known_pro_mma_bouts_any_org_prior"]==3

def build_db():
    db=sqlite3.connect(":memory:")
    db.executescript("""
      CREATE TABLE fighters (fighter_id INTEGER PRIMARY KEY,name TEXT);
      CREATE TABLE fighter_aliases (fighter_id INTEGER,source TEXT,source_id TEXT,name TEXT);
      CREATE TABLE fights (fight_id INTEGER PRIMARY KEY,event_id INTEGER);
      CREATE TABLE events (event_id INTEGER PRIMARY KEY,date TEXT);
      CREATE TABLE fight_aliases (fight_id INTEGER,source TEXT,source_id TEXT);
      CREATE TABLE fight_participants (fight_id INTEGER,fighter_id INTEGER,corner INTEGER,result TEXT);
      INSERT INTO fighters VALUES (1,'Athlete Alpha'),(2,'Athlete Beta'),(3,'Athlete Alpha');
      INSERT INTO fighter_aliases VALUES (1,'ufcstats','aaa','Athlete Alpha'),
          (2,'ufcstats','bbb','Athlete Beta'),(3,'sherdog','cc','Athlete Alpha');
      INSERT INTO events VALUES (1,'2025-04-05');
      INSERT INTO fights VALUES (101,1);
      INSERT INTO fight_aliases VALUES (101,'ufcstats','ufcf101');
      INSERT INTO fight_participants VALUES (101,1,0,'W'),(101,2,1,'L');
    """)
    return db

def test_name_duplicated_but_fight_day_and_two_opponents_identifies_correct_fighter():
    db=build_db()
    a=subject.aliases(db)
    idx,n=subject.source_matched_fights(db,a)
    assert n==1
    source=[{"date":"2025-04-05","a":"Athlete Alpha","b":"Athlete Beta",
             "event":"Synthetic UFC","key":("2025-04-05","athletealpha","athletebeta")}]
    verified,matches,missed,ambiguous,audit=subject.build_verified_map(source,idx,a)
    assert not ambiguous and not missed
    assert matches[0]["a_id"]==1 and matches[0]["b_id"]==2
    assert verified["athletealpha"]==1
    assert 3 not in verified.values()
    assert audit["name_only_links"]==0

def test_wrong_opponent_or_wrong_date_is_not_a_verified_crosswalk():
    db=build_db();idx,n=subject.source_matched_fights(db,subject.aliases(db))
    source=[{"date":"2025-04-05","a":"Athlete Alpha","b":"Athlete Gamma",
         "event":"Synthetic","key":("2025-04-05","athletealpha","athletegamma")}]
    verified,matched,missed,ambiguous,audit=subject.build_verified_map(
        source,idx,subject.aliases(db))
    assert len(missed)==1 and not verified and not matched
