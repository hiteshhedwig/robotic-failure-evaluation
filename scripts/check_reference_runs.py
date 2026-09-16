#!/usr/bin/env python3
"""Rerun a small list of archived cases and compare real joint-state traces."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from robot_eval.runner import run_one

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--cases",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    cases=json.loads(args.cases.read_text())["cases"]
    args.output.mkdir(parents=True,exist_ok=False)
    def check(case):
        reference=ROOT/case["reference"]
        destination=args.output/case["id"]
        c=json.loads((reference/"scenario.json").read_text())
        result=run_one(c,destination)
        old=json.loads((reference/"result.json").read_text())
        before=[json.loads(x)["qpos"] for x in (reference/"trace.jsonl").read_text().splitlines()]
        after=[json.loads(x)["qpos"] for x in (destination/"trace.jsonl").read_text().splitlines()]
        ma=json.loads((reference/"manifest.json").read_text())
        mb=json.loads((destination/"manifest.json").read_text())
        difference=float(np.max(np.abs(np.array(before)-np.array(after)))) if len(before)==len(after) else None
        assets_match=all(ma.get(key)==mb.get(key) for key in ("policy_sha256","model_tree_sha256"))
        passed=(result["status"]==old["status"] and difference is not None and difference<=1e-10 and assets_match)
        row={"case":case["id"],"status":result["status"],"reference_status":old["status"],
             "progress_difference_m":abs(result["progress_m"]-old["progress_m"]),
             "max_qpos_difference":difference,"trace_samples":len(after),
             "policy_and_model_hashes_match":assets_match,"passed":passed}
        print(case["id"],"PASS" if passed else "FAIL",flush=True)
        return row
    with ThreadPoolExecutor(max_workers=2) as pool:
        checks=list(pool.map(check,cases))
    summary={"passed":all(c["passed"] for c in checks),"cases":checks,
             "note":"Local behavior preservation, not a cross-machine determinism guarantee. Evaluator source/profile provenance changed intentionally."}
    (args.output/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    return 0 if summary["passed"] else 1

if __name__=="__main__":sys.exit(main())
