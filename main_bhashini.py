"""
MedGemma + Bhashini Local Speech Standalone Application.
Runs MedGemma 4B Vision & Text AI with local offline Bhashini ASR & TTS for 10 Indian languages.
Strictly isolated standalone entrypoint (main.py remains 100% untouched).
"""

import os
import sys
import tempfile
import time
from typing import Optional
from pathlib import Path

try:
    import torch
    import ollama
    from bhashini_speech import (
        BhashiniLocalASR,
        BhashiniLocalTTS,
        listen_for_speech,
        speak,
        play_audio,
        StopEvent,
        detect_input_language,
        SPEECH_LANGUAGE_CODES,
        RESPONSE_LANGUAGE_HINTS,
        OUTPUT_WAV,
    )
except ImportError as exc:
    print(f"Error importing modules for main_bhashini.py: {exc}")
    raise exc

MODEL_NAME = "medgemma:4b"
SPEECH_COMMAND_PREFIX = "voice"


def _normalize_image_path(image_path: str) -> str:
    image_path = os.path.abspath(image_path)
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    if not os.path.isfile(image_path):
        raise ValueError(f"Path is not a file: {image_path}")

    ext = Path(image_path).suffix.lower()
    if ext in {".jpg", ".jpeg", ".png"}:
        return image_path

    try:
        from PIL import Image
        with Image.open(image_path) as img:
            converted_path = image_path + ".jpg"
            img.convert("RGB").save(converted_path, "JPEG")
            return converted_path
    except Exception:
        return image_path


def get_medgemma_response(prompt: str, image_path: Optional[str] = None, response_language: str = "en") -> str:
    language_hint = RESPONSE_LANGUAGE_HINTS.get(response_language, RESPONSE_LANGUAGE_HINTS["en"])
    
    if image_path:
        image_path = _normalize_image_path(image_path)
        prompt_with_hint = f"{prompt}\n\n{language_hint}" if response_language != "en" else prompt

        try:
            response = ollama.generate(
                model=MODEL_NAME,
                prompt=prompt_with_hint,
                images=[image_path],
                keep_alive=-1,
                options={
                    "num_ctx": 2048,
                    "num_predict": 180,
                    "temperature": 0.3,
                },
            )
            return response.get("response", "").strip()
        except Exception as exc:
            if image_path.endswith(".jpg") and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except OSError:
                    pass
            raise exc

    messages = [{"role": "user", "content": prompt}]
    if response_language != "en":
        messages.insert(0, {"role": "system", "content": language_hint})

    response = ollama.chat(
        model=MODEL_NAME,
        messages=messages,
        keep_alive=-1,
        options={
            "num_ctx": 2048,
            "num_predict": 180,
            "temperature": 0.3,
        },
    )
    return response["message"]["content"]


def parse_image_input(user_input: str):
    text = user_input.strip()
    image_extensions = {".png", ".jpg", ".jpeg", ".webp"}

    if text.startswith("image:") or text.startswith("img:"):
        prefix = "image:" if text.startswith("image:") else "img:"
        rest = text[len(prefix):].strip()

        if "|" in rest:
            image_path, prompt = rest.split("|", 1)
            return prompt.strip(), image_path.strip()

        if " " in rest:
            image_path, prompt = rest.split(" ", 1)
            return prompt.strip(), image_path.strip()

        return "Describe this image", rest.strip()

    if "|" in text:
        image_path, prompt = text.split("|", 1)
        image_path = image_path.strip()
        prompt = prompt.strip()
        if os.path.splitext(image_path)[1].lower() in image_extensions:
            return prompt or "Describe this image", image_path

    if os.path.exists(text) and os.path.isfile(text):
        ext = os.path.splitext(text)[1].lower()
        if ext in image_extensions:
            return "Describe this image", text

    return text, None


def main():
    print("=" * 65)
    print("   MedGemma Standalone (Bhashini Local ASR/TTS)")
    print("   Supported Languages (10): EN, HI, TA, TE, BN, GU, KN, ML, MR, PA")
    print("=" * 65)
    print("Type 'voice' or 'voice:hi' / 'voice:ta' / 'voice:kn' to speak.")
    print("Type 'quit' to exit.\n")

    while True:
        user_input = input("You : ").strip()
        speech_input_lang = None

        if user_input.lower() in ["quit", "exit"]:
            print("Exiting MedGemma Bhashini App. Goodbye!")
            break

        if user_input.lower().startswith(SPEECH_COMMAND_PREFIX):
            requested_lang = "en"
            audio_file_override = None

            cmd_body = user_input[len(SPEECH_COMMAND_PREFIX):].strip()
            if cmd_body.startswith(":"):
                cmd_body = cmd_body[1:].strip()

            if "|" in cmd_body:
                lang_part, path_part = cmd_body.split("|", 1)
                requested_lang = lang_part.strip().lower()
                audio_file_override = path_part.strip()
            elif os.path.exists(cmd_body) and os.path.isfile(cmd_body):
                audio_file_override = cmd_body
            elif cmd_body in SPEECH_LANGUAGE_CODES:
                requested_lang = cmd_body

            if requested_lang not in SPEECH_LANGUAGE_CODES:
                requested_lang = "en"

            if audio_file_override and os.path.exists(audio_file_override):
                print(f"Transcribing audio file '{audio_file_override}' for [{requested_lang.upper()}]...")
                try:
                    model = BhashiniLocalASR.get_model()
                    segments, _info = model.transcribe(audio_file_override, language=requested_lang, beam_size=5)
                    recognized_text = " ".join(seg.text.strip() for seg in segments if seg.text and seg.text.strip())
                except Exception as exc:
                    print(f"Audio file transcription error: {exc}")
                    recognized_text = None
            else:
                recognized_text = listen_for_speech(requested_lang)

            if not recognized_text:
                print("No speech detected or recognition canceled.")
                continue

            print(f"You (voice [{requested_lang.upper()}]): {recognized_text}")
            user_input = recognized_text
            speech_input_lang = requested_lang

        if user_input:
            if speech_input_lang is not None:
                lang = speech_input_lang
            else:
                lang = detect_input_language(user_input)
        else:
            lang = "en"

        if user_input == "":
            continue

        prompt, image_path = parse_image_input(user_input)
        print(f"\nThinking (Language: {lang.upper()})...\n")

        try:
            reply = get_medgemma_response(prompt, image_path, response_language=lang)
        except Exception as exc:
            print(f"MedGemma LLM Error: {exc}")
            continue

        print("MedGemma:")
        print(reply)

        print("\nSynthesizing & Speaking...")
        print("Press 's' or 'q' during playback to stop.\n")

        try:
            speak(reply, lang)
            stop_event = StopEvent()
            play_audio(OUTPUT_WAV, stop_event)
        except Exception as exc:
            print(f"Speech synthesis/audio error: {exc}")


if __name__ == "__main__":
    main()
