# MedGemma Medical Kiosk System 🩺

An offline, touch-enabled Medical Kiosk application designed for the **NVIDIA Jetson Orin Nano (8GB)**. It integrates **local Bhashini ASR/TTS Speech (10 Indian languages)**, **physical healthcare sensors**, **OpenCV camera feeds**, and a **step-by-step Tkinter touch screen assistant**.

---

## 🏛 System Architecture & Memory Budget

Designed to run completely offline on unified memory architectures (like the **Jetson Orin Nano 8GB**):

| Component | RAM / VRAM Footprint | Description |
| :--- | :--- | :--- |
| **Linux OS & JetPack** | ~1.0 GB RAM | Core operating system services |
| **Ollama (`medgemma:4b`)** | ~3.8 GB VRAM/RAM | Quantized clinical LLM + Vision model |
| **Bhashini Local ASR/TTS** | ~520 MB VRAM/RAM | INT8 quantized speech transcribe & VITS TTS engines |
| **GUI & Sensor DSP** | ~200 MB RAM | Tkinter/Pygame screen layouts & SciPy DSP filtering |
| **Total Memory Usage** | **~5.5 GB** | **~2.2 GB free headroom (Zero Out-Of-Memory crashes)** |

---

## ✨ Features

- 🇮🇳 **10 Indian Languages Supported**: English (`en`), Hindi (`hi`), Tamil (`ta`), Telugu (`te`), Bengali (`bn`), Gujarati (`gu`), Kannada (`kn`), Malayalam (`ml`), Marathi (`mr`), Punjabi (`pa`).
- 🫁 **MAX30102 Oximeter Reader**: Live PPG register extraction measuring heart rate (BPM) and blood oxygenation (SpO2).
- 🌡️ **MLX90614 Contactless Thermal Sensor**: Live body temperature scanning with automated fever threshold detection.
- 📈 **AD8232 ECG via ADS1115 ADC**: Live 16-bit analog-to-digital ECG reading with real-time **0.5–40 Hz SciPy Butterworth bandpass filtering** and scrolling graph visualizer.
- 📸 **OpenCV Viewfinder & Snapshot**: Captures live webcam snapshots to analyze skin conditions and medical documents.
- 🚀 **FastAPI Backend Server**: Exposes local REST endpoints to poll vitals, run ASR/TTS, and query MedGemma.
- 🖥️ **Desktop Simulator Mode**: Gracefully falls back to simulated inputs when run on standard Windows/macOS PCs lacking physical I2C pins.

---

## 📁 Repository Structure

```
d:/Deva/MedGemma/
├── main.py                     # Original assistant CLI (UNTOUCHED)
├── kiosk_backend.py            # FastAPI local server API daemon
├── main_kiosk_ui.py            # Touch screen UI launcher (Tkinter wizard)
├── download_bhashini_models.py # Offline model downloader
├── test_bhashini_pipeline.py   # Benchmark & validation test suite
├── app/
│   ├── state_manager.py        # Kiosk wizard state manager
│   └── controller.py           # Background workflow sequencer (ASR/TTS/Sensors/Ollama)
├── hardware/                   # Physical Sensor Drivers Package
│   ├── camera_module.py        # OpenCV camera viewer and snapshot manager
│   ├── ecg_reader.py           # Live AD8232 read via I2C ADS1115 ADC with SciPy DSP
│   ├── oximeter_reader.py      # MAX30102 PPG sensor register reader
│   └── thermal_reader.py       # MLX90614 Contactless IR thermometer driver
└── ui/                         # Display View Package
    ├── main_screen.py          # Kiosk Welcome Screen
    ├── vitals_screen.py        # System initialization checklists & sensor readings
    ├── voice_screen.py         # Spech recording countdowns
    ├── camera_screen.py        # Live viewfinder canvas
    └── result_screen.py        # Printable patient diagnostic report card
```

---

## 🚀 Installation & Setup

1. **Clone and Navigate into the Project**:
   ```bash
   cd MedGemma
   ```

2. **Activate the Virtual Environment**:
   - On Windows:
     ```bash
     .\medgemma-env\Scripts\activate
     ```
   - On Linux/Jetson:
     ```bash
     source medgemma-env/bin/activate
     ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🏃 Running the Application

### 1. Launch the Kiosk Wizard UI (FastAPI Daemon + Tkinter GUI)
This starts the local FastAPI server in a background thread and boots the touchscreen GUI:
```bash
python main_kiosk_ui.py
```

### 2. Pre-download Bhashini Speech Models (For Offline inference)
```bash
python download_bhashini_models.py
```
*(Wavelength models are saved locally to `~/.cache/medgemma/models` or `D:\cache\medgemma\models`).*

### 3. Run Standalone Bhashini Speech CLI
```bash
python main_bhashini.py
```
