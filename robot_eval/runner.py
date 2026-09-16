"""Fresh-process episodes, bounded wall time, and honest infrastructure outcomes."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import re

ROOT=Path(__file__).resolve().parents[1]
ROBOT_OUTCOMES={"COMPLETED","FALL","POSTURE_VIOLATION","TASK_TIMEOUT"}

def stop_group(process):
    try:
        os.killpg(process.pid,signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=3)

def run_one(scenario,output,timeout_s=30,kill_when_trace_ready=False):
    if not re.fullmatch(r"[A-Za-z0-9_-]+",scenario["id"]):
        raise ValueError("Scenario id must be a safe file name")
    output=Path(output).resolve()
    if output.exists():
        raise FileExistsError("Refusing to overwrite trial: "+str(output))
    output.parent.mkdir(parents=True,exist_ok=True)
    inputs=output.parent/".inputs"
    logs=output.parent/".logs"
    inputs.mkdir(exist_ok=True)
    logs.mkdir(exist_ok=True)
    source=inputs/(output.name+".json")
    source.write_text(json.dumps(scenario,indent=2)+"\n")
    started=time.monotonic()
    timed_out=False
    injected_crash=False
    with (logs/(output.name+".log")).open("w") as log:
        process=subprocess.Popen(
            [sys.executable,str(ROOT/"scripts/run_trial.py"),"--scenario",str(source),"--output",str(output)],
            cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
            env={**os.environ,"OMP_NUM_THREADS":"1","MKL_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1"})
        try:
            while process.poll() is None:
                trace=output/"trace.jsonl"
                if kill_when_trace_ready and trace.exists() and trace.stat().st_size>12000:
                    os.killpg(process.pid,signal.SIGKILL)
                    injected_crash=True
                    break
                if time.monotonic()-started>=timeout_s:
                    timed_out=True
                    break
                time.sleep(0.02)
        finally:
            stop_group(process)
    output.mkdir(parents=True,exist_ok=True)
    (output/"scenario.json").write_text(json.dumps(scenario,indent=2)+"\n")
    if timed_out:
        result={"status":"INFRASTRUCTURE_TIMEOUT","reason":"Parent wall-clock deadline"}
    elif not (output/"result.json").exists():
        result={"status":"INFRASTRUCTURE_ERROR","reason":"Worker exited without an atomic result receipt"}
    else:
        try:
            result=json.loads((output/"result.json").read_text())
            expected=0 if result["status"]=="COMPLETED" else 2 if result["status"] in ROBOT_OUTCOMES else 3
            if process.returncode!=expected:
                result={"status":"INFRASTRUCTURE_ERROR","reason":"Worker result/exit-code inconsistency"}
        except (ValueError,KeyError):
            result={"status":"INFRASTRUCTURE_ERROR","reason":"Malformed worker receipt"}
    result.update(scenario_id=scenario["id"],seed=scenario["seed"],robot=scenario.get("robot","g1"),
                  worker_returncode=process.returncode,worker_pid=process.pid,
                  supervisor_wall_seconds=time.monotonic()-started,
                  wall_timeout_s=timeout_s,crash_injected=injected_crash)
    (output/"supervisor.json").write_text(json.dumps(result,indent=2)+"\n")
    return result
