"""Print one audited training-eligibility inventory. No model training."""
import json
from wshlx_ufc.historical_training_eligibility import audit_eligibility

def main():
    out=audit_eligibility()
    print("WSHLX_2021_2026_ELIGIBILITY_START")
    print(json.dumps(out,sort_keys=True,allow_nan=False))
    print("WSHLX_2021_2026_ELIGIBILITY_END")
    print("NO NEW MODEL PROMOTED; TRAINING LABELS NOT SPILLED INTO PRE-EVENT FEATURES")

if __name__=="__main__":
    main()
