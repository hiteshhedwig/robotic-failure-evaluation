"""Go1 adapter for the pinned MuJoCo Playground ONNX deployment example.

Observation order, action scaling, home keyframe, and 50 Hz control follow
Google's play_go1_joystick.py. Full body collisions replace the example's
feet-only terrain model so the evaluator can observe trunk-floor contact.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import mujoco
import numpy as np
from .simulation import G1Simulation, ROOT

PLAYGROUND=ROOT/".deps/mujoco_playground"
MENAGERIE=ROOT/".deps/mujoco_menagerie"
GO1=PLAYGROUND/"rss2025/mujoco_playground/_src/locomotion/go1"
DEPLOY=PLAYGROUND/"rss2025/mujoco_playground/experimental/sim2sim"

def load_model():
    # Match upstream get_assets() without importing its training dependencies.
    assets={}
    for directory,pattern in [(GO1/"xmls","*.xml"),(GO1/"xmls/assets","*"),
                              (MENAGERIE/"unitree_go1","*.xml"),
                              (MENAGERIE/"unitree_go1/assets","*")]:
        for p in directory.glob(pattern):
            if p.is_file(): assets[p.name]=p.read_bytes()
    path=GO1/"xmls/scene_mjx_fullcollisions_flat_terrain.xml"
    return mujoco.MjModel.from_xml_path(str(path),assets=assets)

class Go1Simulation(G1Simulation):
    def __init__(self,command,seed=0):
        sys.path.insert(0,str(ROOT/".runtime/python"))
        import onnxruntime as ort
        lock=json.loads((ROOT/"configs/go1-dependencies.json").read_text())
        for repo,key in [(PLAYGROUND,"playground_revision"),(MENAGERIE,"menagerie_revision")]:
            actual=subprocess.check_output(["git","-C",str(repo),"rev-parse","HEAD"],text=True).strip()
            if actual!=lock[key]:raise RuntimeError("Go1 asset revision mismatch")
        self.model=load_model()
        self.data=mujoco.MjData(self.model)
        mujoco.mj_resetDataKeyframe(self.model,self.data,0)
        self.model.opt.timestep=0.004
        self.model_path=GO1/"xmls/scene_mjx_fullcollisions_flat_terrain.xml"
        self.config_path=DEPLOY/"play_go1_joystick.py"
        self.policy_path=DEPLOY/"onnx/go1_policy.onnx"
        if hashlib.sha256(self.policy_path.read_bytes()).hexdigest()!=lock["policy_sha256"]:
            raise RuntimeError("Go1 policy checksum mismatch")
        options=ort.SessionOptions()
        options.intra_op_num_threads=1
        options.inter_op_num_threads=1
        self.policy=ort.InferenceSession(str(self.policy_path),sess_options=options,
                                        providers=["CPUExecutionProvider"])
        self.config={"control_decimation":5,"simulation_dt":0.004,"num_actions":12,
                     "num_obs":48,"action_scale":0.5,"controller":"MuJoCo position actuators"}
        self.default=self.model.keyframe("home").qpos[7:].copy()
        self.action=np.zeros(12,dtype=np.float32)
        self.command=np.asarray(command,dtype=np.float32)
        self.counter=0
        self.root=self.model.body("trunk").id
        self.floor=self.model.geom("floor").id
        self.ort_version=ort.__version__
        mujoco.mj_forward(self.model,self.data)

    def step(self):
        # Upstream callback executes before each physics step, including control
        # update on every fifth step. Position-actuator gains remain in XML.
        self.counter+=1
        if self.counter%5==0:
            d,m=self.data,self.model
            rotation=d.site_xmat[m.site("imu").id].reshape(3,3)
            obs=np.hstack([d.sensor("local_linvel").data,d.sensor("gyro").data,
                           rotation.T@np.array([0,0,-1]),d.qpos[7:]-self.default,
                           d.qvel[6:],self.action,self.command]).astype(np.float32)
            self.action=self.policy.run(["continuous_actions"],{"obs":obs[None,:]})[0][0]
            self.data.ctrl[:]=self.action*0.5+self.default
        mujoco.mj_step(self.model,self.data)

    def state(self):
        state=super().state()
        state["position_targets"]=self.data.ctrl.tolist()
        state["effort"]=self.data.actuator_force.tolist()
        return state

    def fingerprint(self):
        meta=super().fingerprint()
        lock=json.loads((ROOT/"configs/go1-dependencies.json").read_text())
        meta.update(lock)
        digest=hashlib.sha256()
        for directory in [GO1/"xmls",MENAGERIE/"unitree_go1"]:
            for path in sorted(directory.rglob("*")):
                if path.is_file():
                    digest.update(str(path.relative_to(directory)).encode())
                    digest.update(hashlib.sha256(path.read_bytes()).digest())
        meta.update(robot="go1",upstream_revision=lock["playground_revision"],
                    model_tree_sha256=digest.hexdigest(),onnxruntime=self.ort_version,
                    inference_device="cpu",torch_threads=None)
        return meta
