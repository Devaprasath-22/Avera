# Implementation Plan - Complete Non-Destructive Medical Kiosk for Jetson Orin Nano (8GB)

This plan details the full architecture for an **offline Medical Kiosk on the NVIDIA Jetson Orin Nano (8GB)** integrating **Local Bhashini ASR/TTS**, **Hardware Sensors** (Oximeter, Thermal, ECG), **Camera**, and **Display UI**, constructed **strictly without modifying any existing codebase files** (e.g. `main.py` remains 100% untouched).

---

## 1. Non-Destructive Principles

- **Zero Overwriting**: All existing files (`main.py`, `download_whisper_model.py`, etc.) are preserved intact.
- **Modular Isolation**: All new hardware drivers, display UI, Bhashini speech modules, and entrypoints are created in dedicated new files/directories.
- **Fallback Capability**: You can run the original `python main.py` at any time without side effects.

---

## 2. System & Memory Architecture (Jetson Orin Nano 8GB)

```
+-----------------------------------------------------------------------------------------+
|                              JETSON ORIN NANO 8GB RAM                                   |
|                                                                                         |
|  +--------------------+   +-----------------------+   +------------------------------+  |
|  |   Medical Sensors  |   |     Camera Module     |   |   Bhashini Speech Engine     |  |
|  | Oximeter (SpO2/HR) |   | OpenCV / CSI / USB Cam|   | ASR: Indic-Whisper INT8      |  |
|  | Thermal (Body Temp)|   | Capture image & feed  |   | TTS: Indic VITS/MMS          |  |
|  | ECG (AD8232/SPI)   |   |                       |   | Languages: EN, HI, TA, TE    |  |
|  +---------+----------+   +-----------+-----------+   +--------------+---------------+  |
|            |                          |                              |                  |
|            +--------------------------+------------------------------+                  |
|                                       |                                                 |
|                                       v                                                 |
|                   +---------------------------------------+                             |
|                   |       Vitals & Context Aggregator     |                             |
|                   +-------------------+-------------------+                             |
|                                       |                                                 |
|                                       v                                                 |
|                   +---------------------------------------+                             |
|                   |     MedGemma 4B Vision AI (Ollama)    |                             |
|                   +-------------------+-------------------+                             |
|                                       |                                                 |
|                                       v                                                 |
|                   +---------------------------------------+                             |
|                   |     Display Module (UI Dashboard)     |                             |
|                   | Live ECG Waveform + Vitals + Chat UI  |                             |
|                   +---------------------------------------+                             |
+-----------------------------------------------------------------------------------------+
```

### Memory Budget Breakdown (7.7 GB Unified Memory)
| Component | Estimated Memory | Note |
| :--- | :--- | :--- |
| **Linux OS & JetPack** | ~1.0 GB RAM | Background daemons |
| **Ollama (`medgemma:4b`)** | ~3.8 GB VRAM/RAM | 4-bit quantized LLM + Vision |
| **Bhashini Local ASR** | ~400 MB VRAM/RAM | INT8 CTranslate2 `faster-whisper` Indic |
| **Bhashini Local TTS** | ~120 MB RAM | Lightweight VITS / MMS-TTS |
| **Display UI & DSP Sensor Loops** | ~200 MB RAM | Non-blocking Pygame rendering & SciPy DSP |
| **Total Memory Usage** | **~5.5 GB** | **~2.2 GB free headroom (No OOM crashes)** |

---

## 3. Dedicated New File Structure (Zero Changes to Existing Code)

