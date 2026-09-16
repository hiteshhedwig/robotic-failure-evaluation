"""Export selected recorded-demo excerpts as the inline README animation."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    clips = [
        ("01-baseline.mp4", 8, 11),
        ("02-balance-recovery.mp4", 10, 26),
        ("03-fall.mp4", 16, 24),
        ("04-upright-task-failure.mp4", 39, 44),
    ]
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    filters = []
    for i, (name, start, end) in enumerate(clips):
        command += ["-ss", str(start), "-t", str(end-start),
                    "-i", str(ROOT / "artifacts/demo" / name)]
        filters.append(f"[{i}:v]fps=6,scale=960:-1:flags=lanczos,setpts=PTS-STARTPTS[v{i}]")
    filters.append("".join(f"[v{i}]" for i in range(len(clips))) +
                   "concat=n=4:v=1:a=0,split[a][b]")
    filters += ["[a]palettegen=max_colors=64:stats_mode=diff[p]",
                "[b][p]paletteuse=dither=bayer:bayer_scale=5"]
    command += ["-filter_complex", ";".join(filters), "-loop", "0",
                str(ROOT / "artifacts/demo/walkthrough.gif")]
    subprocess.run(command, check=True)
