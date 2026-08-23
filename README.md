# MedGemma Medical Kiosk System 🩺

An offline, touch-enabled Medical Kiosk application designed for the **NVIDIA Jetson Orin Nano (8GB)**. It features a custom **Retro CRT Terminal / TFT LCD interface**, integrating **local Bhashini ASR/TTS Speech (10 Indian languages)**, **physical healthcare sensors**, **OpenCV camera feeds**, and a **progressive touchscreen diagnostic flow**.

> [!IMPORTANT]
> **100% LOCAL & OFFLINE RUNTIME**: This entire project operates strictly on the local **NVIDIA Jetson Orin Nano (8GB)** hardware. All sensor register polling, ASR speech recognition, TTS speech synthesis, and Ollama `medgemma:4b` AI diagnosis are processed locally on the device with **no internet access, cloud dependencies, or remote server requests**.

---

## 🎨 Retro CRT & TFT Display Aesthetics

The user interface is designed specifically for high-contrast visibility on small **TFT LCD screens** (like the **ILI9341 320x240 / 480x320** monitors) with a classic terminal vibe:
- **Monospaced Fonts**: The entire interface is structured using `Consolas` and `Courier New` monospaced characters.
- **Phosphor Green & Amber Palette**: Styled with deep CRT monitor black-green (`#050805`), high-visibility phosphor green (`#33FF33` / `#00FF00`), and dim green (`#00AA00`) alongside phosphor amber accents (`#FFB000`).
- **Ridge Frame Borders**: Standard card components feature a classic double-line physical frame border (`relief="ridge"`, `bd=3`) with outline highlights.
- **Tactile Screen Buttons**: Buttons have outlines with solid borders (`relief="solid"`, `bd=1`) to resemble physical mechanical console keys.

---

## ⚙️ Progressive System Checkups

To prevent overwhelming the patient and ensure full calibration checks:
- At startup, the kiosk boots into the **System Initialization** page.
- All hardware components begin unchecked (grayed out).
- The kiosk performs verification and checks each device off **one-by-one with a 3-second delay** in a progressive cycle:
  `Display` ➡️ `Speaker` ➡️ `Microphone` ➡️ `Temperature Sensor` ➡️ `Pulse Oximeter` ➡️ `ECG Sensor` ➡️ `Voice Assistant`.
- Live connection state (connected or simulated) is checked dynamically for each sensor driver.

---

## 🖥️ TFT Display Output Methods

You can output the Retro CRT Kiosk to your physical TFT screen in two ways:

### Method A: Linux Framebuffer / X11 Mirroring (Recommended)
If your Jetson Linux OS loads a framebuffer driver (e.g. `/dev/fb1` using `fbtft`) and mirrors the desktop X server output:
1. Running the main launcher launches the standard **Tkinter GUI** container.
2. The UI window opens at the scaled resolution (`540x480`) and automatically aligns to the active TFT display window space.

### Method B: Direct SPI Bit-Banged Driver (`ui/spi_ui.py`)
If you are running direct SPI pins and want to push raw PIL Canvas image buffers directly to the LCD screen without launching an X11 desktop shell:
1. The driver initializes a software bit-banged SPI connection using CircuitPython libraries on specified pins:
   - **SPI Pins**: `board.D11` (MOSI), `board.D9` (MISO), `board.D10` (CLK).
   - **Control Pins**: `board.D8` (CS), `board.D6` (DC).
2. The library (`ui/spi_ui.py`) draws custom telemetry charts, progress indicators, and text centered dynamically before pushing frame updates.

---

## 🛠️ Hardware Pin Connections (Jetson Orin Nano)

Ensure your sensors are wired to the 40-pin GPIO header:

| Sensor Module | Pins / Interface | Jetson 40-Pin Header Pins |
| :--- | :--- | :--- |
| **I2C Bus 1 (ALL Sensors)** | `SDA` / `SCL` | Physical Pins 3 (SDA), 5 (SCL) |
| **MAX30100 Pulse oximeter & heart rate sensor** | I2C Addr `0x57` | VCC (3.3V), GND, SDA, SCL |
| **MLX90614 Non contact IR Themometer sensor**| I2C Addr `0x5A` | VCC (3.3V), GND, SDA, SCL |
| **ADS1115 ADC (for ECG)**| I2C Addr `0x48` | VCC (3.3V), GND, SDA, SCL |
| **AD8232 Single Lead ECG Sensor Module Analog Devices** | Analog Input | Output wired to ADS1115 Channel `A0` |
| **ILI9341 SPI Screen** | SPI Bus / GPIO | MOSI (Pin 19), MISO (Pin 21), CLK (Pin 23), CS (Pin 24), DC (Pin 31) |

---

## 📦 Software Setup & Installation Guide

### 1. Set Up Virtual Environment
```bash
# Clone the repository and navigate in
git clone https://github.com/Devaprasath-22/MedGemma.git
cd MedGemma

# Create and activate virtual environment
# Windows:
python -m venv medgemma-env
.\medgemma-env\Scripts\activate
# Linux/Jetson Orin:
python3 -m venv medgemma-env
source medgemma-env/bin/activate

# Install required packages
pip install -r requirements.txt
```

### 2. Pre-download Speech Recognition and TTS Models
To ensure offline speeds without fetching models on-the-fly, pre-compile models:
```bash
python download_bhashini_models.py
```
*(Models are compiled and stored under `~/.cache/medgemma/models` or `D:\cache\medgemma\models`).*

---

## 🚀 Running the System

### Run the Kiosk UI (FastAPI Daemon + Retro Touchscreen UI)
Execute the primary launcher command. It spins up the local FastAPI daemon thread (to communicate with Ollama and Bhashini) and launches the retro Tkinter wizard display:
```bash
python main_kiosk_ui.py
```

### Run Standalone Tests
Validate Speech pipelines locally:
```bash
python test_bhashini_pipeline.py
```
