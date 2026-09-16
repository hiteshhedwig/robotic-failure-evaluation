#!/usr/bin/env python3
"""Compare actual matched trials; useful as a regression check for a future version."""
import argparse
import json
from pathlib import Path

def load(path):
    if (path/"batch.json").exists():
        rows=json.loads((path/"batch.json").read_text())["results"]
        return {r["scenario_id"]:(r,path/r["scenario_id"]) for r in rows}
    row=json.loads((path/"supervisor.json").read_text())
    return {row["scenario_id"]:(row,path)}

def compare(reference,candidate):
    a,b=load(reference),load(candidate)
    if set(a)!=set(b):
        raise ValueError("Scenario ids differ; refusing an unmatched comparison")
    pairs=[]
    for key in sorted(a):
        before,pa=a[key];after,pb=b[key]
        ca=json.loads((pa/"scenario.json").read_text())
        cb=json.loads((pb/"scenario.json").read_text())
        if ca!=cb:
            raise ValueError("Scenario configurations differ: "+key)
        pair={"id":key,"reference":before["status"],"candidate":after["status"],
              "new_task_failure":before["status"]=="COMPLETED" and after["status"] in {"FALL","TASK_TIMEOUT","POSTURE_VIOLATION"},
              "infrastructure_error":after["status"] not in {"COMPLETED","FALL","TASK_TIMEOUT","POSTURE_VIOLATION"}}
        if (pa/"manifest.json").exists() and (pb/"manifest.json").exists():
            ma=json.loads((pa/"manifest.json").read_text());mb=json.loads((pb/"manifest.json").read_text())
            pair["changed_fingerprints"]=[k for k in ["policy_sha256","model_tree_sha256","evaluation_code_sha256","robot_profile_sha256","adapter_source_sha256"] if ma.get(k)!=mb.get(k)]
        pairs.append(pair)
    return {"matched":True,"pairs":pairs,"regression":any(p["new_task_failure"] or p["infrastructure_error"] for p in pairs),
            "outcome_agreement":all(p["reference"]==p["candidate"] for p in pairs)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--reference",type=Path,required=True)
    p.add_argument("--candidate",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    report=compare(args.reference,args.candidate)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    raise SystemExit(1 if report["regression"] else 0)

if __name__=="__main__":
    main()
