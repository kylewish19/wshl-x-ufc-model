"""Read-only UFC three-view consensus summary for presenter picks."""
import argparse
from pathlib import Path
from wshlx_ufc.consensus_video import write_card


def main():
    p = argparse.ArgumentParser(description="Create frozen-model consensus presentation card")
    p.add_argument("--stage-a", type=Path, required=True)
    p.add_argument("--raw", type=Path, required=True)
    p.add_argument("--json-out", type=Path, required=True)
    p.add_argument("--markdown-out", type=Path, required=True)
    args = p.parse_args()
    card = write_card(args.stage_a, args.raw, args.json_out, args.markdown_out)
    print(f"{card['fighters']} bouts; presentation consensus only; NO original pick or odds change.")


if __name__ == "__main__":
    main()
