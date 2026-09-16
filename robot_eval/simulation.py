"""Headless adaptation of Unitree's pinned MuJoCo deployment loop."""
import subprocess
from pathlib import Path
import sys
import numpy as np
import mujoco
import torch
import yaml

from .base import ROOT, MuJoCoAdapter
UPSTREAM = ROOT / ".deps/unitree_rl_gym"
REVISION = "276801e46c5d433564f24658bac64f254b7d2d4b"
sys.path.insert(0, str(UPSTREAM))
# Reuse upstream control and observation math without editing vendor files.
from deploy.deploy_mujoco.deploy_mujoco import pd_control, get_gravity_orientation

class G1Simulation(MuJoCoAdapter):
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

    def fingerprint(self):
        meta = super().fingerprint()
        meta.update(upstream_revision=REVISION, torch=torch.__version__,
                    torch_threads=torch.get_num_threads())
        return meta
