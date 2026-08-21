"""
Camera Module for MedGemma Medical Kiosk.
Handles OpenCV video stream capture for live display and saves medical image snapshots.
Hybrid Mode: Uses live hardware if connected, otherwise falls back to simulation mode.
"""

import os
import tempfile
import time
from typing import Optional

try:
    import cv2
    import numpy as np
except ImportError as exc:
    print(f"Missing OpenCV in camera_module: {exc}")
    raise exc


class CameraModule:
    def __init__(self, camera_index: int = 0, width: int = 640, height: int = 480):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.cap = None
        self.is_opened = False

        self._init_camera()

    def _init_camera(self):
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.is_opened = True
                print(f"[Camera] Live VideoCapture device {self.camera_index} connected.")
            else:
                print(f"[Camera Warning] Physical camera device not found. Running in Simulation Mode.")
                self.is_opened = False
        except Exception as exc:
            print(f"[Camera Warning] Error opening camera ({exc}). Running in Simulation Mode.")
            self.is_opened = False

    def get_frame(self) -> np.ndarray:
        """Returns BGR numpy image frame from camera or synthetic placeholder."""
        if self.is_opened and self.cap is not None:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                return frame
            else:
                print("[Camera Error] Frame capture failed. Switching to simulation.")
                self.is_opened = False

        # Synthetic Frame Generator
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        # Draw dark medical camera card background
        cv2.rectangle(frame, (0, 0), (self.width, self.height), (30, 35, 45), -1)
        cv2.circle(frame, (self.width // 2, self.height // 2), 70, (0, 180, 220), 2)
        cv2.putText(
            frame,
            "CAMERA FEED (SIMULATION)",
            (self.width // 2 - 140, self.height // 2 + 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (220, 220, 220),
            1,
        )
        return frame

    def capture_snapshot(self, filename: Optional[str] = None) -> str:
        """Saves current frame to JPEG file and returns file path."""
        frame = self.get_frame()
        if filename is None:
            temp_dir = tempfile.gettempdir()
            filename = os.path.join(temp_dir, f"kiosk_snapshot_{int(time.time())}.jpg")

        cv2.imwrite(filename, frame)
        print(f"[Camera] Saved snapshot for MedGemma Vision: {filename}")
        return filename

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.is_opened = False
