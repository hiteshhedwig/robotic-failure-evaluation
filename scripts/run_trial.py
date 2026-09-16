#!/usr/bin/env python3
"""One real-physics episode. A supervisor process supplies the wall-clock deadline."""
import argparse
import json
from pathlib import Path
import platform
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from humanoid_eval.simulation import G1Simulation
from humanoid_eval.monitor import WalkingMonitor

ALLOWED={"id","seed","duration_s","warmup_s","command","minimum_progress_m","push"}

def validate(c):
    extra=set(c)-ALLOWED
    if extra:
        raise ValueError("Unknown scenario keys: "+str(sorted(extra)))
    for key in ["duration_s","warmup_s","minimum_progress_m"]:
        if not isinstance(c[key],(int,float)) or not np.isfinite(c[key]):
            raise ValueError("Invalid "+key)
    if not 0<=c["warmup_s"]<c["duration_s"]<=60 or c["minimum_progress_m"]<=0:
        raise ValueError("Invalid duration/warmup/task objective")
    if len(c["command"])!=3 or not np.isfinite(c["command"]).all():
        raise ValueError("Expected finite [vx, vy, yaw_rate]")
    p=c.get("push")
    if p:
        if set(p)!={"force_n","start_s","duration_s"}:
            raise ValueError("Push requires exactly force_n, start_s, duration_s")
        if len(p["force_n"])!=3 or not np.isfinite(p["force_n"]).all():
            raise ValueError("Expected finite world-frame force vector")
        if not np.isfinite([p["start_s"],p["duration_s"]]).all():
            raise ValueError("Invalid push time")
        if not c["warmup_s"]<=p["start_s"] or not 0<p["duration_s"]<=1:
            raise ValueError("Push must follow warmup; duration must be in (0,1]")
        if p["start_s"]+p["duration_s"]>=c["duration_s"]:
            raise ValueError("Push must finish before episode end")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--scenario",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--seed",type=int)
    args=p.parse_args()
    config=json.loads(Path(args.scenario).read_text())
    if args.seed is not None:
        config["seed"]=args.seed
    out=Path(args.output)
    out.mkdir(parents=True,exist_ok=False)
    (out/"scenario.json").write_text(json.dumps(config,indent=2)+"\n")
    started=time.monotonic()
    result={"status":"INFRASTRUCTURE_ERROR","scenario_id":config.get("id"),"seed":config.get("seed")}
    events=[]
    def event(kind,**data):
        events.append({"event":kind,**data})
        with (out/"events.jsonl").open("a") as log:
            log.write(json.dumps(events[-1],allow_nan=False)+"\n")
    try:
        validate(config)
        sim=G1Simulation(config["command"],config["seed"])
        dt=float(sim.model.opt.timestep)
        steps=round(config["duration_s"]/dt)
        warmup=round(config["warmup_s"]/dt)
        push=config.get("push")
        begin=round(push["start_s"]/dt) if push else None
        finish=begin+round(push["duration_s"]/dt) if push else None
        force=np.array(push["force_n"],dtype=float) if push else np.zeros(3)
        monitor=WalkingMonitor(config["command"][0])
        initial=sim.state()
        meta={**sim.fingerprint(),"python":sys.version,"platform":platform.platform(),
              "initial_qpos":sim.data.qpos.tolist(),"initial_qvel":sim.data.qvel.tolist(),
              "policy_recurrent_state":"Fresh checkpoint; hidden_state and cell_state start at zero",
              "detectors":{"fall":"pelvis-floor contact persists 0.02 s",
                           "posture_violation":"tilt > 60 deg OR pelvis height < 0.45 m for 0.1 s",
                           "recovery":"tilt <=10 deg, height >=0.65 m, |vx-command| <=0.25 m/s, |vy| <=0.25 m/s for 0.4 s"}}
        (out/"manifest.json").write_text(json.dumps(meta,indent=2)+"\n")
        event("RUN_STARTED",time_s=0,physics_dt_s=dt,policy_dt_s=dt*sim.config["control_decimation"])
        origin=None
        min_height=float("inf")
        max_tilt=0
        samples=0
        impulse=np.zeros(3)
        peak_after_push=0
        with (out/"trace.jsonl").open("w") as trace:
            for i in range(steps):
                active=push is not None and begin<=i<finish
                sim.data.xfrc_applied[:]=0
                if active:
                    sim.data.xfrc_applied[sim.root,:3]=force
                    impulse+=force*dt
                if push and i==begin:
                    event("PUSH_STARTED",time_s=float(sim.data.time),force_world_n=force.tolist(),
                          body="pelvis (rigid torso/arms share this body)",point="body center of mass")
                if push and i==finish:
                    event("PUSH_ENDED",time_s=float(sim.data.time),impulse_ns=impulse.tolist())
                sim.step()
                if not np.isfinite(sim.data.qpos).all() or not np.isfinite(sim.data.qvel).all():
                    raise RuntimeError("Non-finite physics state")
                if any(w.number for w in sim.data.warning):
                    result["status"]="INVALID_SIMULATION"
                    event("NUMERICAL_WARNING",time_s=float(sim.data.time),
                          warning_counts=[int(w.number) for w in sim.data.warning])
                    break
                state=sim.state()
                previous=(monitor.fall_time,monitor.posture_time,monitor.recovery_time)
                monitor.update(state,finish*dt if push else None)
                for old,new,kind in zip(previous,(monitor.fall_time,monitor.posture_time,monitor.recovery_time),
                                        ("FALL_DETECTED","POSTURE_VIOLATION","RECOVERY_CONFIRMED")):
                    if old is None and new is not None:
                        event(kind,time_s=new,position=state["position"],tilt_deg=state["tilt_deg"],
                              floor_contact_bodies=state["floor_contact_bodies"])
                if i>=warmup:
                    if origin is None:
                        origin=state["position"]
                        event("EVALUATION_STARTED",time_s=state["time_s"],position=origin)
                    min_height=min(min_height,state["position"][2])
                    max_tilt=max(max_tilt,state["tilt_deg"])
                if push and i>=begin:
                    peak_after_push=max(peak_after_push,state["tilt_deg"])
                if i%10==0 or monitor.fall_time is not None or i==steps-1:
                    state["push_active"]=bool(active)
                    state["applied_force_world_n"]=force.tolist() if active else [0,0,0]
                    trace.write(json.dumps(state,allow_nan=False)+"\n")
                    samples+=1
                if monitor.fall_time is not None:
                    break
        sim.data.xfrc_applied[:]=0
        end=sim.state()
        origin=origin or initial["position"]
        progress=end["position"][0]-origin[0]
        if result["status"]!="INVALID_SIMULATION":
            result["status"]=("FALL" if monitor.fall_time is not None else
                              "POSTURE_VIOLATION" if monitor.posture_time is not None else
                              "COMPLETED" if progress>=config["minimum_progress_m"] else "TASK_TIMEOUT")
        result.update(progress_m=progress,lateral_displacement_m=end["position"][1]-origin[1],
                      min_pelvis_height_m=min_height if np.isfinite(min_height) else None,
                      max_tilt_deg=max_tilt,peak_tilt_after_push_deg=peak_after_push if push else None,
                      fall_time_s=monitor.fall_time,posture_violation_time_s=monitor.posture_time,
                      recovery_confirmed_time_s=monitor.recovery_time,
                      recovery_latency_s=monitor.recovery_time-finish*dt if push and monitor.recovery_time is not None else None,
                      injected_push=push,actual_impulse_ns=impulse.tolist(),
                      final_position=end["position"],simulated_seconds=end["time_s"],
                      trace_samples=samples,physics_steps=sim.counter,
                      initial_evaluation_position=origin)
        event("RUN_FINISHED",time_s=end["time_s"],outcome=result["status"])
    except Exception as exc:
        result["error"]=str(exc)
        event("INFRASTRUCTURE_ERROR",error=str(exc))
        (out/"error.log").write_text(traceback.format_exc())
    finally:
        result["wall_seconds"]=time.monotonic()-started
        temp=out/"result.tmp"
        temp.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
        temp.replace(out/"result.json")
    print(json.dumps(result),flush=True)
    sys.exit(0 if result["status"]=="COMPLETED" else 3 if result["status"] in ("INFRASTRUCTURE_ERROR","INVALID_SIMULATION") else 2)

if __name__=="__main__":
    main()
