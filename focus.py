"""
DOR — Distance & Ocular Regulator
Module: focus.py
Privacy: Zero-I/O. No image data is written to disk or network at any point.
"""
import time

from distance import SAFE_DISTANCE_CM
from blink import MIN_BLINK_RATE


class FocusScore:
    """Composite 0–100 score: distance (50pts) + blink rate (30pts) + consistency (20pts)."""

    def compute(self, distance_cm, is_dist_safe, blink_rate, is_blink_safe):
        dist_pct = min(distance_cm / SAFE_DISTANCE_CM, 1.0)
        blink_pct = min(blink_rate / MIN_BLINK_RATE, 1.0)
        dist_score = dist_pct * 50
        blink_score = blink_pct * 30
        consistency = 20 if is_dist_safe and is_blink_safe else 0
        return int(dist_score + blink_score + consistency)

    @staticmethod
    def grade(score):
        if score >= 80:
            return "Excellent", "#a6e3a1"
        if score >= 60:
            return "Good", "#f9e2af"
        if score >= 40:
            return "Fair", "#fab387"
        return "Poor", "#f38ba8"


class SessionTracker:
    """Aggregates metrics over a session for the end-of-session summary."""

    def __init__(self):
        self.distance_readings = []
        self.blink_readings = []
        self.focus_readings = []
        self.violation_count = 0
        self.start_time = time.time()
        self.safe_seconds = 0.0
        self._last_safe_tick = time.time()

    def record(self, distance_cm, is_safe, blink_rate, focus_score):
        self.distance_readings.append(distance_cm)
        self.blink_readings.append(blink_rate)
        self.focus_readings.append(focus_score)
        now = time.time()
        if is_safe:
            self.safe_seconds += now - self._last_safe_tick
        self._last_safe_tick = now

    def summary(self):
        n = len(self.distance_readings)
        if n == 0:
            return None
        duration = time.time() - self.start_time
        return {
            "duration_sec": int(duration),
            "avg_distance_cm": sum(self.distance_readings) / n,
            "avg_blink_rate": sum(self.blink_readings) / n,
            "avg_focus": sum(self.focus_readings) / len(self.focus_readings),
            "safe_pct": (self.safe_seconds / duration * 100) if duration > 0 else 0,
            "violations": self.violation_count,
        }
