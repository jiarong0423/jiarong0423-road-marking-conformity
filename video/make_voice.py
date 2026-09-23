#!/usr/bin/env python3
"""Voiceover for each slide with the Gemini TTS API.

The key is read from GEMINI_API_KEY only; it is never printed or written.
The subtitle text of each row in script_en.md is sent to the API.

    GEMINI_API_KEY=... /opt/anaconda3/bin/python3 -B video/make_voice.py [--voice Charon]
    /opt/anaconda3/bin/python3 -B video/make_voice.py --vertex [--project P --location L]
        (Vertex AI with gcloud Application Default Credentials; no key handled here)

Writes video/audio/NN.wav (24 kHz mono 16-bit).
"""
import argparse, os, re, sys, time, wave
from pathlib import Path

HERE = Path(__file__).resolve().parent


def rows():
    out = []
    for line in (HERE / "script_en.md").read_text().splitlines():
        m = re.match(r"\|\s*(\d+)\s*\|[^|]*\|[^|]*\|\s*(.+?)\s*\|\s*$", line)
        if m:
            out.append((int(m.group(1)), m.group(2)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="Charon")
    ap.add_argument("--model", default="gemini-2.5-flash-preview-tts")
    ap.add_argument("--only", type=int, nargs="*")
    ap.add_argument("--vertex", action="store_true")
    ap.add_argument("--project")
    ap.add_argument("--location", default="us-central1")
    a = ap.parse_args()
    from google import genai
    from google.genai import types
    if a.vertex:
        import subprocess
        project = a.project or subprocess.run(["gcloud", "config", "get-value", "project"],
                                              capture_output=True, text=True).stdout.strip()
        if not project:
            sys.exit("ERROR no project: pass --project or set gcloud config project")
        client = genai.Client(vertexai=True, project=project, location=a.location)
    else:
        if not os.environ.get("GEMINI_API_KEY"):
            sys.exit("ERROR GEMINI_API_KEY is not set (or use --vertex)")
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    (HERE / "audio").mkdir(exist_ok=True)
    cfg = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=a.voice))))
    for n, text in rows():
        if a.only and n not in a.only:
            continue
        prompt = "Read this calmly and clearly, like a short documentary narration:\n" + text
        for attempt in range(3):
            try:
                r = client.models.generate_content(model=a.model, contents=prompt, config=cfg)
                pcm = r.candidates[0].content.parts[0].inline_data.data
                break
            except Exception as e:
                print(f"ERROR slide {n} attempt {attempt + 1}: {type(e).__name__}: {str(e)[:120]}")
                time.sleep(5 * (attempt + 1))
        else:
            sys.exit(f"ERROR slide {n}: giving up")
        p = HERE / "audio" / f"{n:02d}.wav"
        with wave.open(str(p), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
        print(f"slide {n:2d}: {len(pcm) / 48000:.1f} s -> {p.name}")


if __name__ == "__main__":
    main()
