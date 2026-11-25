"""Static inventory of metric-call sites. Report only; no training or archive edits."""
import ast,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    calls=[];uses=[]
    for folder in ("src","tools","scripts","tests"):
        for p in sorted((ROOT/folder).rglob("*.py")):
            s=p.read_text();tree=ast.parse(s)
            for node in ast.walk(tree):
                if not isinstance(node,ast.Call):continue
                f=node.func
                name=f.id if isinstance(f,ast.Name) else f.attr if isinstance(f,ast.Attribute) else ""
                if name not in ("log_loss","grade_multiclass","_multiclass_nll","score_six"):continue
                entry={"path":str(p.relative_to(ROOT)),"line":node.lineno,"call":ast.get_source_segment(s,node),"function":name}
                (calls if name=="log_loss" else uses).append(entry)
    print("LOG_LOSS_CALLS",json.dumps(calls))
    print("EXPLICIT_METRIC_CALLS",json.dumps(uses))
    Path("metric_call_inventory.json").write_text(json.dumps({"sklearn_log_loss_call_sites":calls,"other_metric_call_sites":uses,"training_changed":False,"prior_grades_changed":False},indent=2))
if __name__=="__main__":main()
