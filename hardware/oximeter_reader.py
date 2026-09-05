"""
Oximeter Sensor Reader (SpO2 & Heart Rate) for MedGemma Medical Kiosk.
Reads MAX30102 Pulse Oximeter & Heart Rate sensor via I2C.

STRICT HARDWARE MODE — NO SIMULATION, NO RANDOM VALUES.
Both SpO2 and heart rate are computed from real buffered samples using the
AC/DC ratio-of-ratios method (SpO2) and peak-interval detection (heart rate).
Nothing is randomized or hardcoded — if a valid reading cannot be computed,
an exception is raised instead.

IMPORTANT CALIBRATION NOTE:
The ratio-of-ratios -> SpO2 mapping below uses the widely-published
approximate calibration curve (SpO2 = 110 - 25*R). This is a common
textbook/reference-design approximation, NOT a clinically calibrated curve.
Real pulse oximeters are calibrated against arterial blood-gas measurements
on a per-device/per-optics basis. For a MEDICAL kiosk you should calibrate
this against a validated reference oximeter before trusting displayed SpO2
values for clinical decisions.
"""

import time
from collections import deque
import numpy as np
from scipy.signal import find_peaks

MAX30102_ADDR = 0x57
REG_FIFO_DATA = 0x07
REG_MODE_CONFIG = 0x09
REG_SPO2_CONFIG = 0x0A
REG_LED1_PA = 0x0C
REG_LED2_PA = 0x0D

FINGER_PRESENT_THRESHOLD = 50000  # raw ADC counts; below this = no finger


class OximeterNotFoundError(Exception):
    """Raised when the MAX30102 cannot be found/configured on the I2C bus."""
    pass


class OximeterReadError(Exception):
    """Raised when a valid reading cannot be computed (no finger, bad signal, read failure)."""
    pass


class OximeterReader:
    def __init__(self, i2c_bus: int = 1, sample_rate: int = 100,
                 buffer_seconds: float = 5.0, max_retries: int = 3):
        self.i2c_bus = i2c_bus
        self.sample_rate = sample_rate
        self.max_retries = max_retries
        self.bus = None
        self.is_connected = False

        buffer_len = int(sample_rate * buffer_seconds)
        self.red_buffer = deque(maxlen=buffer_len)
        self.ir_buffer = deque(maxlen=buffer_len)

        self._connect()

    def _connect(self):
        try:
            import smbus2
        except ImportError as exc:
            raise OximeterNotFoundError(
                "smbus2 is not installed. Install it with: pip install smbus2"
            ) from exc

        try:
            bus = smbus2.SMBus(self.i2c_bus)
            bus.write_byte_data(MAX30102_ADDR, REG_MODE_CONFIG, 0x40)  # reset
            time.sleep(0.05)
            bus.write_byte_data(MAX30102_ADDR, REG_MODE_CONFIG, 0x03)  # SpO2 mode (red+IR)
            bus.write_byte_data(MAX30102_ADDR, REG_SPO2_CONFIG, 0x27)
            bus.write_byte_data(MAX30102_ADDR, REG_LED1_PA, 0x24)
            bus.write_byte_data(MAX30102_ADDR, REG_LED2_PA, 0x24)

            # Confirm we can actually read a FIFO sample
            data = bus.read_i2c_block_data(MAX30102_ADDR, REG_FIFO_DATA, 6)
            if len(data) < 6:
                raise ValueError("No FIFO data returned")

            self.bus = bus
            self.is_connected = True
            print(f"[Oximeter] Live MAX30102 connected on I2C bus {self.i2c_bus}, "
                  f"address 0x{MAX30102_ADDR:X}")
        except Exception as exc:
            raise OximeterNotFoundError(
                f"MAX30102 not found/responding on I2C bus {self.i2c_bus}, "
                f"address 0x{MAX30102_ADDR:X}. Check wiring. Original error: {exc}"
            ) from exc

    def _read_one_sample(self):
        data = self.bus.read_i2c_block_data(MAX30102_ADDR, REG_FIFO_DATA, 6)
        red_val = (data[0] << 16) | (data[1] << 8) | data[2]
        ir_val = (data[3] << 16) | (data[4] << 8) | data[5]
        return red_val, ir_val

    def update(self):
        """Reads one real (red, IR) sample pair from the MAX30102 FIFO into the rolling buffers."""
        if not self.is_connected or self.bus is None:
            raise OximeterNotFoundError("Oximeter is not connected. No data available.")

        last_exc = None
        for _ in range(self.max_retries):
            try:
                red_val, ir_val = self._read_one_sample()
                self.red_buffer.append(red_val)
                self.ir_buffer.append(ir_val)
                return
            except Exception as exc:
                last_exc = exc
                time.sleep(0.01)

        self.is_connected = False
        raise OximeterReadError(
            f"Failed to read oximeter sample after {self.max_retries} attempts. Last error: {last_exc}"
        )

    def read_vitals(self) -> dict:
        """
        Computes SpO2 and heart rate from the buffered samples.
        Raises OximeterReadError if there's no finger present or not enough
        signal to compute a reliable value — never returns a randomized or
        placeholder number.
        """
        if len(self.ir_buffer) < self.sample_rate * 2:
            raise OximeterReadError(
                "Not enough buffered samples yet. Call update() for at least "
                "2 seconds of data before reading vitals."
            )

        red = np.array(self.red_buffer, dtype=np.float64)
        ir = np.array(self.ir_buffer, dtype=np.float64)

        if ir[-1] < FINGER_PRESENT_THRESHOLD or red[-1] < FINGER_PRESENT_THRESHOLD:
            raise OximeterReadError("No finger detected on sensor.")

        # --- SpO2 via AC/DC ratio-of-ratios ---
        red_dc, ir_dc = np.mean(red), np.mean(ir)
        red_ac, ir_ac = np.std(red), np.std(ir)

        if red_dc == 0 or ir_dc == 0 or ir_ac == 0:
            raise OximeterReadError("Invalid signal levels (division by zero in ratio calc).")

        r_ratio = (red_ac / red_dc) / (ir_ac / ir_dc)
        spo2 = 110.0 - 25.0 * r_ratio
        spo2 = round(max(70.0, min(100.0, spo2)), 1)

        # --- Heart rate via real peak detection on IR waveform ---
        min_distance_samples = int(self.sample_rate * 60.0 / 200.0)  # cap at 200bpm
        threshold = np.mean(ir) + 0.5 * np.std(ir)
        peaks, _ = find_peaks(ir, distance=min_distance_samples, height=threshold)

        if len(peaks) < 2:
            raise OximeterReadError(
                "Not enough pulse peaks detected to compute heart rate. "
                "Ensure finger is steady on sensor."
            )

        intervals_sec = np.diff(peaks) / self.sample_rate
        avg_interval = np.mean(intervals_sec)
        hr = 60.0 / avg_interval

        if not (30 <= hr <= 220):
            raise OximeterReadError(f"Computed heart rate {hr:.0f} BPM is outside plausible range.")

        status = "Normal" if spo2 >= 95.0 else "Low SpO2 Alert"

        return {
            "spo2": spo2,
            "heart_rate": int(round(hr)),
            "status": status,
            "live": True,
        }


if __name__ == "__main__":
    try:
        reader = OximeterReader(i2c_bus=1)
        for _ in range(reader.sample_rate * 3):  # ~3 seconds of samples
            reader.update()
            time.sleep(1.0 / reader.sample_rate)
        print(reader.read_vitals())
    except (OximeterNotFoundError, OximeterReadError) as exc:
        print(f"[Oximeter] ERROR: {exc}")