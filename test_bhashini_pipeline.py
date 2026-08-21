"""
Standalone Test and Benchmark Script for Local Bhashini ASR and TTS Pipeline.
Verifies offline performance, latency, audio synthesis quality, and memory utilization
for English, Hindi, Tamil, Telugu, Bengali, Gujarati, Kannada, Malayalam, Marathi, and Punjabi.
"""

import os
import sys
import time
import torch
import numpy as np
import soundfile as sf
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Model Cache Path
BHASHINI_MODEL_DIR = os.environ.get(
    "BHASHINI_MODEL_DIR",
    os.path.expanduser("~/.cache/medgemma/models")
)

TTS_MODEL_IDS = {
    "en": "facebook/mms-tts-eng",
    "hi": "facebook/mms-tts-hin",
    "ta": "facebook/mms-tts-tam",
    "te": "facebook/mms-tts-tel",
    "bn": "facebook/mms-tts-ben",
    "gu": "facebook/mms-tts-guj",
    "kn": "facebook/mms-tts-kan",
    "ml": "facebook/mms-tts-mal",
    "mr": "facebook/mms-tts-mar",
    "pa": "facebook/mms-tts-pan",
}

TEST_PROMPTS = {
    "en": "Hello, welcome to MedGemma Voice Assistant. How can I assist with your health query today?",
    "hi": "नमस्ते, मेडजेम्मा वॉयस असिस्टेंट में आपका स्वागत है। आज मैं आपके स्वास्थ्य संबंधी प्रश्न में कैसे मदद कर सकता हूं?",
    "ta": "வணக்கம், மெட்ஜெம்மா குரல் உதவிக்கு வரவேற்கிறோம். இன்று உங்கள் சுகாதார கேள்விகளுக்கு நான் எவ்வாறு உதவ முடியும்?",
    "te": "నమస్కారం, మెడ్‌గెమ్మా వాయిస్ అసిస్టెంట్‌కి స్వాగతం. ఈరోజు మీ ఆరోగ్య సమస్యలలో నేను ఎలా సహాయపడగలను?",
    "bn": "হ্যালো, মেডজেম্মা ভয়েস অ্যাসিস্ট্যান্টে স্বাগতম। আজ আমি কীভাবে আপনার স্বাস্থ্য সংক্রান্ত প্রশ্নে সাহায্য করতে পারি?",
    "gu": "નમસ્તે, મેડજેમ્મા વોઇસ આસિસ્ટન્ટમાં આપનું સ્વાગત છે. આજે હું આપના સ્વાસ્થ્ય પ્રશ્નમાં કેવી રીતે મદદ કરી શકું?",
    "kn": "ನಮಸ್ಕಾರ, ಮೆಡ್‌ಗೆಮ್ಮಾ ಧ್ವನಿ ಸಹಾಯಕಕ್ಕೆ ಸ್ವಾಗತ. ಇಂದು ನಿಮ್ಮ ಆರೋಗ್ಯದ ಪ್ರಶ್ನೆಗೆ ನಾನು ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?",
    "ml": "നമസ്കാരം, മെഡ്‌ജെമ്മ ശബ്ദ സഹായിയിലേക്ക് സ്വാഗതം. ഇന്ന് നിങ്ങളുടെ ആരോഗ്യ ചോദ്യത്തിൽ എനിക്ക് എങ്ങനെ സഹായിക്കാനാകും?",
    "mr": "नमस्कार, मेडजेम्मा व्हॉइस असिस्टंटमध्ये आपले स्वागत आहे. आज मी तुमच्या आरोग्यविषयक प्रश्नात कशी मदत करू शकतो?",
    "pa": "ਸਤਿ ਸ਼੍ਰੀ ਅਕਾਲ, ਮੈਡਜੇਮਾ ਵੌਇਸ ਸਹਾਇਕ ਵਿੱਚ ਤੁਹਾਡਾ ਸੁਆਗਤ ਹੈ। ਅੱਜ ਮੈਂ ਤੁਹਾਡੇ ਸਿਹਤ ਸੰਬੰਧੀ ਸਵਾਲ ਵਿੱਚ ਕਿਵੇਂ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ?",
}


