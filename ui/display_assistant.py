"""
Tkinter Desktop Simulation UI for MedGemma Medical Kiosk.
Simulates the handheld 320x240 screen layout, integrates OpenCV camera preview,
handles voice recording, and communicates with the FastAPI kiosk_backend server.
"""

import os
import sys
import tempfile
import time
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

try:
    import cv2
    from PIL import Image, ImageTk
    import requests
    import sounddevice as sd
    import soundfile as sf
except ImportError as exc:
    print(f"Missing dependency in display_assistant: {exc}")
    raise exc

BACKEND_URL = "http://127.0.0.1:8000"


class DesktopMockUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MedGemma Kiosk Simulator")
        self.root.geometry("800x600")
        self.root.configure(bg="#1E232D")

        self.current_lang = "en"
        self.is_recording = False
        self.audio_recorded_path = os.path.join(tempfile.gettempdir(), "simulated_input.wav")
        self.snapshot_path = os.path.join(tempfile.gettempdir(), "simulated_snap.jpg")
        
        # OpenCV Webcam Capture
        self.cap = cv2.VideoCapture(0)
        self.camera_active = self.cap.isOpened()
        
        self._setup_style()
        self._build_layout()
        
        # Start GUI polling threads
        self.root.after(30, self._update_camera_stream)
        self.root.after(1000, self._poll_vitals)

    def _setup_style(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure(".", background="#1E232D", foreground="#FFFFFF", fieldbackground="#2A303C")
        self.style.configure("TLabel", background="#1E232D", font=("Arial", 10))
        self.style.configure("Header.TLabel", font=("Arial", 14, "bold"), foreground="#00D2FF")
        self.style.configure("VitalsVal.TLabel", font=("Arial", 12, "bold"), foreground="#00E676")
        self.style.configure("TButton", background="#00D2FF", foreground="#1E232D", font=("Arial", 10, "bold"))
        self.style.map("TButton", background=[("active", "#00B0FF")])

    def _build_layout(self):
        # Header Panel
        header_frame = ttk.Frame(self.root, padding=10)
        header_frame.pack(fill="x")
        
        header_lbl = ttk.Label(header_frame, text="MedGemma Medical Kiosk Simulator", style="Header.TLabel")
        header_lbl.pack(side="left")
        
        # Language Selector
        lang_lbl = ttk.Label(header_frame, text="Language:")
        lang_lbl.pack(side="right", padx=5)
        self.lang_box = ttk.Combobox(
            header_frame, 
            values=["EN", "HI", "TA", "TE", "BN", "GU", "KN", "ML", "MR", "PA"], 
            width=5, 
            state="readonly"
        )
        self.lang_box.set("EN")
        self.lang_box.pack(side="right", padx=5)
        self.lang_box.bind("<<ComboboxSelected>>", self._on_language_change)

        # Main Workspace Panel (Split into Left & Right)
        split_frame = ttk.Frame(self.root, padding=10)
        split_frame.pack(fill="both", expand=True)

        # Left Column: Vitals Cards & Live Camera Feed
        left_frame = ttk.Frame(split_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=5)

        # Vitals Card Frame
        vitals_frame = ttk.LabelFrame(left_frame, text=" Real-Time Patient Vitals ", padding=10)
        vitals_frame.pack(fill="x", pady=5)
        
        self.vitals_lbl = ttk.Label(
            vitals_frame, 
            text="SpO2: --%  |  Heart Rate: -- BPM  |  Temp: --°C (--°F)  |  Status: --",
            style="VitalsVal.TLabel"
        )
        self.vitals_lbl.pack(fill="x")

        # Camera Canvas Frame
        cam_frame = ttk.LabelFrame(left_frame, text=" Camera Viewfinder ", padding=10)
        cam_frame.pack(fill="both", expand=True, pady=5)
        
        self.cam_canvas = tk.Canvas(cam_frame, bg="#2A303C", highlightthickness=0)
        self.cam_canvas.pack(fill="both", expand=True)

        # Right Column: Controls, AI Transcripts, Diagnosis Info
        right_frame = ttk.Frame(split_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=5)

        # Control Panel Buttons
        btn_frame = ttk.LabelFrame(right_frame, text=" Interaction Controls ", padding=10)
        btn_frame.pack(fill="x", pady=5)

        self.mic_btn = ttk.Button(btn_frame, text="🎙 Record Speech (5s)", command=self._record_speech)
        self.mic_btn.pack(fill="x", pady=5)

        self.query_btn = ttk.Button(btn_frame, text="📸 Snap Image & Ask AI", command=self._snap_and_query)
        self.query_btn.pack(fill="x", pady=5)

        # Text Displays
        text_frame = ttk.LabelFrame(right_frame, text=" Diagnostic Chat Output ", padding=10)
        text_frame.pack(fill="both", expand=True, pady=5)

        ttk.Label(text_frame, text="Patient Transcript:").pack(anchor="w")
        self.transcript_text = tk.Text(text_frame, height=3, bg="#2A303C", fg="#FFFFFF", font=("Arial", 10))
        self.transcript_text.pack(fill="x", pady=2)

        ttk.Label(text_frame, text="MedGemma Response:").pack(anchor="w", pady=(5, 0))
        self.response_text = tk.Text(text_frame, height=12, bg="#2A303C", fg="#00E676", font=("Arial", 10), wrap="word")
        self.response_text.pack(fill="both", expand=True, pady=2)

    def _on_language_change(self, event=None):
        self.current_lang = self.lang_box.get().lower()

    def _update_camera_stream(self):
        if self.camera_active:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                # Mirror-flip & Convert BGR to RGB
                frame = cv2.flip(frame, 1)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Resize to fit canvas
                w = self.cam_canvas.winfo_width()
                h = self.cam_canvas.winfo_height()
                if w > 10 and h > 10:
                    img = Image.fromarray(rgb_frame)
                    img_resized = img.resize((w, h), Image.Resampling.LANCZOS)
                    
                    self.photo = ImageTk.PhotoImage(image=img_resized)
                    self.cam_canvas.create_image(0, 0, image=self.photo, anchor="nw")
                    
        self.root.after(30, self._update_camera_stream)

    def _poll_vitals(self):
        def _worker():
            try:
                res = requests.get(f"{BACKEND_URL}/api/vitals", timeout=1.0)
                if res.status_code == 200:
                    v = res.json()
                    text = f"SpO2: {v['spo2']}%  |  Heart Rate: {v['heart_rate']} BPM  |  Temp: {v['temp_c']}°C ({v['temp_f']}°F)  |  Status: {v['status']}"
                    self.root.after(0, lambda: self.vitals_lbl.configure(text=text))
            except Exception:
                pass
        threading.Thread(target=_worker, daemon=True).start()
        self.root.after(1000, self._poll_vitals)

    def _record_speech(self):
        if self.is_recording:
            return
        
        self.is_recording = True
        self.mic_btn.configure(text="🔴 Recording (Speak Now)...", state="disabled")
        
        def _worker():
            try:
                sr = 16000
                duration = 5.0
                print(f"[UI] Recording audio for {duration} seconds...")
                audio = sd.rec(int(duration * sr), samplerate=sr, channels=1, dtype='int16')
                sd.wait()
                
                sf.write(self.audio_recorded_path, audio, sr)
                print(f"[UI] Saved audio output to: {self.audio_recorded_path}")
            except Exception as exc:
                print(f"[UI Audio Error] {exc}")
            finally:
                self.is_recording = False
                self.root.after(0, lambda: self.mic_btn.configure(text="🎙 Record Speech (5s)", state="normal"))
                
        threading.Thread(target=_worker, daemon=True).start()

    def _snap_and_query(self):
        self.query_btn.configure(text="Thinking...", state="disabled")
        self.transcript_text.delete("1.0", tk.END)
        self.response_text.delete("1.0", tk.END)
        
        def _worker():
            try:
                # Capture snapshot from camera feed
                if self.camera_active:
                    ret, frame = self.cap.read()
                    if ret and frame is not None:
                        cv2.imwrite(self.snapshot_path, frame)
                        print(f"[UI] Camera snapshot captured: {self.snapshot_path}")

                # Build multipart request parameters
                files = {}
                data = {"language": self.current_lang}

                if os.path.exists(self.audio_recorded_path):
                    files["audio"] = ("audio.wav", open(self.audio_recorded_path, "rb"), "audio/wav")
                else:
                    data["text_prompt"] = "Describe patient health status"

                if os.path.exists(self.snapshot_path):
                    files["image"] = ("snap.jpg", open(self.snapshot_path, "rb"), "image/jpeg")

                # Send requests to local FastAPI backend
                print("[UI] Sending interact request to local REST API...")
                res = requests.post(f"{BACKEND_URL}/api/assistant/interact", files=files, data=data, timeout=30.0)
                
                # Cleanup open file handles
                for f in files.values():
                    f[1].close()

                if res.status_code == 200:
                    resp = res.json()
                    if resp.get("success"):
                        self.root.after(0, lambda: self.transcript_text.insert(tk.END, resp.get("detected_text", "")))
                        self.root.after(0, lambda: self.response_text.insert(tk.END, resp.get("response_local", "")))
                        
                        # Download and play TTS response
                        self._play_response_audio()
                    else:
                        self.root.after(0, lambda: messagebox.showerror("Backend Error", resp.get("error", "Unknown error")))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Server Error", f"Status Code: {res.status_code}"))

                # Cleanup temp file artifacts
                for path in [self.audio_recorded_path, self.snapshot_path]:
                    if os.path.exists(path):
                        try:
                            os.remove(path)
                        except OSError:
                            pass
            except Exception as exc:
                self.root.after(0, lambda: messagebox.showerror("Connection Error", f"Could not connect to FastAPI server: {exc}"))
            finally:
                self.root.after(0, lambda: self.query_btn.configure(text="📸 Snap Image & Ask AI", state="normal"))

        threading.Thread(target=_worker, daemon=True).start()

    def _play_response_audio(self):
        try:
            res = requests.get(f"{BACKEND_URL}/api/audio", timeout=5.0)
            if res.status_code == 200:
                temp_play_path = os.path.join(tempfile.gettempdir(), f"play_{int(time.time())}.wav")
                with open(temp_play_path, "wb") as f:
                    f.write(res.content)
                
                # Play using sounddevice/soundfile
                data, fs = sf.read(temp_play_path)
                sd.play(data, fs)
                sd.wait()
                
                try:
                    os.remove(temp_play_path)
                except OSError:
                    pass
        except Exception as exc:
            print(f"[UI Audio Playback Error] {exc}")

    def cleanup(self):
        if self.cap.isOpened():
            self.cap.release()
