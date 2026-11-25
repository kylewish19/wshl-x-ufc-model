"""Grade a genuine pre-event research artifact, or aggregate existing grades.
Never overwrite outputs; never treat file timestamps as external proof.
"""
import argparse,json
from pathlib import Path
from wshlx_ufc.combined_research_grade import grade
from wshlx_ufc.combined_research_cumulative import summarize

def read(p):return json.loads(p.read_bytes())
def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest="command",required=True)
    g=sub.add_parser("event")
    for n in ("lock","actual","evidence","output"):g.add_argument("--"+n,type=Path,required=True)
    c=sub.add_parser("cumulative");c.add_argument("--grades",type=Path,nargs="*",default=[]);c.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    if args.output.exists():raise FileExistsError("Never overwrite a grade or summary")
    out=grade(args.lock.read_bytes(),read(args.actual),read(args.evidence)) if args.command=="event" else summarize([read(x) for x in args.grades])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x") as f:json.dump(out,f,indent=2,allow_nan=False)
if __name__=="__main__":main()
