from __future__ import annotations

import json
from pathlib import Path

import run_ufc333_stage_a as base


# The post-Edmonton refresh stores the fitted MethodInterceptCalibrator as a
# standalone artifact, while the older Stage-A event runner expects the same two
# scalar offsets under manifest['final_method_calibration']. Bridge that storage
# format here without retraining or changing any learned values.
_original_configure = base.configure_current_runner


def configure_current_runner_with_edmonton_calibrator():
    _original_configure()
    calibrator_path = (
        base.ROOT
        / "artifacts/v033_ufcedmonton_full_stats/method_calibrator_v033_through_2026-10-17.joblib"
    )
    calibrator = base.edm._orig_joblib_load(calibrator_path)
    if not getattr(calibrator, "is_fitted_", False):
        raise RuntimeError("post-Edmonton method calibrator is not fitted")

    finish_offset = float(calibrator.finish_offset_)
    sub_offset = float(calibrator.sub_offset_)
    inherited_redirect = Path.read_text

    def read_text_with_calibration_bridge(self, *args, **kwargs):
        if str(self).endswith("artifacts/v033_ufc332_full_stats/manifest.json"):
            manifest_path = base.ROOT / "artifacts/v033_ufcedmonton_full_stats/manifest.json"
            manifest = json.loads(base.edm._orig_read_text(manifest_path, *args, **kwargs))
            manifest["final_method_calibration"] = {
                "finish_offset": finish_offset,
                "sub_given_finish_offset": sub_offset,
                "source": "method_calibrator_v033_through_2026-10-17.joblib",
                "bridge_only": True,
            }
            return json.dumps(manifest)
        return inherited_redirect(self, *args, **kwargs)

    Path.read_text = read_text_with_calibration_bridge


base.configure_current_runner = configure_current_runner_with_edmonton_calibrator


if __name__ == "__main__":
    base.main()
