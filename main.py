import json
import os
import sys
import tempfile
import time
import wave
import zipfile
from typing import Optional
from pathlib import Path
from urllib.request import urlretrieve

# Cross-platform keyboard input import for non-blocking stop key during audio playback
try:
    import msvcrt
except ImportError:
    msvcrt = None

try:
    import select
    import termios
    import tty
except ImportError:
    select = None
    termios = None
    tty = None

if "medgemma-env" not in os.path.normcase(sys.executable):
    print("Ollama only works inside the medgemma-env virtual environment.")
    print("Run this instead:")
    print("  .\\medgemma-env\\Scripts\\python.exe main.py")
    raise SystemExit(1)

try:
    import torch
    import ollama
    import sounddevice as sd
    import soundfile as sf
    import numpy as np
    from faster_whisper import WhisperModel
    from transformers import AutoTokenizer, VitsModel
except ImportError as exc:
    print("Missing dependency for the local assistant runtime.")
    print("Please run it from the medgemma-env environment:")
    print("  .\\medgemma-env\\Scripts\\python.exe main.py")
    print(f"Missing module: {exc.name}")
    raise SystemExit(1) from exc

try:
    from langdetect import detect as detect_language
except ImportError:
    def detect_language(text: str) -> str:
        if any("\u0B80" <= ch <= "\u0BFF" for ch in text):
            return "ta"
        if any("\u0900" <= ch <= "\u097F" for ch in text):
            return "hi"
        if any("\u0C00" <= ch <= "\u0C7F" for ch in text):
            return "te"
        return "en"

# ==========================
# CONFIG & PATH RESOLUTION
# ==========================

MODEL_NAME = "medgemma:4b"

# Cache & model directory handling for Jetson Orin Nano / Linux / Windows
BHASHINI_MODEL_DIR = os.environ.get(
    "BHASHINI_MODEL_DIR",
    os.path.expanduser("~/.cache/medgemma/models")
)

# Whisper ASR model path / identifier
DEFAULT_ASR_PATH = os.path.join(BHASHINI_MODEL_DIR, "asr")
WHISPER_MODEL_PATH = os.environ.get(
    "WHISPER_MODEL_PATH",
    DEFAULT_ASR_PATH if os.path.exists(DEFAULT_ASR_PATH) and os.listdir(DEFAULT_ASR_PATH) else "small"
)

# Supported language codes and mapping
SPEECH_LANGUAGE_CODES = {
    "en": "en-US",
    "hi": "hi-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "bn": "bn-IN",
    "gu": "gu-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "mr": "mr-IN",
    "pa": "pa-IN",
}

RESPONSE_LANGUAGE_HINTS = {
    "en": "Please answer in English.",
    "hi": "Please answer in Hindi.",
    "ta": "Please answer in Tamil.",
    "te": "Please answer in Telugu.",
    "bn": "Please answer in Bengali.",
    "gu": "Please answer in Gujarati.",
    "kn": "Please answer in Kannada.",
    "ml": "Please answer in Malayalam.",
    "mr": "Please answer in Marathi.",
    "pa": "Please answer in Punjabi.",
}

