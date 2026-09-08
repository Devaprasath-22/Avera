"""
Camera Module for MedGemma Medical Kiosk.
Handles OpenCV video stream capture for live display and medical image snapshots.

STRICT HARDWARE MODE — NO SIMULATION.
If the camera cannot be opened, or a frame read fails, this raises an exception
instead of returning a synthetic/placeholder image.
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


class CameraNotFoundError(Exception):
    """Raised when the camera device cannot be opened."""
    pass


class CameraReadError(Exception):
    """Raised when a frame cannot be captured after retries."""
    pass


class CameraModule:
    def __init__(self, camera_index: int = 0, width: int = 640, height: int = 480,
                 use_csi: bool = False, max_retries: int = 3):
        """
        camera_index: /dev/videoN index for USB cameras.
        use_csi: set True if this is a Jetson CSI camera (not USB) — uses a
                 GStreamer/nvarguscamerasrc pipeline instead of a plain index,
                 since plain cv2.VideoCapture(index) does not open CSI cameras
                 on Jetson.
        """
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.use_csi = use_csi
        self.max_retries = max_retries
        self.cap = None
        self.is_opened = False

        try:
            self._init_camera()
        except Exception as exc:
            print(f"[Camera Notice] Camera initialization skipped/unavailable: {exc}")

    def _csi_pipeline(self) -> str:
        return (
            f"nvarguscamerasrc sensor-id={self.camera_index} ! "
            f"video/x-raw(memory:NVMM), width={self.width}, height={self.height}, "
            f"format=NV12, framerate=30/1 ! "
            f"nvvidconv ! video/x-raw, format=BGRx ! "
            f"videoconvert ! video/x-raw, format=BGR ! appsink drop=1"
        )

    def _init_camera(self):
        source = self._csi_pipeline() if self.use_csi else self.camera_index
        backend = cv2.CAP_GSTREAMER if self.use_csi else cv2.CAP_ANY

        try:
            self.cap = cv2.VideoCapture(source, backend)
        except Exception as exc:
            raise CameraNotFoundError(f"Error opening camera: {exc}") from exc

        if not self.cap.isOpened():
            raise CameraNotFoundError(
                f"Camera device could not be opened "
                f"({'CSI pipeline' if self.use_csi else f'index {self.camera_index}'}). "
                f"Check that the camera is connected and not in use by another process."
            )

        if not self.use_csi:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        # Confirm we can actually pull a real frame, not just that the device opened.
        ret, frame = self.cap.read()
        if not ret or frame is None:
            self.cap.release()
            raise CameraNotFoundError(
                "Camera opened but returned no frame on test read. "
                "Check camera permissions/driver."
            )

        self.is_opened = True
        print(f"[Camera] Live capture connected "
              f"({'CSI sensor-id ' + str(self.camera_index) if self.use_csi else 'index ' + str(self.camera_index)}).")

    def get_frame(self) -> "np.ndarray":
        """Returns a real BGR numpy frame from the camera. Raises on failure — never fabricates one."""
        if not self.is_opened or self.cap is None:
            raise CameraNotFoundError("Camera is not connected. No frame available.")

        last_exc = None
        for _ in range(self.max_retries):
            ret, frame = self.cap.read()
            if ret and frame is not None:
                return frame
            last_exc = "cap.read() returned ret=False or frame=None"
            time.sleep(0.02)

        self.is_opened = False
        raise CameraReadError(
            f"Frame capture failed after {self.max_retries} attempts. Last error: {last_exc}"
        )

    def capture_snapshot(self, filename: Optional[str] = None) -> str:
        """Saves a real captured frame to JPEG file and returns file path. Raises on failure."""
        frame = self.get_frame()  # will raise if unavailable — no placeholder saved
        if filename is None:
            temp_dir = tempfile.gettempdir()
            filename = os.path.join(temp_dir, f"kiosk_snapshot_{int(time.time())}.jpg")

        success = cv2.imwrite(filename, frame)
        if not success:
            raise CameraReadError(f"Failed to write snapshot to {filename}")

        print(f"[Camera] Saved snapshot for MedGemma Vision: {filename}")
        return filename

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.is_opened = False


if __name__ == "__main__":
    try:
        cam = CameraModule(camera_index=0, use_csi=False)  # set use_csi=True for Jetson CSI camera
        path = cam.capture_snapshot()
        print(f"Saved: {path}")
        cam.release()
    except (CameraNotFoundError, CameraReadError) as exc:
        print(f"[Camera] ERROR: {exc}")