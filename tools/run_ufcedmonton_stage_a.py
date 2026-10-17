from __future__ import annotations
import importlib.util, json, sys
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('vegas122',ROOT/'tools/run_ufcvegas122_stage_a.py')
mod=importlib.util.module_from_spec(spec); assert spec.loader; sys.modules['vegas122']=mod; spec.loader.exec_module(mod)

mod.EVENT_DATE=pd.Timestamp('2026-10-17',tz='UTC')
mod.BASE_SEED=2911017
mod.RAW_DIR=ROOT/'data/raw/ufcvegas122_2026-10-10'
mod.CARD=[
 {'a':'Cody Chovancek','b':'SuYoung You','weight_class':'Bantamweight','scheduled_seconds':900},
 {'a':'Melissa Croden','b':'Chelsea Chandler','weight_class':"Women's Bantamweight",'scheduled_seconds':900},
 {'a':'Chad Anheliger','b':'Steven Koslow','weight_class':'Bantamweight','scheduled_seconds':900},
 {'a':'Katlyn Cerminara','b':'Mackenzie Stiller','weight_class':"Women's Flyweight",'scheduled_seconds':900},
 {'a':'Javad Mahjoub','b':'Joel Faglier','weight_class':'Heavyweight','scheduled_seconds':900},
 {'a':'Julien Leblanc','b':'Nick Galanti','weight_class':'Middleweight','scheduled_seconds':900},
 {'a':'Tanner Boser','b':'Jhonata Diniz','weight_class':'Heavyweight','scheduled_seconds':900},
 {'a':'Mandel Nallo','b':'Nate Landwehr','weight_class':'Lightweight','scheduled_seconds':900},
 {'a':'Louis Jourdain','b':'Timmy Cuamba','weight_class':'Bantamweight','scheduled_seconds':900},
 {'a':'Marc-Andre Barriault','b':'Kyle Daukaus','weight_class':'Middleweight','scheduled_seconds':900},
 {'a':'Kyle Nelson','b':'Cristian Perez','weight_class':'Lightweight','scheduled_seconds':900},
 {'a':'Erin Blanchfield','b':'Jasmine Jasudavicius','weight_class':"Women's Flyweight",'scheduled_seconds':900},
 {'a':'Joaquin Buckley','b':'Mike Malott','weight_class':'Welterweight','scheduled_seconds':1500},
]
mod.HISTORY_ALIASES.update({'katlyncerminara':'katlynchookagian','suyoungyou':'yousuyoung'})

# Force causal history through Vegas 122 despite the older runner's internal cutoff assignment.
_orig_load=mod.rb.load_fights
def causal_load(raw_dir):
 old=mod.rb.TRAINING_CUTOFF; mod.rb.TRAINING_CUTOFF=pd.Timestamp('2026-10-11',tz='UTC')
 try: return _orig_load(raw_dir)
 finally: mod.rb.TRAINING_CUTOFF=old
mod.rb.load_fights=causal_load

# Redirect v0.33 artifact requests to the post-Vegas-122 retrain without changing champion/reference governance.
_orig_joblib_load=mod.joblib.load
def redirected_load(path,*args,**kwargs):
 p=Path(path); s=str(p)
 mapping={
  'winner_v033.joblib':'winner_v033_through_2026-10-10.joblib',
  'method_baseline_v033.joblib':'method_baseline_v033_through_2026-10-10.joblib',
  'method_residual_v033.joblib':'method_residual_v033_through_2026-10-10.joblib',
  'timing_v033_30s.joblib':'timing_v033_30s_through_2026-10-10.joblib',
 }
 if 'artifacts/v033_ufc332_full_stats' in s:
  p=ROOT/'artifacts/v033_ufcvegas122_full_stats'/mapping.get(p.name,p.name)
 return _orig_joblib_load(p,*args,**kwargs)
mod.joblib.load=redirected_load

# Redirect manifest read to the post-Vegas-122 artifact manifest.
_orig_read_text=Path.read_text
def read_text_redirect(self,*args,**kwargs):
 if str(self).endswith('artifacts/v033_ufc332_full_stats/manifest.json'):
  return _orig_read_text(ROOT/'artifacts/v033_ufcvegas122_full_stats/manifest.json',*args,**kwargs)
 return _orig_read_text(self,*args,**kwargs)
Path.read_text=read_text_redirect

if __name__=='__main__':
 old_dir=ROOT/'data/locks/ufcvegas122_2026-10-10'
 old_raw=old_dir/'stage_a_model_raw_v033.json'; backup=old_raw.read_bytes() if old_raw.exists() else None
 mod.main()
 generated=json.loads(old_raw.read_text())
 payload=generated['payload']
 payload['event']='UFC Edmonton: Buckley vs Malott'
 payload['event_date']='2026-10-17'
 payload['stage']='A_ODDS_BLIND_MODEL_RAW_POST_VEGAS122'
 payload['model_state']['fighter_history_through']='2026-10-10'
 payload['model_state']['clean_feedback_rows']=112
 payload['model_state']['shadow_winner']='v0.33 full-stat shadow retrained through 2026-10-10'
 payload['model_state']['method_baseline']='v0.33 baseline retrained through 2026-10-10'
 payload['model_state']['method_calibration']='v0.33 calibrated leading shadow retrained through 2026-10-10'
 payload['model_state']['method_residual']='v0.33 residual comparison retrained through 2026-10-10'
 payload['model_state']['timing']='v0.33 30-second hazard shadow retrained through 2026-10-10'
 lock=mod.freeze_payload(payload)
 out=ROOT/'data/locks/ufcedmonton_2026-10-17'; out.mkdir(parents=True,exist_ok=True)
 (out/'stage_a_model_raw_v033.json').write_text(json.dumps({'sha256':lock.sha256,'payload':lock.payload},indent=2,sort_keys=True),encoding='utf-8')
 weights={
 'Joaquin Buckley':170.5,'Mike Malott':170.5,'Erin Blanchfield':125,'Jasmine Jasudavicius':124.5,'Kyle Nelson':155.5,'Cristian Perez':154.5,'Marc-Andre Barriault':185,'Kyle Daukaus':186,'Louis Jourdain':135.5,'Timmy Cuamba':136,'Mandel Nallo':155.5,'Nate Landwehr':155,'Tanner Boser':247.5,'Jhonata Diniz':251.5,'Julien Leblanc':185,'Nick Galanti':185.5,'Javad Mahjoub':252.5,'Joel Faglier':261,'Katlyn Cerminara':125,'Mackenzie Stiller':124,'Chad Anheliger':135,'Steven Koslow':135,'Melissa Croden':136,'Chelsea Chandler':135.5,'Cody Chovancek':135.5,'SuYoung You':135.5}
 audit={'event':'UFC Edmonton: Buckley vs Malott','event_date':'2026-10-17','official_card_fights':13,'all_26_made_weight':True,'weights_lb':weights,'odds_used':False,'previous_event_integrated':True,'clean_feedback_rows':112,'fighter_history_through':'2026-10-10','joint_simulations_per_fight':10000,'timing_simulations_per_fight':10000,'governance':'Champion/reference unchanged; v0.34 remains diagnostic/shadow only; sparse-data and timing restrictions retained.'}
 (out/'stage_a_audit.json').write_text(json.dumps(audit,indent=2,sort_keys=True),encoding='utf-8')
 if backup is not None: old_raw.write_bytes(backup)
