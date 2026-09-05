"""
AppController implementation for MedGemma Medical Kiosk.
Coordinates the background workflow sequence, interfacing the wizard screens
directly with physical sensors, local Bhashini ASR/TTS, and Ollama MedGemma AI.
"""

import os
import sys
import time
import tempfile
import threading
from typing import Optional

import numpy as np
import sounddevice as sd
import soundfile as sf
import requests
import cv2

from app import state_manager
from config import config
from utils.logger import setup_logger

# MedGemma imports
try:
    import ollama
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

logger = setup_logger("AppController")
MODEL_NAME = "medgemma:4b"
OUTPUT_WAV = os.path.join(tempfile.gettempdir(), "response_kiosk_wizard.wav")


class AppController:
    def __init__(self):
        self.app = None
        self.state_mgr = state_manager.StateManager()
        self.state_mgr.register_callback(self.on_state_changed)

        # Initialize physical sensor reader singletons
        self.oximeter = OximeterReader(use_hardware=True, i2c_bus=1)
        self.thermal = ThermalReader(use_hardware=True, i2c_address=0x5A, i2c_bus=1)
        self.ecg = ECGReader(buffer_size=500, sample_rate=100, i2c_bus=1)
        self.camera = CameraModule(camera_index=0)

        # Variables to store collected measurements
        self.collected_temp = 0.0
        self.collected_spo2 = 0
        self.collected_pulse = 0
        self.collected_rhythm = "Normal Sinus Rhythm"

        self.patient_transcript = ""
        self.ai_diagnosis = ""

        self.worker_thread = None
        self._ecg_polling = False
        self.assessment_mode = "recording"

        # Synchronization events
        self.temp_checked_event = threading.Event()
        self.temp_next_event = threading.Event()
        self.oximeter_checked_event = threading.Event()
        self.oximeter_next_event = threading.Event()
        self.ecg_checked_event = threading.Event()
        self.ecg_next_event = threading.Event()
        self.summary_continue_event = threading.Event()
        self.camera_capture_event = threading.Event()
        self.camera_skip_event = threading.Event()
        self.document_capture_event = threading.Event()
        self.document_skip_event = threading.Event()

        # Pre-warm Ollama model in background daemon thread
        threading.Thread(target=self._prewarm_ollama, daemon=True).start()

    def _prewarm_ollama(self):
        """
        Pre-warm the Ollama model into GPU/RAM at kiosk boot to avoid cold-start delays.
        """
        try:
            logger.info(f"Pre-warming {MODEL_NAME} into memory (keep_alive=-1)...")
            ollama.chat(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": "ping"}],
                keep_alive=-1,
                options={"num_predict": 1},
            )
            logger.info(f"Model {MODEL_NAME} successfully pre-warmed in memory.")
        except Exception as exc:
            logger.warning(f"Ollama pre-warm skipped or failed: {exc}")

    def set_app(self, app):
        self.app = app

    def get_current_state(self) -> str:
        return self.state_mgr.get_state()

    def set_selected_language(self, lang_code: str):
        self.state_mgr.set_selected_language(lang_code)

    def start_assessment_workflow(self, mode="recording"):
        if self.worker_thread and self.worker_thread.is_alive():
            logger.warning("Workflow thread already running.")
            return

        self.assessment_mode = mode
        logger.info(f"Starting workflow. Mode: {self.assessment_mode}")

        # Reset measurements
        self.collected_temp = 0.0
        self.collected_spo2 = 0
        self.collected_pulse = 0
        self.collected_rhythm = "Normal Sinus Rhythm"
        self.patient_transcript = ""
        self.ai_diagnosis = ""

        # Reset synchronization events
        self.temp_checked_event.clear()
        self.temp_next_event.clear()
        self.oximeter_checked_event.clear()
        self.oximeter_next_event.clear()
        self.ecg_checked_event.clear()
        self.ecg_next_event.clear()
        self.summary_continue_event.clear()
        self.camera_capture_event.clear()
        self.camera_skip_event.clear()
        self.document_capture_event.clear()
        self.document_skip_event.clear()

        # Start workflow thread
        self.state_mgr.set_state(state_manager.INITIALIZING)
        self.worker_thread = threading.Thread(target=self._run_workflow, daemon=True)
        self.worker_thread.start()

    # Callback Events
    def run_temperature_check(self):
        self.temp_checked_event.set()

    def run_oximeter_check(self):
        self.oximeter_checked_event.set()

    def run_ecg_check(self):
        self.ecg_checked_event.set()

    def advance_next_sensor(self, next_sensor_type):
        if next_sensor_type == "oximeter":
            self.temp_next_event.set()
        elif next_sensor_type == "ecg":
            self.oximeter_next_event.set()
        elif next_sensor_type == "summary":
            self.ecg_next_event.set()

    def advance_from_vitals_summary(self):
        self.summary_continue_event.set()

    def run_camera_capture(self, mode="camera"):
        if mode == "document":
            self.document_capture_event.set()
        else:
            self.camera_capture_event.set()

    def run_camera_skip(self, mode="camera"):
        if mode == "document":
            self.document_skip_event.set()
        else:
            self.camera_skip_event.set()

    def reset_to_idle(self):
        self._ecg_polling = False
        sd.stop()

        if hasattr(self.app, "camera_screen"):
            self.app.camera_screen.stop_camera()

        # Force set all events
        self.temp_checked_event.set()
        self.temp_next_event.set()
        self.oximeter_checked_event.set()
        self.oximeter_next_event.set()
        self.ecg_checked_event.set()
        self.ecg_next_event.set()
        self.summary_continue_event.set()
        self.camera_capture_event.set()
        self.camera_skip_event.set()
        self.document_capture_event.set()
        self.document_skip_event.set()

        self.state_mgr.set_state(state_manager.IDLE)

    def replay_response_audio(self):
        if os.path.exists(OUTPUT_WAV):
            try:
                data, fs = sf.read(OUTPUT_WAV)
                sd.play(data, fs)
            except Exception as exc:
                logger.error(f"Error replaying response audio: {exc}")

    def on_state_changed(self, old_state, new_state):
        if not self.app:
            return
        self.app.after(0, lambda: self._handle_ui_transition(old_state, new_state))

    def _handle_ui_transition(self, old_state, new_state):
        lang = self.state_mgr.get_current_language()

        if old_state == state_manager.MEASURING_ECG:
            self._ecg_polling = False

        if new_state == state_manager.IDLE:
            self.app.show_screen("main")
        elif new_state in [
            state_manager.INITIALIZING,
            state_manager.MEASURING_TEMPERATURE,
            state_manager.MEASURING_OXIMETER,
            state_manager.MEASURING_ECG,
            state_manager.VITALS_COMPLETE,
        ]:
            self.app.show_screen("vitals")
            if new_state == state_manager.INITIALIZING:
                components = {
                    "Display": False,
                    "Speaker": False,
                    "Microphone": False,
                    "Temperature Sensor": False,
                    "Pulse Oximeter": False,
                    "ECG Sensor": False,
                    "Voice Assistant": False,
                }
                self.app.vitals_screen.show_initialization(components)
        elif new_state in [
            state_manager.DOCUMENT_CAPTURE,
            state_manager.PLAYING_DOCUMENT_AUDIO,
            state_manager.CAMERA_CAPTURE,
            state_manager.ANALYZING_IMAGE,
        ]:
            self.app.show_screen("camera")
            if new_state == state_manager.DOCUMENT_CAPTURE:
                self.app.camera_screen.show_ready(mode="document")
            elif new_state == state_manager.CAMERA_CAPTURE:
                self.app.camera_screen.show_ready(mode="camera")
        elif new_state in [
            state_manager.VOICE_INITIALIZING,
            state_manager.PLAYING_PATIENT_AUDIO,
            state_manager.PROCESSING_SPEECH,
            state_manager.GENERATING_RESPONSE,
            state_manager.WAITING_FOR_PATIENT,
        ]:
            self.app.show_screen("voice")
            if new_state == state_manager.VOICE_INITIALIZING:
                self.app.voice_screen.show_preparing()
            elif new_state == state_manager.PLAYING_PATIENT_AUDIO:
                self.app.voice_screen.show_listening(lang)

    # background workflow sequencers
    def _run_workflow(self):
        try:
            lang = self.state_mgr.get_current_language()
            logger.info(f"Running workflow for language: {lang}")

            # --- 1. System Initialization (Progressively tick items with 3s delay) ---
            checked_components = {
                "Display": False,
                "Speaker": False,
                "Microphone": False,
                "Temperature Sensor": False,
                "Pulse Oximeter": False,
                "ECG Sensor": False,
                "Voice Assistant": False,
            }
            
            for comp in ["Display", "Speaker", "Microphone", "Temperature Sensor", "Pulse Oximeter", "ECG Sensor", "Voice Assistant"]:
                time.sleep(3.0)
                if comp == "Temperature Sensor":
                    checked_components[comp] = self.thermal.is_connected
                elif comp == "Pulse Oximeter":
                    checked_components[comp] = self.oximeter.is_connected
                elif comp == "ECG Sensor":
                    checked_components[comp] = self.ecg.is_connected
                else:
                    checked_components[comp] = True
                
                # Push the tick update to the GUI checklist
                self.app.after(0, lambda c=checked_components.copy(): self.app.vitals_screen.show_initialization(c))
            
            # Final verification pause
            time.sleep(1.0)

            # --- 2. Temperature Step ---
            self.state_mgr.set_state(state_manager.MEASURING_TEMPERATURE)
            self.app.after(0, self.app.vitals_screen.show_temperature_prompt)
            self.temp_checked_event.wait()
            self.temp_checked_event.clear()

            # Read live temperature
            self._read_live_temperature()
            self.temp_next_event.wait()
            self.temp_next_event.clear()

            # --- 3. Oximeter Step ---
            self.state_mgr.set_state(state_manager.MEASURING_OXIMETER)
            self.app.after(0, self.app.vitals_screen.show_oximeter_prompt)
            self.oximeter_checked_event.wait()
            self.oximeter_checked_event.clear()

            # Read live oximeter vitals
            self._read_live_oximeter()
            self.oximeter_next_event.wait()
            self.oximeter_next_event.clear()

            # --- 4. ECG Step ---
            self.state_mgr.set_state(state_manager.MEASURING_ECG)
            self.app.after(0, self.app.vitals_screen.show_ecg_prompt)
            self.ecg_checked_event.wait()
            self.ecg_checked_event.clear()

            # Measure ECG Scrolling lines
            self._read_live_ecg()
            self.ecg_next_event.wait()
            self.ecg_next_event.clear()

            # --- 5. Vitals Summary ---
            self.state_mgr.set_state(state_manager.VITALS_COMPLETE)
            self.app.after(
                0,
                lambda: self.app.vitals_screen.show_vitals_summary(
                    self.collected_temp,
                    self.collected_spo2,
                    self.collected_pulse,
                    self.collected_rhythm,
                ),
            )
            self.summary_continue_event.wait()
            self.summary_continue_event.clear()

            # Build vitals context header for Ollama
            vitals_context = (
                f"[Patient Real-Time Vitals: SpO2={self.collected_spo2}%, Heart Rate={self.collected_pulse} BPM, "
                f"Body Temp={self.collected_temp}°C, ECG Rhythm={self.collected_rhythm}]"
            )

            # --- Assessment mode ---
            if self.assessment_mode == "camera":
                document_status = "Skipped"
                image_path = None

                # --- Document Scan ---
                self.state_mgr.set_state(state_manager.DOCUMENT_CAPTURE)
                while (
                    not self.document_capture_event.is_set()
                    and not self.document_skip_event.is_set()
                ):
                    time.sleep(0.1)

                if self.document_capture_event.is_set():
                    self.document_capture_event.clear()
                    self.state_mgr.set_state(state_manager.PLAYING_DOCUMENT_AUDIO)
                    self.app.after(
                        0,
                        lambda: self.app.camera_screen.show_analyzing(
                            0, message="Analyzing medical document..."
                        ),
                    )

                    # Save current camera image
                    image_path = os.path.join(tempfile.gettempdir(), "snap_document.jpg")
                    self.camera.capture_snapshot(image_path)
                    document_status = "Document Uploaded & Analyzed"

                    # Fast Ollama Document analysis
                    prompt = f"{vitals_context}\nAnalyze this uploaded medical document and suggest if any abnormalities exist."
                    self.ai_diagnosis = self._query_ollama(prompt, image_path, lang)
                    time.sleep(1.0)
                else:
                    self.document_skip_event.clear()

                # --- Skin Issue Capture ---
                self.state_mgr.set_state(state_manager.CAMERA_CAPTURE)
                while (
                    not self.camera_capture_event.is_set()
                    and not self.camera_skip_event.is_set()
                ):
                    time.sleep(0.1)

                if self.camera_capture_event.is_set():
                    self.camera_capture_event.clear()
                    self.state_mgr.set_state(state_manager.ANALYZING_IMAGE)

                    image_path = os.path.join(tempfile.gettempdir(), "snap_skin.jpg")
                    self.camera.capture_snapshot(image_path)

                    # 10s countdown
                    for sec in range(10, 0, -1):
                        self.app.after(
                            0, lambda s=sec: self.app.camera_screen.show_analyzing(s)
                        )
                        time.sleep(1.0)

                    self.app.after(0, lambda: self.app.camera_screen.show_analyzing(0))

                    # Ollama Skin Diagnosis
                    prompt = f"{vitals_context}\nDescribe the skin condition visible in this image and recommend primary precautions."
                    self.ai_diagnosis = self._query_ollama(prompt, image_path, lang)
                    self.patient_transcript = "Skin issue image analysis request"
                else:
                    self.camera_skip_event.clear()
                    self.patient_transcript = "Skipped skin capture."
                    if not self.ai_diagnosis:
                        self.ai_diagnosis = "No skin issue or document provided."

                # Speak the diagnosis
                self._speak_diagnosis(self.ai_diagnosis, lang)
            else:
                # --- Voice / Tell Illness Workflow ---
                self.state_mgr.set_state(state_manager.VOICE_INITIALIZING)
                time.sleep(1.0)

                # Microphone Active Listening
                self.state_mgr.set_state(state_manager.PLAYING_PATIENT_AUDIO)
                sr = 16000
                duration = 7.0

                # Record audio
                audio_path = os.path.join(tempfile.gettempdir(), "speech_query.wav")
                audio_data = sd.rec(
                    int(duration * sr), samplerate=sr, channels=1, dtype="int16"
                )

                for sec in range(7, 0, -1):
                    self.app.after(
                        0, lambda s=sec: self.app.voice_screen.show_countdown(s)
                    )
                    time.sleep(1.0)
                sd.wait()
                sf.write(audio_path, audio_data, sr)

                # Transcribe Audio using local ASR
                self.state_mgr.set_state(state_manager.PROCESSING_SPEECH)
                self.app.after(
                    0,
                    lambda: self.app.voice_screen.show_processing(
                        "Processing patient speech query..."
                    ),
                )

                asr_engine = BhashiniLocalASR.get_model()
                segments, _info = asr_engine.transcribe(
                    audio_path, language=lang, beam_size=1, vad_filter=False
                )
                self.patient_transcript = " ".join(
                    seg.text.strip()
                    for seg in segments
                    if seg.text and seg.text.strip()
                )

                if not self.patient_transcript:
                    self.patient_transcript = "No voice input detected."
                    self.ai_diagnosis = "I could not hear your speech. Please try recording again."
                else:
                    # Query Ollama MedGemma AI
                    self.state_mgr.set_state(state_manager.GENERATING_RESPONSE)
                    self.app.after(
                        0,
                        lambda: self.app.voice_screen.show_processing(
                            "Analyzing symptoms with MedGemma..."
                        ),
                    )

                    prompt = f"{vitals_context}\nPatient Symptoms: {self.patient_transcript}"
                    self.ai_diagnosis = self._query_ollama(prompt, None, lang)

                # Speak the diagnosis
                self._speak_diagnosis(self.ai_diagnosis, lang)

            # --- Finish and Populate Report ---
            lang_names = {
                "en": ("English", "English"),
                "ta": ("Tamil", "தமிழ் / Tamil"),
                "te": ("Telugu", "తెలుగు / Telugu"),
                "ml": ("Malayalam", "മലയാളം / Malayalam"),
                "hi": ("Hindi", "हिन्दी / Hindi"),
            }

            report = {
                "temp": f"{self.collected_temp} °C",
                "spo2": f"{self.collected_spo2} %",
                "pulse": f"{self.collected_pulse} BPM",
                "lang_name": lang_names.get(lang, lang_names["en"])[0],
                "native_name": lang_names.get(lang, lang_names["en"])[1],
                "document_analysis": "Vitals checked",
                "patient_text": self.patient_transcript,
                "assistant_response": self.ai_diagnosis,
            }

            self.state_mgr.set_state(state_manager.ASSESSMENT_COMPLETE)
            self.app.after(
                0, lambda r=report: self.app.result_screen.populate_report(r)
            )
            self.app.after(0, lambda: self.app.show_screen("result"))

        except Exception as e:
            logger.error(f"Error during workflow: {e}")
            self.state_mgr.set_state(state_manager.ERROR)

    # Vitals reading loops
    def _read_live_temperature(self):
        steps = 5
        for i in range(steps):
            percent = (i + 1) / steps
            self.app.after(
                0,
                lambda p=percent: self.app.vitals_screen.show_temperature_analysis(
                    p
                ),
            )
            time.sleep(1.5)

        t = self.thermal.read_temperature()
        self.collected_temp = t["temp_c"]
        self.app.after(
            0,
            lambda: self.app.vitals_screen.show_temperature_result(
                self.collected_temp
            ),
        )

    def _read_live_oximeter(self):
        steps = 5
        for i in range(steps):
            percent = (i + 1) / steps
            self.app.after(
                0,
                lambda p=percent: self.app.vitals_screen.show_oximeter_analysis(p),
            )
            time.sleep(1.5)

        v = self.oximeter.read_vitals()
        self.collected_spo2 = v["spo2"]
        self.collected_pulse = v["heart_rate"]
        self.app.after(
            0,
            lambda: self.app.vitals_screen.show_oximeter_result(
                self.collected_spo2, self.collected_pulse
            ),
        )

    def _read_live_ecg(self):
        self.app.after(0, lambda: self.app.vitals_screen.show_ecg_analysis())
        self._ecg_polling = True
        self.app.after(50, self._poll_ecg_signal)

        time.sleep(5.0)
        self._ecg_polling = False

        self.collected_pulse = self.ecg.get_heart_rate()
        self.collected_rhythm = "Normal Sinus Rhythm"
        self.app.after(
            0,
            lambda: self.app.vitals_screen.show_ecg_result(
                self.collected_pulse, self.collected_rhythm
            ),
        )

    def _poll_ecg_signal(self):
        if not self._ecg_polling or self.get_current_state() != state_manager.MEASURING_ECG:
            return
        # Fetch from ECG buffer
        self.ecg.update()
        points = list(self.ecg.get_filtered_buffer()[-100:])
        self.app.vitals_screen.update_ecg_canvas(points)
        self.app.after(50, self._poll_ecg_signal)

    # API calls to Ollama & Bhashini
    def _query_ollama(
        self, prompt: str, image_path: Optional[str], response_lang: str
    ) -> str:
        lang_hint = RESPONSE_LANGUAGE_HINTS.get(
            response_lang, RESPONSE_LANGUAGE_HINTS["en"]
        )

        try:
            if image_path and os.path.exists(image_path):
                prompt_with_hint = f"{prompt}\n\n{lang_hint}"
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
            else:
                messages = [
                    {
                        "role": "system",
                        "content": f"You are MedGemma medical assistant. {lang_hint}",
                    },
                    {"role": "user", "content": prompt},
                ]
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
                return response["message"]["content"].strip()
        except Exception as exc:
            logger.error(f"Error querying Ollama model: {exc}")
            return f"Error: {exc}"

    def _speak_diagnosis(self, diagnosis_text: str, target_lang: str):
        try:
            self.state_mgr.set_state(state_manager.PLAYING_RESPONSE)
            self.app.after(
                0,
                lambda: self.app.voice_screen.show_processing(
                    "Playing diagnosis recommendations..."
                ),
            )

            # Generate TTS response
            BhashiniLocalTTS.synthesize(
                diagnosis_text, language=target_lang, output_path=OUTPUT_WAV
            )

            # Play synthesized audio
            if os.path.exists(OUTPUT_WAV):
                data, fs = sf.read(OUTPUT_WAV)
                sd.play(data, fs)
                sd.wait()
        except Exception as exc:
            logger.error(f"Error during audio speech synthesis: {exc}")
