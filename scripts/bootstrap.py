#!/usr/bin/env python3
"""Fetch only the pinned deployment/model subset; never installs system packages."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT/".deps/unitree_rl_gym"
REVISION="276801e46c5d433564f24658bac64f254b7d2d4b"
URL="https://github.com/unitreerobotics/unitree_rl_gym.git"
PATHS=["deploy/deploy_mujoco","deploy/pre_train/g1","resources/robots/g1_description","legged_gym"]

def git(*args):
    return subprocess.check_output(["git","-C",str(REPO),*args],text=True).strip()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--verify",action="store_true",help="Verify existing assets without network access")
    args=p.parse_args()
    if not REPO.exists():
        if args.verify:
            raise SystemExit("Pinned dependencies are missing; run bootstrap without --verify")
        REPO.parent.mkdir(parents=True,exist_ok=True)
        # Separate sparse setup supports the inspected older Git 2.25.
        subprocess.run(["git","clone","--depth","1","--filter=blob:none","--no-checkout",URL,str(REPO)],check=True)
        if git("rev-parse","HEAD")!=REVISION:
            subprocess.run(["git","-C",str(REPO),"fetch","--depth","1","--filter=blob:none","origin",REVISION],check=True)
        subprocess.run(["git","-C",str(REPO),"sparse-checkout","init","--cone"],check=True)
        subprocess.run(["git","-C",str(REPO),"sparse-checkout","set",*PATHS],check=True)
        subprocess.run(["git","-C",str(REPO),"checkout","--detach",REVISION],check=True)
    if git("rev-parse","HEAD")!=REVISION:
        raise SystemExit("Existing checkout has a different revision; it was not overwritten")
    if git("status","--porcelain","--untracked-files=no"):
        raise SystemExit("Upstream checkout has modifications; it was not overwritten")
    policy=REPO/"deploy/pre_train/g1/motion.pt"
    lock=json.loads((ROOT/"configs/dependencies.json").read_text())
    digest=hashlib.sha256(policy.read_bytes()).hexdigest()
    if digest!=lock["policy_sha256"]:
        raise SystemExit("Pretrained policy checksum mismatch")
    print("Pinned upstream revision and policy checksum verified")
    print("No system packages or Python environments were modified")

if __name__=="__main__":
    main()