```
d:/Deva/MedGemma/
├── main.py                          <-- UNTOUCHED (Original file)
├── bhashini_speech.py               [NEW] Local Bhashini ASR & TTS (EN, HI, TA, TE)
├── download_bhashini_models.py      [NEW] Offline Bhashini speech downloader
├── test_bhashini_pipeline.py        [NEW] Verification test script for ASR/TTS
├── main_bhashini.py                 [NEW] MedGemma + Bhashini Speech standalone app
├── main_kiosk.py                    [NEW] Full Medical Kiosk (Speech + Sensors + Display + AI)
├── hardware/                        [NEW] Hardware Sensors Package
│   ├── __init__.py
│   ├── oximeter_reader.py           [NEW] SpO2 (%) and Heart Rate (BPM) reader
│   ├── thermal_reader.py            [NEW] Body Temperature sensor reader
│   ├── ecg_reader.py                [NEW] Real-time ECG DSP & waveform buffer
│   └── camera_module.py             [NEW] OpenCV snapshot & video stream manager
└── ui/                              [NEW] Display Module Package
    ├── __init__.py
    └── display_module.py            [NEW] Dashboard with Live ECG graph, vitals & chat UI
```

---

## 4. Component Design Details

### A. Local Bhashini Speech Module ([bhashini_speech.py](file:///d:/Deva/MedGemma/bhashini_speech.py))
- **ASR**: Transcribes English, Hindi, Tamil, and Telugu locally using INT8 quantized Indic model (`faster-whisper` / `ctranslate2`).
- **TTS**: Synthesizes clean speech in EN, HI, TA, TE using lightweight VITS / MMS-TTS open weights.

### B. Hardware Sensor Package (`hardware/`)
1. **[oximeter_reader.py](file:///d:/Deva/MedGemma/hardware/oximeter_reader.py)**: Reads MAX30102 / MAX30100 via I2C/Serial. Includes auto-detect simulation mode if physical sensor isn't plugged in during testing.
2. **[thermal_reader.py](file:///d:/Deva/MedGemma/hardware/thermal_reader.py)**: Reads MLX90614 / IR sensor via I2C. Detects fever thresholds (> 37.5°C).
3. **[ecg_reader.py](file:///d:/Deva/MedGemma/hardware/ecg_reader.py)**: Samples AD8232 / MAX30003 ECG signal at 100–250 Hz. Applies 0.5–40 Hz digital bandpass filter to eliminate noise and maintains a rolling 5-second waveform buffer.
4. **[camera_module.py](file:///d:/Deva/MedGemma/hardware/camera_module.py)**: Captures frames via OpenCV (`cv2.VideoCapture`). Supports instant medical image capture for MedGemma Vision.

### C. Display UI Module ([ui/display_module.py](file:///d:/Deva/MedGemma/ui/display_module.py))
- Full-screen dashboard for Jetson display (HDMI / LCD screen).
- **Sections**:
  - **Vitals Panel**: Live display of SpO2, Heart Rate, Body Temperature, Status.
  - **ECG Waveform Graph**: Live scrolling line plot of ECG signal.
  - **Camera Feed**: Real-time video preview with "Snap Image for AI" trigger.
  - **Bhashini Voice & MedGemma Chat Area**: Transcribed text, language selector (`EN`, `HI`, `TA`, `TE`), AI diagnosis display.

### D. Full Kiosk Application Entrypoint ([main_kiosk.py](file:///d:/Deva/MedGemma/main_kiosk.py))
- Spawns background sensor threads (Oximeter, Thermal, ECG).
- Aggregates live patient vitals into MedGemma context string: `"[Patient Vitals: SpO2=98%, HR=74 bpm, Temp=36.8°C, ECG=Normal Sinus Rhythm]"`.
- Connects local Bhashini ASR & TTS for voice interaction.
- Drives full Pygame UI dashboard on Jetson display.

---

## 5. Verification Plan

1. **Verify Existing Files Untouched**: Ensure `git status` shows `main.py` is completely clean and unmodified.
2. **Test Local Bhashini Speech**:
   ```bash
   python download_bhashini_models.py
   python test_bhashini_pipeline.py
   ```
3. **Test Hardware Drivers & UI in Simulation Mode**:
   ```bash
   python -m hardware.ecg_reader
   python -m ui.display_module
   ```
4. **Run Complete Kiosk Application**:
   ```bash
   python main_kiosk.py
   ```
   *Test live sensor displays, real-time ECG waveform graph, camera snapshot, Bhashini voice prompts (HI/TA/TE/EN), and MedGemma diagnostic responses on Jetson Orin Nano.*
