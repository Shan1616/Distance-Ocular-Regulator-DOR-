# DOR — Distance & Ocular Regulator

Monitor your eye health in real time using just your webcam. DOR tracks **eye-to-screen distance** and **blink rate**, and gently nudges you when you're too close or not blinking enough — all without saving any images.

## Features

- **Distance Tracking** — Triangle Similarity via MediaPipe iris landmarks, accurate to ±5 cm
- **Blink Detection** — Eye Aspect Ratio (EAR) with rolling 30-second window
- **Focus Score** — Composite 0–100 metric: distance (50pts) + blink rate (30pts) + consistency (20pts)
- **Progressive Friction** — Two-stage intervention:
  - Stage 1: Subtle red vignette overlay on screen edges (α=0.3)
  - Stage 2: Intensified vignette (α=0.6) + audio ping + desktop notification
  - Auto-clears when posture is corrected
- **Posture Trend** — Live sparkline graph showing distance history
- **20-20-20 Timer** — Desktop notification every 20 minutes to look 20 feet away
- **Ambient Light Warning** — Detects low-light environments from frame brightness
- **Session Summary** — End-of-session popup with duration, avg distance, focus score, safe %, violations
- **System Tray** — Minimises to tray with show/hide/quit context menu
- **Pause/Resume** — `Ctrl+Shift+P` hotkey to pause monitoring
- **Window Position Memory** — Dashboard position saved between sessions via QSettings
- **Privacy-First** — Zero image data written to disk or network. Frames destroyed immediately after landmark extraction.

## Tech Stack

| Library | Purpose |
|---------|---------|
| OpenCV | Webcam capture, frame downscaling (320×240) |
| MediaPipe | 468-point Face Mesh, iris landmarks |
| NumPy | EAR and distance arithmetic |
| PySide6 | Desktop UI (QMainWindow, QPainter overlay, system tray) |
| plyer | Cross-platform desktop notifications |

## Installation

### Prerequisites

- **Python 3.10+** installed on your system
- A webcam (built-in or USB)

### Windows

```powershell
# 1. Clone the repo
git clone <url>
cd DOR

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python main.py
```

**Note**: PySide6 is a large package (~50 MB) — first install may take a few minutes. If you get a build error, install Microsoft Visual C++ Redistributable or use the pre-built `.exe` (see Build section below).

### Linux

```bash
# 1. Clone the repo
git clone <url>
cd DOR

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python main.py
```

**Note on Linux**: The `winsound` module is mocked by `winsound.py` in the project directory for cross-platform compatibility. The friction overlay uses Qt's `WA_TranslucentBackground` — works on X11, may have limitations on Wayland. System tray requires a compatible desktop environment (GNOME users need the [AppIndicator extension](https://extensions.gnome.org/extension/615/appindicator-support/)).

## Build Standalone .exe

```bash
python build.py
```

Output: `dist/DOR.exe` (single file, no Python required).

## Usage

1. **Calibration**: Sit exactly 50 cm from your screen and click "Start Calibration". A 5-second countdown begins, then 10 frames are captured to compute your personal calibration constant.
2. **Monitoring**: The dashboard shows real-time metrics. Minimise to system tray — the app runs in the background.
3. **Intervention**: If you lean too close (<50 cm) or blink too little (<8/min) for 10+ seconds, a red vignette appears. If it continues for another 10 seconds, the vignette intensifies and an audio ping + notification fires.
4. **Controls**:
   - `Ctrl+Shift+P` — Pause/resume monitoring
   - System tray icon — Show/hide, quit

## Project Structure

```
DOR/
├── main.py           # Entry point, main loop, system integration
├── dashboard.py      # GUI (QMainWindow), sparkline, session summary, icon
├── calibration.py    # One-time calibration wizard (QDialog)
├── friction.py       # Transparent overlay (QPainter)
├── focus.py          # FocusScore + SessionTracker
├── camera.py         # Webcam capture, 320×240 downscale
├── distance.py       # Triangle Similarity distance calculation
├── blink.py          # EAR computation + BlinkTracker
├── privacy.py        # Privacy model documentation
├── winsound.py       # Linux mock for winsound
├── build.py          # PyInstaller build script
├── requirements.txt
└── .gitignore
```

## Privacy

DOR operates on a **Stateless Edge-Processing Pipeline**:

1. Pull frame into volatile RAM via `cv2.VideoCapture.read()`
2. Downscale to 320×240
3. Run MediaPipe — extract numerical landmark coordinates only
4. **Destroy the frame immediately** — `frame = None`
5. Act only on the extracted numbers

No image data is ever written to disk, sent over a network, or retained after processing. This is enforced at the architecture level, not by policy.

## License

MIT — free to use, modify, and distribute. See `LICENSE`.
