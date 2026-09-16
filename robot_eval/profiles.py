"""JSON robot discovery, validated monitoring settings, and lazy adapter loading.

Profiles are trusted local code configuration, not a sandbox for third-party code.
Generated scenarios embed their profile so a saved run does not silently adopt a
later edit to the installed robot defaults.
"""
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import importlib
import inspect
import json
import math
from pathlib import Path
import re
from .base import ROOT

SAFE_ID = re.compile(r"[A-Za-z0-9_-]+")
MONITOR_KEYS = {
    "fall_contact_bodies", "fall_hold_s", "posture_tilt_deg", "posture_min_height_m",
    "posture_hold_s", "recovery_tilt_deg", "recovery_min_height_m",
    "recovery_velocity_tolerance_m_s", "recovery_hold_s",
}

def finite_number(value, name, minimum=0, strictly_positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(name + " must be a finite number")
    if value < minimum or (strictly_positive and value <= 0):
        raise ValueError(name + " is out of range")
    return value

@dataclass(frozen=True)
class RobotProfile:
    definition: dict

    @property
    def id(self):
        return self.definition["id"]

    @property
    def monitor(self):
        return deepcopy(self.definition["monitor"])

    @property
    def sha256(self):
        return hashlib.sha256(json.dumps(self.definition, sort_keys=True,
            separators=(",", ":"), allow_nan=False).encode()).hexdigest()

    def create(self, command, seed):
        module_name, class_name = self.definition["adapter"].split(":")
        factory = getattr(importlib.import_module(module_name), class_name)
        sim = factory(command, seed, **deepcopy(self.definition.get("adapter_options", {})))
        for method in ("step", "state", "fingerprint", "apply_force_world"):
            if not callable(getattr(sim, method, None)):
                raise ValueError("Adapter is missing method: " + method)
        if sim.model.body(sim.root).name != self.definition["root_body"]:
            raise ValueError("Profile root_body differs from adapter root")
        if sim.model.geom(sim.floor).name != self.definition["floor_geom"]:
            raise ValueError("Profile floor_geom differs from adapter floor")
        for body in self.monitor["fall_contact_bodies"]:
            sim.model.body(body)  # MuJoCo validates the body exists.
        dt = finite_number(float(sim.model.opt.timestep), "physics timestep", strictly_positive=True)
        if not isinstance(sim.config.get("control_decimation"), int) or sim.config["control_decimation"] < 1:
            raise ValueError("Adapter needs a positive integer control_decimation")
        # This evaluator records a 50 Hz trace. Reject unsupported timing rather
        # than silently rounding the trace cadence or dividing by zero.
        if dt > 0.02 or abs(round(0.02 / dt) * dt - 0.02) > 1e-9:
            raise ValueError("Physics timestep must divide the 20 ms trace period")
        source = inspect.getsourcefile(factory)
        source_hash = hashlib.sha256(Path(source).read_bytes()).hexdigest() if source else None
        return sim, {"robot_profile": deepcopy(self.definition),
                     "robot_profile_sha256": self.sha256,
                     "adapter_source_sha256": source_hash}

def validate_profile(definition):
    if not isinstance(definition, dict):
        raise ValueError("Robot profile must be an object")
    required = {"schema_version", "id", "label", "adapter", "root_body", "floor_geom",
                "policy_state", "monitor"}
    if not required <= set(definition) or set(definition) - required - {"adapter_options"}:
        raise ValueError("Robot profile has missing or unknown fields")
    if definition["schema_version"] != 1:
        raise ValueError("Unsupported robot profile schema_version")
    if not isinstance(definition["id"], str) or not SAFE_ID.fullmatch(definition["id"]):
        raise ValueError("Invalid robot profile id")
    for key in ("label", "root_body", "floor_geom", "policy_state"):
        if not isinstance(definition[key], str) or not definition[key].strip():
            raise ValueError("Invalid profile " + key)
    if not isinstance(definition["adapter"], str) or not re.fullmatch(
            r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*", definition["adapter"]):
        raise ValueError("adapter must be an importable module:Class")
    if not isinstance(definition.get("adapter_options", {}), dict):
        raise ValueError("adapter_options must be an object")
    monitor = definition["monitor"]
    if not isinstance(monitor, dict) or set(monitor) != MONITOR_KEYS:
        raise ValueError("Monitor settings have missing or unknown fields")
    bodies = monitor["fall_contact_bodies"]
    if not isinstance(bodies, list) or not bodies or any(not isinstance(x, str) or not x for x in bodies):
        raise ValueError("fall_contact_bodies must be nonempty body names")
    for key, value in monitor.items():
        if key != "fall_contact_bodies":
            finite_number(value, key, strictly_positive=key.endswith("_s"))
    if monitor["posture_tilt_deg"] > 180 or monitor["recovery_tilt_deg"] > 180:
        raise ValueError("Tilt thresholds must be <=180 degrees")
    if monitor["recovery_min_height_m"] < monitor["posture_min_height_m"]:
        raise ValueError("Recovery height must not be below posture failure height")
    if monitor["recovery_tilt_deg"] > monitor["posture_tilt_deg"]:
        raise ValueError("Recovery tilt must not exceed posture failure tilt")
    json.dumps(definition, allow_nan=False)
    return RobotProfile(deepcopy(definition))

def discover_profiles(directory=None):
    directories=[ROOT/"configs/robots"]
    if directory is not None:
        extra=Path(directory)
        if not extra.is_dir():
            raise ValueError("Robot profile directory does not exist: "+str(extra))
        if extra.resolve()!=directories[0].resolve():
            directories.append(extra)
    profiles={}
    for directory in directories:
        for path in sorted(directory.glob("*.json")):
            profile=validate_profile(json.loads(path.read_text()))
            if profile.id in profiles:
                raise ValueError("Duplicate robot profile id: "+profile.id)
            profiles[profile.id]=profile
    return profiles

def resolve_profile(robot="g1", inline=None, directory=None):
    if inline is not None:
        profile = validate_profile(inline)
        if profile.id != robot:
            raise ValueError("Scenario robot and embedded profile id differ")
        return profile
    profiles = discover_profiles(directory)
    if robot not in profiles:
        raise ValueError("Unsupported robot: " + str(robot))
    return profiles[robot]
