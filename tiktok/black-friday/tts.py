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

from script import EDGE_VOICES, GAP, PIPER_VOICES, SEGMENTS

HERE = Path(__file__).parent
AUDIO = HERE / "audio"
AUDIO.mkdir(exist_ok=True)
KEY = os.environ.get("FISH_API_KEY", "proxy-injected")
ENGINE = os.environ.get("TTS_ENGINE", "fish")  # fish | edge | piper | free (edge, иначе piper)
PIPER_DIR = Path(os.environ.get("PIPER_DIR", HERE / "piper"))


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


def tts_edge(seg: dict, out: Path) -> None:
    import asyncio
    import edge_tts
    cfg = EDGE_VOICES[seg.get("edge", seg["voice"])]
    asyncio.run(edge_tts.Communicate(seg["text"], cfg["voice"], rate=cfg["rate"], pitch=cfg["pitch"]).save(str(out)))


def tts_piper(seg: dict, out: Path) -> None:
    import wave
    from piper import PiperVoice
    cfg = PIPER_VOICES[seg.get("edge", seg["voice"])]
    voice = PiperVoice.load(str(PIPER_DIR / f"{cfg['model']}.onnx"))
    wav = out.with_suffix(".wav")
    with wave.open(str(wav), "wb") as wf:
        try:  # piper-tts >= 1.3
            from piper import SynthesisConfig
            voice.synthesize_wav(seg["text"], wf, syn_config=SynthesisConfig(length_scale=cfg["length_scale"]))
        except ImportError:  # piper-tts 1.2
            voice.synthesize(seg["text"], wf, length_scale=cfg["length_scale"])
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(wav), "-b:a", "192k", str(out)], check=True)
    wav.unlink()


def duration(p: Path) -> float:
    return float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]).strip())


def main() -> None:
    global ENGINE
    force = "--force" in sys.argv
    if ENGINE == "free":
        try:
            tts_edge(SEGMENTS[0], AUDIO / "_probe.mp3")
            ENGINE = "edge"
        except Exception as e:  # Microsoft иногда не отдаёт звук серверам CI
            print("Edge TTS недоступен:", e, "→ использую Piper")
            ENGINE = "piper"
        (AUDIO / "_probe.mp3").unlink(missing_ok=True)
    print("TTS engine:", ENGINE)
    t = 0.3
    timeline = []
    for seg in SEGMENTS:
        out = AUDIO / f"{seg['id']}.mp3"
        if force or not out.exists():
            print("TTS:", seg["id"])
            if ENGINE == "edge":
                tts_edge(seg, out)
            elif ENGINE == "piper":
                tts_piper(seg, out)
            else:
                tts(seg["text"], seg["voice"], out)
        d = duration(out)
        timeline.append({**seg, "start": round(t, 3), "dur": round(d, 3)})
        t += d + GAP
    (HERE / "timeline.json").write_text(json.dumps(
        {"total": round(t + 0.6, 3), "segments": timeline}, ensure_ascii=False, indent=2))
    print("total", round(t, 2), "s")


if __name__ == "__main__":
    main()
