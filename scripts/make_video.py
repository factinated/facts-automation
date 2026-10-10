#!/usr/bin/env python3
"""Generate a simple vertical facts video with free local tools."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

TITLE = "3 Surprising Facts About Space"
FACTS = [
    ("A day on Venus", "Venus rotates so slowly that one rotation takes longer than its year."),
    ("The Moon is moving away", "The Moon drifts about 3.8 centimetres farther from Earth each year."),
    ("Stars beyond counting", "Astronomers estimate that the observable universe contains an enormous number of stars."),
]

def run(args):
    subprocess.run(args, check=True)

def main():
    narration = TITLE + ". " + " ".join(f"{heading}. {detail}" for heading, detail in FACTS)
    text_path = OUT / "narration.txt"
    audio_path = OUT / "narration.wav"
    text_path.write_text(narration, encoding="utf-8")
    run(["espeak-ng", "-v", "en-gb", "-s", "145", "-f", str(text_path), "-w", str(audio_path)])

    title_file = OUT / "title.txt"
    body_file = OUT / "body.txt"
    title_file.write_text(TITLE, encoding="utf-8")
    body_file.write_text("\n\n".join(f"{h}\n{d}" for h, d in FACTS), encoding="utf-8")

    font_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_regular = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    duration = max(25, len(narration.split()) / 2.3)
    vf = (
        "drawbox=x=0:y=0:w=iw:h=ih:color=#10182c:t=fill,"
        f"drawtext=fontfile={font_bold}:textfile={title_file}:fontcolor=white:fontsize=62:"
        "x=(w-text_w)/2:y=180:line_spacing=10,"
        f"drawtext=fontfile={font_regular}:textfile={body_file}:fontcolor=#dbeafe:fontsize=38:"
        "x=90:y=520:line_spacing=30"
    )
    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        f"color=c=#10182c:s=1080x1920:r=24:d={duration}",
        "-i", str(audio_path), "-vf", vf, "-t", str(duration), "-shortest",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart", str(OUT / "space_facts_short.mp4")
    ])
    print("Video created at output/space_facts_short.mp4")

if __name__ == "__main__":
    main()
