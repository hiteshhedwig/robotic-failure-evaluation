"""Headless adaptation of Unitree's pinned MuJoCo deployment loop."""
import hashlib
import subprocess
from pathlib import Path
import sys
import numpy as np
import mujoco
import torch
import yaml

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / ".deps/unitree_rl_gym"
REVISION = "276801e46c5d433564f24658bac64f254b7d2d4b"
sys.path.insert(0, str(UPSTREAM))
# Reuse upstream control and observation math without editing vendor files.
from deploy.deploy_mujoco.deploy_mujoco import pd_control, get_gravity_orientation

class G1Simulation:
    def __init__(self, command, seed=0):
        actual=subprocess.check_output(["git","-C",str(UPSTREAM),"rev-parse","HEAD"],text=True).strip()
        if actual!=REVISION:
            raise RuntimeError("Upstream revision differs from the pinned deployment")
        torch.set_num_threads(1)
        torch.manual_seed(seed)
        self.rng = np.random.default_rng(seed)
        self.config_path = UPSTREAM / "deploy/deploy_mujoco/configs/g1.yaml"
        self.config = yaml.safe_load(self.config_path.read_text())
        c = self.config
        self.model_path = Path(c["xml_path"].replace("{LEGGED_GYM_ROOT_DIR}", str(UPSTREAM)))
        self.policy_path = Path(c["policy_path"].replace("{LEGGED_GYM_ROOT_DIR}", str(UPSTREAM)))
        self.model = mujoco.MjModel.from_xml_path(str(self.model_path))
        self.data = mujoco.MjData(self.model)
        self.model.opt.timestep = c["simulation_dt"]
        self.policy = torch.jit.load(str(self.policy_path), map_location="cpu").eval()
        self.policy.reset_memory()
        self.kp = np.array(c["kps"], dtype=np.float32)
        self.kd = np.array(c["kds"], dtype=np.float32)
        self.default = np.array(c["default_angles"], dtype=np.float32)
        self.target = self.default.copy()
        self.action = np.zeros(c["num_actions"], dtype=np.float32)
        self.obs = np.zeros(c["num_obs"], dtype=np.float32)
        self.command = np.array(command, dtype=np.float32)
        self.counter = 0
        self.root = self.model.body("pelvis").id
        self.floor = self.model.geom("floor").id
        mujoco.mj_forward(self.model, self.data)

    def step(self):
        c, d = self.config, self.data
        # Same effort calculation, scaling, cadence and phase as upstream.
        d.ctrl[:] = pd_control(self.target, d.qpos[7:], self.kp,
                              np.zeros_like(self.kd), d.qvel[6:], self.kd)
        mujoco.mj_step(self.model, d)
        self.counter += 1
        if self.counter % c["control_decimation"] == 0:
            self.obs[:3] = d.qvel[3:6] * c["ang_vel_scale"]
            self.obs[3:6] = get_gravity_orientation(d.qpos[3:7])
            self.obs[6:9] = self.command * np.array(c["cmd_scale"], dtype=np.float32)
            n = c["num_actions"]
            self.obs[9:9+n] = (d.qpos[7:]-self.default) * c["dof_pos_scale"]
            self.obs[9+n:9+2*n] = d.qvel[6:] * c["dof_vel_scale"]
            self.obs[9+2*n:9+3*n] = self.action
            phase = (self.counter*c["simulation_dt"]) % 0.8 / 0.8
            self.obs[9+3*n:9+3*n+2] = [np.sin(2*np.pi*phase), np.cos(2*np.pi*phase)]
            with torch.inference_mode():
                self.action = self.policy(torch.from_numpy(self.obs).unsqueeze(0)).numpy().squeeze()
            self.target = self.action*c["action_scale"] + self.default

    def state(self):
        d, m = self.data, self.model
        contacts = []
        for contact in d.contact:
            a, b = int(contact.geom1), int(contact.geom2)
            if self.floor in (a, b):
                geom = b if a == self.floor else a
                body = m.body(int(m.geom_bodyid[geom])).name
                contacts.append(body)
        return {"time_s": float(d.time), "position": d.xpos[self.root].tolist(),
                "tilt_deg": float(np.rad2deg(np.arccos(np.clip(d.xmat[self.root,8],-1,1)))),
                "velocity": d.qvel[:3].tolist(), "qpos": d.qpos.tolist(),
                "qvel": d.qvel.tolist(), "action": self.action.tolist(),
                "effort": d.ctrl.tolist(), "floor_contact_bodies": sorted(set(contacts))}

    def fingerprint(self):
        digest = hashlib.sha256()
        for path in sorted(self.model_path.parent.rglob("*")):
            if path.is_file():
                digest.update(str(path.relative_to(self.model_path.parent)).encode())
                digest.update(hashlib.sha256(path.read_bytes()).digest())
        code = hashlib.sha256()
        for path in sorted((ROOT/"robot_eval").glob("*.py")) + [ROOT/"scripts/run_trial.py"]:
            code.update(path.name.encode())
            code.update(path.read_bytes())
        return {"upstream_revision": REVISION, "evaluation_code_sha256":code.hexdigest(),
                "policy_sha256": hashlib.sha256(self.policy_path.read_bytes()).hexdigest(),
                "model_tree_sha256": digest.hexdigest(),
                "deployment_config_sha256": hashlib.sha256(self.config_path.read_bytes()).hexdigest(),
                "deployment_config": self.config, "mujoco": mujoco.__version__,
                "torch": torch.__version__, "numpy": np.__version__,
                "inference_device": "cpu", "torch_threads": torch.get_num_threads()}
