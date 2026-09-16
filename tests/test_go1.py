"""Quadruped checks use actual model contacts, policy actions and subprocesses."""
import json
from pathlib import Path
import mujoco
import numpy as np
import pytest
from robot_eval.go1 import Go1Simulation
from robot_eval.monitor import WalkingMonitor
from robot_eval.runner import run_one

ROOT=Path(__file__).resolve().parents[1]

def test_go1_walks_with_normal_foot_contacts():
    sim=Go1Simulation([0.5,0,0])
    monitor=WalkingMonitor(robot="go1")
    contacts=set()
    for _ in range(750):
        sim.step()
        state=sim.state()
        monitor.update(state)
        contacts.update(state["floor_contact_bodies"])
    assert sim.data.qpos[0]>1
    assert contacts
    assert "trunk" not in contacts
    assert monitor.fall_time is None
    assert monitor.posture_time is None
    assert np.linalg.norm(sim.action)>0
    assert sim.data.qpos.shape==(19,)

def test_go1_actual_trunk_floor_contact_is_a_fall():
    sim=Go1Simulation([0.5,0,0])
    sim.data.qpos[:3]=[0,0,0.08]
    sim.data.qpos[3:7]=[0,1,0,0]
    mujoco.mj_forward(sim.model,sim.data)
    monitor=WalkingMonitor(robot="go1")
    saw_trunk=False
    for _ in range(150):
        sim.data.ctrl[:]=sim.data.qpos[7:]
        mujoco.mj_step(sim.model,sim.data)
        state=sim.state()
        saw_trunk |= "trunk" in state["floor_contact_bodies"]
        monitor.update(state)
    assert saw_trunk
    assert monitor.fall_time is not None

def test_go1_policy_resets_previous_action():
    first=Go1Simulation([0.5,0,0])
    for _ in range(20):first.step()
    assert np.linalg.norm(first.action)>0
    second=Go1Simulation([0.5,0,0])
    assert np.count_nonzero(second.action)==0
    assert second.data.time==0

def test_go1_uses_same_runner_and_robot_specific_manifest(tmp_path):
    c=json.loads((ROOT/"configs/go1/push-y-0.json").read_text())
    result=run_one(c,tmp_path/"trial")
    assert result["status"]=="COMPLETED"
    assert result["robot"]=="go1"
    manifest=json.loads((tmp_path/"trial/manifest.json").read_text())
    assert manifest["detectors"]["posture_min_height_m"]==0.12
    assert manifest["detectors"]["recovery_min_height_m"]==0.22
    assert manifest["deployment_config"]["control_decimation"]==5
    assert manifest["inference_device"]=="cpu"
    assert manifest["menagerie_revision"]

def test_unknown_robot_is_an_infrastructure_error(tmp_path):
    c=json.loads((ROOT/"configs/go1/push-y-0.json").read_text())
    c["robot"]="unsupported"
    result=run_one(c,tmp_path/"invalid")
    assert result["status"]=="INFRASTRUCTURE_ERROR"
    assert "Unsupported robot" in result["error"]
