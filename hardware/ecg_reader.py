"""
AD8232 Single-Lead ECG Sensor Reader (via ADS1115 16-bit I2C ADC) for MedGemma Medical Kiosk.

STRICT HARDWARE MODE — NO SIMULATION.
If the ADS1115 ADC is not found, or a read fails, this raises an exception
instead of generating a synthetic P-QRS-T waveform or a hardcoded heart rate.
"""

import time
import numpy as np
from scipy.signal import butter, filtfilt, find_peaks

ADS1115_ADDR = 0x48
REG_CONVERSION = 0x00
REG_CONFIG = 0x01


class ECGSensorNotFoundError(Exception):
    """Raised when the ADS1115 ADC cannot be located/configured on the I2C bus."""
    pass


class ECGReadError(Exception):
    """Raised when a sample cannot be read after retries."""
    pass


class ECGReader:
    def __init__(self, use_hardware: bool = True, buffer_size: int = 500, sample_rate: int = 100,
                 i2c_bus: int = 1, max_retries: int = 3, **kwargs):
        self.use_hardware = use_hardware
        self.buffer_size = buffer_size
        self.sample_rate = sample_rate
        self.buffer = np.zeros(self.buffer_size, dtype=np.float32)
        self.i2c_bus = i2c_bus
        self.max_retries = max_retries
        self.bus = None
        self.is_connected = False

        if self.use_hardware:
            try:
                self._connect()
            except Exception as exc:
                print(f"[ECG Notice] Hardware connection skipped/unavailable: {exc}")

        # Butterworth bandpass filter (0.5 Hz - 40 Hz), standard for ECG
        nyquist = 0.5 * self.sample_rate
        low = 0.5 / nyquist
        high = 40.0 / nyquist
        self.b, self.a = butter(2, [low, high], btype="bandpass")

    def _connect(self):
        try:
            import smbus2
        except ImportError as exc:
            raise ECGSensorNotFoundError(
                "smbus2 is not installed. Install it with: pip install smbus2"
            ) from exc

        try:
            bus = smbus2.SMBus(self.i2c_bus)
            # AIN0 single-ended, +/-4.096V range, continuous conversion mode, 128SPS
            config = [0xC4, 0x83]
            bus.write_i2c_block_data(ADS1115_ADDR, REG_CONFIG, config)
            time.sleep(0.05)  # allow first conversion to complete

            # Confirm we can actually read a conversion, not just that the write succeeded
            data = bus.read_i2c_block_data(ADS1115_ADDR, REG_CONVERSION, 2)
            if len(data) < 2:
                raise ValueError("No conversion data returned")

            self.bus = bus
            self.is_connected = True
            print(f"[ECG] Live AD8232/ADS1115 ADC connected on I2C bus {self.i2c_bus}, "
                  f"address 0x{ADS1115_ADDR:X}")
        except Exception as exc:
            raise ECGSensorNotFoundError(
                f"ADS1115 ADC not found/responding on I2C bus {self.i2c_bus}, "
                f"address 0x{ADS1115_ADDR:X}. Check wiring. Original error: {exc}"
            ) from exc

    def update(self):
        """Reads one real ECG voltage sample from ADS1115 AIN0. Raises on failure — never fabricates a sample."""
        if not self.is_connected or self.bus is None:
            raise ECGSensorNotFoundError("ECG ADC is not connected. No data available.")

        last_exc = None
        for _ in range(self.max_retries):
            try:
                data = self.bus.read_i2c_block_data(ADS1115_ADDR, REG_CONVERSION, 2)
                raw_val = (data[0] << 8) | data[1]
                if raw_val > 32767:
                    raw_val -= 65536
                sample_val = float(raw_val) / 32768.0

                self.buffer = np.roll(self.buffer, -1)
                self.buffer[-1] = sample_val
                return
            except Exception as exc:
                last_exc = exc
                time.sleep(0.01)

        self.is_connected = False
        raise ECGReadError(
            f"Failed to read ECG sample after {self.max_retries} attempts. Last error: {last_exc}"
        )

    def get_filtered_buffer(self) -> np.ndarray:
        """Applies digital bandpass filter to rolling buffer and returns the real filtered waveform."""
        if len(self.buffer) < 15:
            raise ECGReadError("Not enough samples buffered yet for filtering.")
        filtered = filtfilt(self.b, self.a, self.buffer)
        return filtered.astype(np.float32)

    def get_heart_rate(self) -> int:
        """
        Estimates heart rate (BPM) from real R-wave peaks in the filtered buffer.
        Raises ECGReadError if not enough data or no reliable peaks are found —
        never returns a hardcoded/placeholder value.
        """
        filtered = self.get_filtered_buffer()

        # R-waves are the dominant sharp peaks; require a minimum spacing so we
        # don't double-count within one heartbeat (assume max plausible HR ~200bpm).
        min_distance_samples = int(self.sample_rate * 60.0 / 200.0)
        threshold = np.std(filtered) * 1.5

        peaks, _ = find_peaks(filtered, distance=min_distance_samples, height=threshold)

        if len(peaks) < 2:
            raise ECGReadError(
                "Not enough R-wave peaks detected to compute heart rate. "
                "Check lead placement/contact."
            )

        intervals_samples = np.diff(peaks)
        avg_interval_sec = np.mean(intervals_samples) / self.sample_rate
        bpm = 60.0 / avg_interval_sec

        if not (30 <= bpm <= 220):
            raise ECGReadError(f"Computed heart rate {bpm:.0f} BPM is outside plausible range.")

        return int(round(bpm))


if __name__ == "__main__":
    try:
        reader = ECGReader(i2c_bus=1)
        for _ in range(reader.buffer_size):
            reader.update()
            time.sleep(1.0 / reader.sample_rate)
        print("Heart rate:", reader.get_heart_rate(), "BPM")
    except (ECGSensorNotFoundError, ECGReadError) as exc:
        print(f"[ECG] ERROR: {exc}")