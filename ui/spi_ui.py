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

# Retro CRT Theme Color RGB tuples
RETRO_BG = (5, 8, 5)          # Deep CRT monitor black-green
RETRO_CARD = (13, 20, 13)     # Dark green console card
RETRO_GREEN = (51, 255, 51)   # Phosphor green
RETRO_AMBER = (255, 176, 0)   # Terminal Amber
RETRO_RED = (255, 51, 51)     # Red warning trace
RETRO_DIM = (0, 170, 0)       # Dim green

class SpiUI:
    def __init__(self):
        self.width = 320
        self.height = 240
        # Initialize canvas with Retro CRT Background
        self.image = Image.new("RGB", (self.width, self.height), color=RETRO_BG)
        self.draw = ImageDraw.Draw(self.image)
        self.disp = None
        
        try:
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            self.font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
            self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
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
                print("SPI Display Initialized Successfully in Retro CRT Mode!")
            except Exception as e:
                print(f"Error initializing SPI display: {e}")
                self.disp = None

    def render(self):
        """Pushes the current PIL Image to the SPI display."""
        if self.disp:
            self.disp.image(self.image)
        else:
            # If testing on Windows, save simulated image locally
            self.image.save("simulated_screen.png")

    def clear(self, color=RETRO_BG):
        self.draw.rectangle((0, 0, self.width, self.height), fill=color)

    def draw_text_centered(self, text, y, font, color=RETRO_GREEN):
        # Calculate text bounding box
        bbox = self.draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (self.width - text_w) // 2
        self.draw.text((x, y), text, font=font, fill=color)

    def show_message(self, title, subtitle="", bg_color=RETRO_BG, fg_color=RETRO_GREEN):
        self.clear(bg_color)
        
        # Retro bordered frame outline
        self.draw.rectangle((4, 4, self.width - 4, self.height - 4), outline=RETRO_GREEN, width=2)
        
        self.draw_text_centered(title, 70, self.font_large, color=fg_color)
        if subtitle:
            self.draw_text_centered(subtitle, 110, self.font_medium, color=RETRO_AMBER)
        self.render()

    def show_progress(self, title, percentage, color=RETRO_GREEN):
        self.clear(RETRO_BG)
        self.draw.rectangle((4, 4, self.width - 4, self.height - 4), outline=RETRO_GREEN, width=2)
        
        self.draw_text_centered(title, 50, self.font_large, color=RETRO_AMBER)
        
        # Draw progress bar container
        bar_x = 40
        bar_y = 110
        bar_w = 240
        bar_h = 24
        self.draw.rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), outline=RETRO_GREEN, width=2)
        
        # Fill progress with solid ticks
        fill_w = int((percentage / 100.0) * (bar_w - 4))
        if fill_w > 0:
            self.draw.rectangle((bar_x + 2, bar_y + 2, bar_x + 2 + fill_w, bar_y + bar_h - 2), fill=color)
            
        self.draw_text_centered(f"STATUS: {percentage}%", 150, self.font_medium, color=RETRO_GREEN)
        self.render()

    def show_results(self, temp, spo2, pulse):
        self.clear(RETRO_BG)
        self.draw.rectangle((4, 4, self.width - 4, self.height - 4), outline=RETRO_GREEN, width=2)
        
        self.draw_text_centered("VITALS SUMMARY REPORT", 15, self.font_large, color=RETRO_GREEN)
        
        self.draw.text((30, 65), f"Temp:  {temp:.1f} °C", font=self.font_medium, fill=RETRO_AMBER)
        self.draw.text((30, 105), f"SpO2:  {spo2} %", font=self.font_medium, fill=RETRO_GREEN)
        self.draw.text((30, 145), f"Pulse: {pulse} BPM", font=self.font_medium, fill=RETRO_RED)
        
        self.draw_text_centered(">>> TELEMETRY PUSHED <<<", 195, self.font_small, color=RETRO_DIM)
        self.render()
