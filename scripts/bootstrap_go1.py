#!/usr/bin/env python3
"""Fetch pinned Go1 deployment assets and a project-local CPU ONNX runtime."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]

def checkout(name,url,revision,paths,verify):
    repo=ROOT/".deps"/name
    def git(*args):
        return subprocess.check_output(["git","-C",str(repo),*args],text=True).strip()
    if not repo.exists():
        if verify:raise RuntimeError("Missing "+name+"; run bootstrap.py")
        repo.parent.mkdir(exist_ok=True)
        subprocess.run(["git","clone","--depth","1","--filter=blob:none","--no-checkout",url,str(repo)],check=True)
        if git("rev-parse","HEAD")!=revision:
            subprocess.run(["git","-C",str(repo),"fetch","--depth","1","--filter=blob:none","origin",revision],check=True)
        subprocess.run(["git","-C",str(repo),"sparse-checkout","init","--cone"],check=True)
        subprocess.run(["git","-C",str(repo),"sparse-checkout","set",*paths],check=True)
        subprocess.run(["git","-C",str(repo),"checkout","--detach",revision],check=True)
    if git("rev-parse","HEAD")!=revision or git("status","--porcelain","--untracked-files=no"):
        raise RuntimeError("Refusing modified or mismatched dependency: "+name)
    return repo

def setup(verify=False):
    lock=json.loads((ROOT/"configs/go1-dependencies.json").read_text())
    playground=checkout("mujoco_playground",lock["playground_repository"],
        lock["playground_revision"],["rss2025/mujoco_playground/_src/locomotion/go1",
        "rss2025/mujoco_playground/experimental/sim2sim"],verify)
    checkout("mujoco_menagerie",lock["menagerie_repository"],lock["menagerie_revision"],
             ["unitree_go1"],verify)
    policy=playground/"rss2025/mujoco_playground/experimental/sim2sim/onnx/go1_policy.onnx"
    if hashlib.sha256(policy.read_bytes()).hexdigest()!=lock["policy_sha256"]:
        raise RuntimeError("Go1 policy checksum mismatch")
    runtime=ROOT/".runtime/python"
    installed={d.metadata["Name"].lower():d.version for d in importlib.metadata.distributions(path=[str(runtime)])}
    if installed.get("onnxruntime")!=lock["onnxruntime"]:
        if verify:raise RuntimeError("Missing project-local ONNX runtime; run bootstrap.py")
        subprocess.run([sys.executable,"-m","pip","install","--target",str(runtime),
                        "--no-deps","onnxruntime=="+lock["onnxruntime"]],check=True)
    print("Pinned Go1 repositories, policy and local CPU runtime verified")

if __name__=="__main__":
    setup("--verify" in sys.argv)
