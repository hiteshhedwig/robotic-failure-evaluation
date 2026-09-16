"""Extension tests: real model execution plus isolated configuration/report logic."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import pytest
from robot_eval.base import ROOT
from robot_eval.experiments import generate_suite
from robot_eval.profiles import discover_profiles, resolve_profile, validate_profile
from robot_eval.scenarios import validate, timing
from robot_eval.runner import run_one
from robot_eval.reporting import summarize, write_report

def recipe():
    r=json.loads((ROOT/"configs/experiments/walking-push-sweep.json").read_text())
    r["seeds"]=[0]
    return r

@pytest.fixture(scope="module")
def resolved_suite():
    return generate_suite(recipe())

def test_recipe_expands_matched_force_schedules_and_snapshots(resolved_suite):
    cases=resolved_suite["scenarios"]
    assert len(cases)==6
    pushes=[c for c in cases if c.get("push")]
    assert len({c["push"]["start_s"] for c in pushes})==1
    directions=[np.array(c["push"]["force_n"])/np.linalg.norm(c["push"]["force_n"]) for c in pushes]
    assert all(np.array_equal(directions[0],d) for d in directions)
    assert {c["robot"] for c in cases}=={"g1","go1"}
    for c in cases:
        assert c["robot_profile"]==resolve_profile(c["robot"]).definition
        assert validate(c).id==c["robot"]
        assert c["experiment"]["condition"] in {"reference","light","strong"}
        grid=timing(c,resolved_suite["robot_probes"][c["robot"]]["physics_dt_s"])
        assert grid.steps>0
        if c.get("push"):
            assert abs(grid.begin*grid.dt-c["push"]["start_s"])<=grid.dt/2+1e-9

def test_generation_is_repeatable(resolved_suite):
    assert generate_suite(recipe())==resolved_suite

def test_body_weight_units_use_actual_model_mass_and_gravity():
    r=recipe()
    r["disturbance"]["force_mode"]="body_weight"
    r["disturbance"]["levels"]=[{"name":"weight","magnitude":1.0}]
    suite=generate_suite(r)
    for c in suite["scenarios"]:
        probe=suite["robot_probes"][c["robot"]]
        assert np.linalg.norm(c["push"]["force_n"])==pytest.approx(probe["body_mass_kg"]*probe["gravity_m_s2"])
        assert c["experiment"]["force_mode"]=="body_weight"

@pytest.mark.parametrize("mutation",[
    lambda r:r["disturbance"].update(directions=[[0,0,0]]),
    lambda r:r["disturbance"].update(levels=[{"name":"bad","magnitude":-1}]),
    lambda r:r.update(seeds=[0,0]),
    lambda r:r.update(seeds=[True]),
    lambda r:r["disturbance"].update(type="unknown"),
    lambda r:r["disturbance"].update(onset_range_s=[9.9,10]),
    lambda r:r["disturbance"].update(levels=[{"name":"same","magnitude":1},{"name":"same","magnitude":2}]),
])
def test_bad_recipes_are_rejected(mutation):
    r=recipe()
    mutation(r)
    with pytest.raises(ValueError):generate_suite(r)

def test_profile_validation_and_grid_rejection():
    definition=deepcopy(resolve_profile("go1").definition)
    definition["monitor"]["fall_hold_s"]=-1
    with pytest.raises(ValueError):validate_profile(definition)
    c=json.loads((ROOT/"configs/go1/push-y-120.json").read_text())
    c["push"]["duration_s"]=0.0001
    with pytest.raises(ValueError,match="physics grid"):timing(c,0.004)

def test_external_profile_runs_without_changing_core_or_report(tmp_path):
    # A renamed Go1 configuration proves dispatch is not hardcoded. This is
    # still the same real Go1 model, not evidence for a third physical platform.
    directory=tmp_path/"profiles";directory.mkdir()
    definition=deepcopy(resolve_profile("go1").definition)
    definition["id"]="external-quadruped"
    definition["label"]="External Go1 configuration example"
    path=directory/"custom.json"
    path.write_text(json.dumps(definition))
    assert set(discover_profiles(directory))=={"g1","go1","external-quadruped"}
    r=recipe()
    r["robots"]=["external-quadruped"]
    r["disturbance"]["levels"]=[{"name":"nominal","magnitude":0}]
    suite=generate_suite(r,directory)
    # Change the source defaults after resolution; the embedded snapshot wins.
    edited=deepcopy(definition)
    edited["monitor"]["posture_tilt_deg"]=1
    path.write_text(json.dumps(edited))
    c=suite["scenarios"][0]
    output=tmp_path/"trial"
    receipt=run_one(c,output)
    assert receipt["status"]=="COMPLETED"
    manifest=json.loads((output/"manifest.json").read_text())
    assert manifest["robot_profile"]==definition
    report=write_report([output],tmp_path/"report")
    assert report["robots"]==["external-quadruped"]
    assert report["conditions"][0]["fall_wilson95"] is None
    assert "external-quadruped" in (tmp_path/"report/report.md").read_text().lower()

def test_wrong_adapter_body_is_an_infrastructure_error(tmp_path):
    c=json.loads((ROOT/"configs/go1/push-y-0.json").read_text())
    c["robot_profile"]=deepcopy(resolve_profile("go1").definition)
    c["robot_profile"]["root_body"]="wrong-body"
    result=run_one(c,tmp_path/"invalid-profile")
    assert result["status"]=="INFRASTRUCTURE_ERROR"
    assert "root_body" in result["error"]

def synthetic_trial(folder,*,force=10,task_goal=2,profile_hash="a",status="COMPLETED",seed=0):
    # Report-only fixtures, explicitly not simulated robot accomplishments.
    folder.mkdir()
    c={"id":"arbitrary-name","robot":"unseen-robot","seed":seed,
       "command":[0.5,0,0],"duration_s":10,"warmup_s":2,"minimum_progress_m":task_goal,
       "push":{"force_n":[0,force,0],"start_s":3,"duration_s":0.2}}
    result={"scenario_id":c["id"],"robot":c["robot"],"status":status,
            "progress_m":3,"recovery_latency_s":None}
    (folder/"scenario.json").write_text(json.dumps(c))
    (folder/"supervisor.json").write_text(json.dumps(result))
    (folder/"manifest.json").write_text(json.dumps({"robot_profile_sha256":profile_hash}))
    return folder

@pytest.mark.parametrize("changes",[{"force":20},{"task_goal":4},{"profile_hash":"b"}])
def test_report_does_not_pool_incompatible_conditions(tmp_path,changes):
    a=synthetic_trial(tmp_path/"a")
    b=synthetic_trial(tmp_path/"b",**changes)
    assert len(summarize([a,b]))==2

def test_report_rejects_duplicate_inputs_and_suppresses_repeat_intervals(tmp_path):
    a=synthetic_trial(tmp_path/"a")
    with pytest.raises(ValueError,match="Repeated trial"):summarize([a,a])
    b=synthetic_trial(tmp_path/"b")
    rows=summarize([a,b])
    assert len(rows)==1
    assert rows[0]["valid"]==2
    assert rows[0]["fall_wilson95"] is None
    assert "duplicate" in rows[0]["interval_note"]

def test_report_handles_only_infrastructure_errors_and_preserves_output(tmp_path):
    trial=synthetic_trial(tmp_path/"infra",status="INFRASTRUCTURE_ERROR")
    result=write_report([trial],tmp_path/"report")
    assert result["robot_trials"]==0
    assert result["infrastructure_failures"]==1
    with pytest.raises(FileExistsError):write_report([trial],tmp_path/"report")

def test_one_command_pipeline_executes_both_real_robots(tmp_path):
    r=recipe()
    r["disturbance"]["levels"]=[{"name":"nominal","magnitude":0}]
    source=tmp_path/"experiment.json"
    source.write_text(json.dumps(r))
    subprocess.run([sys.executable,str(ROOT/"scripts/evaluate.py"),"--experiment",str(source),
                    "--output",str(tmp_path/"evaluation"),"--workers","2"],check=True,
                   stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=60)
    summary=json.loads((tmp_path/"evaluation/report/summary.json").read_text())
    assert summary["robots"]==["g1","go1"]
    assert summary["runs"]==summary["robot_trials"]==2
    assert summary["infrastructure_failures"]==0
    assert all(row["outcomes"]=={"COMPLETED":1} for row in summary["conditions"])
