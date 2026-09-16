#!/usr/bin/env python3
"""Small descriptive report with conditional, explicitly scoped uncertainty."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import statistics

ROBOT={"COMPLETED","FALL","POSTURE_VIOLATION","TASK_TIMEOUT"}

def wilson(k,n):
    if n==0:
        return None
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
        for r in batch["results"]:
            label=r["scenario_id"].split("-seed")[0]
            groups.setdefault(label,[]).append(r)
    rows=[]
    for label,attempts in groups.items():
        valid=[r for r in attempts if r["status"] in ROBOT]
        counts=Counter(r["status"] for r in valid)
        n=len(valid)
        strength=math.sqrt(sum(x*x for x in (valid[0].get("injected_push") or {}).get("force_n",[0,0,0]))) if valid else None
        latency=[r["recovery_latency_s"] for r in valid if r["status"]=="COMPLETED" and r.get("recovery_latency_s") is not None]
        rows.append({"condition":label,"force_n":strength,"attempted":len(attempts),"valid":n,
                     "infrastructure_failures":len(attempts)-n,"outcomes":dict(counts),
                     "success_rate":counts["COMPLETED"]/n if n else None,
                     "fall_rate":counts["FALL"]/n if n else None,
                     "success_wilson95":wilson(counts["COMPLETED"],n) if label!="reference" else None,
                     "fall_wilson95":wilson(counts["FALL"],n) if label!="reference" else None,
                     "median_progress_m":statistics.median(r["progress_m"] for r in valid) if valid else None,
                     "balance_recovered_and_completed":len(latency),
                     "median_recovery_latency_s":statistics.median(latency) if latency else None})
    return sorted(rows,key=lambda r:r["force_n"] if r["force_n"] is not None else -1)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("campaigns",nargs="+",type=Path)
    p.add_argument("--output",type=Path,default=Path("artifacts/evaluation"))
    args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    rows=summarize(args.campaigns)
    report={"conditions":rows,
            "statistical_scope":"Exploratory, conditional on this G1 model, policy, ground, pulse duration and direction/onset sampling. Eight matched seeded schedules per pushed condition; no physical-robot inference.",
            "reference_note":"Nominal reference repetitions are identical and do not supply independent reliability samples; no binomial interval is reported for them.",
            "selection_note":"175 N is an exploratory follow-up chosen after the initial 100/250 N bracket, not held-out confirmation.",
            "recovery_definition":"Return to a predefined posture/velocity band for 0.4 simulated seconds after the pulse ends; this is balance recovery, not getting up.",
            "attribution":"The logs establish injection and observed outcomes. They do not identify an internal policy failure mechanism."}
    (args.output/"summary.json").write_text(json.dumps(report,indent=2)+"\n")
    lines=["# G1 walking under controlled pushes\n\n",
           "The task is forward walking for ten simulated seconds, with a two-second warmup and at least 2 m of evaluated forward progress. A fall is sustained pelvis/rigid-torso ground contact. No lateral corridor constraint is imposed; lateral displacement is reported in each trial.\n\n",
           "| Pulse force | Completed / valid | Falls / valid | Task timeouts / valid | Fall proportion, 95% Wilson interval | Median forward progress | Median recovery latency among recovered completions |\n| --- | --- | --- | --- | --- | --- | --- |\n"]
    for row in rows:
        n=row["valid"];k=row["outcomes"].get("FALL",0)
        interval=row["fall_wilson95"]
        ci="{:.0%} [{:.0%}, {:.0%}]".format(row["fall_rate"],*interval) if interval else "Nominal repeated baseline; no interval"
        latency="{:.3f} s".format(row["median_recovery_latency_s"]) if row["median_recovery_latency_s"] is not None else "Not observed / not applicable"
        lines.append("| {} N | {}/{} | {}/{} | {}/{} | {} | {:.3f} m | {} |\n".format(row["force_n"],row["outcomes"].get("COMPLETED",0),n,k,n,row["outcomes"].get("TASK_TIMEOUT",0),n,ci,row["median_progress_m"],latency))
    lines += ["\n## How to interpret this\n\n",
              "- Each push lasts 0.2 s. Direction is sampled from world +/-X and +/-Y, and onset from one 0.8 s gait cycle [3.0, 3.8], quantized to 2 ms. Configs record all realized values.\n",
              "- The eight schedules are matched across severity levels. Cross-condition results are paired, not independent groups. The intervals describe within-condition sampling under the stated design.\n",
              "- The 175 N follow-up was chosen at the midpoint after 100 N completed and 250 N fell in all initial schedules. All initial results are retained. This is exploratory testing, not a held-out benchmark.\n",
              "- Zero observed falls among eight pushed trials still leaves substantial uncertainty. It does not establish a fall-free controller.\n",
              "- Infrastructure errors are counted separately and excluded from robot-outcome denominators. There were {} in these campaigns.\n".format(sum(r["infrastructure_failures"] for r in rows)),
              "- Recovery latency includes the 0.4 s verification window and is reported only for trials that recovered and completed. Survivors are not assigned a fabricated time-to-fall.\n",
              "- The reference repeats have identical nominal initial conditions; their repetition is a reset/reproducibility check, not eight independent reliability samples.\n",
              "- Ground truth is simulator state/contact data, not a controller success signal. Body orientation, force intervals, policy output, and contacts are timestamped. Fall association does not diagnose the policy's internal cause.\n",
              "\n## Evidence and reproduction\n\n",
              "Each trial directory contains scenario.json, manifest.json, trace.jsonl, events.jsonl, result.json and supervisor.json. Parent process logs are in .logs/. Recorded scenario files can be passed unchanged to scripts/run_experiment.py --scenario ... --output NEW_DIRECTORY. Same configurations are reproducible; bitwise agreement is not promised across other machines or simulator builds.\n"]
    (args.output/"report.md").write_text("".join(lines))
    print(json.dumps(rows,indent=2))

if __name__=="__main__":
    main()
