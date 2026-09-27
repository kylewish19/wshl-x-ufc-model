import importlib.util
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("rebuild_v027_alias_test",ROOT/"tools/rebuild_v027.py")
m=importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["rebuild_v027_alias_test"]=m
spec.loader.exec_module(m)

def test_audited_name_aliases():
    assert m.norm_name("Alatengheili") == m.norm_name("Heili Alateng")
    assert m.norm_name("Tina Black") == m.norm_name("Valesca Machado")
    assert m.norm_name("Mahammadali Osmanli") == m.norm_name("Mehemmedeli Osmanli")
