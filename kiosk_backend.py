"""
FastAPI Local Backend Server for MedGemma Dual-Mode UI Kiosk.
Provides REST endpoints for status check, vitals collection, speech recognition,
Ollama MedGemma inference (with optional image uploads), and local TTS synthesis.
"""

import os
import sys
import tempfile
import time
import base64
import threading
from typing import Optional

try:
    from fastapi import FastAPI, UploadFile, File, Form
    from fastapi.responses import FileResponse, JSONResponse
    import uvicorn
    import ollama
except ImportError as exc:
    print(f"Missing dependency in kiosk_backend: {exc}")
    raise exc

# Include local imports
try:
    from bhashini_speech import (
        BhashiniLocalASR,
        BhashiniLocalTTS,
        detect_input_language,
        RESPONSE_LANGUAGE_HINTS,
    )
    from hardware import OximeterReader, ThermalReader, ECGReader, CameraModule
except ImportError as exc:
    print(f"Error importing modules: {exc}")
    raise exc

app = FastAPI(title="MedGemma Kiosk Backend")

# Initialize models and drivers
MODEL_NAME = "medgemma:4b"
OUTPUT_WAV = os.path.join(tempfile.gettempdir(), "backend_response.wav")

asr = BhashiniLocalASR.get_model()
tts = BhashiniLocalTTS.get_model()

oximeter = OximeterReader(use_hardware=True, i2c_bus=1)
thermal = ThermalReader(use_hardware=True, i2c_address=0x5A, i2c_bus=1)
ecg = ECGReader(buffer_size=500, sample_rate=100, i2c_bus=1)

# App State / Thread-safe values
vitals_lock = threading.Lock()
current_vitals = {"spo2": 98.0, "heart_rate": 72, "temp_c": 36.6, "temp_f": 97.9, "status": "Normal"}

def sensor_loop():
    global current_vitals
    while True:
        try:
            ecg.update()
            # Periodically poll oximeter & thermal at 1 Hz
            if int(time.time() * 100) % 100 == 0:
                v = oximeter.read_vitals()
                t = thermal.read_temperature()
                with vitals_lock:
                    current_vitals = {
                        "spo2": v["spo2"],
                        "heart_rate": v["heart_rate"],
                        "temp_c": t["temp_c"],
                        "temp_f": t["temp_f"],
                        "status": v["status"],
                    }
            time.sleep(0.01)
        except Exception as exc:
            print(f"[Backend Sensor Error] {exc}")
            time.sleep(1.0)

# Start sensor loop thread
threading.Thread(target=sensor_loop, daemon=True).start()


@app.get("/api/status")
def get_status():
    return {"status": "ok", "backend": "MedGemma Kiosk REST API"}


@app.get("/api/vitals")
def get_vitals():
    with vitals_lock:
        return current_vitals


@app.get("/api/audio")
def get_audio():
    if os.path.exists(OUTPUT_WAV):
        return FileResponse(OUTPUT_WAV, media_type="audio/wav")
    return JSONResponse(status_code=404, content={"error": "Audio file not found"})


@app.post("/api/assistant/interact")
async def interact(
    language: str = Form("en"),
    text_prompt: Optional[str] = Form(None),
    audio: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None)
):
    try:
        user_query = ""
        
        # 1. Transcribe audio if provided
        if audio is not None:
            temp_audio_path = os.path.join(tempfile.gettempdir(), f"uploaded_{int(time.time())}.wav")
            with open(temp_audio_path, "wb") as f:
                f.write(await audio.read())
            
            # Use ASR transcription
            segments, _info = asr.transcribe(temp_audio_path, language=language, beam_size=1, vad_filter=False)
            user_query = " ".join(seg.text.strip() for seg in segments if seg.text and seg.text.strip())
            try:
                os.remove(temp_audio_path)
            except OSError:
                pass
        elif text_prompt:
            user_query = text_prompt.strip()

        if not user_query:
            return {"success": False, "error": "No speech or text query detected"}

        # 2. Gather vitals context
        with vitals_lock:
            v = current_vitals
        vitals_context = (
            f"[Patient Real-Time Vitals: SpO2={v['spo2']}%, Heart Rate={v['heart_rate']} BPM, "
            f"Body Temp={v['temp_c']}°C ({v['temp_f']}°F), Vitals Status={v['status']}]"
        )
        full_prompt = f"{vitals_context}\nPatient Query: {user_query}"
        
        # 3. Detect input language and generate Ollama prompt hint
        detected_lang = detect_input_language(user_query) if language == "en" else language
        lang_hint = RESPONSE_LANGUAGE_HINTS.get(detected_lang, RESPONSE_LANGUAGE_HINTS["en"])
        
        # 4. Handle Vision vs Chat
        image_path = None
        if image is not None:
            image_path = os.path.join(tempfile.gettempdir(), f"uploaded_snap_{int(time.time())}.jpg")
            with open(image_path, "wb") as f:
                f.write(await image.read())

        if image_path and os.path.exists(image_path):
            prompt_with_hint = f"{full_prompt}\n\n{lang_hint}"
            response = ollama.generate(
                model=MODEL_NAME,
                prompt=prompt_with_hint,
                images=[image_path],
                options={"num_ctx": 2048, "num_predict": 180, "temperature": 0.3}
            )
            reply = response.get("response", "").strip()
            try:
                os.remove(image_path)
            except OSError:
                pass
        else:
            messages = [
                {"role": "system", "content": f"You are MedGemma medical assistant. {lang_hint}"},
                {"role": "user", "content": full_prompt},
            ]
            response = ollama.chat(
                model=MODEL_NAME,
                messages=messages,
                options={"num_ctx": 2048, "num_predict": 180, "temperature": 0.3}
            )
            reply = response["message"]["content"].strip()

        # 5. Synthesize TTS response
        tts.synthesize(reply, target_language=detected_lang, output_path=OUTPUT_WAV)

        return {
            "success": True,
            "detected_text": user_query,
            "response_local": reply,
            "audio_url": "/api/audio"
        }
    except Exception as exc:
        print(f"[Backend Error] {exc}")
        return {"success": False, "error": str(exc)}


if __name__ == "__main__":
    # Run FastAPI local server on port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)
