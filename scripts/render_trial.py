#!/usr/bin/env python3
"""Render a valid recorded trial for any registered/embedded robot profile."""
import argparse
import json
from pathlib import Path
import subprocess
import render_demo as demo

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--trial",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--title",default="Recorded experiment")
    parser.add_argument("--intro",default="Inspect the recorded command, disturbance, robot response and independently measured task outcome.")
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    demo.OUTPUT=args.output.resolve()
    path=demo.render("trial",str(args.trial.resolve()),args.title,args.intro)
    subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(path),"-f","null","-"],check=True)
    (demo.OUTPUT/"media-validation.json").write_text(json.dumps(
        {"passed":True,"file":path.name,"fully_decoded":True},indent=2)+"\n")

if __name__=="__main__":main()
