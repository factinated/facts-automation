#!/usr/bin/env python3
"""Build a review-only Factinated Short using free Pixabay video clips."""
import json
import os
import hashlib
import time
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
ASSETS = OUT / "pixabay_assets"
CACHE = ROOT / ".pixabay_api_cache"
OUT.mkdir(exist_ok=True)
ASSETS.mkdir(exist_ok=True)
CACHE.mkdir(exist_ok=True)
W, H = 1080, 1920
API_KEY = os.environ.get("PIXABAY_API_KEY", "").strip()
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

FACTS = [
    ("A DAY ON VENUS", "Venus rotates so slowly that one rotation takes longer than its year.", "venus planet"),
    ("THE MOON IS DRIFTING AWAY", "The Moon moves about 3.8 centimetres farther from Earth each year.", "earth moon space"),
    ("STARS BEYOND COUNTING", "The observable universe contains an astonishing number of stars.", "galaxy stars space"),
]

def run(args):
    subprocess.run(args, check=True)

def request_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "FactinatedVideoAutomation/1.0"})
    with urllib.request.urlopen(req, timeout=35) as response:
        return json.loads(response.read().decode("utf-8"))

def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "FactinatedVideoAutomation/1.0"})
    with urllib.request.urlopen(req, timeout=90) as response:
        path.write_bytes(response.read())

def cached_video_search(query):
    # Pixabay asks API users to cache results for at least 24 hours.
    cache_file = CACHE / (hashlib.sha256(query.encode("utf-8")).hexdigest() + ".json")
    if cache_file.exists():
        try:
            saved = json.loads(cache_file.read_text(encoding="utf-8"))
            if time.time() - float(saved["cached_at"]) < 24 * 60 * 60:
                print(f"Using cached Pixabay search for: {query}")
                return saved["data"]
        except (ValueError, KeyError, OSError):
            pass
    params = urllib.parse.urlencode({
        "key": API_KEY, "q": query, "per_page": 20,
        "safesearch": "true", "video_type": "film", "order": "popular"
    })
    data = request_json("https://pixabay.com/api/videos/?" + params)
    cache_file.write_text(json.dumps({"cached_at": time.time(), "data": data}), encoding="utf-8")
    return data

def find_clip(query, index, used_sources):
    # Use targeted alternatives when the popular search results repeat a scene.
    alternatives = {
        "venus planet": ["venus planet", "venus surface space", "planet venus animation"],
        "earth moon space": ["earth moon space", "moon orbit earth", "moon surface space"],
        "galaxy stars space": ["galaxy stars space", "deep space nebula", "milky way stars"]
    }
    for search_query in alternatives.get(query, [query]):
        hits = cached_video_search(search_query).get("hits", [])
        for hit in hits:
            source = hit.get("pageURL", "")
            if source and source in used_sources:
                continue
            renditions = hit.get("videos", {})
            chosen = next((renditions.get(k) for k in ("large", "medium", "small")
                           if renditions.get(k, {}).get("url")), None)
            if not chosen:
                continue
            target = ASSETS / f"clip_{index+1}.mp4"
            try:
                download(chosen["url"], target)
                if target.stat().st_size > 100_000:
                    username = hit.get("user", "Pixabay contributor")
                    source = source or "https://pixabay.com/videos/"
                    used_sources.add(source)
                    print(f"Found unique clip for scene {index+1} using {search_query!r}; contributor: {username}.")
                    return target, username, source
            except Exception:
                if target.exists():
                    target.unlink()
                continue
    raise RuntimeError(f"No unique usable Pixabay clip found for scene {index+1}. Stopping rather than repeating footage.")

def wrap(draw, text, font, max_width):
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

