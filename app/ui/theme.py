"""浅色科技风 · Apple Liquid Glass 主题。"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QProxyStyle, QStyle

FONT_FAMILY = '"Microsoft YaHei UI", "PingFang SC", "HarmonyOS Sans SC", "Segoe UI", sans-serif'
MONO_FAMILY = '"Cascadia Mono", "JetBrains Mono", Consolas, monospace'

C = {
    "text": "#161A22",
    "text2": "#5C6675",
    "text3": "#93A0B4",
    "accent": "#2B6CF6",
    "accent2": "#5E5CE6",
    "accent_soft": "rgba(43,108,246,0.14)",
    "glass": "rgba(255,255,255,0.55)",
    "glass2": "rgba(255,255,255,0.34)",
    "glass_strong": "rgba(255,255,255,0.80)",
    "line": "rgba(18,28,48,0.09)",
    "line_light": "rgba(255,255,255,0.70)",
    "ok": "#12A150",
    "warn": "#E08A00",
    "bad": "#E5484D",
    "purple": "#AF52DE",
    "shadow": "rgba(20,32,60,0.20)",
}


def qss(scale: float = 1.0) -> str:
    glass = C["glass"]
    glass2 = C["glass2"]
    strong = C["glass_strong"]
    base_fx = 13 if scale >= 1 else 12

    return f"""
    * {{ font-family: {FONT_FAMILY}; color: {C['text']}; }}
    QWidget {{ background: transparent; }}

    QWidget#appframe {{
        background: {glass};
        border: 1px solid {C['line_light']};
        border-radius: 18px;
    }}
    QWidget#titlebar {{ background: transparent; }}

    /* ---------- 玻璃卡片 ---------- */
    QFrame.card {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(255,255,255,0.62), stop:1 {glass2});
        border: 1px solid {C['line_light']};
        border-radius: 15px;
    }}
    QFrame.card[flat="true"] {{ background: {glass2}; }}

    /* ---------- 文字 ---------- */
    QLabel.h1 {{ font-size: 15px; font-weight: 700; letter-spacing: .3px; }}
    QLabel.h2 {{ font-size: 12px; font-weight: 700; color: {C['text2']}; }}
    QLabel.dim {{ color: {C['text2']}; font-size: 12px; }}
    QLabel.dimmer {{ color: {C['text3']}; font-size: 11px; }}
    QLabel.count {{ color: {C['text3']}; font-size: 11px; font-weight: 600; }}
    QLabel.mono {{ font-family: {MONO_FAMILY}; font-size: 11px; color: {C['text2']}; }}

    /* ---------- 按钮 ---------- */
    QPushButton {{
        background: {strong};
        border: 1px solid {C['line']};
        border-radius: 10px;
        padding: 7px 14px;
        font-size: {base_fx}px;
        color: {C['text']};
    }}
    QPushButton:hover {{ background: rgba(255,255,255,0.92); border-color: rgba(43,108,246,0.35); }}
    QPushButton:pressed {{ background: rgba(235,240,250,0.95); }}
    QPushButton:disabled {{ color: {C['text3']}; background: rgba(255,255,255,0.35); border-color: {C['line']}; }}

    QPushButton.primary {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4C86FF, stop:1 {C['accent']});
        border: 1px solid rgba(30,90,220,0.55);
        color: #FFFFFF; font-weight: 700; font-size: 14px; padding: 10px 22px; border-radius: 12px;
    }}
    QPushButton.primary:hover {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #5C93FF, stop:1 #3477FF); }}
    QPushButton.primary:pressed {{ background: #2560E0; }}
    QPushButton.primary:disabled {{ background: rgba(43,108,246,0.35); color: rgba(255,255,255,0.85); border-color: transparent; }}

    QPushButton.ghost {{ background: rgba(255,255,255,0.45); border: 1px solid {C['line']}; }}
    QPushButton.seg {{ padding: 6px 12px; font-size: 12px; border-radius: 9px; }}
    QPushButton.seg[active="true"] {{
        background: {C['accent_soft']}; border: 1px solid rgba(43,108,246,0.45); color: {C['accent']}; font-weight: 700;
    }}
    QPushButton.small {{ padding: 4px 10px; font-size: 12px; border-radius: 8px; }}

    /* ---------- 输入 ---------- */
    QLineEdit {{
        background: rgba(255,255,255,0.72);
        border: 1px solid {C['line']};
        border-radius: 10px;
        padding: 7px 11px;
        font-size: {base_fx}px;
        selection-background-color: {C['accent_soft']};
    }}
    QLineEdit:focus {{ border: 1px solid rgba(43,108,246,0.55); background: rgba(255,255,255,0.92); }}

    QComboBox {{
        background: rgba(255,255,255,0.72);
        border: 1px solid {C['line']}; border-radius: 10px; padding: 6px 10px; min-height: 20px;
    }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
    QComboBox QAbstractItemView {{
        background: #FFFFFF; border: 1px solid {C['line']}; border-radius: 10px;
        padding: 4px; selection-background-color: {C['accent_soft']};
    }}

    QRadioButton {{ spacing: 7px; font-size: {base_fx}px; }}
    QRadioButton::indicator {{
        width: 18px; height: 18px; border-radius: 9px;
        border: 1.5px solid rgba(20,30,50,0.25); background: rgba(255,255,255,0.85);
    }}
    QRadioButton::indicator:hover {{ border-color: {C['accent']}; }}
    QRadioButton::indicator:checked {{
        border: 1.5px solid {C['accent']};
        background: {C['accent']} url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"white\" stroke-width=\"3\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><polyline points=\"5 13 10 18 19 7\"/></svg>');
        background-position: center; background-repeat: no-repeat; background-size: 12px 12px;
    }}

    /* ---------- 列表 ---------- */
    QListWidget {{
        background: transparent; border: none; font-size: {base_fx}px;
    }}
    QListWidget::item {{ border-radius: 11px; margin: 2px 4px; }}
    QListWidget::item:hover {{ background: rgba(43,108,246,0.07); }}
    QListWidget::item:selected {{ background: {C['accent_soft']}; }}

    /* ---------- 树 ---------- */
    QTreeWidget {{ background: transparent; border: none; font-size: {base_fx}px; }}
    QTreeWidget::item {{ padding: 4px 2px; margin: 0px; }}
    QTreeWidget::item:hover {{ background: rgba(43,108,246,0.06); }}
    QTreeWidget::item:selected {{ background: rgba(43,108,246,0.10); color: {C['text']}; }}
    QTreeWidget::branch {{ background: transparent; }}
    QHeaderView::section {{
        background: transparent; border: none; padding: 4px 6px;
        color: {C['text3']}; font-size: 11px; font-weight: 700;
    }}

    /* ---------- 进度 ---------- */
    QProgressBar {{
        background: rgba(20,30,50,0.08); border: none; border-radius: 5px; height: 9px;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {C['accent2']}, stop:1 {C['accent']});
        border-radius: 5px;
    }}

    /* ---------- 滚动条 ---------- */
    QScrollBar:vertical {{ background: transparent; width: 9px; margin: 3px 1px 3px 1px; }}
    QScrollBar::handle:vertical {{ background: rgba(20,32,60,0.20); border-radius: 5px; min-height: 26px; }}
    QScrollBar::handle:vertical:hover {{ background: rgba(20,32,60,0.34); }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
    QScrollBar:horizontal {{ background: transparent; height: 9px; margin: 1px 3px 1px 3px; }}
    QScrollBar::handle:horizontal {{ background: rgba(20,32,60,0.20); border-radius: 5px; min-width: 26px; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

    /* ---------- 日志 ---------- */
    QPlainTextEdit {{
        background: rgba(255,255,255,0.45); border: 1px solid {C['line']};
        border-radius: 10px; font-family: {MONO_FAMILY}; font-size: 11px; color: {C['text2']};
        padding: 6px;
    }}

    QToolTip {{
        background: rgba(28,34,48,0.92); color: #FFFFFF; border: none;
        padding: 6px 9px; border-radius: 7px; font-size: 12px;
    }}
    """


# ---------------------------------------------------------------- 复选框绘制


class GlassStyle(QProxyStyle):
    """圆角复选框 + 三态指示，风格与 Apple 控件一致。"""

    def __init__(self, base_style: str = "Fusion"):
        super().__init__(base_style)

    def drawPrimitive(self, element, option, painter, widget=None):
        pe = QStyle.PrimitiveElement
        if element in (pe.PE_IndicatorCheckBox, pe.PE_IndicatorItemViewItemCheck):
            self._draw_check(option, painter, widget)
            return
        super().drawPrimitive(element, option, painter, widget)

    def _draw_check(self, option, painter: QPainter, widget=None):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        size = 17
        r = option.rect
        x = r.x() + (r.width() - size) / 2
        y = r.y() + (r.height() - size) / 2 + 0.5
        rect = QRectF(x, y, size, size)

        state = option.state
        checked = bool(state & QStyle.StateFlag.State_On)
        partial = bool(state & QStyle.StateFlag.State_NoChange)
        hover = bool(state & QStyle.StateFlag.State_MouseOver)
        enabled = bool(state & QStyle.StateFlag.State_Enabled)

        path = QPainterPath()
        path.addRoundedRect(rect, 5.0, 5.0)

        if checked or partial:
            grad_color = QColor(C["accent"])
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(grad_color)
            painter.drawPath(path)
            pen = QPen(QColor("#FFFFFF"), 2.0)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            if partial:
                painter.drawLine(QPointF(x + 4.5, y + size / 2), QPointF(x + size - 4.5, y + size / 2))
            else:
                pp = QPainterPath()
                pp.moveTo(x + 4.2, y + size / 2 + 0.2)
                pp.lineTo(x + 7.0, y + size - 4.6)
                pp.lineTo(x + size - 4.2, y + 4.8)
                painter.drawPath(pp)
        else:
            painter.setPen(QPen(QColor(160, 172, 190, 200 if hover else 150), 1.4))
            painter.setBrush(QColor(255, 255, 255, 235 if enabled else 140))
            painter.drawPath(path)
        painter.restore()
