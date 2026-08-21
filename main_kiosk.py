"""
Complete Offline Medical Kiosk Entrypoint for NVIDIA Jetson Orin Nano (8GB).
Integrates Medical Hardware Sensors (SpO2, Temp, ECG), Camera Module, Bhashini Speech (10 languages),
Ollama MedGemma 4B Vision & Text AI, and Pygame UI Dashboard.
Strictly non-destructive application (main.py remains 100% untouched).
"""

import os
import sys
import time
import threading
import tempfile
from typing import Optional
from pathlib import Path

try:
    import torch
    import ollama
    import pygame

    from bhashini_speech import (
        BhashiniLocalASR,
        BhashiniLocalTTS,
        listen_for_speech,
        speak,
        play_audio,
        StopEvent,
        RESPONSE_LANGUAGE_HINTS,
        OUTPUT_WAV,
    )
    from hardware import OximeterReader, ThermalReader, ECGReader, CameraModule
    from ui import KioskDisplayUI
except ImportError as exc:
    print(f"Error importing modules for main_kiosk.py: {exc}")
    raise exc

MODEL_NAME = "medgemma:4b"


class MedicalKioskApp:
    def __init__(self):
        print("=" * 65)
        print(" Initializing MedGemma Medical Kiosk System")
        print(" Target Platform: NVIDIA Jetson Orin Nano (8GB)")
        print("=" * 65)

        # Initialize Hardware Sensor Package
        self.oximeter = OximeterReader(use_hardware=False)
        self.thermal = ThermalReader(use_hardware=False)
        self.ecg = ECGReader(buffer_size=500, sample_rate=100)
        self.camera = CameraModule(camera_index=0)

        # Initialize UI Dashboard
        self.ui = KioskDisplayUI(width=1280, height=720)

        # App State
        self.running = True
        self.is_thinking = False
        self.current_user_prompt = ""
        self.current_ai_reply = "Welcome to MedGemma Kiosk. Select language and tap 'Speak Voice' or 'Snap Image'."
        self.current_language = "en"
        self.vitals_data = {}
        self.camera_frame = None

        # Start Sensor DSP Worker Thread
        self.sensor_thread = threading.Thread(target=self._sensor_update_loop, daemon=True)
        self.sensor_thread.start()

    def _sensor_update_loop(self):
        """Background thread updating ECG DSP buffer and vitals sensors at 60 Hz."""
        while self.running:
            try:
                # Update ECG DSP sample
                self.ecg.update()
                time.sleep(1.0 / 60.0)
            except Exception:
                time.sleep(0.05)

    def _get_aggregated_vitals_context(self) -> str:
        """Returns patient vitals formatted into medical context string for MedGemma LLM."""
        v = self.oximeter.read_vitals()
        t = self.thermal.read_temperature()

        context = (
            f"[Patient Real-Time Vitals: SpO2={v['spo2']}%, Heart Rate={v['heart_rate']} BPM, "
            f"Body Temp={t['temp_c']}°C ({t['temp_f']}°F), Fever={t['is_fever']}, Vitals Status={v['status']}]"
        )
        return context

    def query_medgemma(self, prompt: str, image_path: Optional[str] = None):
        """Runs MedGemma 4B Vision/Text LLM with patient vitals context in background thread."""
        self.is_thinking = True
        self.current_user_prompt = prompt
        
        def _worker():
            vitals_context = self._get_aggregated_vitals_context()
            full_prompt = f"{vitals_context}\nPatient Query: {prompt}"
            lang_hint = RESPONSE_LANGUAGE_HINTS.get(self.current_language, RESPONSE_LANGUAGE_HINTS["en"])

            try:
                if image_path and os.path.exists(image_path):
                    prompt_with_hint = f"{full_prompt}\n\n{lang_hint}" if self.current_language != "en" else full_prompt
                    response = ollama.generate(
                        model=MODEL_NAME,
                        prompt=prompt_with_hint,
                        images=[image_path],
                        options={
                            "num_ctx": 2048,
                            "num_predict": 180,
                            "temperature": 0.3,
                        },
                    )
                    reply = response.get("response", "").strip()
                else:
                    messages = [
                        {"role": "system", "content": f"You are MedGemma medical assistant. {lang_hint}"},
                        {"role": "user", "content": full_prompt},
                    ]
                    response = ollama.chat(
                        model=MODEL_NAME,
                        messages=messages,
                        options={
                            "num_ctx": 2048,
                            "num_predict": 180,
                            "temperature": 0.3,
                        },
                    )
                    reply = response["message"]["content"].strip()

                self.current_ai_reply = reply

                # Synthesize and play speech in background
                speak(reply, self.current_language, OUTPUT_WAV)
                stop_evt = StopEvent()
                play_audio(OUTPUT_WAV, stop_evt)

            except Exception as exc:
                self.current_ai_reply = f"Diagnosis Error: {exc}"
            finally:
                self.is_thinking = False

        threading.Thread(target=_worker, daemon=True).start()

    def run(self):
        print("\n[Kiosk System Active] Pygame Dashboard UI & Sensors Running...")
        
        while self.running:
            # 1. Fetch live sensor data
            vitals = self.oximeter.read_vitals()
            temp_data = self.thermal.read_temperature()
            vitals.update(temp_data)
            self.vitals_data = vitals

            ecg_buf = self.ecg.get_filtered_buffer()
            self.camera_frame = self.camera.get_frame()

            # 2. Process Pygame Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    action = self.ui.handle_click(event.pos)
                    
                    if action["type"] == "set_language":
                        self.current_language = action["value"]
                        print(f"[UI] Selected Language: {self.current_language.upper()}")

                    elif action["type"] == "speak_voice" and not self.is_thinking:
                        print(f"[UI] Triggered Voice Input for [{self.current_language.upper()}]...")
                        
                        def _voice_worker():
                            text = listen_for_speech(self.current_language, duration=5.0)
                            if text:
                                self.query_medgemma(text)
                            else:
                                print("[UI] No speech captured.")

                        threading.Thread(target=_voice_worker, daemon=True).start()

                    elif action["type"] == "snap_camera" and not self.is_thinking:
                        print("[UI] Triggered Medical Camera Snapshot...")
                        snapshot_path = self.camera.capture_snapshot()
                        self.query_medgemma("Please analyze this patient medical image and vitals.", snapshot_path)

            # 3. Render Dashboard UI
            self.ui.render(
                vitals=self.vitals_data,
                ecg_buffer=ecg_buf,
                camera_frame=self.camera_frame,
                reply_text=self.current_ai_reply,
                user_prompt=self.current_user_prompt,
                is_thinking=self.is_thinking,
            )

            self.ui.clock.tick(30)  # 30 FPS UI render rate

        self.camera.release()
        pygame.quit()
        print("[Kiosk System Shutdown] Goodbye!")


def main():
    app = MedicalKioskApp()
    app.run()


if __name__ == "__main__":
    main()
