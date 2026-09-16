#!/usr/bin/env python3
"""Generate a suite, run bounded workers, and produce a report in one command."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from robot_eval.experiments import generate_suite

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--experiment",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--profiles",type=Path)
    parser.add_argument("--workers",type=int,choices=[1,2],default=1)
    parser.add_argument("--wall-timeout",type=float,default=30)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError("Refusing to overwrite experiment output")
    suite=generate_suite(json.loads(args.experiment.read_text()),args.profiles)
    args.output.mkdir(parents=True,exist_ok=False)
    source=args.output/"suite.json"
    source.write_text(json.dumps(suite,indent=2)+"\n")
    runs=args.output/"runs"
    run=subprocess.run([sys.executable,str(ROOT/"scripts/run_experiment.py"),
                        "--suite",str(source),"--output",str(runs),
                        "--workers",str(args.workers),"--wall-timeout",str(args.wall_timeout)])
    # Infrastructure failures should still yield an inspectable report.
    if (runs/"batch.json").exists():
        subprocess.run([sys.executable,str(ROOT/"scripts/report.py"),str(runs),
                        "--output",str(args.output/"report")],check=True)
    else:
        raise RuntimeError("Runner did not produce a batch receipt; inspect experiment output")
    return run.returncode

if __name__=="__main__":sys.exit(main())
