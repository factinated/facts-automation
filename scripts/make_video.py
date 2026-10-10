#!/usr/bin/env python3
"""Build a space-facts Short with illustrated scenes and neural British narration."""
from pathlib import Path
import subprocess
import sys
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)
W, H = 1080, 1920
TITLE = "3 SURPRISING SPACE FACTS"
FACTS = [
    ("A DAY ON VENUS", "Venus rotates so slowly that one rotation takes longer than its year.", "venus"),
    ("THE MOON IS DRIFTING AWAY", "The Moon moves about 3.8 centimetres farther from Earth each year.", "moon"),
    ("STARS BEYOND COUNTING", "The observable universe contains an astonishing number of stars.", "stars"),
]
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def run(args):
    subprocess.run(args, check=True)

def fit_lines(draw, text, font, max_width):
    words = text.split()
    lines, line = [], ""
    for word in words:
        candidate = (line + " " + word).strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines

def make_scene(index, heading, detail, kind):
    random.seed(100 + index)
    im = Image.new("RGB", (W, H), (8, 12, 32))
    px = im.load()
    # Soft vertical midnight-blue gradient
    for y in range(H):
        t = y / H
        col = (int(8 + 8*t), int(12 + 7*t), int(32 + 28*t))
        ImageDraw.Draw(im).line((0, y, W, y), fill=col)
    d = ImageDraw.Draw(im, "RGBA")
    # Stars
    for _ in range(180):
        x, y = random.randrange(W), random.randrange(H)
        r = random.choice([1, 1, 2, 3])
        d.ellipse((x-r, y-r, x+r, y+r), fill=(190, 220, 255, random.randrange(90, 230)))
    # Glowing illustrated planet / moon artwork
    if kind == "venus":
        cx, cy, r = 540, 680, 245
        glow = Image.new("RGBA", (W, H), (0,0,0,0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse((cx-r-50, cy-r-50, cx+r+50, cy+r+50), fill=(236, 150, 76, 48))
        glow = glow.filter(ImageFilter.GaussianBlur(45))
        im = Image.alpha_composite(im.convert("RGBA"), glow)
        d = ImageDraw.Draw(im, "RGBA")
        d.ellipse((cx-r, cy-r, cx+r, cy+r), fill=(211, 133, 73, 255), outline=(255, 213, 157, 255), width=5)
        for j in range(7):
            yy = cy-r+40+j*58
            d.arc((cx-r+15, yy-30, cx+r-15, yy+40), 0, 180, fill=(255, 191, 115, 150), width=12)
        d.ellipse((cx-90, cy-150, cx+35, cy-25), fill=(255, 210, 144, 65))
    elif kind == "moon":
        # Earth and Moon linked by a fine orbit arc
        d.arc((115, 390, 965, 1110), 195, 345, fill=(115, 180, 255, 180), width=4)
        d.ellipse((140, 600, 420, 880), fill=(48, 115, 215, 255), outline=(145, 210, 255, 255), width=5)
        d.arc((170, 630, 390, 850), 20, 260, fill=(72, 190, 160, 230), width=35)
        d.ellipse((730, 480, 890, 640), fill=(202, 210, 224, 255), outline=(245, 248, 255, 255), width=4)
        for x, y, r in [(770,525,14),(825,570,20),(785,600,9),(850,525,8)]:
            d.ellipse((x-r,y-r,x+r,y+r), fill=(130,145,166,180))
        d.line((435, 710, 715, 580), fill=(255, 210, 120, 230), width=4)
        d.polygon([(715,580),(683,579),(700,608)], fill=(255,210,120,230))
    else:
        # Galaxy swirl made from softly glowing star clusters
        cx, cy = 540, 690
        for i in range(520):
            t = random.random() * 11
            arm = random.randrange(4) * 1.5708
            radius = random.random() * 330
            ang = t + arm + radius * 0.009
            x = int(cx + radius * __import__("math").cos(ang))
            y = int(cy + radius * 0.62 * __import__("math").sin(ang))
            r = random.choice([1,2,3,4])
            d.ellipse((x-r,y-r,x+r,y+r), fill=random.choice([(120,180,255,220),(205,160,255,220),(255,220,160,230)]))
        d.ellipse((cx-18,cy-18,cx+18,cy+18), fill=(255,245,210,255))
    # Top label and scene copy
    d = ImageDraw.Draw(im, "RGBA")
    d.rounded_rectangle((70, 90, 400, 148), radius=24, fill=(77, 210, 255, 35), outline=(77, 210, 255, 180), width=2)
    small = ImageFont.truetype(BOLD, 25)
    d.text((94, 105), f"SPACE FILE  /  0{index+1}", font=small, fill=(130, 225, 255, 255))
    head_font = ImageFont.truetype(BOLD, 53)
    y = 1120
    for line in fit_lines(d, heading, head_font, 900):
        d.text((90, y), line, font=head_font, fill=(255,255,255,255), stroke_width=1, stroke_fill=(20,30,65,255))
        y += 68
    body_font = ImageFont.truetype(REGULAR, 38)
    y += 38
    for line in fit_lines(d, detail, body_font, 880):
        d.text((92, y), line, font=body_font, fill=(206,222,247,255))
        y += 58
    # Bottom progress indicator
    d.rounded_rectangle((75, 1795, 1005, 1807), radius=6, fill=(255,255,255,45))
    d.rounded_rectangle((75, 1795, 75 + int(930*(index+1)/3), 1807), radius=6, fill=(77,210,255,255))
    path = OUT / f"scene_{index+1}.png"
    im.convert("RGB").save(path, quality=95)
    return path

def main():
    narration = "Here are three surprising space facts. " + " ".join(f"{heading}. {detail}" for heading, detail, _ in FACTS)
    audio_path = OUT / "narration.mp3"
    run([sys.executable, "-m", "edge_tts", "--voice", "en-GB-RyanNeural", "--rate=-8%", "--text", narration, "--write-media", str(audio_path)])
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)], check=True, capture_output=True, text=True)
    duration = float(probe.stdout.strip()) + 1.0
    weights = [len((h + " " + detail).split()) for h, detail, _ in FACTS]
    total = sum(weights)
    durations = [duration * w / total for w in weights]
    scenes = [make_scene(i, h, detail, kind) for i, (h, detail, kind) in enumerate(FACTS)]
    segments = []
    for i, (scene, seg_duration) in enumerate(zip(scenes, durations)):
        segment = OUT / f"segment_{i+1}.mp4"
        # A subtle zoom makes each illustrated scene feel less static.
        run(["ffmpeg", "-y", "-loop", "1", "-i", str(scene), "-t", f"{seg_duration:.3f}",
             "-vf", "zoompan=z='min(zoom+0.00035,1.045)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=24,format=yuv420p",
             "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", str(segment)])
        segments.append(segment)
    concat_file = OUT / "segments.txt"
    concat_file.write_text("".join(f"file '{p.as_posix()}'\n" for p in segments), encoding="utf-8")
    silent = OUT / "silent_video.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(silent)])
    final = OUT / "space_facts_short.mp4"
    run(["ffmpeg", "-y", "-i", str(silent), "-i", str(audio_path), "-t", f"{duration:.3f}",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(final)])
    print("Video created at output/space_facts_short.mp4")

if __name__ == "__main__":
    main()
