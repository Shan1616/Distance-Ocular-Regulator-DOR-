"""
DOR — Distance & Ocular Regulator
Module: friction.py
Privacy: Zero-I/O. No image data is written to disk or network at any point.
"""
import threading
import winsound

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QApplication, QWidget

STAGE1_DELAY_SEC = 10


class FrictionOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_X11NetWmWindowTypeDesktop)

        self._opacity = 0.0
        self._has_pinged = False
        self._has_notified = False

        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.virtualGeometry())
        self.hide()

    def paintEvent(self, event):
        if self._opacity <= 0:
            return

        painter = QPainter(self)
        painter.setOpacity(self._opacity)
        painter.setBrush(QColor(255, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)

        w = self.width()
        h = self.height()
        border = 50

        painter.drawRect(0, 0, w, border)
        painter.drawRect(0, h - border, w, border)
        painter.drawRect(0, 0, border, h)
        painter.drawRect(w - border, 0, border, h)

    def _notify(self):
        try:
            from plyer import notification
            notification.notify(
                title="DOR — Force Intervention",
                message="Please sit back or blink to maintain healthy posture.",
                timeout=5,
            )
        except ImportError:
            pass

    def apply_stage1(self):
        self._opacity = 0.3
        self.showFullScreen()
        self.update()
        self._has_pinged = False
        self._has_notified = False

    def apply_stage2(self):
        self._opacity = 0.6
        if not self.isVisible():
            self.showFullScreen()
        self.update()

        if not self._has_pinged:
            threading.Thread(
                target=lambda: winsound.Beep(1000, 200), daemon=True
            ).start()
            self._has_pinged = True

        if not self._has_notified:
            threading.Thread(target=self._notify, daemon=True).start()
            self._has_notified = True

    def clear(self):
        self._opacity = 0.0
        self._has_pinged = False
        self._has_notified = False
        self.hide()
        self.update()
