"""
DOR — Distance & Ocular Regulator
Module: blink.py
Privacy: Zero-I/O. No image data is written to disk or network at any point.
"""
import numpy as np
import time

EAR_BLINK_THRESHOLD = 0.25
EAR_CONSEC_FRAMES = 2
MIN_BLINK_RATE = 8 # per minute

# MediaPipe landmark indices
LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

def _eye_aspect_ratio(landmarks, eye_indices: list) -> float:
    """
    Computes the Eye Aspect Ratio (EAR) for a single eye.
    """
    pts = [np.array([landmarks[i].x, landmarks[i].y]) for i in eye_indices]
    
    # |p2 - p6|
    v1 = np.linalg.norm(pts[1] - pts[5])
    # |p3 - p5|
    v2 = np.linalg.norm(pts[2] - pts[4])
    # |p1 - p4|
    h = np.linalg.norm(pts[0] - pts[3])
    
    ear = (v1 + v2) / (2.0 * h) if h > 0 else 0
    return float(ear)

def compute_ear(landmarks) -> float:
    """
    Computes average EAR for both eyes.
    """
    left_ear = _eye_aspect_ratio(landmarks, LEFT_EYE)
    right_ear = _eye_aspect_ratio(landmarks, RIGHT_EYE)
    return (left_ear + right_ear) / 2.0

class BlinkTracker:
    def __init__(self):
        self.consec_frames = 0
        self.blink_timestamps = []
        
    def process_frame(self, ear: float):
        """
        Takes EAR for the current frame, updates consecutive frames count,
        and registers a blink if threshold is met.
        """
        if ear < EAR_BLINK_THRESHOLD:
            self.consec_frames += 1
        else:
            if self.consec_frames >= EAR_CONSEC_FRAMES:
                self.blink_timestamps.append(time.time())
            self.consec_frames = 0
            
    def get_blink_rate(self) -> float:
        """
        Calculates blink rate (blinks per minute) over a rolling 30-second window.
        """
        current_time = time.time()
        # Filter timestamps to only those within the last 30 seconds
        self.blink_timestamps = [t for t in self.blink_timestamps if current_time - t <= 30.0]
        
        # Rate per minute = (blinks in 30s) * 2
        return len(self.blink_timestamps) * 2.0

    def check_blink_rate_threshold(self) -> bool:
        """
        Returns True if blink rate is safe (>= MIN_BLINK_RATE), False otherwise.
        """
        return self.get_blink_rate() >= MIN_BLINK_RATE
