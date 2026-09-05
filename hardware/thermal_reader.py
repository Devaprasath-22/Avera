"""
MLX90614 Non-Contact IR Thermometer Sensor Reader for MedGemma Medical Kiosk.
Reads MLX90614 via I2C on Jetson Orin Nano (or any Linux SBC).

STRICT HARDWARE MODE — NO SIMULATION.
If the sensor is not physically connected/detected, or a read fails validation,
this raises a SensorNotFoundError / SensorReadError instead of returning any
fabricated or estimated temperature. This is intentional for a medical kiosk:
returning a plausible-looking fake number is worse than returning nothing.
"""

import time


class SensorNotFoundError(Exception):
    """Raised when the MLX90614 cannot be located on any I2C bus."""
    pass


class SensorReadError(Exception):
    """Raised when a read is attempted but fails validation (PEC/range) after retries."""
    pass


def _pec8(data: bytes) -> int:
    """CRC-8 (poly 0x07) as used by SMBus PEC / MLX90614."""
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if (crc & 0x80) else (crc << 1) & 0xFF
    return crc


class ThermalReader:
    # Candidate I2C buses across Jetson Orin Nano devkit/carrier boards.
    # Confirm the correct one for your board with: sudo i2cdetect -y -r <bus>
    CANDIDATE_BUSES = [7, 8, 9, 1, 0]

    def __init__(self, i2c_address: int = 0x5A, i2c_bus: int = None, max_retries: int = 3):
        self.i2c_address = i2c_address
        self.i2c_bus = i2c_bus
        self.max_retries = max_retries
        self.bus = None
        self.is_connected = False

        self._connect()  # raises SensorNotFoundError if nothing is found

    def _connect(self):
        try:
            import smbus2
        except ImportError as exc:
            raise SensorNotFoundError(
                "smbus2 is not installed. Install it with: pip install smbus2"
            ) from exc

        buses_to_try = [self.i2c_bus] if self.i2c_bus is not None else self.CANDIDATE_BUSES

        for bus_num in buses_to_try:
            try:
                bus = smbus2.SMBus(bus_num)
                data = bus.read_i2c_block_data(self.i2c_address, 0x07, 3)
                if self._is_valid_reading(data):
                    self.bus = bus
                    self.i2c_bus = bus_num
                    self.is_connected = True
                    print(f"[Thermal] Live MLX90614 connected on bus {bus_num}, "
                          f"address 0x{self.i2c_address:X}")
                    return
                bus.close()
            except Exception:
                continue

        raise SensorNotFoundError(
            f"MLX90614 not found at address 0x{self.i2c_address:X} on any of "
            f"buses {buses_to_try}. Check wiring and run "
            f"'sudo i2cdetect -y -r <bus>' to confirm which bus shows 0x5a."
        )

    def _is_valid_reading(self, data) -> bool:
        if len(data) < 3:
            return False
        low, high, pec = data[0], data[1], data[2]
        write_byte = self.i2c_address << 1
        read_byte = write_byte | 1
        expected_pec = _pec8(bytes([write_byte, 0x07, read_byte, low, high]))
        if expected_pec != pec:
            return False
        temp_raw = (high << 8) | low
        temp_c = (temp_raw * 0.02) - 273.15
        return -20.0 <= temp_c <= 100.0

    def read_temperature(self) -> dict:
        """
        Returns real body temperature in Celsius and Fahrenheit, plus fever status.
        Raises SensorReadError if a valid reading cannot be obtained — never
        returns fabricated data.
        """
        if not self.is_connected or self.bus is None:
            raise SensorNotFoundError("Sensor is not connected. No data available.")

        last_exc = None
        for attempt in range(self.max_retries):
            try:
                data = self.bus.read_i2c_block_data(self.i2c_address, 0x07, 3)
                if not self._is_valid_reading(data):
                    raise ValueError("PEC mismatch or out-of-range reading")

                temp_raw = (data[1] << 8) | data[0]
                temp_c = (temp_raw * 0.02) - 273.15
                temp_f = (temp_c * 9.0 / 5.0) + 32.0
                is_fever = temp_c >= 37.5
                return {
                    "temp_c": round(temp_c, 1),
                    "temp_f": round(temp_f, 1),
                    "is_fever": is_fever,
                    "live": True,
                }
            except Exception as exc:
                last_exc = exc
                time.sleep(0.05)

        raise SensorReadError(
            f"Failed to get a valid reading from MLX90614 after "
            f"{self.max_retries} attempts. Last error: {last_exc}"
        )


if __name__ == "__main__":
    try:
        reader = ThermalReader()
        print(reader.read_temperature())
    except (SensorNotFoundError, SensorReadError) as exc:
        print(f"[Thermal] ERROR: {exc}")