#!/usr/bin/env python3
"""Build DOR into a standalone executable with PyInstaller."""
import os
import sys
from pathlib import Path

try:
    import PyInstaller.__main__
except ImportError:
    print("PyInstaller not found. Install it with: python -m pip install pyinstaller")
    sys.exit(1)

ROOT = Path(__file__).parent.resolve()
DIST = ROOT / "dist"

# OS-agnostic separator for PyInstaller data
separator = ";" if os.name == "nt" else ":"
data_spec = f"{ROOT / 'face_landmarker.task'}{separator}."

PyInstaller.__main__.run([
    str(ROOT / "main.py"),
    "--name=DOR",
    "--onefile",
    "--windowed", 
    "--clean",
    "--noconfirm",
    f"--add-data={data_spec}",
    "--hidden-import=mediapipe",      # Forces MediaPipe dependencies to load
    "--collect-data=mediapipe",       # Forces MediaPipe internal models to package
    f"--distpath={str(DIST)}",
    "--icon=eye_185923.ico",                 # Uses your new custom icon
])

# Dynamically set the extension for the success message
ext = ".exe" if os.name == "nt" else ""
print(f"\nBuild complete. Executable at: {DIST / f'DOR{ext}'}")