TTS_MODEL_MAPPING = {
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

SPEECH_COMMAND_PREFIX = "voice"
OUTPUT_WAV = "response.wav"

SYSTEM_PROMPT = (
    "You are a voice-based health assistant on a home device, speaking to people who "
    "describe symptoms out loud. Your job is to give genuinely useful spoken guidance for "
    "whatever is described — common or serious, vague or detailed.\n\n"

    "STYLE:\n"
    "- Speak naturally and directly. Do not say 'I am not a medical professional' or open "
    "with sympathy phrases like 'I am sorry to hear that.' Get straight to useful content.\n"
    "- Keep sentences short and clear since this is heard, not read. There is no fixed "
    "length — say what's genuinely useful and stop there. A simple question needs a short "
    "answer; a concerning combination of symptoms needs more explanation.\n"
    "- Never mention being an AI or language model. Never state a definitive diagnosis — "
    "use language like 'this is often caused by' or 'this can sometimes mean.'\n\n"

    "CONTENT — cover what's relevant, skip what isn't:\n"
    "1. Likely cause(s) in plain language, matched to what was actually described.\n"
    "2. Practical self-care steps that apply right now — be concrete and specific "
    "(e.g. rest, hydration, typical over-the-counter options like paracetamol/"
    "acetaminophen or ibuprofen for pain and fever, warm fluids for a sore throat, "
    "rest/ice/elevation for a minor injury) rather than vague advice.\n"
    "3. Specific signs that mean the person should seek care — name the actual trigger "
    "(a temperature threshold, duration, or accompanying symptom) instead of a generic "
    "'consult a doctor' line.\n"
    "4. If the symptoms described together are urgent or concerning — for example fever "
    "with stiff neck or confusion, chest pain, breathing difficulty, sudden severe "
    "headache, symptoms in an infant, or a combination that doesn't usually resolve on "
    "its own — say clearly that they should seek care promptly, and briefly explain why "
    "this combination matters more than any one symptom alone.\n"
    "5. If the symptom is mild and self-limiting (common cold, minor headache, mild "
    "fatigue), it is fine to say reassurance is appropriate and no urgent care is "
    "needed — don't manufacture urgency where none exists.\n\n"

    "USING CONVERSATION HISTORY:\n"
    "- Before answering, check whether the person mentioned other symptoms earlier in "
    "this conversation. Treat a new symptom as potentially connected to earlier ones, "
    "not as an isolated fresh question.\n"
    "- If the new symptom plausibly fits with or worsens the earlier picture (e.g. a "
    "headache mentioned after a cold, or fatigue mentioned after a fever), say so "
    "explicitly and give combined advice that addresses both, not two separate answers.\n"
    "- Re-evaluate urgency using the full combination of symptoms mentioned so far, not "
    "just the newest one — a symptom that seemed mild alone can become concerning "
    "combined with what was said earlier.\n"
    "- Only treat a new symptom as unrelated if it clearly doesn't fit the earlier "
    "picture (e.g. a skin rash mentioned after a prior headache).\n\n"

    "CLARIFYING QUESTIONS:\n"
    "- Only ask a follow-up if there truly isn't enough information, even accounting for "
    "conversation history, to say anything useful (e.g. 'I don't feel good').\n"
    "- If enough detail exists between the current message and history, do not ask a "
    "question — give the advice directly.\n\n"

    "SPECIAL CASES:\n"
    "- If the person describes something requiring immediate emergency action (e.g. "
    "severe chest pain, signs of stroke, difficulty breathing, uncontrolled bleeding, "
    "loss of consciousness), lead with telling them to seek emergency care immediately, "
    "before anything else.\n"
    "- Be more cautious with symptoms in infants, young children, elderly people, or "
    "pregnant individuals — lower your threshold for recommending a doctor.\n"
    "- If asked something outside symptom/health guidance (e.g. general chat), respond "
    "naturally and briefly without forcing the structure above."
)
MAX_HISTORY_TURNS = 6   # number of user+assistant exchange pairs to remember (12 messages)

# ==========================
# OLLAMA MEDGEMMA INTERACTION
# ==========================

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


def _extract_context_usage(response) -> tuple[int, int]:
    prompt_eval_count = getattr(response, "prompt_eval_count", None)
    eval_count = getattr(response, "eval_count", None)

    if prompt_eval_count is None or eval_count is None:
        try:
            prompt_eval_count = response.get("prompt_eval_count")
            eval_count = response.get("eval_count")
        except AttributeError:
            prompt_eval_count = None
            eval_count = None

    return int(prompt_eval_count or 0), int(eval_count or 0)


def get_medgemma_response(
    prompt: str,
    image_path: Optional[str] = None,
    response_language: str = "en",
    history: Optional[list] = None,
) -> tuple[str, tuple[int, int]]:
    language_hint = RESPONSE_LANGUAGE_HINTS.get(response_language, RESPONSE_LANGUAGE_HINTS["en"])
    combined_system = SYSTEM_PROMPT if response_language == "en" else f"{SYSTEM_PROMPT}\n\n{language_hint}"

    if image_path:
        image_path = _normalize_image_path(image_path)
        try:
            response = ollama.generate(
                model=MODEL_NAME,
                prompt=prompt,
                images=[image_path],
                system=combined_system,
                keep_alive=-1,
            )
            return response.get("response", "").strip(), _extract_context_usage(response)
        except Exception as exc:
            if image_path.endswith(".jpg") and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except OSError:
                    pass
            raise exc

    messages = [{"role": "system", "content": combined_system}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt})

    response = ollama.chat(
        model=MODEL_NAME,
        messages=messages,
        keep_alive=-1,
    )
    return response["message"]["content"], _extract_context_usage(response)


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


