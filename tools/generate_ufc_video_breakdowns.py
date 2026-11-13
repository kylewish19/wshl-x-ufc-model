"""Generate non-destructive, evidence-grounded UFC video breakdowns from frozen models."""
import argparse
from pathlib import Path

from wshlx_ufc.video_breakdown import write_outputs


def main():
    p = argparse.ArgumentParser(description="WSHL_X model-grounded UFC video explanations")
    p.add_argument("--stage-a", type=Path, required=True)
    p.add_argument("--raw", type=Path, required=True)
    p.add_argument("--json-out", type=Path, required=True)
    p.add_argument("--markdown-out", type=Path, required=True)
    p.add_argument("--notes", type=Path, default=None,
                   help="Optional reviewed tactical research with URLs; never mutates Stage A")
    a = p.parse_args()
    card = write_outputs(a.stage_a, a.raw, a.json_out, a.markdown_out, a.notes)
    print("Generated " + str(card["fight_count"]) + " non-destructive breakdowns for " + card["event"])
    print("Original frozen predictions and model weights unchanged.")


if __name__ == "__main__":
    main()
