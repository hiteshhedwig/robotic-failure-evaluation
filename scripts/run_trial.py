#!/usr/bin/env python3
"""Thin worker CLI; the shared episode engine contains no robot-name branches."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from robot_eval.episode import run_episode

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--scenario",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--seed",type=int)
    args=parser.parse_args()
    config=json.loads(Path(args.scenario).read_text())
    if args.seed is not None:config["seed"]=args.seed
    result=run_episode(config,args.output)
    print(json.dumps(result),flush=True)
    return 0 if result["status"]=="COMPLETED" else 3 if result["status"] in {"INFRASTRUCTURE_ERROR","INVALID_SIMULATION"} else 2

if __name__=="__main__":sys.exit(main())