# ==========================
# LOCAL BHASHINI ASR ENGINE
# ==========================

def _is_converted_whisper_model_dir(path: str) -> bool:
    if not os.path.isdir(path):
        return False
    try:
        entries = set(os.listdir(path))
    except OSError:
        return False
    return "model.bin" in entries or {"config.json", "tokenizer.json"}.issubset(entries)


def _find_converted_whisper_model(root: str) -> Optional[str]:
    if not os.path.isdir(root):
        return None

    if _is_converted_whisper_model_dir(root):
        return root

    for dirpath, dirnames, filenames in os.walk(root):
        if "model.bin" in filenames and "config.json" in filenames:
            return dirpath

    return None


class BhashiniLocalASR:
    _instance = None
    _model = None

    @classmethod
    def get_model(cls, model_source: str = WHISPER_MODEL_PATH):
        if cls._model is not None:
            return cls._model

        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        asr_cache_dir = os.path.join(BHASHINI_MODEL_DIR, "asr")

        # Resolve snapshot subfolder inside cache root if present
        resolved_source = model_source
        if os.path.isdir(model_source) and not _is_converted_whisper_model_dir(model_source):
            snapshot_dir = _find_converted_whisper_model(model_source)
            if snapshot_dir:
                resolved_source = snapshot_dir

        print(f"Loading local ASR model from '{resolved_source}' on {device} ({compute_type})...")
        try:
            if os.path.isdir(resolved_source):
                cls._model = WhisperModel(resolved_source, device=device, compute_type=compute_type)
            else:
                cls._model = WhisperModel(resolved_source, device=device, compute_type=compute_type, download_root=asr_cache_dir)
        except Exception as exc:
            print(f"Error loading ASR model ({resolved_source}): {exc}. Falling back to default 'small' model...")
            cls._model = WhisperModel("small", device=device, compute_type=compute_type, download_root=asr_cache_dir)

        return cls._model


