#!/usr/bin/env python3
"""Build DOR into a standalone executable with PyInstaller."""
import os
import sys
from pathlib import Path

try:
    import PyInstaller.__main__
except ImportError:
    print("PyInstaller not found. Install it with: pip install pyinstaller")
    sys.exit(1)

ROOT = Path(__file__).parent.resolve()
DIST = ROOT / "dist"

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
    f"--distpath={str(DIST)}",
    "--icon=NONE",
])

print(f"\nBuild complete. Executable at: {DIST / 'DOR.exe'}")
