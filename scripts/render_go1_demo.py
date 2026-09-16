#!/usr/bin/env python3
"""Render four real Go1 trial traces using the shared annotated replay exporter."""
import json
from pathlib import Path
import subprocess
import render_demo as demo

ROOT=Path(__file__).resolve().parents[1]

def main():
    demo.OUTPUT=ROOT/"artifacts/go1/demo"
    demo.OUTPUT.mkdir(parents=True,exist_ok=True)
    cases=[
      ("01-baseline","artifacts/go1/campaign/reference-seed0","Walking baseline",
       "Go1 executes the same forward-distance task as G1. Its existing policy controls all twelve leg joints; normal foot contacts are expected."),
      ("02-balance-recovery","artifacts/go1/campaign/moderate-seed0","Push tolerated",
       "A 250 N sideways pulse disturbs Go1. The evaluator measures whether it returns to its balance band and finishes the forward task."),
      ("03-fall","artifacts/go1/campaign/strong-seed0","Confirmed fall",
       "A 500 N pulse is applied on the same schedule. Sustained trunk-floor contact confirms a fall, independently of policy output."),
      ("04-posture-violation","artifacts/go1/campaign/extreme-seed5","Posture violation",
       "A 1000 N pulse produces a persistent posture violation. No sustained trunk-floor contact is confirmed, so the outcome is not labeled FALL.")
    ]
    paths=[demo.render(*case) for case in cases]
    playlist=demo.OUTPUT/"playlist.txt"
    playlist.write_text("".join("file '{}'\n".format(p.name) for p in paths))
    full=demo.OUTPUT/"00-go1-walkthrough.mp4"
    subprocess.run(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",str(playlist),
                    "-c","copy","-movflags","+faststart",str(full)],check=True)
    validation=[]
    for path in [full]+paths:
        subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(path),"-f","null","-"],check=True)
        meta=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_entries",
            "format=duration,size:stream=width,height,nb_frames","-of","json",str(path)],text=True))
        validation.append({"file":path.name,"fully_decoded":True,**meta})
    (demo.OUTPUT/"media-validation.json").write_text(json.dumps({"passed":True,"files":validation},indent=2)+"\n")
    print("Go1 walkthrough and all chapters fully decoded",flush=True)

if __name__=="__main__":main()
