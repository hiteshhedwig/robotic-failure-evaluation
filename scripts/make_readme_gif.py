"""Export selected G1 and Go1 recorded-demo excerpts for the README."""
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]

if __name__=="__main__":
    clips=[
        ("artifacts/demo/02-balance-recovery.mp4",10,26),
        ("artifacts/demo/03-fall.mp4",16,24),
        ("artifacts/go1/demo/02-balance-recovery.mp4",11,28),
        ("artifacts/go1/demo/03-fall.mp4",18,29),
    ]
    command=["ffmpeg","-hide_banner","-loglevel","error","-y"]
    filters=[]
    for i,(name,start,end) in enumerate(clips):
        command += ["-ss",str(start),"-t",str(end-start),"-i",str(ROOT/name)]
        filters.append(f"[{i}:v]fps=6,scale=960:-1:flags=lanczos,setpts=PTS-STARTPTS[v{i}]")
    filters.append("".join(f"[v{i}]" for i in range(len(clips)))+"concat=n=4:v=1:a=0,split[a][b]")
    filters += ["[a]palettegen=max_colors=64:stats_mode=diff[p]",
                "[b][p]paletteuse=dither=bayer:bayer_scale=5"]
    output=ROOT/"artifacts/demo/two-robot-preview.gif"
    command += ["-filter_complex",";".join(filters),"-loop","0",str(output)]
    subprocess.run(command,check=True)
    subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(output),"-f","null","-"],check=True)
    (output.with_suffix(".json")).write_text(json.dumps({
        "passed":True,"fully_decoded":True,"selected_video_excerpts":clips,
        "note":"Selected saved-state replay excerpts; no extra robot rollout. Reading holds and 0.5x playback retained."},indent=2)+"\n")
    print("Two-robot README animation exported and fully decoded")
