"""
Thermal Body Temperature Sensor Reader for MedGemma Medical Kiosk.
Reads MLX90614 IR contactless thermometer via I2C.
Strictly live-only mode: raises RuntimeError if the sensor is disconnected.
"""

import time


class ThermalReader:
    def __init__(self, use_hardware: bool = True, i2c_address: int = 0x5A, i2c_bus: int = 1):
        self.i2c_address = i2c_address
        self.i2c_bus = i2c_bus

        try:
            import smbus2
            self.bus = smbus2.SMBus(self.i2c_bus)
            # Test communication to verify MLX90614 presence
            self.bus.read_i2c_block_data(self.i2c_address, 0x07, 3)
            print(f"[Thermal] Live MLX90614 successfully connected at I2C address 0x{i2c_address:X}")
        except Exception as exc:
            raise RuntimeError(
                f"MLX90614 Thermal sensor failed to initialize at address 0x{i2c_address:X} on I2C bus {i2c_bus} (Error: {exc}). "
                f"Verify that physical MLX90614 is wired correctly."
            ) from exc

    def read_temperature(self) -> dict:
        """Returns physical body temperature in Celsius and Fahrenheit, plus fever status."""
        try:
            # Read RAM register 0x07 (Object 1 temperature)
            data = self.bus.read_i2c_block_data(self.i2c_address, 0x07, 3)
            temp_raw = (data[1] << 8) | data[0]
            
            # MLX90614 temperature conversion factor (0.02 Kelvin per LSB)
            temp_c = (temp_raw * 0.02) - 273.15
            temp_f = (temp_c * 9.0 / 5.0) + 32.0
            
            is_fever = temp_c >= 37.5
            return {
                "temp_c": round(temp_c, 1),
                "temp_f": round(temp_f, 1),
                "is_fever": is_fever
            }
        except Exception as exc:
            raise RuntimeError(f"Failed to read from MLX90614 I2C thermal sensor: {exc}") from exc
