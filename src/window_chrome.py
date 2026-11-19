"""Barra finestra IZI, ripresa dai controlli di IZI Select."""
import sys
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QApplication, QHBoxLayout, QLabel, QWidget

HEIGHT = 34

class CaptionButton(QAbstractButton):
    def __init__(self, kind):
        super().__init__()
        self.kind = kind
        self.hover = False
        self.setFixedSize(46, HEIGHT)
        self.setFocusPolicy(Qt.NoFocus)

    def set_kind(self, kind):
        self.kind = kind
        self.update()

    def enterEvent(self, event):
        self.hover = True
        self.update()

    def leaveEvent(self, event):
        self.hover = False
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        close = self.kind == "close"
        if self.isDown():
            p.fillRect(self.rect(), QColor("#B8101E" if close else "#3A3A3A"))
        elif self.hover:
            p.fillRect(self.rect(), QColor("#E81123" if close else "#454545"))
        pen = QPen(QColor("#FFFFFF" if close and (self.hover or self.isDown()) else "#C8C8C8"), 1.2)
        pen.setCapStyle(Qt.FlatCap)
        p.setPen(pen)
        cx, cy, size = self.width()/2, self.height()/2, 5
        if self.kind == "min":
            p.drawLine(QPointF(cx-size, cy+0.5), QPointF(cx+size, cy+0.5))
        elif self.kind == "max":
            p.drawRect(QRectF(cx-size, cy-size, 2*size, 2*size))
        elif self.kind == "restore":
            p.drawRect(QRectF(cx-size, cy-size+2, 2*size-2, 2*size-2))
            p.drawPolyline([QPointF(cx-size+2, cy-size+2), QPointF(cx-size+2, cy-size),
                            QPointF(cx+size, cy-size), QPointF(cx+size, cy+size-2),
                            QPointF(cx+size-2, cy+size-2)])
        else:
            p.drawLine(QPointF(cx-size, cy-size), QPointF(cx+size, cy+size))
            p.drawLine(QPointF(cx-size, cy+size), QPointF(cx+size, cy-size))

class MacDot(QAbstractButton):
    COLORS = {"close":"#FF5F57", "min":"#FEBC2E", "max":"#28C840", "restore":"#28C840"}
    def __init__(self, kind):
        super().__init__()
        self.kind = kind
        self.setFixedSize(14,14)
    def set_kind(self, kind):
        self.kind = kind
        self.update()
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(self.COLORS[self.kind]))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(1,1,12,12))

class TitleBar(QWidget):
    about = Signal()
    def __init__(self, title):
        super().__init__()
        self.setObjectName("titleBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(HEIGHT)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0,0,0,0)
        lay.setSpacing(0)
        self.btn_max = None
        if sys.platform == "darwin":
            lay.addSpacing(14)
            for kind in ("close","min","max"):
                button = MacDot(kind)
                button.clicked.connect(self.action(kind))
                if kind == "max":
                    self.btn_max = button
                lay.addWidget(button)
                lay.addSpacing(8)
            lay.addStretch()
        icon = CaptionButton("max")
        icon.setFixedWidth(30)
        icon.setToolTip("About IZI Transfer")
        icon.clicked.connect(self.about.emit)
        lay.addWidget(icon)
        label = QLabel(title)
        label.setObjectName("titleLabel")
        label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lay.addWidget(label)
        lay.addStretch()
        if sys.platform != "darwin":
            for kind in ("min","max","close"):
                button = CaptionButton(kind)
                button.clicked.connect(self.action(kind))
                if kind == "max":
                    self.btn_max = button
                lay.addWidget(button)

    def action(self, kind):
        def run():
            window = self.window()
            if kind == "close":
                window.close()
            elif kind == "min":
                window.showMinimized()
            elif window.isMaximized():
                window.showNormal()
            else:
                window.showMaximized()
            self.sync()
        return run

    def sync(self):
        if self.btn_max:
            self.btn_max.set_kind("restore" if self.window().isMaximized() else "max")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.window().windowHandle():
            self.window().windowHandle().startSystemMove()
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.window().isMaximized():
                self.window().showNormal()
            else:
                self.window().showMaximized()
            self.sync()