def make_overlay(index, heading, detail, credit):
    image = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    # Full-screen footage with a small brand tag and bold, high-contrast captions.
    small = ImageFont.truetype(BOLD, 25)
    draw.rounded_rectangle((58, 100, 420, 164), radius=28, fill=(5, 12, 28, 205), outline=(80, 220, 255, 230), width=2)
    draw.text((82, 118), f"FACTINATED  /  0{index+1}", font=small, fill=(130, 232, 255, 255))
    head_font = ImageFont.truetype(BOLD, 68)
    y = 1120
    for line in wrap(draw, heading, head_font, 950):
        draw.text((W//2, y), line, font=head_font, anchor="mm", align="center",
                  fill=(255, 255, 255, 255), stroke_width=5, stroke_fill=(0, 0, 0, 230))
        y += 82
    body_font = ImageFont.truetype(BOLD, 40)
    y += 32
    for line in wrap(draw, detail, body_font, 900):
        draw.text((W//2, y), line, font=body_font, anchor="mm", align="center",
                  fill=(255, 235, 115, 255), stroke_width=4, stroke_fill=(0, 0, 0, 230))
        y += 54
    credit_font = ImageFont.truetype(REGULAR, 18)
    draw.text((58, 1870), f"Footage: Pixabay • {credit}", font=credit_font,
              fill=(255, 255, 255, 235), stroke_width=2, stroke_fill=(0, 0, 0, 220))
    path = OUT / f"overlay_{index+1}.png"
    image.save(path)
    return path

def main():
    if not API_KEY:
        raise SystemExit("Missing PIXABAY_API_KEY. Add it under repository Settings > Secrets and variables > Actions.")
    audio_text = "Here are three surprising space facts. " + " ".join(f"{h}. {d}" for h, d, _ in FACTS)
    audio_path = OUT / "pixabay_narration.mp3"
    run([sys.executable, "-m", "edge_tts", "--voice", "en-GB-RyanNeural", "--rate=-8%",
         "--text", audio_text, "--write-media", str(audio_path)])
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
                           check=True, capture_output=True, text=True)
    duration = float(probe.stdout.strip()) + 0.7
    weights = [len((h + " " + d).split()) for h, d, _ in FACTS]
    total = sum(weights)
    durations = [duration * w / total for w in weights]
    segments = []
    used_sources = set()
    (OUT / "pixabay_sources.txt").write_text("", encoding="utf-8")
    for i, ((heading, detail, query), seg_duration) in enumerate(zip(FACTS, durations)):
        clip, username, page_url = find_clip(query, i, used_sources)
        overlay = make_overlay(i, heading, detail, username)
        segment = OUT / f"pixabay_segment_{i+1}.mp4"
        # Loop a unique free clip if necessary, crop to vertical, and add bold captions.
        video_filter = (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,setsar=1,fps=24"
        )
        run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(clip), "-i", str(overlay),
             "-t", f"{seg_duration:.3f}", "-filter_complex",
             f"[0:v]{video_filter}[bg];[bg][1:v]overlay=0:0:format=auto,format=yuv420p[v]",
             "-map", "[v]", "-an", "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-preset", "veryfast",
             "-crf", "21", "-movflags", "+faststart", str(segment)])
        segments.append(segment)
        # Keep source links and contributors alongside the review artifact.
        with (OUT / "pixabay_sources.txt").open("a", encoding="utf-8") as f:
            f.write(f"Scene {i+1}: {heading}\nContributor: {username}\nSource: {page_url}\n\n")
    concat_file = OUT / "pixabay_segments.txt"
    concat_file.write_text("".join(f"file '{p.as_posix()}'\n" for p in segments), encoding="utf-8")
    silent = OUT / "pixabay_silent.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
         "-c", "copy", str(silent)])
    final = OUT / "factinated_free_footage_test.mp4"
    run(["ffmpeg", "-y", "-i", str(silent), "-i", str(audio_path), "-t", f"{duration:.3f}",
         "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-shortest",
         "-movflags", "+faststart", str(final)])
    print(f"Video created: {final}")
    print("This workflow saves a review artifact only. It does not publish to YouTube.")

if __name__ == "__main__":
    main()
