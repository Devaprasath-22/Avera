"""
Thermal Body Temperature Sensor Reader for MedGemma Medical Kiosk.
Reads MLX90614 IR contactless thermometer via I2C.
Hybrid Mode: Uses live hardware if connected, otherwise falls back to simulation mode.
"""

import time
import math
import random


class ThermalReader:
    def __init__(self, use_hardware: bool = True, i2c_address: int = 0x5A, i2c_bus: int = 1):
        self.i2c_address = i2c_address
        self.i2c_bus = i2c_bus
        self.is_connected = False

        if use_hardware:
            try:
                import smbus2
                self.bus = smbus2.SMBus(self.i2c_bus)
                # Test communication to verify MLX90614 presence
                self.bus.read_i2c_block_data(self.i2c_address, 0x07, 3)
                self.is_connected = True
                print(f"[Thermal] Live MLX90614 connected at address 0x{i2c_address:X}")
            except Exception as exc:
                print(f"[Thermal Warning] Physical IR sensor not found ({exc}). Running in Simulation Mode.")
                self.is_connected = False

    def read_temperature(self) -> dict:
        """Returns body temperature in Celsius and Fahrenheit, plus fever status."""
        if self.is_connected:
            try:
                data = self.bus.read_i2c_block_data(self.i2c_address, 0x07, 3)
                temp_raw = (data[1] << 8) | data[0]
                temp_c = (temp_raw * 0.02) - 273.15
                temp_f = (temp_c * 9.0 / 5.0) + 32.0
                is_fever = temp_c >= 37.5
                return {
                    "temp_c": round(temp_c, 1),
                    "temp_f": round(temp_f, 1),
                    "is_fever": is_fever,
                    "live": True
                }
            except Exception as exc:
                print(f"[Thermal Error] Read failed ({exc}). Falling back to simulation.")
                self.is_connected = False

        # Simulation Mode
        t = time.time()
        base_c = 36.6 + 0.3 * math.sin(t / 8.0) + random.uniform(-0.1, 0.1)
        temp_c = round(base_c, 1)
        temp_f = round((temp_c * 9.0 / 5.0) + 32.0, 1)
        is_fever = temp_c >= 37.5

        return {
            "temp_c": temp_c,
            "temp_f": temp_f,
            "is_fever": is_fever,
            "live": False,
        }
