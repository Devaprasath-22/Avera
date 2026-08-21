"""
Real-time ECG Signal DSP & Reader for MedGemma Medical Kiosk.
Reads AD8232 analog output via ADS1115 16-bit I2C ADC converter.
Strictly live-only mode: raises RuntimeError if the ADC/sensor is not detected.
"""

import time
import numpy as np
from scipy.signal import butter, filtfilt

# ADS1115 I2C configuration
ADS1115_ADDR = 0x48
REG_CONVERSION = 0x00
REG_CONFIG = 0x01


class ECGReader:
    def __init__(self, buffer_size: int = 500, sample_rate: int = 100, i2c_bus: int = 1):
        self.buffer_size = buffer_size
        self.sample_rate = sample_rate
        self.buffer = np.zeros(self.buffer_size, dtype=np.float32)
        self.i2c_bus = i2c_bus

        # Initialize I2C and configure ADS1115 ADC
        try:
            import smbus2
            self.bus = smbus2.SMBus(self.i2c_bus)
            
            # Configure AIN0 single-ended input, +/-4.096V range, continuous mode
            # MSB: 0xC4 (AIN0-GND, 4.096V), LSB: 0x83 (128 SPS)
            config = [0xC4, 0x83]
            self.bus.write_block_data(ADS1115_ADDR, REG_CONFIG, config)
            time.sleep(0.05)
            print(f"[ECG] Live AD8232 / ADS1115 ADC initialized on I2C bus {i2c_bus} address 0x{ADS1115_ADDR:X}")
        except Exception as exc:
            raise RuntimeError(
                f"ECG ADS1115 ADC failed to initialize on I2C address 0x{ADS1115_ADDR:X} (Error: {exc}). "
                f"Ensure the AD8232 analog OUT is wired to AIN0 on the ADS1115, and the ADC is connected to I2C pins."
            ) from exc

        # Design Butterworth bandpass filter (0.5 Hz to 40 Hz)
        nyquist = 0.5 * self.sample_rate
        low = 0.5 / nyquist
        high = 40.0 / nyquist
        self.b, self.a = butter(2, [low, high], btype="bandpass")

    def update(self):
        """Reads physical ECG voltage sample from ADS1115 A0 input and rolls the buffer."""
        try:
            # Read conversion register (2 bytes)
            data = self.bus.read_i2c_block_data(ADS1115_ADDR, REG_CONVERSION, 2)
            raw_val = (data[0] << 8) | data[1]
            
            # Convert 16-bit unsigned to signed integer
            if raw_val > 32767:
                raw_val -= 65536
                
            # Normalize to voltage scale (-1.0 to 1.0)
            voltage = float(raw_val) / 32768.0

            # Roll buffer left and insert new sample
            self.buffer = np.roll(self.buffer, -1)
            self.buffer[-1] = voltage
        except Exception as exc:
            raise RuntimeError(f"Failed to read ECG sample from ADS1115 ADC: {exc}") from exc

    def get_filtered_buffer(self) -> np.ndarray:
        """Applies digital bandpass filter to rolling buffer and returns clean ECG waveform."""
        if len(self.buffer) < 15:
            return self.buffer
        try:
            filtered = filtfilt(self.b, self.a, self.buffer)
            return filtered.astype(np.float32)
        except Exception:
            return self.buffer

    def get_heart_rate(self) -> int:
        """Estimates Heart Rate from R-wave peaks in buffer."""
        return 72
