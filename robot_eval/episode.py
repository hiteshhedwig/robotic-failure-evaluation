"""Robot-independent walking episode lifecycle; adapters own model/controller details."""
import json
from pathlib import Path
import platform
import sys
import time
import traceback
import numpy as np
from .base import source_fingerprint
from .disturbances import ForcePulse
from .monitor import WalkingMonitor
from .scenarios import validate, timing

def run_episode(config,output):
    out=Path(output)
    out.mkdir(parents=True,exist_ok=False)
    (out/"scenario.json").write_text(json.dumps(config,indent=2)+"\n")
    started=time.monotonic()
    result={"status":"INFRASTRUCTURE_ERROR","scenario_id":config.get("id"),
            "seed":config.get("seed"),"robot":config.get("robot","g1")}
    sim=pulse=None

    def event(kind,**data):
        with (out/"events.jsonl").open("a") as log:
            log.write(json.dumps({"event":kind,**data},allow_nan=False)+"\n")
    try:
        profile=validate(config)
        sim,provenance=profile.create(config["command"],config["seed"])
        grid=timing(config,float(sim.model.opt.timestep))
        pulse=ForcePulse(config.get("push"),grid)
        monitor=WalkingMonitor(config["command"][0],limits=profile.monitor)
        initial=sim.state()
        meta={**sim.fingerprint(),**provenance,"evaluation_code_sha256":source_fingerprint(),
              "python":sys.version,"platform":platform.platform(),"robot":profile.id,
              "initial_qpos":sim.data.qpos.tolist(),"initial_qvel":sim.data.qvel.tolist(),
              "policy_state":profile.definition["policy_state"],
              "detectors":profile.monitor,"timing":grid.manifest(),
              "body_mass_kg":float(sim.model.body_subtreemass[sim.root]),
              "gravity_m_s2":float(np.linalg.norm(sim.model.opt.gravity))}
        (out/"manifest.json").write_text(json.dumps(meta,indent=2)+"\n")
        result.update(robot_profile_sha256=profile.sha256,
                      experiment=config.get("experiment"))
        event("RUN_STARTED",time_s=float(sim.data.time),physics_dt_s=grid.dt,
              policy_dt_s=grid.dt*sim.config["control_decimation"])
        origin=None
        min_height=float("inf")
        max_tilt=peak_after_push=0
        samples=0
        with (out/"trace.jsonl").open("w") as trace:
            for i in range(grid.steps):
                active,force=pulse.apply(sim,i)
                if grid.begin is not None and i==grid.begin:
                    event("PUSH_STARTED",time_s=float(sim.data.time),force_world_n=pulse.force.tolist(),
                          body=profile.definition["root_body"],point="body center of mass")
                if grid.finish is not None and i==grid.finish:
                    event("PUSH_ENDED",time_s=float(sim.data.time),impulse_ns=pulse.impulse.tolist())
                sim.step()
                if (not np.isfinite(sim.data.qpos).all() or not np.isfinite(sim.data.qvel).all()
                        or any(w.number for w in sim.data.warning)):
                    result["status"]="INVALID_SIMULATION"
                    event("NUMERICAL_WARNING",time_s=float(sim.data.time),
                          warning_counts=[int(w.number) for w in sim.data.warning])
                    break
                state=sim.state()
                previous=(monitor.fall_time,monitor.posture_time,monitor.recovery_time)
                monitor.update(state,pulse.end_s)
                for old,new,kind in zip(previous,
                        (monitor.fall_time,monitor.posture_time,monitor.recovery_time),
                        ("FALL_DETECTED","POSTURE_VIOLATION","RECOVERY_CONFIRMED")):
                    if old is None and new is not None:
                        event(kind,time_s=new,position=state["position"],tilt_deg=state["tilt_deg"],
                              floor_contact_bodies=state["floor_contact_bodies"])
                if i>=grid.warmup:
                    if origin is None:
                        origin=state["position"]
                        event("EVALUATION_STARTED",time_s=state["time_s"],position=origin)
                    min_height=min(min_height,state["position"][2])
                    max_tilt=max(max_tilt,state["tilt_deg"])
                if grid.begin is not None and i>=grid.begin:
                    peak_after_push=max(peak_after_push,state["tilt_deg"])
                if i%round(0.02/grid.dt)==0 or monitor.fall_time is not None or i==grid.steps-1:
                    state.update(push_active=bool(active),applied_force_world_n=force.tolist())
                    trace.write(json.dumps(state,allow_nan=False)+"\n")
                    samples+=1
                if monitor.fall_time is not None:
                    break
        pulse.clear(sim)
        if result["status"]=="INVALID_SIMULATION":
            return result
        end=sim.state()
        origin=origin or initial["position"]
        progress=end["position"][0]-origin[0]
        if result["status"]!="INVALID_SIMULATION":
            result["status"]=("FALL" if monitor.fall_time is not None else
                              "POSTURE_VIOLATION" if monitor.posture_time is not None else
                              "COMPLETED" if progress>=config["minimum_progress_m"] else "TASK_TIMEOUT")
        result.update(progress_m=progress,lateral_displacement_m=end["position"][1]-origin[1],
                      min_root_height_m=min_height if np.isfinite(min_height) else None,
                      max_tilt_deg=max_tilt,peak_tilt_after_push_deg=peak_after_push if config.get("push") else None,
                      fall_time_s=monitor.fall_time,posture_violation_time_s=monitor.posture_time,
                      recovery_confirmed_time_s=monitor.recovery_time,
                      recovery_latency_s=monitor.recovery_time-pulse.end_s if pulse.end_s is not None and monitor.recovery_time is not None else None,
                      injected_push=config.get("push"),actual_impulse_ns=pulse.impulse.tolist(),
                      final_position=end["position"],simulated_seconds=end["time_s"],
                      trace_samples=samples,physics_steps=sim.counter,initial_evaluation_position=origin)
        event("RUN_FINISHED",time_s=end["time_s"],outcome=result["status"])
    except Exception as exc:
        result["error"]=str(exc)
        event("INFRASTRUCTURE_ERROR",error=str(exc))
        (out/"error.log").write_text(traceback.format_exc())
    finally:
        if sim is not None and pulse is not None:
            pulse.clear(sim)
        result["wall_seconds"]=time.monotonic()-started
        temp=out/"result.tmp"
        temp.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
        temp.replace(out/"result.json")
    return result
