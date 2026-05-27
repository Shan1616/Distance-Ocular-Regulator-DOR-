"""
DOR — Distance & Ocular Regulator
Module: dashboard.py
Privacy: Zero-I/O. No image data is written to disk or network at any point.
"""
from collections import deque

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QIcon, QPainter, QColor, QPen, QPainterPath, QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QFrame, QLabel, QMainWindow,
    QMenu, QProgressBar, QPushButton, QSystemTrayIcon, QVBoxLayout,
    QWidget,
)

from distance import SAFE_DISTANCE_CM
from blink import MIN_BLINK_RATE
from focus import FocusScore


def dor_icon():
    """Generate DOR app icon programmatically — no external image files needed."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#89b4fa"))
    p.drawEllipse(4, 4, 56, 56)
    p.setBrush(QColor("#1e1e2e"))
    p.drawEllipse(10, 10, 44, 44)
    p.setBrush(QColor("#cdd6f4"))
    p.drawEllipse(18, 18, 28, 28)
    p.setBrush(QColor("#89b4fa"))
    p.drawEllipse(26, 26, 12, 12)

    p.end()
    return QIcon(pixmap)


class TrendSparkline(QWidget):
    """Mini line graph showing the last N distance readings."""

    MAX_POINTS = 60
    PADDING = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = deque(maxlen=self.MAX_POINTS)
        self.setFixedHeight(52)
        self.setMinimumWidth(200)

    def add_point(self, value):
        self._data.append(value)
        self.update()

    def paintEvent(self, event):
        if not self._data:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        r = 6

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#181825"))
        p.drawRoundedRect(0, 0, w, h, r, r)

        n = len(self._data)
        max_val = max(max(self._data), SAFE_DISTANCE_CM + 20)
        pl = self.PADDING
        pw = w - pl * 2

        safe_line_y = int(h - (SAFE_DISTANCE_CM / max_val) * (h - pl * 2) - pl)
        pen_dash = QPen(QColor("#585b70"), 1, Qt.PenStyle.DashLine)
        p.setPen(pen_dash)
        p.drawLine(pl, safe_line_y, pl + pw, safe_line_y)

        pen_line = QPen(QColor("#89b4fa"), 2)
        pen_line.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen_line.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen_line)

        path = QPainterPath()
        for i, val in enumerate(self._data):
            x = pl + (i / max(n - 1, 1)) * pw
            y = h - (val / max_val) * (h - pl * 2) - pl
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)

        p.drawPath(path)

        p.setPen(QColor("#6c7086"))
        p.setFont(QFont("Segoe UI", 7))
        p.drawText(pl, h - 2, f"Trend ({n} samples)")


class SessionSummaryDialog(QDialog):
    """End-of-session stats popup."""

    def __init__(self, summary, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DOR Session Summary")
        self.setFixedSize(380, 280)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setObjectName("summaryDialog")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Session Summary")
        title.setObjectName("summaryTitle")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        if summary is None:
            layout.addWidget(QLabel("No data recorded."), alignment=Qt.AlignmentFlag.AlignCenter)
        else:
            h, m, s = summary["duration_sec"] // 3600, (summary["duration_sec"] % 3600) // 60, summary["duration_sec"] % 60
            stats = [
                f"Duration:      {h:02d}:{m:02d}:{s:02d}",
                f"Avg Distance:   {summary['avg_distance_cm']:.0f} cm",
                f"Avg Blink Rate: {summary['avg_blink_rate']:.1f} /min",
                f"Focus Score:    {summary['avg_focus']:.0f}/100",
                f"Safe Time:      {summary['safe_pct']:.0f}%",
                f"Violations:     {summary['violations']}",
            ]
            for s in stats:
                label = QLabel(s)
                label.setObjectName("summaryStat")
                layout.addWidget(label)

        btn = QPushButton("OK")
        btn.setObjectName("summaryBtn")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setStyleSheet("""
            #summaryDialog { background: #1e1e2e; }
            #summaryTitle {
                color: #89b4fa; font-size: 16px; font-weight: bold;
                padding-bottom: 12px;
            }
            #summaryStat {
                color: #cdd6f4; font-size: 12px;
                padding: 2px 20px;
            }
            #summaryBtn {
                background: #89b4fa; color: #11111b;
                font-size: 12px; font-weight: bold;
                border: none; border-radius: 6px;
                padding: 8px 24px; margin-top: 12px;
            }
            #summaryBtn:hover { background: #74c7ec; }
        """)


class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DOR Monitor")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Title ---
        title = QLabel("DOR Monitor")
        title.setObjectName("title")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Distance & Ocular Regulator")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignCenter)

        # --- Focus Score Ring ---
        self.focus_label = QLabel("--")
        self.focus_label.setObjectName("focusScore")
        self.focus_grade = QLabel("")
        self.focus_grade.setObjectName("focusGrade")
        focus_frame = QFrame()
        focus_frame.setObjectName("focusFrame")
        f_layout = QVBoxLayout(focus_frame)
        f_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f_layout.addWidget(self.focus_label)
        f_layout.addWidget(self.focus_grade)
        layout.addWidget(focus_frame)

        # --- Card ---
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(6)

        self.dist_label = QLabel("Distance: -- cm")
        self.dist_label.setObjectName("metric")
        card_layout.addWidget(self.dist_label)
        self.dist_bar = QProgressBar()
        self.dist_bar.setRange(0, 100)
        self.dist_bar.setValue(0)
        self.dist_bar.setTextVisible(False)
        self.dist_bar.setFixedHeight(5)
        card_layout.addWidget(self.dist_bar)

        self.blink_label = QLabel("Blinks: -- /min")
        self.blink_label.setObjectName("metric")
        card_layout.addWidget(self.blink_label)
        self.blink_bar = QProgressBar()
        self.blink_bar.setRange(0, 100)
        self.blink_bar.setValue(0)
        self.blink_bar.setTextVisible(False)
        self.blink_bar.setFixedHeight(5)
        card_layout.addWidget(self.blink_bar)

        layout.addWidget(card)

        # --- Sparkline ---
        self.sparkline = TrendSparkline()
        layout.addWidget(self.sparkline, alignment=Qt.AlignmentFlag.AlignCenter)

        # --- Info row ---
        info = QHBoxLayout()
        info.setContentsMargins(14, 2, 14, 2)
        self.session_label = QLabel("Session: 00:00:00")
        self.session_label.setObjectName("info")
        self.violations_label = QLabel("Flags: 0")
        self.violations_label.setObjectName("info")
        self.light_label = QLabel("")
        self.light_label.setObjectName("info")
        info.addWidget(self.session_label)
        info.addStretch()
        info.addWidget(self.light_label)
        info.addStretch()
        info.addWidget(self.violations_label)
        layout.addLayout(info)

        # --- Break timer ---
        self.break_label = QLabel("")
        self.break_label.setObjectName("breakLabel")
        layout.addWidget(self.break_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # --- Status ---
        self.status_label = QLabel("Status: Monitoring...")
        self.status_label.setObjectName("status")
        layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # --- Icon ---
        icon = dor_icon()
        self.setWindowIcon(icon)

        # --- System tray ---
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(icon)
        tray_menu = QMenu()
        tray_menu.addAction("Show / Hide", self.toggle_visible)
        tray_menu.addSeparator()
        qa = tray_menu.addAction("Quit")
        qa.triggered.connect(self._quit)
        self.tray.setContextMenu(tray_menu)
        self.tray.show()
        self.tray.activated.connect(self._on_tray_activated)

        # --- Window geometry ---
        self.setFixedSize(420, 360)
        self._load_geometry()

        self._green = "#a6e3a1"
        self._red = "#f38ba8"
        self._apply_styles()

    def toggle_visible(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def _load_geometry(self):
        settings = QSettings("DOR", "DOR")
        geom = settings.value("dashboard_geometry")
        if geom:
            self.restoreGeometry(geom)

    def save_geometry(self):
        settings = QSettings("DOR", "DOR")
        settings.setValue("dashboard_geometry", self.saveGeometry())

    def closeEvent(self, event):
        self.save_geometry()
        event.accept()

    def _apply_styles(self):
        self.setStyleSheet("""
            #central { background: #1e1e2e; }
            #title {
                color: #89b4fa; font-size: 16px; font-weight: bold;
                padding-top: 8px; padding-bottom: 0px;
            }
            #subtitle {
                color: #6c7086; font-size: 8px; padding-bottom: 4px;
            }
            #focusFrame {
                background: #181825; border-radius: 8px;
                padding: 6px; margin: 0 80px;
            }
            #focusScore {
                color: #a6e3a1; font-size: 28px; font-weight: bold;
                qproperty-alignment: AlignCenter;
            }
            #focusGrade {
                color: #6c7086; font-size: 10px;
                qproperty-alignment: AlignCenter;
            }
            #card {
                background: #181825; border-radius: 8px;
                padding: 10px 14px; margin: 6px 10px 0 10px;
            }
            #metric {
                color: #cdd6f4; font-size: 12px; font-weight: bold; padding: 0;
            }
            QProgressBar {
                background: #313244; border: none; border-radius: 3px;
                min-height: 5px; max-height: 5px;
            }
            QProgressBar::chunk { border-radius: 3px; }
            #info {
                color: #6c7086; font-size: 9px;
            }
            #breakLabel {
                color: #6c7086; font-size: 9px; padding: 0;
            }
            #status {
                color: #6c7086; font-size: 10px; font-weight: bold;
                padding-bottom: 6px;
            }
        """)

    def _bar_style(self, color):
        return (
            "QProgressBar { background: #313244; border: none; border-radius: 3px;"
            " min-height: 5px; max-height: 5px; }"
            f"QProgressBar::chunk {{ background: {color}; border-radius: 3px; }}"
        )

    def update_metrics(self, distance_cm, is_dist_safe, blink_rate,
                       is_blink_safe, session_str, violations=0,
                       focus_score=None, sparkline_val=None):
        d_color = self._green if is_dist_safe else self._red
        b_color = self._green if is_blink_safe else self._red

        self.dist_label.setText(f"Distance: {distance_cm:.0f} cm")
        self.dist_label.setStyleSheet(
            f"#metric {{ color: {d_color}; font-size: 12px; font-weight: bold; padding: 0; }}"
        )
        dist_pct = min(int((distance_cm / SAFE_DISTANCE_CM) * 100), 100) if distance_cm > 0 else 0
        self.dist_bar.setStyleSheet(self._bar_style(d_color))
        self.dist_bar.setValue(dist_pct)

        self.blink_label.setText(f"Blinks: {blink_rate:.0f} /min")
        self.blink_label.setStyleSheet(
            f"#metric {{ color: {b_color}; font-size: 12px; font-weight: bold; padding: 0; }}"
        )
        blink_pct = min(int((blink_rate / MIN_BLINK_RATE) * 100), 100) if blink_rate > 0 else 0
        self.blink_bar.setStyleSheet(self._bar_style(b_color))
        self.blink_bar.setValue(blink_pct)

        if focus_score is not None:
            _, grade_color = FocusScore.grade(focus_score)
            self.focus_label.setText(str(focus_score))
            grade_text, _ = FocusScore.grade(focus_score)
            self.focus_label.setStyleSheet(
                f"#focusScore {{ color: {grade_color}; font-size: 28px; font-weight: bold; qproperty-alignment: AlignCenter; }}"
            )
            self.focus_grade.setText(grade_text)
            self.focus_grade.setStyleSheet(
                f"#focusGrade {{ color: {grade_color}; font-size: 10px; qproperty-alignment: AlignCenter; }}"
            )

        if sparkline_val is not None:
            self.sparkline.add_point(sparkline_val)

        self.session_label.setText(f"Session: {session_str}")
        self.violations_label.setText(f"Flags: {violations}")

    def set_status(self, text, is_warning):
        color = self._red if is_warning else "#6c7086"
        self.status_label.setText(f"Status: {text}")
        self.status_label.setStyleSheet(
            f"#status {{ color: {color}; font-size: 10px; font-weight: bold; padding-bottom: 6px; }}"
        )

    def set_light_warning(self, is_dark):
        if is_dark:
            self.light_label.setText("💡 Low light")
            self.light_label.setStyleSheet("#info { color: #f38ba8; font-size: 9px; }")
        else:
            self.light_label.setText("")
            self.light_label.setStyleSheet("#info { color: #6c7086; font-size: 9px; }")

    def set_break_label(self, text):
        self.break_label.setText(text)

    def _on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.toggle_visible()

    def _quit(self):
        QApplication.quit()
