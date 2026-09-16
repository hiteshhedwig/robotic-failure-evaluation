#!/usr/bin/env python3
"""One protected trial or a small predeclared batch; no manual GUI launches."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from robot_eval.runner import run_one,ROBOT_OUTCOMES

def main():
    p=argparse.ArgumentParser()
    source=p.add_mutually_exclusive_group(required=True)
    source.add_argument("--scenario")
    source.add_argument("--suite")
    p.add_argument("--output",required=True)
    p.add_argument("--workers",type=int,choices=[1,2],default=1)
    p.add_argument("--wall-timeout",type=float,default=30)
    args=p.parse_args()
    output=Path(args.output)
    if args.scenario:
        c=json.loads(Path(args.scenario).read_text())
        r=run_one(c,output,args.wall_timeout)
        print(json.dumps(r),flush=True)
        sys.exit(0 if r["status"] in ROBOT_OUTCOMES else 3)
    suite=json.loads(Path(args.suite).read_text())
    ids=[c["id"] for c in suite["scenarios"]]
    if len(set(ids))!=len(ids):
        raise ValueError("Duplicate scenario ids")
    output.mkdir(parents=True,exist_ok=False)
    (output/"design.json").write_text(json.dumps(suite,indent=2)+"\n")
    def evaluate(c):
        r=run_one(c,output/c["id"],args.wall_timeout)
        print(c["id"],r["status"],flush=True)
        return r
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results=list(pool.map(evaluate,suite["scenarios"]))
    summary={"runs":len(results),"robot_trials":sum(r["status"] in ROBOT_OUTCOMES for r in results),
             "infrastructure_failures":sum(r["status"] not in ROBOT_OUTCOMES for r in results),
             "results":results}
    (output/"batch.json").write_text(json.dumps(summary,indent=2)+"\n")
    sys.exit(0 if summary["infrastructure_failures"]==0 else 3)

if __name__=="__main__":
    main()
