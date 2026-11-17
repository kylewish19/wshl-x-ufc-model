"""Reproduce longitudinal WSHL_X UFC baseline/Stage B audit without model writes."""
from __future__ import annotations

import json
from wshlx_ufc.longitudinal_audit import audit


def main():
    j=audit()
    print("WSHLX_FULL_AUDIT_START")
    print(json.dumps(j,sort_keys=True,allow_nan=False))
    print("WSHLX_FULL_AUDIT_END")
    r=j["reconstructed_reference_before_334"]
    print(f"Reference clean archived: {r['winner_correct']}/{r['fights']} "
          f"winners; {r['method_class_correct']}/{r['fights']} method classes; "
          f"{r['exact_fighter_and_method']}/{r['fights']} exact.")
    h=j["sanity_check"]
    print(f"Last89 locked fighter+exact method: {h['subsequent_89_exact_model']}/89 "
          f"vs first64-trained fixed {h['chosen_fixed_method']}: "
          f"{h['subsequent_89_exact_fixed_method']}/89")
    for name in ("post_recheck_actionable_scenario",
                 "original_sep19_frozen_scenario"):
        x=j["strategy_stage_b_recorded"][name]
        print(f"{name}: {x['wins']}-{x['losses']}; "
              f"risk {x['risked_units']:.2f}u; "
              f"net {x['net_units']:+.4f}u; "
              f"ROI {x['roi']:.1%}; no actual user bet claims.")
    print("NO MODEL CHANGES OR CHALLENGER PROMOTIONS")


if __name__=="__main__":
    main()
