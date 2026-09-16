#!/usr/bin/env python3
"""Join the two verified robot walkthroughs and validate the complete export."""
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]

def main():
    output=ROOT/"artifacts/demo"
    clips=[output/"00-complete-walkthrough.mp4",ROOT/"artifacts/go1/demo/00-go1-walkthrough.mp4"]
    playlist=output/"two-robot-playlist.txt"
    playlist.write_text("".join("file '{}'\n".format(p.as_posix()) for p in clips))
    final=output/"00-two-robot-walkthrough.mp4"
    subprocess.run(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",str(playlist),
                    "-c","copy","-movflags","+faststart",str(final)],check=True)
    subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(final),"-f","null","-"],check=True)
    meta=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_entries",
        "format=duration,size:stream=width,height,nb_frames","-of","json",str(final)],text=True))
    result={"passed":True,"file":final.name,"fully_decoded":True,
            "sources":[str(p.relative_to(ROOT)) for p in clips],**meta}
    (output/"two-robot-media-validation.json").write_text(json.dumps(result,indent=2)+"\n")
    print("Combined walkthrough fully decoded")

if __name__=="__main__":main()
