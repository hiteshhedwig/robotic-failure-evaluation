#!/usr/bin/env python3
"""Render actual saved G1 physics states with readable experiment explanations.

The replay does not rerun a policy or invent motion. 50 Hz recorded state samples
play at 25 fps (0.5x), with explicitly labeled reading holds at recorded events.
"""
import os
import sys
os.environ.setdefault("MUJOCO_GL","egl")
import json
from pathlib import Path
import subprocess
import textwrap
import numpy as np
import mujoco

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
OUTPUT=ROOT/"artifacts/demo"
MODEL=ROOT/".deps/unitree_rl_gym/resources/robots/g1_description/scene.xml"
FPS=25

def ts(seconds):
    n=max(0,round(seconds*100))
    return "{}:{:02d}:{:02d}.{:02d}".format(n//360000,n//6000%60,n//100%60,n%100)

def wrapped(text,width=37):
    return r"\N".join(textwrap.wrap(text,width))

def render(slug,source,title,intro):
    folder=ROOT/source
    c=json.loads((folder/"scenario.json").read_text())
    result=json.loads((folder/"result.json").read_text())
    events=[json.loads(x) for x in (folder/"events.jsonl").read_text().splitlines()]
    states=[json.loads(x) for x in (folder/"trace.jsonl").read_text().splitlines()]
    push=c.get("push")
    marks=[(0,5,"The experiment",intro,
            "Goal: at least 2 m forward progress after warmup, with no confirmed fall.")]
    if push:
        on=next(x["time_s"] for x in events if x["event"]=="PUSH_STARTED")
        off=next(x["time_s"] for x in events if x["event"]=="PUSH_ENDED")
        strength=np.linalg.norm(push["force_n"])
        marks += [(on,5,"Inject a measured push",
                   "Apply {} N in world direction {} for {:.1f} simulated seconds. The arrow illustrates the recorded force on the root body.".format(strength,push["force_n"],push["duration_s"]),
                   "The pulse is an input disturbance. Its presence alone is not a robot failure."),
                  (off,4,"The push has ended",
                   "External force is zero again. The existing walking policy continues. We now observe whether balance and task progress recover.",
                   "The robot response is measured from simulator posture, velocity and contacts.")]
    else:
        marks += [(2,4,"Start scoring the task",
                   "The first two simulated seconds allow startup to settle. Now measure forward progress, posture and ground contact for the rest of the episode.",
                   "The policy commands 0.5 m/s. Normal foot-floor contact is expected.")]
    recovery=result.get("recovery_confirmed_time_s")
    if recovery is not None:
        marks += [(recovery,5,"Balance recovery confirmed",
                   "Body tilt, root height and horizontal velocity have returned to the specified band for 0.4 simulated seconds.",
                   "Balance recovery is separate from task completion. The robot still needs 2 m of scored forward progress.")]
    if result["status"]=="FALL":
        detail="Root-body floor contact persisted for 0.02 simulated seconds. The evaluator confirms FALL and terminates this episode."
        proof="The policy is not asked to get up. A fall is not an infrastructure crash."
    elif result["status"]=="POSTURE_VIOLATION":
        detail="Tilt exceeded 60 degrees or root height fell below the robot-specific limit for 0.1 simulated seconds. No sustained root-floor contact was confirmed."
        proof="A posture violation and a confirmed fall are separate observable outcomes."
    elif result["status"]=="TASK_TIMEOUT":
        detail="The robot is upright, but scored progress is only {:.3f} m at the 10 s task horizon. The required 2 m was not reached.".format(result["progress_m"])
        proof="TASK_TIMEOUT is a measured task failure, not a hung worker or a wall-clock timeout."
    else:
        detail="The robot completed {:.3f} m of scored forward progress without a confirmed fall.".format(result["progress_m"])
        proof="COMPLETED requires the task objective; simply observing a moving robot would not be enough."
    marks += [(states[-1]["time_s"],7,"Outcome: "+result["status"],detail,proof)]
    marks.sort(key=lambda m:m[0])
    # Map each checkpoint to a nearby recorded sample; no interpolated states.
    at={}
    for mark in marks:
        index=next((i for i,state in enumerate(states)
                    if state["time_s"]>=mark[0]-1e-9),len(states)-1)
        at.setdefault(index,[]).append(mark)
    robot=c.get("robot","g1")
    if robot=="go1":
        from robot_eval.go1 import load_model
        model=load_model()
    else:
        model=mujoco.MjModel.from_xml_path(str(MODEL))
    data=mujoco.MjData(model)
    model.vis.global_.offwidth=800
    model.vis.global_.offheight=600
    camera=mujoco.MjvCamera()
    camera.distance=1.7 if robot=="go1" else 2.6
    camera.azimuth=135
    camera.elevation=-14
    raw=OUTPUT/(slug+"-source.mp4")
    log=(OUTPUT/(slug+"-encode.log")).open("w")
    encoder=subprocess.Popen(["ffmpeg","-y","-v","error","-f","rawvideo","-pixel_format","rgb24",
        "-video_size","800x600","-framerate",str(FPS),"-i","-","-an","-c:v","libx264",
        "-threads","2","-preset","fast","-crf","20","-pix_fmt","yuv420p",str(raw)],
        stdin=subprocess.PIPE,stderr=log)
    timeline=[]
    output_frame=0
    card=marks[0]
    try:
        with mujoco.Renderer(model,height=600,width=800) as renderer:
            for index,state in enumerate(states):
                data.qpos[:]=state["qpos"]
                data.qvel[:]=state["qvel"]
                mujoco.mj_forward(model,data)
                camera.lookat[:]=data.qpos[:3]
                camera.lookat[2]=max(0.18 if robot=="go1" else 0.55,float(data.qpos[2]))
                renderer.update_scene(data,camera=camera)
                force=np.array(state["applied_force_world_n"])
                if state["push_active"] and np.linalg.norm(force)>0:
                    scene=renderer.scene
                    start=data.xipos[model.body("trunk" if robot=="go1" else "pelvis").id]-force/np.linalg.norm(force)*0.55
                    end=data.xipos[model.body("trunk" if robot=="go1" else "pelvis").id]
                    geom=scene.geoms[scene.ngeom]
                    mujoco.mjv_initGeom(geom,mujoco.mjtGeom.mjGEOM_ARROW,np.zeros(3),np.zeros(3),np.eye(3).reshape(-1),np.array([1,0.2,0.1,1]))
                    mujoco.mjv_connector(geom,mujoco.mjtGeom.mjGEOM_ARROW,0.025,start,end)
                    scene.ngeom+=1
                frame=renderer.render().tobytes()
                for checkpoint in at.get(index,[]):
                    card=checkpoint
                    hold_frames=round(card[1]*FPS)
                    encoder.stdin.write(frame*hold_frames)
                    timeline.append({"start":output_frame/FPS,"end":(output_frame+hold_frames)/FPS,
                                     "freeze":True,"state":state,"heading":card[2],"body":card[3],"proof":card[4]})
                    output_frame+=hold_frames
                encoder.stdin.write(frame)
                timeline.append({"start":output_frame/FPS,"end":(output_frame+1)/FPS,
                                 "freeze":False,"state":state,"heading":card[2],"body":card[3],"proof":card[4]})
                output_frame+=1
    finally:
        encoder.stdin.close()
        encoder.wait(timeout=30)
        log.close()
    if encoder.returncode:
        raise RuntimeError("Video encoder failed")
    ass=OUTPUT/(slug+".ass")
    subtitles(ass,timeline,title,c,result)
    final=OUTPUT/(slug+".mp4")
    subprocess.run(["ffmpeg","-y","-v","error","-i",str(raw),"-vf",
        "scale=900:675,pad=1440:900:520:105:color=0x101820,ass="+str(ass),"-an",
        "-c:v","libx264","-threads","3","-preset","fast","-crf","20","-pix_fmt","yuv420p",
        "-movflags","+faststart",str(final)],check=True,timeout=120)
    manifest={"source_trial":source,"source_outcome":result["status"],"duration_seconds":output_frame/FPS,
              "note":"Recorded physics-state replay at 0.5x with labeled editorial holds. Force arrows are explanatory graphics.",
              "checkpoints":[{"source_time_s":m[0],"hold_s":m[1],"heading":m[2]} for m in marks]}
    (OUTPUT/(slug+".json")).write_text(json.dumps(manifest,indent=2)+"\n")
    print("Rendered",final.name,result["status"],flush=True)
    return final

def subtitles(path,timeline,title,c,result):
    lines=["[Script Info]\nScriptType: v4.00+\nPlayResX: 1440\nPlayResY: 900\n[V4+ Styles]\n",
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"]
    for name,size,color,bold in [("Title",29,"FFFFFF",-1),("Accent",18,"BFD65A",-1),
                                  ("Heading",27,"FFFFFF",-1),("Body",23,"E7E5E2",0),
                                  ("Proof",21,"BFD65A",0),("Data",17,"CBCBCB",0)]:
        lines.append("Style: {},DejaVu Sans,{},&H00{},&H00FFFFFF,&H00101820,&H00101820,{},0,0,0,100,100,0,0,1,0,0,7,0,0,0,1\n".format(name,size,color,bold))
    lines.append("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    def text(a,b,style,x,y,value):
        lines.append("Dialogue: 0,{},{},{},,0,0,0,,{{\\an7\\pos({},{})\\q2}}{}\n".format(ts(a),ts(b),style,x,y,value))
    total=timeline[-1]["end"]
    text(0,total,"Title",25,18,"Robotic Failure Evaluation | "+c.get("robot","g1").upper()+" | "+title)
    text(0,total,"Accent",25,62,"RECORDED STATE REPLAY | 0.5x + reading pauses | Pretrained "+c.get("robot","g1").upper()+" policy | SIMULATION ONLY")
    for part in timeline:
        a,b=part["start"],part["end"]
        s=part["state"]
        text(a,b,"Accent",25,132,"PAUSED FOR EXPLANATION" if part["freeze"] else "RECORDED MOTION PLAYING AT 0.5x")
        text(a,b,"Heading",25,180,wrapped(part["heading"],31))
        text(a,b,"Body",25,270,wrapped(part["body"]))
        text(a,b,"Proof",25,540,wrapped(part["proof"],39))
        text(a,b,"Data",25,775,wrapped("Reading pauses freeze this replay frame. They are not extra robot stops.",43))
        progress=s["position"][0]-result["initial_evaluation_position"][0]
        scored="warmup / not scored" if s["time_s"]<c["warmup_s"] else "{:.3f} m / required 2.000 m".format(progress)
        line="Source {:.3f}s | Tilt {:.1f} deg | Root height {:.3f} m".format(s["time_s"],s["tilt_deg"],s["position"][2])
        line+=r"\NScored forward progress: "+scored
        line+=r"\NRecorded applied force [N]: "+str(s["applied_force_world_n"])
        text(a,b,"Data",520,805,line)
    path.write_text("".join(lines))

def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    cases=[
        ("01-baseline","artifacts/push-pilot/push-y-0","Walking baseline",
         "First establish normal walking with no disturbance. The robot must advance and remain upright; ordinary foot contacts are not falls."),
        ("02-balance-recovery","artifacts/push-pilot/push-y-100","Push tolerated; balance recovered",
         "Apply a 100 N sideways pulse during walking. Does the policy return to its balance band and still complete the forward task?"),
        ("03-fall","artifacts/push-pilot/push-y-250","A stronger push causes a fall",
         "Use the same onset and direction with a 250 N pulse. We detect the resulting body-floor contact independently of the policy."),
        ("04-upright-task-failure","artifacts/boundary/boundary-seed1","Upright does not mean task success",
         "A 175 N backward pulse may leave the robot upright. The experiment still checks whether it covered the required forward distance.")
    ]
    paths=[render(*case) for case in cases]
    playlist=OUTPUT/"playlist.txt"
    playlist.write_text("".join("file '{}'\n".format(p.name) for p in paths))
    full=OUTPUT/"00-complete-walkthrough.mp4"
    subprocess.run(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",str(playlist),
                    "-c","copy","-movflags","+faststart",str(full)],check=True)
    results=[]
    for path in [full]+paths:
        subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(path),"-f","null","-"],check=True,timeout=90)
        metadata=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_entries",
            "format=duration,size:stream=codec_name,width,height,nb_frames","-of","json",str(path)],text=True))
        results.append({"file":path.name,"fully_decoded":True,**metadata})
    (OUTPUT/"media-validation.json").write_text(json.dumps({"passed":True,"files":results},indent=2)+"\n")
    print("All exported videos fully decoded",flush=True)

if __name__=="__main__":
    main()
