"""Expand a reusable experiment recipe into explicit, portable trial scenarios."""
from copy import deepcopy
import math
import random
import numpy as np
from .profiles import finite_number, resolve_profile, SAFE_ID
from .scenarios import validate, vector, timing

def generate_suite(recipe,profiles_directory=None):
    required={"schema_version","id","robots","seeds","task","disturbance"}
    if not isinstance(recipe,dict) or set(recipe)-required-{"notes"} or not required<=set(recipe):
        raise ValueError("Experiment has missing or unknown fields")
    if recipe["schema_version"]!=1 or not isinstance(recipe["id"],str) or not SAFE_ID.fullmatch(recipe["id"]):
        raise ValueError("Invalid experiment version/id")
    robots,seeds=recipe["robots"],recipe["seeds"]
    if not isinstance(robots,list) or not robots or any(not isinstance(r,str) for r in robots) or len(set(robots))!=len(robots):
        raise ValueError("robots must be a nonempty unique list")
    if not isinstance(seeds,list) or not seeds or any(isinstance(s,bool) or not isinstance(s,int) or s<0 for s in seeds) or len(set(seeds))!=len(seeds):
        raise ValueError("seeds must be unique nonnegative integers")
    task=recipe["task"]
    if not isinstance(task,dict) or set(task)!={"duration_s","warmup_s","command","minimum_progress_m"}:
        raise ValueError("Unsupported task; expected the walking-distance fields")
    disturbance=recipe["disturbance"]
    keys={"type","force_mode","duration_s","onset_range_s","directions","levels"}
    if not isinstance(disturbance,dict) or set(disturbance)!=keys:
        raise ValueError("Disturbance has missing or unknown fields")
    if disturbance["type"]!="root_force_pulse" or disturbance["force_mode"] not in ("newtons","body_weight"):
        raise ValueError("Unsupported disturbance type or force_mode")
    finite_number(disturbance["duration_s"],"pulse duration",strictly_positive=True)
    onset=disturbance["onset_range_s"]
    if not isinstance(onset,list) or len(onset)!=2:
        raise ValueError("onset_range_s must contain two numbers")
    for value in onset:finite_number(value,"onset")
    if onset[0]>onset[1]:raise ValueError("Invalid onset range")
    directions=disturbance["directions"]
    if not isinstance(directions,list) or not directions:raise ValueError("Directions are required")
    for direction in directions:
        vector(direction,"direction")
        if math.sqrt(sum(v*v for v in direction))==0:
            raise ValueError("Direction must be nonzero")
    levels=disturbance["levels"]
    if not isinstance(levels,list) or not levels:raise ValueError("Force levels are required")
    for level in levels:
        if not isinstance(level,dict) or set(level)!={"name","magnitude"}:
            raise ValueError("Force level requires name and magnitude")
        if not isinstance(level["name"],str) or not SAFE_ID.fullmatch(level["name"]):
            raise ValueError("Invalid force-level name")
        finite_number(level["magnitude"],"force magnitude")
    if len({level["name"] for level in levels})!=len(levels):
        raise ValueError("Duplicate condition name")
    if len(robots)*len(seeds)*len(levels)>256:
        raise ValueError("Recipe exceeds the 256-trial local generation limit; split the campaign")
    profiles={robot:resolve_profile(robot,directory=profiles_directory) for robot in robots}
    # Validate the maximum disturbance interval before loading model/policy assets.
    for robot,profile in profiles.items():
        validate({"id":"validation","robot":robot,"robot_profile":profile.definition,"seed":seeds[0],
                  **task,"push":{"force_n":[1,0,0],"start_s":onset[1],"duration_s":disturbance["duration_s"]}})
    if onset[0]<task["warmup_s"]:raise ValueError("Onset range must follow warmup")
    probes={}
    for robot,profile in profiles.items():
        sim,_=profile.create(task["command"],seeds[0])
        probes[robot]={"physics_dt_s":float(sim.model.opt.timestep),
                       "body_mass_kg":float(sim.model.body_subtreemass[sim.root]),
                       "gravity_m_s2":float(np.linalg.norm(sim.model.opt.gravity)),
                       "robot_profile_sha256":profile.sha256}
        if probes[robot]["body_mass_kg"]<=0 or probes[robot]["gravity_m_s2"]<=0:
            raise ValueError("Force normalization requires positive model mass and gravity")
        del sim
    scenarios=[]
    for seed in seeds:
        rng=random.Random(seed)
        direction=np.array(rng.choice(directions),dtype=float)
        direction/=np.linalg.norm(direction)
        requested_start=rng.uniform(*onset)
        for robot,profile in profiles.items():
            probe=probes[robot]
            for level in levels:
                magnitude=level["magnitude"]
                scale=probe["body_mass_kg"]*probe["gravity_m_s2"] if disturbance["force_mode"]=="body_weight" else 1
                scenario={"id":robot+"-"+level["name"]+"-seed"+str(seed),
                          "robot":robot,"robot_profile":deepcopy(profile.definition),"seed":seed,
                          **deepcopy(task),
                          "experiment":{"id":recipe["id"],"condition":level["name"],
                                        "schedule_id":"seed"+str(seed),"force_mode":disturbance["force_mode"],
                                        "magnitude":magnitude,"body_mass_kg":probe["body_mass_kg"],
                                        "gravity_m_s2":probe["gravity_m_s2"]}}
                if magnitude>0:
                    scenario["push"]={"force_n":(direction*magnitude*scale).tolist(),
                                      "start_s":requested_start,"duration_s":disturbance["duration_s"]}
                validate(scenario)
                timing(scenario,probe["physics_dt_s"])  # Validate realized grid, too.
                scenarios.append(scenario)
    return {"schema_version":1,"experiment":deepcopy(recipe),"robot_probes":probes,
            "sampling_note":"Seeded direction/onset schedules matched across robots and levels; realized physics-grid times are in each manifest. No cross-robot robustness ranking.",
            "scenarios":scenarios}
