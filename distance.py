"""
DOR — Distance & Ocular Regulator
Module: distance.py
Privacy: Zero-I/O. No image data is written to disk or network at any point.
"""
import numpy as np

SAFE_DISTANCE_CM = 50.0

# Module-level variable to store the calibration constant K
_CALIBRATION_K = None

def set_calibration_k(k: float):
    global _CALIBRATION_K
    _CALIBRATION_K = k

def is_calibrated() -> bool:
    return _CALIBRATION_K is not None

def get_pupil_pixel_width(landmarks) -> float:
    """
    Calculates the normalized width between the centers of the left and right eyes.
    Using normalized coordinates keeps the ratio consistent regardless of resolution.
    """
    # Left eye center approximation (corners: 33 outer, 133 inner)
    left_x = (landmarks[33].x + landmarks[133].x) / 2.0
    left_y = (landmarks[33].y + landmarks[133].y) / 2.0
    
    # Right eye center approximation (corners: 362 inner, 263 outer)
    right_x = (landmarks[362].x + landmarks[263].x) / 2.0
    right_y = (landmarks[362].y + landmarks[263].y) / 2.0
    
    # Euclidean distance
    dist = np.sqrt((left_x - right_x)**2 + (left_y - right_y)**2)
    return float(dist)

def calculate_distance(pupil_width: float) -> float:
    """
    Returns distance in cm based on current pupil width and stored K.
    """
    if not is_calibrated() or pupil_width == 0:
        return 0.0
    return _CALIBRATION_K / pupil_width

def check_distance_threshold(distance_cm: float) -> bool:
    """
    Returns True if distance is safe (>= SAFE_DISTANCE_CM), False otherwise.
    """
    return distance_cm >= SAFE_DISTANCE_CM
