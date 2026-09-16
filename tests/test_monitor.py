"""Detector checks include actual MuJoCo contacts; no robot success is mocked."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import mujoco
import numpy as np
from robot_eval.simulation import G1Simulation
from robot_eval.monitor import WalkingMonitor

def test_walking_foot_contacts_are_not_falls():
    sim=G1Simulation([0.5,0,0])
    monitor=WalkingMonitor()
    feet=set()
    for _ in range(1500):
        sim.step()
        state=sim.state()
        monitor.update(state)
        feet.update(state["floor_contact_bodies"])
    assert any("ankle_roll" in body for body in feet)
    assert monitor.fall_time is None
    assert monitor.posture_time is None
    assert sim.data.qpos[0]>1.0

def test_a_physically_fallen_body_is_detected():
    sim=G1Simulation([0.5,0,0])
    sim.data.qpos[:3]=[0,0,0.2]
    sim.data.qpos[3:7]=[np.sqrt(0.5),np.sqrt(0.5),0,0]
    mujoco.mj_forward(sim.model,sim.data)
    monitor=WalkingMonitor()
    saw_contact=False
    for _ in range(500):
        sim.data.ctrl[:]=0
        mujoco.mj_step(sim.model,sim.data)
        state=sim.state()
        monitor.update(state)
        saw_contact=saw_contact or "pelvis" in state["floor_contact_bodies"]
    assert saw_contact
    assert monitor.fall_time is not None
    assert monitor.fall_time>=0.02

def test_recurrent_policy_is_fresh_per_episode():
    first=G1Simulation([0.5,0,0])
    for _ in range(30):
        first.step()
    assert bool(first.policy.hidden_state.count_nonzero())
    second=G1Simulation([0.5,0,0])
    assert not bool(second.policy.hidden_state.count_nonzero())
    assert not bool(second.policy.cell_state.count_nonzero())

def test_push_is_not_an_automatic_failure():
    import json
    results=[]
    for n in (25,100,250):
        path=ROOT/"artifacts/push-pilot"/("push-y-"+str(n))/"result.json"
        r=json.loads(path.read_text())
        results.append(r)
        assert r["injected_push"] is not None
        assert abs(r["actual_impulse_ns"][1]-n*0.2)<1e-8
    assert [r["status"] for r in results]==["COMPLETED","COMPLETED","FALL"]
    assert results[1]["recovery_latency_s"]>results[0]["recovery_latency_s"]
    assert results[2]["recovery_latency_s"] is None
