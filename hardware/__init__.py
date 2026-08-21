"""
Hardware Package for MedGemma Medical Kiosk.
Contains Sensor Drivers for Oximeter (SpO2/HR), Thermal Camera, ECG DSP, and Camera.
Includes automatic fallback to simulation mode when hardware sensors are disconnected during testing.
"""

from .oximeter_reader import OximeterReader
from .thermal_reader import ThermalReader
from .ecg_reader import ECGReader
from .camera_module import CameraModule

__all__ = ["OximeterReader", "ThermalReader", "ECGReader", "CameraModule"]
