#!/usr/bin/env python3
"""Generate a sample facts Short using a free neural voice."""
from pathlib import Path
import subprocess
import sys

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
    audio_path = OUT / "narration.mp3"
    text_path.write_text(narration, encoding="utf-8")

    # Neural British English text-to-speech. No API key is required.
    run([
        sys.executable, "-m", "edge_tts",
        "--voice", "en-GB-RyanNeural",
        "--rate=-8%",
        "--text", narration,
        "--write-media", str(audio_path),
    ])

    title_file = OUT / "title.txt"
    body_file = OUT / "body.txt"
    title_file.write_text(TITLE, encoding="utf-8")
    body_file.write_text("\n\n".join(f"{h}\n{d}" for h, d in FACTS), encoding="utf-8")

    font_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_regular = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    probe = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)
    ], check=True, capture_output=True, text=True)
    duration = float(probe.stdout.strip()) + 1.5
    vf = (
        "drawbox=x=0:y=0:w=iw:h=ih:color=#0b1024:t=fill,"
        "drawbox=x=70:y=95:w=940:h=8:color=#55d6ff:t=fill,"
        "drawbox=x=70:y=110:w=220:h=8:color=#a78bfa:t=fill,"
        f"drawtext=fontfile={font_bold}:textfile={title_file}:fontcolor=white:fontsize=62:"
        "x=(w-text_w)/2:y=180:line_spacing=10,"
        f"drawtext=fontfile={font_regular}:textfile={body_file}:fontcolor=#dbeafe:fontsize=38:"
        "x=90:y=520:line_spacing=30"
    )
    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        f"color=c=#0b1024:s=1080x1920:r=24:d={duration}",
        "-i", str(audio_path), "-vf", vf, "-t", str(duration), "-shortest",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart", str(OUT / "space_facts_short.mp4")
    ])
    print("Video created at output/space_facts_short.mp4")

if __name__ == "__main__":
    main()
