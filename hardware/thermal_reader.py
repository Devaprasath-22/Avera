"""
Thermal Body Temperature Sensor Reader for MedGemma Medical Kiosk.
Reads MLX90614 IR contactless thermometer via I2C.
Includes simulation fallback if sensor is detached.
"""

import time
import math
import random


class ThermalReader:
    def __init__(self, use_hardware: bool = False, i2c_address: int = 0x5A):
        self.use_hardware = use_hardware
        self.i2c_address = i2c_address
        self.is_connected = False

        if self.use_hardware:
            try:
                import smbus2
                self.bus = smbus2.SMBus(1)
                self.is_connected = True
                print(f"[Thermal] Initialized MLX90614 IR sensor at address 0x{i2c_address:X}")
            except Exception as exc:
                print(f"[Thermal] Physical I2C sensor initialization failed ({exc}). Using Simulation Mode.")
                self.is_connected = False

    def read_temperature(self) -> dict:
        """Returns body temperature in Celsius and Fahrenheit, plus fever status."""
        if self.is_connected:
            try:
                # Read RAM register 0x07 (Object 1 temperature)
                data = self.bus.read_i2c_block_data(self.i2c_address, 0x07, 3)
                temp_raw = (data[1] << 8) | data[0]
                temp_c = (temp_raw * 0.02) - 273.15
                temp_f = (temp_c * 9.0 / 5.0) + 32.0
                is_fever = temp_c >= 37.5
                return {"temp_c": round(temp_c, 1), "temp_f": round(temp_f, 1), "is_fever": is_fever}
            except Exception:
                pass

        # Simulation Mode: Realistic body temperature ~36.5°C to 37.0°C with minor variation
        t = time.time()
        base_c = 36.6 + 0.3 * math.sin(t / 8.0) + random.uniform(-0.1, 0.1)
        temp_c = round(base_c, 1)
        temp_f = round((temp_c * 9.0 / 5.0) + 32.0, 1)
        is_fever = temp_c >= 37.5

        return {
            "temp_c": temp_c,
            "temp_f": temp_f,
            "is_fever": is_fever,
        }


if __name__ == "__main__":
    reader = ThermalReader(use_hardware=False)
    print("Testing ThermalReader Simulation:")
    for _ in range(5):
        print(reader.read_temperature())
        time.sleep(0.5)
