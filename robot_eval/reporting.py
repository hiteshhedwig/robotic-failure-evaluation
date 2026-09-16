"""Configuration-driven summaries; robot names and sample counts are data."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import statistics

ROBOT_OUTCOMES={"COMPLETED","FALL","POSTURE_VIOLATION","TASK_TIMEOUT"}
FINGERPRINTS=("robot_profile_sha256","policy_sha256","model_tree_sha256",
              "evaluation_code_sha256","adapter_source_sha256")

def wilson(k,n):
    if n==0:return None
    z=statistics.NormalDist().inv_cdf(0.975)
    p=k/n
    scale=1+z*z/n
    center=(p+z*z/(2*n))/scale
    radius=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/scale
    return [max(0,center-radius),min(1,center+radius)]

def read_json(path,default=None):
    return json.loads(path.read_text()) if path.exists() else default

def summarize(paths):
    groups={}
    seen=set()
    for root in map(Path,paths):
        batch=read_json(root/"batch.json")
        entries=[(row,root/row["scenario_id"]) for row in batch["results"]] if batch is not None else [(read_json(root/"supervisor.json"),root)]
        for result,folder in entries:
            if result is None:raise ValueError("Missing batch or supervisor receipt: "+str(root))
            identity=folder.resolve()
            if identity in seen:raise ValueError("Repeated trial input: "+str(folder))
            seen.add(identity)
            scenario=read_json(folder/"scenario.json",{})
            manifest=read_json(folder/"manifest.json",{})
            experiment=scenario.get("experiment") or result.get("experiment") or {}
            robot=scenario.get("robot",result.get("robot","g1"))
            condition=experiment.get("condition",result["scenario_id"].split("-seed")[0])
            task={k:scenario.get(k) for k in ("command","duration_s","warmup_s","minimum_progress_m")}
            push=scenario.get("push") or result.get("injected_push") or {}
            strength=math.sqrt(sum(x*x for x in push.get("force_n",[0,0,0])))
            fingerprints={key:manifest.get(key) for key in FINGERPRINTS}
            profile=scenario.get("robot_profile")
            if fingerprints["robot_profile_sha256"] is None and profile:
                fingerprints["robot_profile_sha256"]=hashlib.sha256(
                    json.dumps(profile,sort_keys=True,separators=(",",":")).encode()).hexdigest()
            context={"robot":robot,"experiment_id":experiment.get("id","legacy"),
                     "condition":condition,"force_n":round(strength,9),
                     "force_mode":experiment.get("force_mode","newtons"),
                     "requested_magnitude":experiment.get("magnitude",strength),
                     "pulse_duration_s":push.get("duration_s"),
                     "task":task,"fingerprints":fingerprints}
            key=json.dumps(context,sort_keys=True)
            group=groups.setdefault(key,{"context":context,"attempts":[]})
            sample_key=json.dumps({"seed":scenario.get("seed"),"push":push},sort_keys=True)
            group["attempts"].append((result,sample_key))
    rows=[]
    for group in groups.values():
        context=group["context"]
        valid=[(r,key) for r,key in group["attempts"] if r["status"] in ROBOT_OUTCOMES]
        counts=Counter(r["status"] for r,_ in valid)
        n=len(valid)
        repeated=len({key for _,key in valid})<n
        estimate=context["force_n"]>0 and not repeated
        latencies=[r["recovery_latency_s"] for r,_ in valid
                   if r["status"]=="COMPLETED" and r.get("recovery_latency_s") is not None]
        progress=[r["progress_m"] for r,_ in valid if r.get("progress_m") is not None]
        rows.append({**context,"attempted":len(group["attempts"]),"valid":n,
                     "infrastructure_failures":len(group["attempts"])-n,"outcomes":dict(counts),
                     "success_rate":counts["COMPLETED"]/n if n else None,
                     "fall_rate":counts["FALL"]/n if n else None,
                     "success_wilson95":wilson(counts["COMPLETED"],n) if estimate else None,
                     "fall_wilson95":wilson(counts["FALL"],n) if estimate else None,
                     "interval_note":"Conditional pushed-trial interval" if estimate else
                         "No interval: nominal reset repetitions" if context["force_n"]==0 else
                         "No interval: duplicate seed/push configurations",
                     "median_progress_m":statistics.median(progress) if progress else None,
                     "balance_recovered_and_completed":len(latencies),
                     "median_recovery_latency_s":statistics.median(latencies) if latencies else None})
    return sorted(rows,key=lambda r:(r["robot"],r["experiment_id"],r["force_n"],r["condition"],
                                    json.dumps(r["fingerprints"],sort_keys=True)))

def write_report(paths,output):
    rows=summarize(paths)
    out=Path(output)
    out.mkdir(parents=True,exist_ok=False)
    report={"conditions":rows,"campaigns":[str(p) for p in paths],
            "runs":sum(row["attempted"] for row in rows),
            "robot_trials":sum(row["valid"] for row in rows),
            "infrastructure_failures":sum(row["infrastructure_failures"] for row in rows),
            "robots":sorted({row["robot"] for row in rows}),
            "statistical_scope":"Exploratory and conditional on recorded models, policies, task and disturbance sampling. No physical-robot inference.",
            "aggregation_note":"Robots, experiment IDs, conditions, task settings, force magnitude/mode/duration and available fingerprints define separate groups. Historical missing fingerprints stay explicit.",
            "comparison_note":"Matched schedules and normalized body-weight forces do not establish equivalent difficulty or a cross-robot ranking.",
            "uncertainty_note":"Wilson intervals are conditional proportions, not a guarantee of independence. Nominal repeats and duplicate seed/push configurations receive no interval. Inspect the experiment design.",
            "attribution":"Injected disturbance, system response and measured outcome are distinct. Outcome detection does not establish internal policy cause.",
            "designs":[]}
    for path in map(Path,paths):
        design=read_json(path/"design.json",{})
        report["designs"].append({"path":str(path),"experiment":design.get("experiment"),
                                 "note":design.get("note"),"sampling":design.get("sampling"),
                                 "sampling_note":design.get("sampling_note")})
    (out/"summary.json").write_text(json.dumps(report,indent=2)+"\n")
    lines=["# Robotic failure evaluation\n\n",
           "Robots: **"+", ".join(r.upper() for r in report["robots"])+"**. "
           +str(report["robot_trials"])+" valid robot trials from "+str(report["runs"])+" attempts; "
           +str(report["infrastructure_failures"])+" infrastructure/invalid outcomes.\n\n",
           "| Group | Robot | Experiment / condition | Pulse | Completed | Falls | Posture | Task timeout | Valid | Infra/invalid | Fall 95% Wilson interval |\n",
           "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"]
    for index,row in enumerate(rows,1):
        counts=row["outcomes"]
        ci=row["fall_wilson95"]
        interval="{:.1%}–{:.1%}".format(*ci) if ci else "Not estimated"
        lines.append("| {} | {} | {} / {} | {:.3f} N | {} | {} | {} | {} | {} | {} | {} |\n".format(
            index,row["robot"].upper(),row["experiment_id"],row["condition"],row["force_n"],
            counts.get("COMPLETED",0),counts.get("FALL",0),counts.get("POSTURE_VIOLATION",0),
            counts.get("TASK_TIMEOUT",0),row["valid"],row["infrastructure_failures"],interval))
    lines.append("\n## Recorded task and group configuration\n\n")
    for index,row in enumerate(rows,1):
        lines.append("- Group {}: task {}; pulse duration {}; force mode {}, requested magnitude {}; {}. Fingerprints and resolved robot profiles are retained in summary/trial manifests.\n".format(
            index,json.dumps(row["task"],sort_keys=True),row["pulse_duration_s"],
            row["force_mode"],row["requested_magnitude"],row["interval_note"]))
    lines.append("\n## Interpretation\n\n")
    for key in ("statistical_scope","aggregation_note","comparison_note","uncertainty_note","attribution"):
        lines.append("- "+report[key]+"\n")
    lines.append("- A lower fall count is not an improvement when other task failures replace falls. All valid task-failure categories remain visible.\n")
    lines.append("\n## Evidence and reproduction\n\nThe resolved suite and each trial's scenario, manifest, trace, events, result and supervisor receipt preserve inputs and observations. Rerun a scenario into a new output directory and use scripts/compare.py with --reference and --candidate. Report generation never overwrites an existing directory.\n")
    (out/"report.md").write_text("".join(lines))
    return report
