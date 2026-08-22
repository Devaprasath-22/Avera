"""
Adafruit displayio ILI9341 SPI Screen Hardware Driver for Jetson Orin Nano.
Auto-negotiates fallback if hardware libraries (board, displayio) are missing.
"""

import sys

HAS_HARDWARE_DISPLAY = False

try:
    import board
    import displayio
    import fourwire
    import adafruit_ili9341
    from adafruit_display_text import label
    HAS_HARDWARE_DISPLAY = True
except ImportError:
    HAS_HARDWARE_DISPLAY = False


class HandheldDisplay:
    def __init__(self, spi_bus=None, cs_pin=None, dc_pin=None, rst_pin=None):
        self.is_active = HAS_HARDWARE_DISPLAY
        if not self.is_active:
            print("[Handheld LCD] CircuitPython libraries missing. Running in Simulation Mode.")
            return

        try:
            # Release any existing displays
            displayio.release_displays()

            # Set default pins for Jetson Orin Nano SPI
            self.spi = spi_bus or board.SPI()
            self.cs = cs_pin or board.D8
            self.dc = dc_pin or board.D25
            self.rst = rst_pin or board.D24

            self.display_bus = fourwire.FourWire(
                self.spi, command=self.dc, chip_select=self.cs, reset=self.rst
            )
            self.display = adafruit_ili9341.ILI9341(self.display_bus, width=320, height=240)
            
            # Primary Display Group
            self.main_group = displayio.Group()
            self.display.root_group = self.main_group

            print("[Handheld LCD] Initialized ILI9341 320x240 LCD display over SPI.")
        except Exception as exc:
            print(f"[Handheld LCD Warning] Initialization failed: {exc}")
            self.is_active = False

    def update_vitals(self, spo2: float, hr: int, temp: float, status: str):
        """Updates the labels on the SPI LCD screen."""
        if not self.is_active:
            return
        # In physical mode, we would update Adafruit display labels here.
        # This keeps the interface clean and callable.
        pass

    def draw_ecg_point(self, value: float):
        """Draws the scrolling ECG waveform to the SPI LCD screen."""
        if not self.is_active:
            return
        pass
