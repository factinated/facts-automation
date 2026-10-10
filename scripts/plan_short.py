#!/usr/bin/env python3
"""Create a source-backed Factinated Short plan with OpenAI; no video generation or publishing."""
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")

PROMPT = """
You are the research producer for Factinated, a YouTube Shorts channel about surprising, genuinely interesting facts.
Create ONE original 35-50 second YouTube Short. Choose the topic yourself; do not ask the user.
Use web search to research every factual claim. Prefer primary sources, universities, museums, peer-reviewed research, and established scientific or historical institutions. Do not invent facts or citations. If a claim cannot be supported, replace it.
Make the opening hook compelling but accurate. Use 3-4 connected facts, with a clear story arc and a satisfying ending. Avoid generic filler.
Plan footage for each scene so a free stock-footage search can find a genuinely relevant visual. Describe exactly what should be visible, and give 3 concise Pixabay search queries per scene. Do not suggest a clip that merely shares a broad topic if the visual would not illustrate the narration.
Return ONLY valid JSON with this shape:
{
  "topic": "short topic name",
  "title": "YouTube title",
  "description": "description including a brief sources note",
  "tags": ["tag1", "tag2"],
  "hook": "spoken opening",
  "narration": "complete narration, 90-120 words maximum",
  "scenes": [
    {
      "heading": "short on-screen heading",
      "narration": "exact spoken line(s) for this scene",
      "visual_brief": "specific footage that directly illustrates these lines",
      "pixabay_queries": ["query 1", "query 2", "query 3"],
      "source_urls": ["https://..."],
      "source_note": "what the cited source supports"
    }
  ],
  "fact_check_notes": ["important caveat or verification note"]
}
Keep 3-5 scenes. All factual scenes must include at least one real source URL returned by web search. Never state that a source proves more than it actually supports. Use natural British English. Keep the tone curious and cinematic, not clickbait.
"""

def main():
    if not API_KEY:
        raise SystemExit("Missing OPENAI_API_KEY. Add it in GitHub Settings > Secrets and variables > Actions.")
    payload = {
        "model": MODEL,
        "tools": [{"type": "web_search_preview"}],
        "input": PROMPT,
        "max_output_tokens": 4500
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        # Avoid printing request headers or the API key.
        raise SystemExit(f"OpenAI API request failed (HTTP {exc.code}). Response: {details[:1800]}") from None
    except Exception as exc:
        raise SystemExit(f"OpenAI API request failed: {type(exc).__name__}: {exc}") from None

    text_parts = []
    for item in data.get("output", []):
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    text_parts.append(content.get("text", ""))
    raw = "\\n".join(text_parts).strip()
    if not raw:
        raise SystemExit("OpenAI returned no text. Check the model and API account settings.")
    # Be tolerant if the model wraps JSON in a Markdown fence.
    if raw.startswith("```"):
        raw = raw.split("\\n", 1)[1]
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    try:
        plan = json.loads(raw)
    except json.JSONDecodeError:
        (OUT / "factinated_ai_plan_raw.txt").write_text(raw, encoding="utf-8")
        raise SystemExit("The AI response was not valid JSON. Raw response saved as factinated_ai_plan_raw.txt.")
    required = ["topic", "title", "description", "narration", "scenes"]
    missing = [key for key in required if not plan.get(key)]
    if missing:
        raise SystemExit("AI plan missing required fields: " + ", ".join(missing))
    for i, scene in enumerate(plan["scenes"], 1):
        if not scene.get("visual_brief") or not scene.get("pixabay_queries"):
            raise SystemExit(f"Scene {i} has no usable visual brief or Pixabay search queries.")
        if not scene.get("source_urls"):
            raise SystemExit(f"Scene {i} has no source URL; refusing to mark the plan source-backed.")
    json_path = OUT / "factinated_ai_plan.json"
    json_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    md = [
        "# Factinated AI Short Plan", "",
        f"## Topic: {plan['topic']}", "",
        f"**YouTube title:** {plan['title']}", "",
        "## Narration", "", plan["narration"], "",
        "## Scene plan", ""
    ]
    for i, scene in enumerate(plan["scenes"], 1):
        md += [
            f"### Scene {i}: {scene.get('heading', 'Scene')}", "",
            f"**Narration:** {scene.get('narration', '')}", "",
            f"**Visual brief:** {scene['visual_brief']}", "",
            "**Pixabay searches:** " + " | ".join(scene["pixabay_queries"]), "",
            "**Sources:**"
        ]
        md += [f"- {url}" for url in scene["source_urls"]]
        if scene.get("source_note"):
            md += ["", f"**Source note:** {scene['source_note']}"]
        md += [""]
    md += ["## YouTube description", "", plan["description"], "",
           "## Tags", "", ", ".join(plan.get("tags", [])), "",
           "## Fact-check notes", ""]
    md += [f"- {note}" for note in plan.get("fact_check_notes", [])]
    md += ["", "---", "This is an AI-generated draft for human review. It has not been turned into a video or published."]
    (OUT / "factinated_ai_plan.md").write_text("\\n".join(md) + "\\n", encoding="utf-8")
    print(f"AI plan created for review: {json_path}")
    print(f"Readable report created: {OUT / 'factinated_ai_plan.md'}")
    print("Review-only: no video was generated and nothing was published.")

if __name__ == "__main__":
    main()