def listen_for_speech(language: str = "en", duration: float = 5.0) -> Optional[str]:
    lang_key = language.lower()
    whisper_lang = {"en": "en", "hi": "hi", "ta": "ta", "te": "te"}.get(lang_key, "en")

    try:
        model = BhashiniLocalASR.get_model()
    except Exception as exc:
        print(f"Failed to initialize Bhashini ASR engine: {exc}")
        return None

    print(f"\n[Microphone Active] Listening for [{whisper_lang.upper()}] speech...")
    print(f"Speak into microphone now ({duration}s recording)...")

    audio_bytes = None
    sample_rate = 16000

    # Strategy 1: Try PyAudio / SpeechRecognition capture
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.Microphone(sample_rate=16000) as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = r.record(source, duration=duration)
            raw_data = audio_data.get_raw_data(convert_rate=16000, convert_width=2)
            audio_arr = np.frombuffer(raw_data, dtype=np.int16)
            peak_amp = int(np.max(np.abs(audio_arr))) if len(audio_arr) > 0 else 0
            if peak_amp > 10:
                audio_bytes = raw_data
                print(f"Audio captured via PyAudio (Peak amplitude: {peak_amp} / 32767)")
    except Exception:
        audio_bytes = None

    # Strategy 2: Fallback to sounddevice capture if PyAudio capture was quiet or failed
    if audio_bytes is None:
        try:
            input_dev = sd.default.device[0] if isinstance(sd.default.device, (list, tuple)) else None
            dev_info = sd.query_devices(input_dev, kind="input") if input_dev is not None else sd.query_devices(kind="input")
            native_sr = int(dev_info.get("default_samplerate", 16000))
        except Exception:
            native_sr = 16000

        try:
            recording = sd.rec(int(duration * native_sr), samplerate=native_sr, channels=1, dtype="float32")
            sd.wait()

            audio = recording.squeeze()
            max_amp = float(np.max(np.abs(audio)))
            print(f"Audio captured via sounddevice (Peak amplitude: {max_amp:.5f})")

            if max_amp <= 0.0001:
                print("\n[Notice] Microphone signal level is clamped to 0 by system audio driver.")
                print(" -> On Lenovo laptops: Open 'Lenovo Vantage' app -> Device -> Audio -> Turn OFF 'Microphone Privacy / Mute'.")
                print(" -> Check hardware key: Press Fn + F4 (or Mic Mute key) to unmute physical microphone.")
                print(" -> Alternative: You can test speech recognition using audio files: 'voice:test_response_en.wav' or 'voice:ta|test_response_ta.wav'\n")
                return None

            # Resample float32 audio to 16000 Hz if necessary
            if native_sr != sample_rate:
                try:
                    from scipy.signal import resample
                    num_samples = int(len(audio) * sample_rate / native_sr)
                    audio = resample(audio, num_samples)
                except Exception:
                    num_samples = int(len(audio) * sample_rate / native_sr)
                    audio = np.interp(
                        np.linspace(0, len(audio), num_samples, endpoint=False),
                        np.arange(len(audio)),
                        audio
                    )

            audio = audio / max_amp  # Boost microphone gain to 1.0 peak
            audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()
        except Exception as exc:
            print(f"Microphone recording error: {exc}")
            return None

    if not audio_bytes:
        return None

    try:
        temp_path = os.path.join(tempfile.gettempdir(), "medgemma_asr_input.wav")
        with wave.open(temp_path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(audio_bytes)

        print("Processing speech with local Bhashini ASR model...")
        segments, _info = model.transcribe(temp_path, language=whisper_lang, beam_size=5, vad_filter=False)
        text = " ".join(seg.text.strip() for seg in segments if seg.text and seg.text.strip())

        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

        return text.strip() if text else None
    except Exception as exc:
        print(f"ASR transcription error: {exc}")
        return None


# ==========================
# LOCAL BHASHINI TTS ENGINE (MMS-TTS / VITS)
# ==========================

def _clean_text_for_speech(text: str) -> str:
    # Clean markdown formatting like asterisks, backticks, bold markers before TTS synthesis
    cleaned = text.replace("*", "").replace("`", "").replace("#", "").strip()
    return cleaned


class BhashiniLocalTTS:
    _loaded_models = {}
    _loaded_tokenizers = {}

    @classmethod
    def get_tts_engine(cls, language: str = "en"):
        lang_key = language.lower() if language.lower() in TTS_MODEL_MAPPING else "en"
        
        if lang_key in cls._loaded_models:
            return cls._loaded_tokenizers[lang_key], cls._loaded_models[lang_key]

        local_path = os.path.join(BHASHINI_MODEL_DIR, "tts", lang_key)
        model_id_or_path = local_path if (os.path.exists(local_path) and os.listdir(local_path)) else TTS_MODEL_MAPPING[lang_key]
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading local Bhashini TTS engine for [{lang_key.upper()}] from '{model_id_or_path}' on {device}...")

        try:
            tokenizer = AutoTokenizer.from_pretrained(model_id_or_path)
            model = VitsModel.from_pretrained(model_id_or_path).to(device)
            cls._loaded_tokenizers[lang_key] = tokenizer
            cls._loaded_models[lang_key] = model
            return tokenizer, model
        except Exception as exc:
            print(f"Failed to load local TTS model for [{lang_key}]: {exc}")
            raise exc

    @classmethod
    def synthesize(cls, text: str, language: str = "en", output_path: str = OUTPUT_WAV):
        cleaned_text = _clean_text_for_speech(text)
        if not cleaned_text:
            return

        tokenizer, model = cls.get_tts_engine(language)
        device = "cuda" if torch.cuda.is_available() else "cpu"

        # Truncate text into sentence chunks to prevent token limits on long outputs
        sentences = [s.strip() for s in cleaned_text.replace("\n", " ").split(".") if s.strip()]
        if not sentences:
            sentences = [cleaned_text]

        audio_parts = []
        sample_rate = model.config.sampling_rate

        for sentence in sentences[:10]: # Limit to first 10 sentences for rapid speech synthesis
            inputs = tokenizer(sentence, return_tensors="pt").to(device)
            if "input_ids" in inputs:
                if inputs["input_ids"].shape[1] == 0:
                    continue
                inputs["input_ids"] = inputs["input_ids"].long()
            if "attention_mask" in inputs:
                inputs["attention_mask"] = inputs["attention_mask"].long()
            try:
                with torch.no_grad():
                    output = model(**inputs).waveform
                audio_data = output.squeeze().cpu().numpy()
                audio_parts.append(audio_data)
            except RuntimeError as exc:
                print(f"Skipping sentence synthesis due to model error: {exc}")
                continue

        if audio_parts:
            combined_audio = np.concatenate(audio_parts)
            sf.write(output_path, combined_audio, sample_rate)


def speak_with_indic_parler(text: str, language: str = "en"):
    """Optional high-quality Indic Parler-TTS fallback (Requires >4GB VRAM)."""
    from parler_tts import ParlerTTSForConditionalGeneration
    
    cleaned_text = _clean_text_for_speech(text)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_id = "ai4bharat/indic-parler-tts"
    
    model = ParlerTTSForConditionalGeneration.from_pretrained(model_id).to(device)
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    description_tokenizer = AutoTokenizer.from_pretrained(model.config.text_encoder._name_or_path)

    desc = "A clear female speaker delivers her words at a moderate pace with natural intonation."
    description_ids = description_tokenizer(desc, return_tensors="pt").input_ids.to(device)
    prompt_ids = tokenizer(cleaned_text, return_tensors="pt").input_ids.to(device)

    with torch.no_grad():
        generation = model.generate(input_ids=description_ids, prompt_input_ids=prompt_ids)

    audio_arr = generation.to(torch.float32).cpu().numpy().squeeze()
    sf.write(OUTPUT_WAV, audio_arr, model.config.sampling_rate)


def speak(text: str, language: str = "en"):
    if os.environ.get("USE_PARLER_TTS", "0") == "1":
        speak_with_indic_parler(text, language)
    else:
        BhashiniLocalTTS.synthesize(text, language, OUTPUT_WAV)


# ==========================
# CROSS-PLATFORM AUDIO PLAYBACK & KEYBOARD STOP
# ==========================

def _check_stop_key(stop_event) -> bool:
    """Non-blocking keyboard check supporting both Windows (msvcrt) and Linux/Jetson (select/sys.stdin)."""
    # 1. Windows non-blocking key check
    if msvcrt is not None:
        if msvcrt.kbhit():
            key = msvcrt.getwch().lower()
            if key in {"s", "q"}:
                stop_event.set()
                print("\n[Playback Stopped by User]")
                return True

    # 2. Linux / Jetson Orin Nano non-blocking key check
    elif select is not None and sys.stdin.isatty():
        try:
            rlist, _, _ = select.select([sys.stdin], [], [], 0)
            if rlist:
                key = sys.stdin.read(1).lower()
                if key in {"s", "q"}:
                    stop_event.set()
                    print("\n[Playback Stopped by User]")
                    return True
        except Exception:
            pass

    return False


class StopEvent:
    def __init__(self):
        self._stopped = False

    def is_set(self):
        return self._stopped

    def set(self):
        self._stopped = True


def play_audio(path, stop_event=None):
    if stop_event is None:
        stop_event = StopEvent()

    if not os.path.exists(path):
        return

    data, samplerate = sf.read(path)

    if data.dtype == "float64":
        data = data.astype("float32")

    if data.ndim == 1:
        data = data.reshape(-1, 1)

    channels = data.shape[1] if data.ndim > 1 else 1

    output_device = None
    default_device = sd.default.device
    if isinstance(default_device, (tuple, list)) and len(default_device) == 2:
        output_device = default_device[1]
    elif isinstance(default_device, int):
        output_device = default_device

    with sd.OutputStream(samplerate=samplerate, channels=channels, device=output_device) as stream:
        frames_per_chunk = 2048
        total_frames = data.shape[0]
        offset = 0

        while offset < total_frames and not stop_event.is_set():
            end = min(offset + frames_per_chunk, total_frames)
            stream.write(data[offset:end])
            offset = end

            if _check_stop_key(stop_event):
                stream.stop()
                break

            time.sleep(0.01)

        if stop_event.is_set() and stream.active:
            stream.stop()


# ==========================
# MAIN APPLICATION LOOP
# ==========================

def detect_input_language(text: str) -> str:
    try:
        detected = detect_language(text)
    except Exception:
        detected = "en"

    if detected in SPEECH_LANGUAGE_CODES:
        return detected

    if any("\u0B80" <= ch <= "\u0BFF" for ch in text):
        return "ta"
    if any("\u0C00" <= ch <= "\u0C7F" for ch in text):
        return "te"
    if any("\u0980" <= ch <= "\u09FF" for ch in text):
        return "bn"
    if any("\u0A80" <= ch <= "\u0AFF" for ch in text):
        return "gu"
    if any("\u0C80" <= ch <= "\u0CFF" for ch in text):
        return "kn"
    if any("\u0D00" <= ch <= "\u0D7F" for ch in text):
        return "ml"
    if any("\u0A00" <= ch <= "\u0A7F" for ch in text):
        return "pa"
    if any("\u0900" <= ch <= "\u097F" for ch in text):
        return "hi"
    return "en"


def main():

    print("=" * 65)
    print("   MedGemma Voice Assistant (Bhashini Local ASR/TTS)")
    print("   Optimized for Jetson Orin Nano (8GB) & Offline Systems")
    print("=" * 65)
    print("Supported Languages:")
    print(" - English (en), Hindi (hi), Tamil (ta), Telugu (te), Bengali (bn)")
    print(" - Gujarati (gu), Kannada (kn), Malayalam (ml), Marathi (mr), Punjabi (pa)")
    print("\nType 'voice' or 'voice:hi' / 'voice:ta' / 'voice:kn' / 'voice:ml' / 'voice:bn' to speak.")
    print("Type 'quit' to exit. Type 'new' or 'reset' to clear conversation memory.\n")

    conversation_history: list = []

    while True:
        user_input = input("You : ").strip()
        speech_input_lang = None

        if user_input.lower() in ["quit", "exit"]:
            print("Exiting MedGemma Assistant. Goodbye!")
            break

        if user_input.lower() in ["new", "reset", "clear"]:
            conversation_history.clear()
            print("Conversation memory cleared. Starting fresh.\n")
            continue

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
            reply, context_usage = get_medgemma_response(
                prompt, image_path, response_language=lang, history=conversation_history
            )
        except Exception as exc:
            print(f"MedGemma LLM Error: {exc}")
            continue

        print("MedGemma:")
        print(reply)

        if image_path is None:
            conversation_history.append({"role": "user", "content": prompt})
            conversation_history.append({"role": "assistant", "content": reply})
            max_messages = MAX_HISTORY_TURNS * 2
            if len(conversation_history) > max_messages:
                conversation_history[:] = conversation_history[-max_messages:]

        input_context, output_context = context_usage
        print(f"\nInput context tokens: {input_context}")
        print(f"Output context tokens: {output_context}")

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