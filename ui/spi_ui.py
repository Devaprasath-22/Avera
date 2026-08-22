import os
import time
from PIL import Image, ImageDraw, ImageFont

# Try importing SPI libraries. If not present (e.g. on Windows), we will fallback/stub.
try:
    import board
    import digitalio
    import adafruit_rgb_display.ili9341 as ili9341
    SPI_AVAILABLE = True
except ImportError:
    SPI_AVAILABLE = False
    print("WARNING: SPI libraries not found. Running in simulation mode.")

class SpiUI:
    def __init__(self):
        self.width = 320
        self.height = 240
        self.image = Image.new("RGB", (self.width, self.height), color=(255, 255, 255))
        self.draw = ImageDraw.Draw(self.image)
        self.disp = None
        
        try:
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            self.font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
            self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except:
            self.font_large = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_small = ImageFont.load_default()

        if SPI_AVAILABLE:
            try:
                # DESELECT TOUCH PANEL so it doesn't corrupt SPI bus
                try:
                    tp_cs = digitalio.DigitalInOut(board.D7) # Pin 26
                    tp_cs.direction = digitalio.Direction.OUTPUT
                    tp_cs.value = True
                except Exception as e:
                    print("Could not set TP_CS:", e)

                # Configuration for CS and DC pins
                cs_pin = digitalio.DigitalInOut(board.D8)    # Pin 24
                dc_pin = digitalio.DigitalInOut(board.D6)    # MOVED to Pin 31 to avoid driver conflicts
                # reset_pin is removed; user will tie it to 3.3V

                # Create SOFTWARE SPI bus using Bit-Banging (Bypasses any kernel SPI issues)
                import adafruit_bitbangio as bitbangio
                spi = bitbangio.SPI(board.D11, MOSI=board.D10, MISO=board.D9)

                # Create the ILI9341 display
                self.disp = ili9341.ILI9341(
                    spi,
                    rotation=90,  # 320x240 landscape
                    cs=cs_pin,
                    dc=dc_pin,
                    baudrate=5000000,
                )
                print("SPI Display Initialized Successfully!")
            except Exception as e:
                print(f"Error initializing SPI display: {e}")
                self.disp = None

    def render(self):
        """Pushes the current PIL Image to the SPI display."""
        if self.disp:
            self.disp.image(self.image)
        else:
            # If testing on Windows, just save to a file or print
            self.image.save("simulated_screen.png")

    def clear(self, color=(255, 255, 255)):
        self.draw.rectangle((0, 0, self.width, self.height), fill=color)

    def draw_text_centered(self, text, y, font, color=(0, 0, 0)):
        # Calculate text bounding box
        bbox = self.draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (self.width - text_w) // 2
        self.draw.text((x, y), text, font=font, fill=color)

    def show_message(self, title, subtitle="", bg_color=(255, 255, 255), fg_color=(0,0,0)):
        self.clear(bg_color)
        self.draw_text_centered(title, 80, self.font_large, color=fg_color)
        if subtitle:
            self.draw_text_centered(subtitle, 120, self.font_medium, color=fg_color)
        self.render()

    def show_progress(self, title, percentage, color=(0, 200, 0)):
        self.clear((255, 255, 255))
        self.draw_text_centered(title, 60, self.font_large, color=(0, 0, 0))
        
        # Draw progress bar container
        bar_x = 40
        bar_y = 120
        bar_w = 240
        bar_h = 30
        self.draw.rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), outline=(0, 0, 0), width=2)
        
        # Fill progress
        fill_w = int((percentage / 100.0) * (bar_w - 4))
        if fill_w > 0:
            self.draw.rectangle((bar_x + 2, bar_y + 2, bar_x + 2 + fill_w, bar_y + bar_h - 2), fill=color)
            
        self.draw_text_centered(f"{percentage}%", 160, self.font_medium, color=(0,0,0))
        self.render()

    def show_results(self, temp, spo2, pulse):
        self.clear((255, 255, 255))
        self.draw_text_centered("VITALS SUMMARY", 20, self.font_large, color=(0, 0, 0))
        
        self.draw.text((30, 70), f"Temp: {temp:.1f} °F", font=self.font_medium, fill=(255, 100, 0))
        self.draw.text((30, 110), f"SpO2: {spo2} %", font=self.font_medium, fill=(0, 150, 0))
        self.draw.text((30, 150), f"Pulse: {pulse} BPM", font=self.font_medium, fill=(200, 0, 0))
        
        self.draw_text_centered("Reading Complete...", 200, self.font_small, color=(100, 100, 100))
        self.render()
