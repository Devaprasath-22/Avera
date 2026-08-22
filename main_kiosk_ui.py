"""
Healthcare Kiosk UI Launcher.
Starts the FastAPI local backend daemon and boots the HealthcareApp Tkinter window flow.
Strictly non-destructive (main.py remains 100% untouched).
"""

import sys
import time
import threading
import tkinter as tk

from ui.main_screen import MainScreen, BG_DARK
from ui.vitals_screen import VitalsScreen
from ui.voice_screen import VoiceScreen
from ui.result_screen import ResultScreen
from ui.camera_screen import CameraScreen
from app.controller import AppController
from utils.logger import setup_logger

logger = setup_logger("AppWindow")


class HealthcareApp(tk.Tk):
    """
    Main Tkinter window container for the Healthcare Kiosk.
    Sets up window dimensions, configures dark mode theme,
    initializes UI screens, and binds the workflow controller.
    """
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        
        # Configure Main Window
        self.title("MedGemma Healthcare AI Kiosk")
        self.geometry("540x480")
        self.resizable(False, False)
        self.configure(bg=BG_DARK)
        
        # Center the window on screen
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")
        
        # Handle close window button cleanly
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Container frame containing active screen
        self.container = tk.Frame(self, bg=BG_DARK)
        self.container.pack(side="top", fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        
        # Instantiate UI Screens
        self.main_screen = MainScreen(self.container, self.controller)
        self.vitals_screen = VitalsScreen(self.container, self.controller)
        self.voice_screen = VoiceScreen(self.container, self.controller)
        self.result_screen = ResultScreen(self.container, self.controller)
        self.camera_screen = CameraScreen(self.container, self.controller)
        
        self.screens = {
            "main": self.main_screen,
            "vitals": self.vitals_screen,
            "voice": self.voice_screen,
            "result": self.result_screen,
            "camera": self.camera_screen
        }
        
        # Show main welcome screen initially
        self.show_screen("main")

    def show_screen(self, screen_name):
        """
        Switches the visible screen frame inside the container.
        """
        logger.debug(f"Displaying screen: {screen_name}")
        
        # Hide all screens
        for screen in self.screens.values():
            screen.grid_remove()
            
        # Grid the requested screen
        target_screen = self.screens.get(screen_name)
        if target_screen:
            target_screen.grid(row=0, column=0, sticky="nsew")
        else:
            logger.error(f"Invalid screen requested: {screen_name}")
            
    def on_closing(self):
        """
        Triggered when closing the window. Stop any running workflows/audio threads.
        """
        logger.info("Closing application. Stopping worker and audio resources...")
        self.controller.reset_to_idle()
        self.destroy()
        sys.exit(0)


def main():
    logger.info("Starting Offline Healthcare Assistant Kiosk...")
    
    # Start FastAPI Local Backend Daemon Server on port 8000
    print("[Launcher] Starting local FastAPI backend server...")
    try:
        import uvicorn
        from kiosk_backend import app as backend_app
        backend_thread = threading.Thread(
            target=lambda: uvicorn.run(backend_app, host="127.0.0.1", port=8000, log_level="warning"),
            daemon=True
        )
        backend_thread.start()
        # Wait for backend server startup
        time.sleep(1.5)
    except Exception as exc:
        print(f"[Launcher Warning] Could not start FastAPI daemon ({exc}). Launching UI standalone...")

    controller = AppController()
    app = HealthcareApp(controller)
    controller.set_app(app)
    app.mainloop()


if __name__ == "__main__":
    main()