def test_bhashini_tts():
    print("\n==================================================")
    print(" Testing Local Bhashini / Indic TTS (MMS-TTS / VITS)")
    print("==================================================")
    from transformers import AutoTokenizer, VitsModel

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    results = []

    for lang, prompt in TEST_PROMPTS.items():
        print(f"\n--- Testing TTS for [{lang.upper()}] ---")
        model_path = os.path.join(BHASHINI_MODEL_DIR, "tts", lang)
        model_id_or_path = model_path if (os.path.exists(model_path) and os.listdir(model_path)) else TTS_MODEL_IDS[lang]

        t0 = time.time()
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_id_or_path)
            model = VitsModel.from_pretrained(model_id_or_path).to(device)
            load_time = time.time() - t0

            t_synth_start = time.time()
            inputs = tokenizer(prompt, return_tensors="pt").to(device)
            with torch.no_grad():
                output = model(**inputs).waveform

            audio_data = output.squeeze().cpu().numpy()
            synth_time = time.time() - t_synth_start

            output_file = f"test_response_{lang}.wav"
            sf.write(output_file, audio_data, model.config.sampling_rate)

            duration = len(audio_data) / model.config.sampling_rate
            print(f"[OK] [{lang.upper()}] Model loaded in {load_time:.2f}s | Synthesis in {synth_time:.2f}s | Audio duration: {duration:.2f}s")
            print(f"Saved audio output: {output_file}")
            results.append((lang, True, synth_time, duration))
        except Exception as exc:
            print(f"[FAIL] [{lang.upper()}] TTS Error: {exc}")
            results.append((lang, False, 0.0, 0.0))

    return results


def test_bhashini_asr():
    print("\n==================================================")
    print(" Testing Local Bhashini / Indic ASR (faster-whisper)")
    print("==================================================")
    from faster_whisper import WhisperModel

    asr_dir = os.path.join(BHASHINI_MODEL_DIR, "asr")
    model_name = os.environ.get("BHASHINI_ASR_MODEL", "small")

    t0 = time.time()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"

    try:
        print(f"Loading ASR model '{model_name}' on {device} ({compute_type})...")
        if os.path.exists(asr_dir) and os.listdir(asr_dir):
            model = WhisperModel(asr_dir, device=device, compute_type=compute_type)
        else:
            model = WhisperModel(model_name, device=device, compute_type=compute_type, download_root=asr_dir)
        load_time = time.time() - t0
        print(f"[OK] ASR model loaded successfully in {load_time:.2f}s")

        for lang in list(TEST_PROMPTS.keys()):
            wav_file = f"test_response_{lang}.wav"
            if os.path.exists(wav_file):
                t_trans_start = time.time()
                segments, info = model.transcribe(wav_file, language=lang, beam_size=3)
                transcription = " ".join(seg.text.strip() for seg in segments)
                trans_time = time.time() - t_trans_start
                print(f"\n[ASR: {lang.upper()}] ({trans_time:.2f}s) Transcribed text: {transcription}")

    except Exception as exc:
        print(f"[FAIL] ASR Test Error: {exc}")


def print_memory_stats():
    print("\n==================================================")
    print(" System & GPU Memory Usage Snapshot")
    print("==================================================")
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / (1024 ** 2)
        reserved = torch.cuda.memory_reserved() / (1024 ** 2)
        print(f"GPU VRAM Allocated: {allocated:.2f} MB")
        print(f"GPU VRAM Reserved:  {reserved:.2f} MB")
    else:
        print("Running on CPU mode.")


def main():
    print("=" * 60)
    print(" MedGemma Bhashini / Indic Speech Pipeline Benchmark")
    print(" Target: Jetson Orin Nano (8GB)")
    print(" Languages: EN, HI, TA, TE, BN, GU, KN, ML, MR, PA")
    print("=" * 60)

    test_bhashini_tts()
    test_bhashini_asr()
    print_memory_stats()


if __name__ == "__main__":
    main()
