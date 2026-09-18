from pathlib import Path

def test_consolidated_master_audit_exists_and_is_current():
    text = Path("docs/MASTER_UFC_RECORD_AUDIT_2026-09-18.md").read_text()
    assert "64" in text
    assert "36-28" in text
    assert "28-36" in text
    assert "15-49" in text
    assert "UFC Paris" in text
    assert "90d03447e12f7e4c41bb9856f465e51cc91ed14ece794960ac0604fe80fc702b" in text
