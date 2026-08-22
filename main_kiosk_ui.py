"""
Dual-Mode Medical Kiosk UI Launcher.
Starts the FastAPI local backend daemon, detects the environment,
and launches the appropriate UI (Tkinter Simulator or SPI physical LCD display).
"""

import sys
import time
import threading
import tkinter as tk

try:
    import uvicorn
    from kiosk_backend import app
    from ui.handheld import HandheldDisplay, HAS_HARDWARE_DISPLAY
    from ui.display_assistant import DesktopMockUI
except ImportError as exc:
    print(f"Missing dependency in launcher: {exc}")
    raise exc


def main():
    print("=" * 65)
    print(" MedGemma Medical Kiosk Dual-Mode UI Launcher")
    print(" Target Platform: NVIDIA Jetson Orin Nano / Windows Dev PC")
    print("=" * 65)

    # 1. Start FastAPI Local Backend Daemon Server
    print("[Launcher] Starting local FastAPI backend server on port 8000...")
    backend_thread = threading.Thread(
        target=lambda: uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning"),
        daemon=True
    )
    backend_thread.start()
    
    # Wait for backend server startup
    time.sleep(1.5)

    # 2. Select UI Mode
    if HAS_HARDWARE_DISPLAY:
        print("[Launcher] Physical LCD display detected. Booting SPI interface...")
        try:
            display = HandheldDisplay()
            
            # Physical Hardware Event loop
            # Keeps the daemon alive and listens for hardware pin events
            print("[Launcher] SPI Physical interface running. Press Ctrl+C to exit.")
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            print("[Launcher] Exiting handheld interface...")
    else:
        print("[Launcher] Physical display absent. Launching Tkinter Desktop Simulator...")
        root = tk.Tk()
        ui = DesktopMockUI(root)

        def on_close():
            ui.cleanup()
            root.destroy()
            print("[Launcher] Kiosk UI Shutdown. Goodbye!")
            sys.exit(0)

        root.protocol("WM_DELETE_WINDOW", on_close)
        root.mainloop()


if __name__ == "__main__":
    main()
