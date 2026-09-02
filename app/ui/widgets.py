"""自定义控件：文件列表（缩略图+双行信息）与元数据勾选树。"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetrics, QImageReader, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (QAbstractButton, QDialog, QDialogButtonBox, QHBoxLayout,
                               QLabel, QListWidget, QPushButton, QStyle, QStyledItemDelegate,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .theme import C, qss

THUMB = 46


def load_thumb(path: str, size: int = THUMB) -> QPixmap:
    try:
        reader = QImageReader(path)
        reader.setAutoTransform(True)
        reader.setScaledSize(QSize(size * 2, size * 2))
        img = reader.read()
        if img.isNull():
            return QPixmap()
        pm = QPixmap.fromImage(img)
        return pm.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    except Exception:
        return QPixmap()


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} GB"


def rounded_pixmap(pm: QPixmap, radius: int = 8) -> QPixmap:
    if pm.isNull():
        return pm
    out = QPixmap(pm.size())
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing, True)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, pm.width(), pm.height()), radius, radius)
    p.setClipPath(path)
    p.drawPixmap(0, 0, pm)
    p.end()
    return out


# ---------------------------------------------------------------- 文件列表


class FileDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def sizeHint(self, option, index) -> QSize:
        return QSize(200, 58)

    def paint(self, painter: QPainter, option, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = option.rect.adjusted(4, 2, -4, -2)
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 11, 11)

        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillPath(path, QBrush(QColor(43, 108, 246, 26)))
            painter.setPen(QPen(QColor(43, 108, 246, 70), 1))
            painter.drawPath(path)
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillPath(path, QBrush(QColor(20, 32, 60, 12)))

        pm = index.data(Qt.DecorationRole)
        if isinstance(pm, QPixmap) and not pm.isNull():
            x = rect.x() + 8
            y = rect.y() + (rect.height() - pm.height()) // 2
            painter.drawPixmap(x, y, pm)
            tx = x + THUMB + 10
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 200))
            painter.drawRoundedRect(QRectF(rect.x() + 8, rect.y() + 6, THUMB, THUMB), 8, 8)
            tx = rect.x() + 8 + THUMB + 10

        avail = rect.right() - tx - 12
        fm = QFontMetrics(option.font)

        name = index.data(Qt.DisplayRole) or ""
        bold = QFont(option.font)
        bold.setWeight(QFont.Weight.DemiBold)
        painter.setFont(bold)
        painter.setPen(QColor(C["text"]))
        painter.drawText(QRect(tx, rect.y() + 10, avail, 18), Qt.TextFlag.TextSingleLine,
                         fm.elidedText(name, Qt.TextElideMode.ElideMiddle, avail))

        painter.setFont(option.font)
        painter.setPen(QColor(C["text2"]))
        sub = index.data(Qt.UserRole + 2) or ""
        painter.drawText(QRect(tx, rect.y() + 29, avail, 16), Qt.TextFlag.TextSingleLine,
                         QFontMetrics(option.font).elidedText(sub, Qt.TextElideMode.ElideRight, avail))

        status = index.data(Qt.UserRole + 3) or ""
        if status:
            color = {"ok": C["ok"], "done": C["accent"], "bad": C["bad"], "warn": C["warn"]}.get(status, C["text3"])
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(color))
            painter.drawEllipse(QRectF(rect.right() - 14, rect.y() + rect.height() / 2 - 3.5, 7, 7))
        painter.restore()


class FileList(QListWidget):
    filesDropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegate(FileDelegate(self))
        self.setSpacing(1)
        self.setUniformItemSizes(False)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.setDragDropMode(QListWidget.DragDropMode.NoDragDrop)
        self.setIconSize(QSize(THUMB, THUMB))
        self.setMouseTracking(True)


# ---------------------------------------------------------------- 元数据树


@dataclass
class AggItem:
    key: str
    label: str
    value: str
    category: str
    default_remove: bool
    note: str = ""
    hits: int = 0
    multi: bool = False


class MetaTree(QTreeWidget):
    """分组 + 三态勾选的元数据树。勾选 = 移除。"""

    selectionChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["项目", "值", "命中"])
        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(False)
        self.setIndentation(16)
        self.setAnimated(True)
        self.setUniformRowHeights(False)
        self.setVerticalScrollMode(QTreeWidget.ScrollMode.ScrollPerPixel)
        self.setMouseTracking(True)
        self.setExpandsOnDoubleClick(False)
        self.header().setStretchLastSection(False)
        self._block = False
        self.itemChanged.connect(self._on_item_changed)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

    # ---- 构建
    def load(self, groups: list[tuple], selected: dict[str, bool], total_files: int):
        """groups: (分类key, 分类名, 说明, 颜色, 条目列表, 是否锁定)"""
        self._block = True
        self.clear()
        self._total = total_files
        for cat_key, cat_label, cat_hint, cat_color, items, locked in groups:
            if not items:
                continue
            parent = QTreeWidgetItem(self, [cat_label, cat_hint, f"{len(items)}"])
            if not locked:
                parent.setFlags(parent.flags() | Qt.ItemFlag.ItemIsUserCheckable
                                | Qt.ItemFlag.ItemIsAutoTristate)
            parent.setData(0, Qt.ItemDataRole.UserRole, ("__cat__", cat_key))
            f = parent.font(0)
            f.setWeight(QFont.Weight.DemiBold)
            parent.setFont(0, f)
            parent.setForeground(0, QColor(cat_color))
            parent.setForeground(2, QColor(C["text3"]))
            for it in items:
                child = QTreeWidgetItem(parent, [it.label, it.value, f"{it.hits}/{total_files}"])
                if not locked:
                    child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    child.setCheckState(
                        0, Qt.CheckState.Checked if selected.get(it.key, it.default_remove)
                        else Qt.CheckState.Unchecked)
                child.setData(0, Qt.ItemDataRole.UserRole, ("__item__", it.key))
                child.setForeground(1, QColor(C["text2"]))
                child.setForeground(2, QColor(C["text3"]))
                child.setToolTip(0, f"{it.label}\n{it.value}" + (f"\n\n{it.note}" if it.note else ""))
                child.setToolTip(1, it.value)
                if it.note:
                    child.setForeground(0, QColor(C["warn"]))
            parent.setExpanded(True)
            if not locked:
                self._sync_parent(parent)
        self.resize_columns()
        self._block = False

    def resize_columns(self):
        w = self.width()
        if w <= 0:
            return
        hits_w = 0 if w < 780 else 62
        name_w = max(190, int(w * 0.40)) if w >= 900 else max(150, int(w * 0.55))
        self.setColumnWidth(0, name_w)
        self.setColumnWidth(2, hits_w)
        self.setColumnHidden(2, hits_w == 0)
        self.setColumnHidden(1, w < 640)
        if not self.isColumnHidden(1):
            self.setColumnWidth(1, max(120, w - name_w - hits_w - 30))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resize_columns()

    # ---- 勾选联动
    def _sync_parent(self, parent: QTreeWidgetItem):
        self._block = True
        states = [parent.child(i).checkState(0) for i in range(parent.childCount())]
        if not states:
            parent.setCheckState(0, Qt.CheckState.Unchecked)
        elif all(s == Qt.CheckState.Checked for s in states):
            parent.setCheckState(0, Qt.CheckState.Checked)
        elif any(s == Qt.CheckState.Checked for s in states):
            parent.setCheckState(0, Qt.CheckState.PartiallyChecked)
        else:
            parent.setCheckState(0, Qt.CheckState.Unchecked)
        self._block = False

    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        if self._block or column != 0:
            return
        role = item.data(0, Qt.ItemDataRole.UserRole)
        if not role:
            return
        kind, key = role
        if kind == "__cat__":
            state = item.checkState(0)
            if state == Qt.CheckState.PartiallyChecked:
                state = Qt.CheckState.Checked
            self._block = True
            item.setCheckState(0, state)
            for i in range(item.childCount()):
                item.child(i).setCheckState(0, state)
            self._block = False
        else:
            parent = item.parent()
            if parent is not None:
                self._sync_parent(parent)
        self.selectionChanged.emit()

    # ---- 查询
    def _iter_items(self):
        """遍历可勾选的条目（跳过锁定的图像数据）。"""
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            cat = root.child(i)
            for j in range(cat.childCount()):
                child = cat.child(j)
                if child.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                    yield cat, child

    def collect(self) -> dict[str, bool]:
        out: dict[str, bool] = {}
        for _cat, child in self._iter_items():
            role = child.data(0, Qt.ItemDataRole.UserRole)
            if role and role[0] == "__item__":
                out[role[1]] = child.checkState(0) == Qt.CheckState.Checked
        return out

    def set_all(self, value: bool, categories: set[str] | None = None):
        self._block = True
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            cat = root.child(i)
            _, key = cat.data(0, Qt.ItemDataRole.UserRole)
            v = value if categories is None else (key in categories)
            for j in range(cat.childCount()):
                cat.child(j).setCheckState(0, Qt.CheckState.Checked if v else Qt.CheckState.Unchecked)
            self._sync_parent(cat)
        self._block = False
        self.selectionChanged.emit()

    def apply_defaults(self, defaults: dict[str, bool]):
        self._block = True
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            cat = root.child(i)
            for j in range(cat.childCount()):
                child = cat.child(j)
                key = child.data(0, Qt.ItemDataRole.UserRole)[1]
                child.setCheckState(0, Qt.CheckState.Checked if defaults.get(key, False) else Qt.CheckState.Unchecked)
            self._sync_parent(cat)
        self._block = False
        self.selectionChanged.emit()

    def filter_rows(self, text: str):
        root = self.invisibleRootItem()
        t = text.strip().lower()
        for i in range(root.childCount()):
            cat = root.child(i)
            shown = 0
            for j in range(cat.childCount()):
                child = cat.child(j)
                match = not t or any(
                    t in (child.text(c) or "").lower() for c in range(self.columnCount())
                ) or t in (child.toolTip(0) or "").lower()
                child.setHidden(not match)
                shown += 1 if match else 0
            cat.setHidden(shown == 0 and bool(t))
            cat.setExpanded(bool(t))


# ---------------------------------------------------------------- 玻璃风格弹窗


class GlassDialog(QDialog):
    """与主界面风格一致的浅色玻璃弹窗。"""

    def __init__(self, parent=None, title: str = "", body: str = "", icon: str = "none",
                 buttons: list[tuple[str, str]] | None = None, scale: float = 1.0):
        """buttons: [(key, label), ...] 默认 [('ok', OK)]；icon: none/info/warn/error。"""
        super().__init__(parent)
        self._result_key: str | None = None
        self._scale = scale
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(qss(scale))
        self._build(title, body, icon, buttons or [("ok", "OK")])

    def _build(self, title: str, body: str, icon: str, buttons: list[tuple[str, str]]):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        frame = QWidget(objectName="appframe")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(22, 18, 22, 18)
        fl.setSpacing(12)

        head = QHBoxLayout()
        icon_lbl = QLabel(self._icon_text(icon))
        icon_lbl.setStyleSheet(f"font-size: 28px; color: {C['text3']};")
        if icon != "none":
            head.addWidget(icon_lbl)
        title_lbl = QLabel(title)
        title_lbl.setProperty("class", "h1")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700;")
        head.addWidget(title_lbl)
        head.addStretch(1)
        fl.addLayout(head)

        body_lbl = QLabel(body)
        body_lbl.setProperty("class", "dim")
        body_lbl.setWordWrap(True)
        body_lbl.setTextFormat(Qt.TextFormat.PlainText)
        fl.addWidget(body_lbl)
        self._body = body_lbl

        btn_box = QHBoxLayout()
        btn_box.addStretch(1)
        self._btns: dict[str, QPushButton] = {}
        for key, label in buttons:
            b = QPushButton(label)
            b.setProperty("class", "small")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            if key == "ok" or key == "yes":
                b.setProperty("class", "primary")
                b.setMinimumWidth(72)
            b.clicked.connect(lambda _=False, k=key: self._on_btn(k))
            self._btns[key] = b
            btn_box.addWidget(b)
        fl.addLayout(btn_box)
        outer.addWidget(frame)

        self.setFixedWidth(int(420 * self._scale))

    def _icon_text(self, icon: str) -> str:
        return {"warn": "⚠", "error": "✕", "info": "ℹ"}.get(icon, "")

    def _on_btn(self, key: str):
        self._result_key = key
        self.accept() if key in ("ok", "yes") else self.reject()

    def result_key(self) -> str | None:
        return self._result_key

    @classmethod
    def ask(cls, parent, title: str, body: str, yes: str = "Yes", no: str = "No",
            icon: str = "warn", scale: float = 1.0) -> bool:
        d = cls(parent, title, body, icon, [("no", no), ("yes", yes)], scale)
        d.exec()
        return d.result_key() == "yes"

    @classmethod
    def info(cls, parent, title: str, body: str, scale: float = 1.0):
        d = cls(parent, title, body, "info", [("ok", "OK")], scale)
        d.exec()

    @classmethod
    def warn(cls, parent, title: str, body: str, scale: float = 1.0):
        d = cls(parent, title, body, "warn", [("ok", "OK")], scale)
        d.exec()
