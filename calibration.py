"""
DOR — Distance & Ocular Regulator
Module: calibration.py
Privacy: Zero-I/O. No image data is written to disk or network at any point.
"""
import cv2
import mediapipe as mp

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

from distance import set_calibration_k, get_pupil_pixel_width
from camera import CameraStream


class CalibrationDialog(QDialog):
    def __init__(self, face_mesh, parent=None):
        super().__init__(parent)
        self.face_mesh = face_mesh
        self._widths = []
        self._attempts = 0

        self.setWindowTitle("DOR Setup")
        self.setFixedSize(450, 300)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog
        )
        self.setObjectName("calibDialog")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label = QLabel(
            "Please sit exactly 50 cm from your screen.\n"
            "Click 'Start Calibration' when you are ready."
        )
        self.label.setObjectName("calibLabel")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        self.btn = QPushButton("Start Calibration")
        self.btn.setObjectName("calibBtn")
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.clicked.connect(self._on_start)
        layout.addWidget(self.btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setStyleSheet("""
            #calibDialog { background: #1e1e2e; }
            #calibLabel {
                color: #cdd6f4; font-size: 13px; padding: 20px;
            }
            #calibBtn {
                background: #89b4fa; color: #11111b;
                font-size: 12px; font-weight: bold;
                border: none; border-radius: 6px;
                padding: 10px 24px; min-width: 160px;
            }
            #calibBtn:hover { background: #74c7ec; }
            #calibBtn:disabled {
                background: #45475a; color: #6c7086;
            }
        """)

        try:
            self.cam = CameraStream()
        except RuntimeError:
            self.label.setText("Error: Could not access the webcam.")
            self.btn.setEnabled(False)
            QTimer.singleShot(3000, self.reject)

    def _on_start(self):
        self.btn.setEnabled(False)
        self.btn.setText("Calibrating...")
        self._widths = []
        self._attempts = 0
        self._countdown(5)

    def _countdown(self, n):
        if self._is_deleted():
            return
        if n <= 0:
            self._capture_frame()
            return
        self.label.setText(
            f"Starting in {n} seconds...\nKeep looking at the screen."
        )
        QTimer.singleShot(1000, lambda: self._countdown(n - 1))

    def _capture_frame(self):
        if self._is_deleted():
            return

        if self._attempts == 0:
            self.label.setText("Capturing...\nPlease hold still.")

        frame = self.cam.read_frame()
        if frame is not None:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            results = self.face_mesh.detect(mp_image)

            mp_image = None
            rgb = None
            frame = None

            if results.face_landmarks:
                self._widths.append(
                    get_pupil_pixel_width(results.face_landmarks[0])
                )

        self._attempts += 1

        if len(self._widths) >= 10 or self._attempts >= 30:
            self._finish()
        else:
            QTimer.singleShot(100, self._capture_frame)

    def _finish(self):
        if self._is_deleted():
            return

        if len(self._widths) >= 10:
            avg = sum(self._widths) / len(self._widths)
            set_calibration_k(50.0 * avg)
            self.label.setText("Calibration complete! ✅\nDetected distance: 50 cm")
            self.label.setStyleSheet(
                "#calibLabel { color: #a6e3a1; font-size: 13px; padding: 20px; }"
            )
            self.btn.setText("Done")
            self.btn.setEnabled(True)
            self.btn.clicked.disconnect()
            self.btn.clicked.connect(self.accept)
            QTimer.singleShot(1500, self.accept)
        else:
            self.label.setText(
                "Failed to detect face consistently.\n"
                "Ensure good lighting and try again."
            )
            self.label.setStyleSheet(
                "#calibLabel { color: #f38ba8; font-size: 13px; padding: 20px; }"
            )
            self.btn.setText("Try Again")
            self.btn.setEnabled(True)
            self.btn.clicked.disconnect()
            self.btn.clicked.connect(self._on_start)

    def _is_deleted(self):
        try:
            return not self.isVisible()
        except RuntimeError:
            return True
