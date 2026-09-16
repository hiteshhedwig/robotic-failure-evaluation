"""Infrastructure checks kill or time out real G1 worker processes."""
import json
import os
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from robot_eval.runner import run_one

def scenario():
    return json.loads((ROOT/"configs/baseline.json").read_text())

def test_nominal_worker(tmp_path):
    r=run_one(scenario(),tmp_path/"nominal")
    assert r["status"]=="COMPLETED"
    assert r["worker_returncode"]==0
    assert (tmp_path/"nominal"/"manifest.json").exists()

def test_killed_simulation_is_not_a_robot_fall(tmp_path):
    c=scenario()
    c["duration_s"]=30
    r=run_one(c,tmp_path/"crashed",kill_when_trace_ready=True)
    assert r["status"]=="INFRASTRUCTURE_ERROR"
    assert r["crash_injected"]
    assert r["worker_returncode"]<0
    assert (tmp_path/"crashed"/"trace.jsonl").stat().st_size>12000
    with pytest.raises(ProcessLookupError):
        os.kill(r["worker_pid"],0)

def test_parent_deadline_is_not_task_timeout(tmp_path):
    r=run_one(scenario(),tmp_path/"timedout",timeout_s=0.1)
    assert r["status"]=="INFRASTRUCTURE_TIMEOUT"
    with pytest.raises(ProcessLookupError):
        os.kill(r["worker_pid"],0)

def test_unreachable_task_is_a_robot_task_timeout(tmp_path):
    c=scenario()
    c["duration_s"]=2
    c["warmup_s"]=1
    c["minimum_progress_m"]=100
    r=run_one(c,tmp_path/"task-timeout")
    assert r["status"]=="TASK_TIMEOUT"
    assert r["worker_returncode"]==2

def test_invalid_input_is_not_robot_failure(tmp_path):
    c=scenario()
    c["duration_s"]=-1
    r=run_one(c,tmp_path/"invalid")
    assert r["status"]=="INFRASTRUCTURE_ERROR"

def test_existing_evidence_is_not_overwritten(tmp_path):
    out=tmp_path/"existing"
    out.mkdir()
    with pytest.raises(FileExistsError):
        run_one(scenario(),out)
