"""
Offline model downloader script for MedGemma Bhashini Local ASR and TTS models.
Pre-downloads and caches model weights for English, Hindi, Tamil, Telugu, Bengali, Gujarati, Kannada, Malayalam, Marathi, and Punjabi.
"""

import os
import sys
from pathlib import Path
from huggingface_hub import snapshot_download

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

def _get_default_cache_dir() -> str:
    if "BHASHINI_MODEL_DIR" in os.environ:
        return os.environ["BHASHINI_MODEL_DIR"]
    d_drive_cache = r"D:\cache\medgemma\models"
    if os.path.exists(r"D:\Deva"):
        os.makedirs(d_drive_cache, exist_ok=True)
        return d_drive_cache
    return os.path.expanduser("~/.cache/medgemma/models")

DEFAULT_CACHE_DIR = _get_default_cache_dir()

# MMS-TTS Models for Indic languages + English (Lightweight VITS architecture, ~100-150MB per model)
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

# Default ASR Model using faster-whisper / CTranslate2
DEFAULT_ASR_MODEL = os.environ.get("BHASHINI_ASR_MODEL", "small")


def download_tts_models(cache_dir: str):
    """Download MMS-TTS models for all target languages."""
    print("\n--- Downloading Local Bhashini / Indic TTS Models ---")
    from transformers import AutoTokenizer, VitsModel

    for lang, model_id in TTS_MODEL_IDS.items():
        print(f"\n[TTS: {lang.upper()}] Downloading {model_id}...")
        try:
            model_path = os.path.join(cache_dir, "tts", lang)
            os.makedirs(model_path, exist_ok=True)
            
            # Download snapshot to local folder
            snapshot_download(repo_id=model_id, local_dir=model_path)
            
            # Verify loading with transformers
            _tokenizer = AutoTokenizer.from_pretrained(model_path)
            _model = VitsModel.from_pretrained(model_path)
            print(f"[OK] TTS model for '{lang}' successfully downloaded and verified at: {model_path}")
        except Exception as exc:
            print(f"[FAIL] Failed to download TTS model for '{lang}': {exc}")


def download_asr_model(cache_dir: str, model_name: str = DEFAULT_ASR_MODEL):
    """Download and cache faster-whisper ASR model."""
    print(f"\n--- Downloading Local Bhashini / Indic ASR Model ({model_name}) ---")
    from faster_whisper import WhisperModel

    asr_dir = os.path.join(cache_dir, "asr")
    os.makedirs(asr_dir, exist_ok=True)

    try:
        print(f"[ASR] Initializing download for faster-whisper model '{model_name}'...")
        # WhisperModel automatically downloads and caches into download_root if not present
        model = WhisperModel(model_name, device="cpu", compute_type="int8", download_root=asr_dir)
        print(f"[OK] ASR model '{model_name}' successfully downloaded and verified in: {asr_dir}")
    except Exception as exc:
        print(f"[FAIL] Failed to download ASR model '{model_name}': {exc}")


def main():
    print("=" * 60)
    print(" MedGemma Bhashini / Indic Local Model Downloader")
    print(" Target Environment: Jetson Orin Nano (8GB) / Offline Systems")
    print(" Supported Languages: EN, HI, TA, TE, BN, GU, KN, ML, MR, PA")
    print("=" * 60)
    print(f"Cache Location: {DEFAULT_CACHE_DIR}")

    os.makedirs(DEFAULT_CACHE_DIR, exist_ok=True)

    download_tts_models(DEFAULT_CACHE_DIR)
    download_asr_model(DEFAULT_CACHE_DIR)

    print("\n" + "=" * 60)
    print(" Download Complete! Models are ready for offline inference.")
    print("=" * 60)


if __name__ == "__main__":
    main()
