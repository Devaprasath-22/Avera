"""
Camera Module for MedGemma Medical Kiosk.
Handles OpenCV video stream capture for live display and saves medical image snapshots.
Strictly live-only mode: raises RuntimeError if the camera device cannot be opened.
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

        self._init_camera()

    def _init_camera(self):
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                print(f"[Camera] Live VideoCapture device {self.camera_index} successfully initialized.")
            else:
                raise RuntimeError(f"Failed to open live VideoCapture device at index {self.camera_index}")
        except Exception as exc:
            raise RuntimeError(
                f"Camera device {self.camera_index} failed to initialize (Error: {exc}). "
                f"Ensure a physical USB webcam or CSI camera is connected and recognized by the OS."
            ) from exc

    def get_frame(self) -> np.ndarray:
        """Returns BGR numpy image frame from the live camera stream."""
        if self.cap is not None:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                return frame
        raise RuntimeError("Failed to capture frame from live camera stream.")

    def capture_snapshot(self, filename: Optional[str] = None) -> str:
        """Saves current live frame to JPEG file and returns file path."""
        frame = self.get_frame()
        if filename is None:
            temp_dir = tempfile.gettempdir()
            filename = os.path.join(temp_dir, f"kiosk_snapshot_{int(time.time())}.jpg")

        cv2.imwrite(filename, frame)
        print(f"[Camera] Saved live snapshot for MedGemma Vision: {filename}")
        return filename

    def release(self):
        if self.cap is not None:
            self.cap.release()
