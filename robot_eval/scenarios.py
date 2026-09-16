"""Strict walking-task scenario validation and explicit physics-grid timing."""
from dataclasses import dataclass
import math
from .profiles import SAFE_ID, finite_number, resolve_profile

ALLOWED={"id","seed","duration_s","warmup_s","command","minimum_progress_m",
         "push","robot","robot_profile","experiment"}

def vector(value,name):
    if not isinstance(value,list) or len(value)!=3:
        raise ValueError(name+" must contain three numbers")
    for x in value:
        if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x):
            raise ValueError(name+" must contain finite numbers")

def validate(c):
    if not isinstance(c,dict) or set(c)-ALLOWED:
        raise ValueError("Unknown scenario keys or non-object scenario")
    if not isinstance(c.get("id"),str) or not SAFE_ID.fullmatch(c["id"]):
        raise ValueError("Invalid scenario id")
    if not isinstance(c.get("seed"),int) or isinstance(c["seed"],bool) or c["seed"]<0:
        raise ValueError("seed must be a nonnegative integer")
    for key in ("duration_s","warmup_s","minimum_progress_m"):
        finite_number(c.get(key),key)
    if not 0<=c["warmup_s"]<c["duration_s"]<=60 or c["minimum_progress_m"]<=0:
        raise ValueError("Invalid duration/warmup/task objective")
    vector(c.get("command"),"command")
    profile=resolve_profile(c.get("robot","g1"),c.get("robot_profile"))
    push=c.get("push")
    if push is not None:
        if not isinstance(push,dict) or set(push)!={"force_n","start_s","duration_s"}:
            raise ValueError("Push requires exactly force_n, start_s, duration_s")
        vector(push["force_n"],"force_n")
        finite_number(push["start_s"],"push start")
        finite_number(push["duration_s"],"push duration",strictly_positive=True)
        if push["start_s"]<c["warmup_s"] or push["duration_s"]>1:
            raise ValueError("Push must follow warmup and last at most one second")
        if push["start_s"]+push["duration_s"]>=c["duration_s"]:
            raise ValueError("Push must finish before episode end")
    experiment=c.get("experiment")
    if experiment is not None:
        keys={"id","condition","schedule_id","force_mode","magnitude","body_mass_kg","gravity_m_s2"}
        if not isinstance(experiment,dict) or set(experiment)!=keys:
            raise ValueError("Invalid experiment metadata")
        for key in ("id","condition","schedule_id"):
            if not isinstance(experiment[key],str) or not SAFE_ID.fullmatch(experiment[key]):
                raise ValueError("Invalid experiment "+key)
        if experiment["force_mode"] not in ("newtons","body_weight"):
            raise ValueError("Invalid force_mode")
        for key in ("magnitude","body_mass_kg","gravity_m_s2"):
            finite_number(experiment[key],key,strictly_positive=key!="magnitude")
    return profile

@dataclass(frozen=True)
class EpisodeTiming:
    dt: float
    steps: int
    warmup: int
    begin: int | None
    finish: int | None

    def manifest(self):
        return {"physics_dt_s":self.dt,"trace_dt_s":0.02,
                "realized_duration_s":self.steps*self.dt,
                "realized_warmup_s":self.warmup*self.dt,
                "realized_push_start_s":None if self.begin is None else self.begin*self.dt,
                "realized_push_end_s":None if self.finish is None else self.finish*self.dt}

def timing(c,dt):
    steps,warmup=round(c["duration_s"]/dt),round(c["warmup_s"]/dt)
    push=c.get("push")
    begin=round(push["start_s"]/dt) if push is not None else None
    finish=begin+round(push["duration_s"]/dt) if push is not None else None
    if not 0<=warmup<steps:
        raise ValueError("Task interval collapses on the physics grid")
    if begin is not None and not warmup<=begin<finish<steps:
        raise ValueError("Push interval collapses or leaves the task on the physics grid")
    return EpisodeTiming(dt,steps,warmup,begin,finish)
