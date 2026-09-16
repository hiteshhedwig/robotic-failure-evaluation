"""Known interval boundary checks and comparison of actual reproduced fall receipts."""
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.report import wilson
from scripts.compare import compare

def test_zero_eight_is_not_certainty():
    low,high=wilson(0,8)
    assert low==pytest.approx(0,abs=1e-12)
    assert high==pytest.approx(0.32440756,abs=1e-7)

def test_all_eight_is_not_certainty():
    low,high=wilson(8,8)
    assert low==pytest.approx(0.67559244,abs=1e-7)
    assert high==pytest.approx(1,abs=1e-12)

def test_no_trials_has_no_interval():
    assert wilson(0,0) is None

def test_recorded_fall_reproduces():
    report=compare(ROOT/"artifacts/campaign/strong-seed0",ROOT/"artifacts/reproductions/fall-0")
    assert report["matched"]
    assert report["outcome_agreement"]
    assert not report["regression"]
    assert report["pairs"][0]["changed_fingerprints"]==[]

def test_unmatched_trials_are_rejected():
    with pytest.raises(ValueError):
        compare(ROOT/"artifacts/campaign/strong-seed0",ROOT/"artifacts/campaign/mild-seed0")


def test_comparator_flags_a_new_task_failure(tmp_path):
    # Synthetic receipt mutation tests comparator logic only, not robot behavior.
    import json
    source=ROOT/"artifacts/campaign/mild-seed0"
    scenario=json.loads((source/"scenario.json").read_text())
    result=json.loads((source/"supervisor.json").read_text())
    for name in ["reference","candidate"]:
        out=tmp_path/name;out.mkdir()
        (out/"scenario.json").write_text(json.dumps(scenario))
        record=dict(result)
        if name=="candidate":record["status"]="FALL"
        (out/"supervisor.json").write_text(json.dumps(record))
    report=compare(tmp_path/"reference",tmp_path/"candidate")
    assert report["regression"]
    assert report["pairs"][0]["new_task_failure"]
