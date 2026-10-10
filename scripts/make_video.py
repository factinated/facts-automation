#!/usr/bin/env python3
"""Build a space-facts Short using real NASA imagery and animated camera moves."""
from pathlib import Path
import json
import random
import subprocess
import sys
import urllib.parse
import urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
ASSETS = OUT / "assets"
OUT.mkdir(exist_ok=True)
ASSETS.mkdir(exist_ok=True)
W, H = 1080, 1920
FACTS = [
    ("A DAY ON VENUS", "Venus rotates so slowly that one rotation takes longer than its year.", "Venus planet", "venus"),
    ("THE MOON IS DRIFTING AWAY", "The Moon moves about 3.8 centimetres farther from Earth each year.", "Earth Moon from space", "moon"),
    ("STARS BEYOND COUNTING", "The observable universe contains an astonishing number of stars.", "Hubble galaxy deep space", "galaxy"),
]
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def run(args):
    subprocess.run(args, check=True)

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "FactsChannelDemo/1.0"})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))

def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "FactsChannelDemo/1.0"})
    with urllib.request.urlopen(req, timeout=45) as response:
        path.write_bytes(response.read())

def nasa_image(query, fallback_name):
    """Find a usable real image from NASA's public image library."""
    try:
        search_url = "https://images-api.nasa.gov/search?" + urllib.parse.urlencode({
            "q": query, "media_type": "image", "page_size": 15
        })
        results = get_json(search_url).get("collection", {}).get("items", [])
        for item in results:
            data = item.get("data", [{}])[0]
            nasa_id = data.get("nasa_id", "")
            if not nasa_id:
                continue
            # Prefer an original-sized JPEG/PNG, avoiding very large TIFFs.
            manifest = get_json("https://images-api.nasa.gov/asset/" + urllib.parse.quote(nasa_id, safe=""))
            links = [x.get("href", "") for x in manifest.get("collection", {}).get("items", [])]
            candidates = [u for u in links if u.lower().endswith((".jpg", ".jpeg", ".png"))]
            if not candidates:
                candidates = [u for u in item.get("links", []) if u.get("rel") == "preview" for u in [u.get("href", "")]]
            if candidates:
                target = ASSETS / f"{fallback_name}.jpg"
                download(candidates[0], target)
                with Image.open(target) as im:
                    im.verify()
                print(f"Using NASA image: {data.get('title', nasa_id)}")
                return target
    except Exception as exc:
        print(f"NASA image lookup for {query!r} failed: {exc}")
    return None

def fit_lines(draw, text, font, max_width):
    lines, line = [], ""
    for word in text.split():
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

def prepare_photo(source, index, heading, detail):
    # Fill the vertical canvas with real photography, then add a cinematic text-safe gradient.
    if source:
        with Image.open(source) as original:
            im = original.convert("RGB")
            scale = max(W / im.width, H / im.height)
            im = im.resize((int(im.width * scale), int(im.height * scale)), Image.Resampling.LANCZOS)
            left = max(0, (im.width - W) // 2)
            top = max(0, (im.height - H) // 2)
            im = im.crop((left, top, left + W, top + H))
    else:
        # Graceful fallback if NASA's library is temporarily unavailable.
        im = Image.new("RGB", (W, H), (7, 12, 30))
        d = ImageDraw.Draw(im)
        random.seed(index + 20)
        for _ in range(400):
            x, y = random.randrange(W), random.randrange(H)
            r = random.choice([1, 1, 2, 3])
            d.ellipse((x-r, y-r, x+r, y+r), fill=(170, 195, 235))
    im = ImageEnhance.Color(im).enhance(1.12)
    im = ImageEnhance.Contrast(im).enhance(1.08)
    # A dark gradient protects text readability without flattening the image.
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for y in range(H):
        alpha = int(20 + 210 * max(0, (y / H - 0.34) / 0.66) ** 1.3)
        od.line((0, y, W, y), fill=(2, 7, 20, alpha))
    im = Image.alpha_composite(im.convert("RGBA"), overlay)
    d = ImageDraw.Draw(im, "RGBA")
    small = ImageFont.truetype(BOLD, 25)
    d.rounded_rectangle((64, 88, 388, 148), radius=24, fill=(8, 20, 42, 190), outline=(105, 211, 255, 220), width=2)
    d.text((88, 104), f"SPACE FILE  /  0{index+1}", font=small, fill=(150, 229, 255, 255))
    head_font = ImageFont.truetype(BOLD, 53)
    y = 1290
    for line in fit_lines(d, heading, head_font, 930):
        d.text((68, y), line, font=head_font, fill=(255,255,255,255), stroke_width=1, stroke_fill=(0,0,0,220))
        y += 68
    body_font = ImageFont.truetype(REGULAR, 38)
    y += 25
    for line in fit_lines(d, detail, body_font, 910):
        d.text((72, y), line, font=body_font, fill=(225,235,250,255), stroke_width=1, stroke_fill=(0,0,0,160))
        y += 56
    d.rounded_rectangle((68, 1800, 1012, 1812), radius=6, fill=(255,255,255,70))
    d.rounded_rectangle((68, 1800, 68 + int(944*(index+1)/3), 1812), radius=6, fill=(95,210,255,255))
    path = OUT / f"scene_{index+1}.png"
    im.convert("RGB").save(path, quality=95)
    return path

def main():
    narration = "Here are three surprising space facts. " + " ".join(f"{heading}. {detail}" for heading, detail, _, _ in FACTS)
    audio_path = OUT / "narration.mp3"
    run([sys.executable, "-m", "edge_tts", "--voice", "en-GB-RyanNeural", "--rate=-8%", "--text", narration, "--write-media", str(audio_path)])
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)], check=True, capture_output=True, text=True)
    duration = float(probe.stdout.strip()) + 1.0
    weights = [len((h + " " + detail).split()) for h, detail, _, _ in FACTS]
    total = sum(weights)
    durations = [duration * w / total for w in weights]
    scenes = []
    for i, (heading, detail, query, name) in enumerate(FACTS):
        photo = nasa_image(query, name)
        scenes.append(prepare_photo(photo, i, heading, detail))
    segments = []
    for i, (scene, seg_duration) in enumerate(zip(scenes, durations)):
        segment = OUT / f"segment_{i+1}.mp4"
        # More noticeable slow push-in with a gentle sideways drift.
        zoom = "zoompan=z='min(zoom+0.0010,1.12)':x='iw/2-(iw/zoom/2)+sin(on/75)*18':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=24,format=yuv420p"
        run(["ffmpeg", "-y", "-loop", "1", "-i", str(scene), "-t", f"{seg_duration:.3f}",
             "-vf", zoom, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(segment)])
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
