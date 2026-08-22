# Implementation Plan - Integrating Dual-Mode Nvidia-Jetson-Nano UI (Non-Destructive)

This plan details how we will integrate the custom **dual-mode touch UI** from the [Nvidia-Jetson-Nano](https://github.com/kishorkumar8848/Nvidia-Jetson-Nano) repository into our codebase. The integration will be completed **strictly without altering any existing codebase files** (e.g. `main.py` remains 100% untouched).

---

## 1. UI Architecture & Dual-Mode Behavior

The UI has two operating modes depending on the hardware detected:
1. **SPI Physical Mode** (Jetson Orin Nano with SPI LCD):
   - Initializes Adafruit `displayio`, `fourwire`, and `adafruit_ili9341` to run a 320x240 touch GUI.
   - Leverages `xpt2046_circuitpython` to handle touchscreen coordinate mappings.
   - Uses custom bitmap PCF fonts (`NotoSansDevanagari-Regular-12.pcf`) to render Hindi/Indic text directly onto the LCD frame buffer.
   - Monitors physical hardware pushbuttons (Pin 7 for RECORD, Pin 11 for CAMERA) and listens to USB click events via `evdev`.
2. **Desktop Simulator Mode** (Fallback on standard PCs):
   - Boots a Tkinter desktop window simulating the handheld screen's layout.
   - Displays real-time status fields, detected speech transcripts, translated queries, and clinical assistant outputs.
   - Integrates live mirror-flipped camera preview via OpenCV `cv2.VideoCapture` and takes snapshots for image analysis.

---

## 2. Non-Destructive Code Layout (New Files Only)

We will place all new UI components, drivers, and the offline integration backend in dedicated new files:

```
d:/Deva/MedGemma/
├── main.py                          <-- UNTOUCHED (Original file)
├── bhashini_speech.py               [NEW] Local Bhashini ASR & TTS (EN, HI, TA, TE)
├── download_bhashini_models.py      [NEW] Offline Bhashini speech weight pre-downloader
├── test_bhashini_pipeline.py        [NEW] Offline pipeline verification script
├── kiosk_backend.py                 [NEW] FastAPI local server handling /api/assistant/interact
├── main_kiosk_ui.py                 [NEW] Dual-mode UI launcher (Tkinter fallback / ILI9341 SPI)
├── ui/                              [NEW] UI Resources & Drivers
│   ├── display_assistant.py         Tkinter UI implementation
│   ├── handheld.py                  displayio ILI9341 hardware driver
│   ├── icons.py                     Icon font glyph constants
│   ├── NotoSansDevanagari-Regular-12.pcf  Hindi rendering font
│   └── forkawesome-16.pcf           Icon symbols font
```

---

## 3. Component Details & Integrations

### A. Local Backend Server (`kiosk_backend.py`)
To keep the UI responsive and fast, we run a lightweight FastAPI server on the Jetson. This server exposes:
- **`GET /api/status`**: Health check verification.
- **`POST /api/assistant/interact`**:
  1. Accepts `audio_file` bytes, `image_file` bytes, and target `language` code.
  2. Transcribes audio to text via local ASR (`bhashini_speech.py`).
  3. Detects input language. If non-English, injects language instructions into the Ollama prompt.
  4. Runs Ollama `medgemma:4b` with the query and optional image file.
  5. Synthesizes response audio locally via lightweight VITS/MMS-TTS (`bhashini_speech.py`).
  6. Returns JSON: `{"success": true, "detected_text": "...", "response_local": "...", "audio_response_path": "..."}`.

### B. Dual-Mode Launcher (`main_kiosk_ui.py`)
- Detects the presence of physical SPI screen drivers.
- If present, runs the `displayio` loop drawing to the ILI9341 LCD.
- Otherwise, starts `DesktopMockUI` (Tkinter) with OpenCV mirror-flipped camera preview.
- Interfaces via REST calls to the FastAPI backend.

---

## 4. Verification & Testing Plan

1. **Verify Original Code Intact**: Confirm `main.py` has no changes.
2. **Download Bhashini Assets**:
   ```bash
   python download_bhashini_models.py
   ```
3. **Start Kiosk Backend Daemon**:
   ```bash
   python kiosk_backend.py
   ```
4. **Launch Kiosk UI**:
   ```bash
   python main_kiosk_ui.py
   ```
   *Verify that the Tkinter simulation window launches on the desktop, captures webcam snapshot, records audio, communicates with FastAPI backend, and outputs local speech via TTS.*
