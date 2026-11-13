"""Publish researched tactical UFC scripts without stating model picks in the narration."""
import argparse
from pathlib import Path
from wshlx_ufc.tactical_video import create_reports


def main():
    p = argparse.ArgumentParser(description="Build sourced, outcome-unrevealed tactical videos")
    p.add_argument("--stage-a", type=Path, required=True)
    p.add_argument("--research", type=Path, required=True)
    p.add_argument("--raw", type=Path, required=True)
    p.add_argument("--markdown-out", type=Path, required=True)
    p.add_argument("--json-out", type=Path, required=True)
    a = p.parse_args()
    card = create_reports(a.stage_a, a.research, a.markdown_out, a.json_out, a.raw)
    print(f"{card['fight_count']} sourced tactical previews written. No locked pick changed.")
    print("Host, not auto-narration, reveals winner/method/timing selections.")


if __name__ == "__main__":
    main()
