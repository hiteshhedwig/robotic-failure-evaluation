"""Shared MuJoCo state/provenance helpers; no robot or policy runtime imports."""
from pathlib import Path
from typing import Protocol
import hashlib
import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

def source_fingerprint():
    digest = hashlib.sha256()
    paths = sorted((ROOT / "robot_eval").rglob("*.py")) + [ROOT / "scripts/run_trial.py"]
    for path in paths:
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()

class RobotAdapter(Protocol):
    """A fresh model/controller instance per episode; no global control callbacks."""
    model: mujoco.MjModel
    data: mujoco.MjData
    config: dict
    root: int
    floor: int
    counter: int

    def step(self) -> None: ...
    def state(self) -> dict: ...
    def fingerprint(self) -> dict: ...
    def apply_force_world(self, force) -> None: ...

class MuJoCoAdapter:
    """Optional base for adapters; subclasses load/reset models and implement step."""
    def apply_force_world(self, force):
        self.data.xfrc_applied[:] = 0
        self.data.xfrc_applied[self.root, :3] = force

    def state(self):
        d, m = self.data, self.model
        contacts = set()
        for contact in d.contact:
            a, b = int(contact.geom1), int(contact.geom2)
            if self.floor in (a, b):
                geom = b if a == self.floor else a
                contacts.add(m.body(int(m.geom_bodyid[geom])).name)
        return {"time_s": float(d.time), "position": d.xpos[self.root].tolist(),
                "tilt_deg": float(np.rad2deg(np.arccos(np.clip(d.xmat[self.root, 8], -1, 1)))),
                "velocity": d.qvel[:3].tolist(), "qpos": d.qpos.tolist(),
                "qvel": d.qvel.tolist(), "action": self.action.tolist(),
                "effort": d.actuator_force.tolist(),
                "control": d.ctrl.tolist(), "floor_contact_bodies": sorted(contacts)}

    def fingerprint(self):
        digest = hashlib.sha256()
        for directory in getattr(self, "asset_directories", [self.model_path.parent]):
            for path in sorted(directory.rglob("*")):
                if path.is_file():
                    digest.update(str(path.relative_to(directory)).encode())
                    digest.update(hashlib.sha256(path.read_bytes()).digest())
        return {"evaluation_code_sha256": source_fingerprint(),
                "policy_sha256": hashlib.sha256(self.policy_path.read_bytes()).hexdigest(),
                "model_tree_sha256": digest.hexdigest(),
                "deployment_config_sha256": hashlib.sha256(self.config_path.read_bytes()).hexdigest(),
                "deployment_config": self.config, "mujoco": mujoco.__version__,
                "numpy": np.__version__, "inference_device": "cpu"}
