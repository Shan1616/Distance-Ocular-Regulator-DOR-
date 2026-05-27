"""
DOR — Distance & Ocular Regulator
Module: camera.py
Privacy: Zero-I/O. No image data is written to disk or network at any point.
"""

import cv2

class CameraStream:
    def __init__(self, camera_index=0):
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera {camera_index}")
        
    def read_frame(self):
        """
        Reads a frame and immediately downscales it to 320x240.
        Returns the downscaled frame or None if reading fails.
        """
        ret, frame = self.cap.read()
        if not ret:
            return None
        # Downscale immediately to minimize memory footprint and processing time
        small_frame = cv2.resize(frame, (320, 240))
        return small_frame

    def release(self):
        self.cap.release()
