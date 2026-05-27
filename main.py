"""
DOR — Distance & Ocular Regulator
Module: main.py
Privacy: Zero-I/O. No image data is written to disk or network at any point.
"""
import sys
import time
import traceback
from pathlib import Path

import cv2
import mediapipe as mp

from PySide6.QtCore import QTimer
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import QApplication

from camera import CameraStream
from calibration import CalibrationDialog
from distance import (
    is_calibrated,
    get_pupil_pixel_width,
    calculate_distance,
    check_distance_threshold,
)
from blink import compute_ear, BlinkTracker
from dashboard import Dashboard, SessionSummaryDialog, dor_icon
from friction import FrictionOverlay, STAGE1_DELAY_SEC
from focus import FocusScore, SessionTracker

MODEL_PATH = str(Path(__file__).parent / "face_landmarker.task")
LIGHT_THRESHOLD = 40       # avg pixel brightness below this → low light warning
LIGHT_CONSEC_FRAMES = 15   # consecutive low-light frames before warning
BREAK_20_CYCLE_MIN = 20    # 20-20-20 rule interval


def _create_face_mesh():
    BaseOptions = mp.tasks.BaseOptions
    FaceLandmarker = mp.tasks.vision.FaceLandmarker
    FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode
    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=VisionRunningMode.IMAGE,
    )
    return FaceLandmarker.create_from_options(options)


def format_session_time(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def _notify_break():
    try:
        from plyer import notification
        notification.notify(
            title="DOR — 20-20-20 Break",
            message="Look at something 20 feet away for 20 seconds.",
            timeout=8,
        )
    except ImportError:
        pass


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("DOR")
    app.setWindowIcon(dor_icon())

    face_mesh = _create_face_mesh()

    # --- Calibration ---
    calib = CalibrationDialog(face_mesh)
    if not calib.exec():
        face_mesh.close()
        sys.exit(1)
    if not is_calibrated():
        print("Calibration failed or aborted. Exiting.")
        face_mesh.close()
        sys.exit(1)

    # --- Core systems ---
    dashboard = Dashboard()
    friction = FrictionOverlay()
    cam = CameraStream()
    blink_tracker = BlinkTracker()
    focus_score = FocusScore()
    session = SessionTracker()

    # --- State ---
    start_time = time.time()
    last_distance_check = 0.0
    current_distance = 50.0
    is_dist_safe = True
    violation_start_time = None
    total_violations = 0
    light_frames = 0
    light_warned = False
    break_20_count = 0
    paused = False

    # --- Pause/Resume hotkey ---
    def toggle_pause():
        nonlocal paused
        paused = not paused
        if paused:
            friction.clear()
            dashboard.set_status("Paused — Ctrl+Shift+P to resume", is_warning=False)
            dashboard.set_break_label("⏸ Paused")
        else:
            dashboard.set_break_label("")
            loop()

    pause_shortcut = QShortcut(QKeySequence("Ctrl+Shift+P"), dashboard)
    pause_shortcut.activated.connect(toggle_pause)

    # --- 20-20-20 timer ---
    def on_20_break():
        nonlocal break_20_count
        break_20_count += 1
        _notify_break()

    break_timer = QTimer()
    break_timer.timeout.connect(on_20_break)
    break_timer.start(BREAK_20_CYCLE_MIN * 60 * 1000)

    # --- Main loop ---
    overall_start = time.time()

    def process_frame():
        nonlocal last_distance_check, current_distance, is_dist_safe
        nonlocal violation_start_time, total_violations
        nonlocal light_frames, light_warned

        frame = cam.read_frame()
        if frame is None:
            return

        # Ambient light estimate
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        avg_brightness = gray.mean()

        # MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        results = face_mesh.detect(mp_image)

        # Destroy frames
        gray = None
        mp_image = None
        rgb_frame = None
        frame = None

        # Light check
        if avg_brightness < LIGHT_THRESHOLD:
            light_frames += 1
        else:
            light_frames = 0
            light_warned = False
        if light_frames >= LIGHT_CONSEC_FRAMES and not light_warned:
            light_warned = True
        dashboard.set_light_warning(light_warned)

        session_seconds = int(time.time() - start_time)

        # --- Face landmarks processing ---
        if results.face_landmarks:
            landmarks = results.face_landmarks[0]
            ear = compute_ear(landmarks)
            blink_tracker.process_frame(ear)

            if time.time() - last_distance_check >= 2.0:
                width = get_pupil_pixel_width(landmarks)
                current_distance = calculate_distance(width)
                is_dist_safe = check_distance_threshold(current_distance)
                last_distance_check = time.time()

        blink_rate = blink_tracker.get_blink_rate()
        is_blink_safe = blink_tracker.check_blink_rate_threshold()
        all_safe = is_dist_safe and is_blink_safe

        # --- Violations & friction ---
        if all_safe:
            violation_start_time = None
            friction.clear()
            dashboard.set_status("All Good", is_warning=False)
        else:
            if violation_start_time is None:
                violation_start_time = time.time()
                total_violations += 1
                session.violation_count += 1
            violation_duration = time.time() - violation_start_time

            if violation_duration >= STAGE1_DELAY_SEC:
                if violation_duration >= STAGE1_DELAY_SEC + 10:
                    friction.apply_stage2()
                    dashboard.set_status("Force Intervention Active", is_warning=True)
                else:
                    friction.apply_stage1()
                    dashboard.set_status("Nudge Intervention Active", is_warning=True)
            else:
                dashboard.set_status("Correct posture/blink", is_warning=True)

        # --- Focus score ---
        fs = focus_score.compute(current_distance, is_dist_safe, blink_rate, is_blink_safe)

        # --- Session tracking ---
        session.record(current_distance, all_safe, blink_rate, fs)

        # --- 20-20-20 countdown ---
        mins_until_break = BREAK_20_CYCLE_MIN - (int(time.time() - overall_start) // 60) % BREAK_20_CYCLE_MIN
        dashboard.set_break_label(
            f"20-20-20: {mins_until_break} min  |  Breaks: {break_20_count}"
        )

        # --- Dashboard update ---
        dashboard.update_metrics(
            current_distance,
            is_dist_safe,
            blink_rate,
            is_blink_safe,
            format_session_time(session_seconds),
            total_violations,
            focus_score=fs,
            sparkline_val=current_distance,
        )

    def loop():
        if paused:
            return
        frame_start = time.time()
        process_frame()
        if paused:
            return
        elapsed = time.time() - frame_start
        sleep_ms = max(1, 100 - int(elapsed * 1000))
        QTimer.singleShot(sleep_ms, loop)

    loop()

    # --- Session summary on quit ---
    def show_summary():
        dashboard.save_geometry()
        summary = session.summary()
        dlg = SessionSummaryDialog(summary)
        dlg.exec()

    app.aboutToQuit.connect(show_summary)

    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
