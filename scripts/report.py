#!/usr/bin/env python3
"""Descriptive, robot-separated results with scoped uncertainty."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import statistics

ROBOT={"COMPLETED","FALL","POSTURE_VIOLATION","TASK_TIMEOUT"}

def wilson(k,n):
    if n==0:return None
    z=statistics.NormalDist().inv_cdf(0.975)
    p=k/n
    scale=1+z*z/n
    center=(p+z*z/(2*n))/scale
    radius=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/scale
    return [max(0,center-radius),min(1,center+radius)]

def summarize(paths):
    groups={}
    for path in paths:
        batch=json.loads((path/"batch.json").read_text())
        for result in batch["results"]:
            label=result["scenario_id"].split("-seed")[0]
            groups.setdefault((result.get("robot","g1"),label),[]).append(result)
    rows=[]
    for (robot,label),attempts in groups.items():
        valid=[r for r in attempts if r["status"] in ROBOT]
        counts=Counter(r["status"] for r in valid)
        n=len(valid)
        strength=math.sqrt(sum(x*x for x in (valid[0].get("injected_push") or {}).get("force_n",[0,0,0]))) if valid else None
        latency=[r["recovery_latency_s"] for r in valid if r["status"]=="COMPLETED" and r.get("recovery_latency_s") is not None]
        rows.append({"robot":robot,"condition":label,"force_n":strength,
                     "attempted":len(attempts),"valid":n,"infrastructure_failures":len(attempts)-n,
                     "outcomes":dict(counts),"success_rate":counts["COMPLETED"]/n if n else None,
                     "fall_rate":counts["FALL"]/n if n else None,
                     "success_wilson95":wilson(counts["COMPLETED"],n) if label!="reference" else None,
                     "fall_wilson95":wilson(counts["FALL"],n) if label!="reference" else None,
                     "median_progress_m":statistics.median(r["progress_m"] for r in valid) if valid else None,
                     "balance_recovered_and_completed":len(latency),
                     "median_recovery_latency_s":statistics.median(latency) if latency else None})
    return sorted(rows,key=lambda r:(r["robot"],r["force_n"] if r["force_n"] is not None else -1))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("campaigns",nargs="+",type=Path)
    parser.add_argument("--output",type=Path,default=Path("artifacts/two-robot/evaluation"))
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    rows=summarize(args.campaigns)
    report={"conditions":rows,
      "campaigns":[str(p) for p in args.campaigns],
      "statistical_scope":"Exploratory, conditional on each model, policy, ground and disturbance distribution; no physical-robot inference.",
      "reference_note":"Identical nominal reset repetitions are not independent reliability samples; no interval for references.",
      "comparison_note":"Force tiers have matched schedules within each robot. Different robot masses, policies, time steps and severity ranges preclude a cross-robot robustness ranking.",
      "selection_note":"G1 175 N was selected after 100/250 N bracketing. Go1 tiers were selected after 20-1000 N pilot bracketing. These are exploratory, not held-out estimates.",
      "timing":"G1 physics 2 ms; Go1 physics 4 ms; policy and recorded-state traces 20 ms for both.",
      "attribution":"Injection, physical response and outcome are recorded separately. Association does not establish an internal policy failure mechanism."}
    (args.output/"summary.json").write_text(json.dumps(report,indent=2)+"\n")
    lines=["# Robotic failure evaluation: G1 and Go1\n\n",
      "Both robots execute a 0.5 m/s forward command for 10 simulated seconds, with 2 s warmup and at least 2 m scored world-X progress. No lateral corridor is required. One optional world-frame force pulse lasts 0.2 s. Ground-truth contact and posture monitors are robot-specific.\n\n",
      "| Robot | Pulse | Completed | Falls | Posture violations | Task timeouts | Valid | Fall 95% Wilson interval |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n"]
    for row in rows:
        outcomes=row["outcomes"]
        interval=row["fall_wilson95"]
        ci="{:.1%}–{:.1%}".format(*interval) if interval else "Not estimated"
        lines.append("| {} | {} N | {} | {} | {} | {} | {} | {} |\n".format(
            row["robot"].upper(),row["force_n"],outcomes.get("COMPLETED",0),
            outcomes.get("FALL",0),outcomes.get("POSTURE_VIOLATION",0),
            outcomes.get("TASK_TIMEOUT",0),row["valid"],ci))
    lines += ["\n## Interpretation\n\n"]
    for key in ["statistical_scope","reference_note","comparison_note","selection_note","timing","attribution"]:
        lines.append("- "+report[key]+"\n")
    lines.append("- Each pushed condition uses eight seeded direction/onset schedules: world +/-X or +/-Y; onset sampled in [3.0, 3.8] s, quantized to each physics step. See each saved design.json for realized parameters.\n")
    lines.append("- Infrastructure/invalid episodes are excluded from robot-outcome denominators; separately counted total: {}.\n".format(sum(r["infrastructure_failures"] for r in rows)))
    lines.append("- Zero falls in eight trials still permits an approximately 32% upper Wilson limit. There is no hardware safety claim or statistically demonstrated software improvement.\n")
    lines.append("\n## Reproduction and evidence\n\nEach trial contains scenario, manifest, timestamped state/command/contact traces, events, result and supervisor receipt. Rerun its scenario.json with scripts/run_experiment.py into a new output folder. The manifests retain source/model/policy fingerprints. Historical G1 results remain archived; current-code baseline checks verify that the adapter refactor preserves its behavior.\n")
    (args.output/"report.md").write_text("".join(lines))
    print(json.dumps(rows,indent=2))

if __name__=="__main__":main()
