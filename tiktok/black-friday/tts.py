"""Генерация озвучки через Fish Audio TTS API.

Ключ берётся из FISH_API_KEY (в облачной сессии его подставляет прокси).
Результат: audio/<id>.mp3 и timeline.json с таймингами сцен.
"""
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

from script import GAP, SEGMENTS

HERE = Path(__file__).parent
AUDIO = HERE / "audio"
AUDIO.mkdir(exist_ok=True)
KEY = os.environ.get("FISH_API_KEY", "proxy-injected")


def tts(text: str, voice: str, out: Path) -> None:
    body = json.dumps({
        "text": text,
        "reference_id": voice,
        "format": "mp3",
        "mp3_bitrate": 192,
        "normalize": True,
        "latency": "normal",
    }).encode()
    req = urllib.request.Request(
        "https://api.fish.audio/v1/tts", data=body, method="POST",
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "model": "s1"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        out.write_bytes(r.read())


def duration(p: Path) -> float:
    return float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]).strip())


def main() -> None:
    force = "--force" in sys.argv
    t = 0.3
    timeline = []
    for seg in SEGMENTS:
        out = AUDIO / f"{seg['id']}.mp3"
        if force or not out.exists():
            print("TTS:", seg["id"])
            tts(seg["text"], seg["voice"], out)
        d = duration(out)
        timeline.append({**seg, "start": round(t, 3), "dur": round(d, 3)})
        t += d + GAP
    (HERE / "timeline.json").write_text(json.dumps(
        {"total": round(t + 0.6, 3), "segments": timeline}, ensure_ascii=False, indent=2))
    print("total", round(t, 2), "s")


if __name__ == "__main__":
    main()
