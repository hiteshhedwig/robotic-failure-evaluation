#!/usr/bin/env python3
"""List robot profiles or expand an experiment JSON; no simulations are stepped."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from robot_eval.experiments import generate_suite
from robot_eval.profiles import discover_profiles

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--experiment",type=Path)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--profiles",type=Path,help="Directory of trusted local robot profile JSON files")
    parser.add_argument("--list-robots",action="store_true")
    args=parser.parse_args()
    if args.list_robots:
        print(json.dumps({key:p.definition for key,p in discover_profiles(args.profiles).items()},indent=2))
        return
    if args.experiment is None or args.output is None:
        parser.error("--experiment and --output are required unless listing robots")
    if args.output.exists():raise FileExistsError("Refusing to overwrite generated suite")
    suite=generate_suite(json.loads(args.experiment.read_text()),args.profiles)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(suite,indent=2)+"\n")
    print("Generated",len(suite["scenarios"]),"resolved scenarios:",args.output)

if __name__=="__main__":main()
