#!/usr/bin/env python3
"""Generate one Higgsfield test clip and save it for human review."""
import json, os, time, urllib.error, urllib.request
from pathlib import Path

API_KEY = os.environ.get("HF_API_KEY", "").strip()
ENDPOINT = "https://api.higgsfield.ai/bytedance/seedance-2.5/text-to-video"
OUT = Path("output")
OUT.mkdir(exist_ok=True)

def request_json(url, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Key {API_KEY}", "Content-Type": "application/json",
        "Accept": "application/json"
    }, method="GET" if payload is None else "POST")
    try:
        with urllib.request.urlopen(req, timeout=90) as res:
            raw = res.read()
            return json.loads(raw.decode()) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Higgsfield API returned HTTP {exc.code}: {detail[:1000]}") from None

def find_video_url(obj):
    if isinstance(obj, dict):
        for key in ("video", "output", "result", "asset"):
            val = obj.get(key)
            if isinstance(val, str) and val.startswith("https://"): return val
            found = find_video_url(val) if isinstance(val, (dict, list)) else None
            if found: return found
        for key in ("url", "download_url", "video_url", "public_url"):
            val = obj.get(key)
            if isinstance(val, str) and val.startswith("https://"): return val
        for val in obj.values():
            found = find_video_url(val)
            if found: return found
    elif isinstance(obj, list):
        for val in obj:
            found = find_video_url(val)
            if found: return found
    return None

def main():
    if not API_KEY:
        raise SystemExit("Missing HF_API_KEY. Add it under repository Settings > Secrets and variables > Actions.")
    prompt = ("Vertical 9:16 cinematic science documentary footage: photorealistic planet Earth "
              "from low orbit, curved blue horizon and thin glowing atmosphere, sunlight rising "
              "over the edge of the planet, slow subtle camera drift, realistic clouds and ocean, "
              "premium space documentary look, natural motion, no text, no subtitles, no logos, no watermark.")
    print("Submitting one 5-second 720p test clip to Higgsfield.")
    result = request_json(ENDPOINT, {"prompt": prompt, "duration": 5, "resolution": "720p",
        "aspect_ratio": "9:16", "output_format": "mp4", "generate_audio": False})
    status_url = result.get("status_url") or result.get("statusUrl")
    request_id = result.get("request_id") or result.get("requestId") or result.get("id")
    if not status_url and request_id:
        status_url = f"https://api.higgsfield.ai/requests/{request_id}/status"
    final = result
    if not find_video_url(final):
        if not status_url:
            raise RuntimeError("No video URL or status URL in API response. Response keys: " + ", ".join(result.keys()))
        deadline = time.time() + 900
        while time.time() < deadline:
            time.sleep(8)
            final = request_json(status_url)
            status = str(final.get("status", final.get("state", "unknown"))).lower()
            print(f"Generation status: {status}")
            if status in ("failed", "error", "cancelled", "canceled"):
                raise RuntimeError("Higgsfield generation failed: " + json.dumps(final)[:1000])
            if find_video_url(final): break
        else:
            raise RuntimeError("Timed out waiting for generation. Check the Higgsfield API Requests page.")
    url = find_video_url(final)
    if not url: raise RuntimeError("No downloadable video URL found. Response keys: " + ", ".join(final.keys()))
    target = OUT / "factinated_higgsfield_test.mp4"
    req = urllib.request.Request(url, headers={"User-Agent": "FactinatedVideoAutomation/1.0"})
    with urllib.request.urlopen(req, timeout=120) as res: target.write_bytes(res.read())
    if target.stat().st_size < 100_000:
        raise RuntimeError(f"Downloaded video is unexpectedly small ({target.stat().st_size} bytes).")
    print(f"Test clip saved: {target} ({target.stat().st_size} bytes).")
    print("This workflow only saves an artifact for review. It does not publish to YouTube.")

if __name__ == "__main__":
    main()
