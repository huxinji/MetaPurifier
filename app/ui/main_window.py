"""主窗口：Apple Liquid Glass 风格的无损元数据清理器。"""

from __future__ import annotations

import os

from PySide6.QtCore import (QEvent, QPoint, QRect, QRectF, QSize, Qt, QThread, Signal,
                            QTimer)
from PySide6.QtGui import (QColor, QFont, QGuiApplication, QIcon, QPainter, QPainterPath,
                           QPixmap)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QComboBox,
                               QDialog, QDialogButtonBox, QFileDialog, QFrame, QGraphicsDropShadowEffect,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
                               QPlainTextEdit, QProgressBar, QPushButton, QRadioButton,
                               QSizePolicy, QSplitter, QVBoxLayout, QWidget)

from ..core import cleaner, formats, scanner
from ..core.cleaner import CleanResult, Plan
from . import effects
from .i18n import current_lang, set_lang, t
from .theme import C, GlassStyle, qss
from .widgets import AggItem, FileList, GlassDialog, MetaTree, THUMB, human_size, load_thumb, rounded_pixmap

EXTS = {".jpg", ".jpeg", ".jpe", ".png", ".webp", ".tif", ".tiff"}
CAPTION_H = 46


# ---------------------------------------------------------------- 线程

class ScanWorker(QThread):
    sig_file = Signal(object)
    sig_done = Signal(int, int)

    def __init__(self, paths: list[str]):
        super().__init__()
        self.paths = paths

    def run(self):
        ok = 0
        for p in self.paths:
            fs = scanner.scan_file(p)
            fs.parsed = None  # 释放整份字节，处理时重新解析
            if fs.ok:
                ok += 1
            self.sig_file.emit(fs)
        self.sig_done.emit(ok, len(self.paths))


class CleanWorker(QThread):
    sig_progress = Signal(int, int, str)
    sig_done = Signal(object)

    def __init__(self, paths, plan: Plan, mode: str, dest: str, suffix: str,
                 backup: bool, backup_dir: str):
        super().__init__()
        self.paths = paths
        self.plan = plan
        self.mode = mode
        self.dest = dest
        self.suffix = suffix
        self.backup = backup
        self.backup_dir = backup_dir
        self.results: list[CleanResult] = []

    def run(self):
        total = len(self.paths)
        for i, path in enumerate(self.paths, 1):
            name = os.path.basename(path)
            self.sig_progress.emit(i, total, t("progress_fmt", name))
            res = CleanResult(src=path)
            try:
                with open(path, "rb") as fh:
                    data = fh.read()
                p = formats.parse(data)
                if p.fmt not in formats.SUPPORTED:
                    raise RuntimeError(t("err_unsupported_fmt", p.fmt))
                out, res = cleaner.apply_plan(data, p, self.plan)
                res.src = path
                if not res.payload_ok:
                    res.error = t("err_payload_mismatch")
                    res.ok = False
                else:
                    dst, tip = cleaner.write_output(
                        out, path, self.mode, self.dest, self.suffix, self.backup, self.backup_dir)
                    res.dst = dst
                    res.ok = True
                    res.note = (res.note + "；" if res.note else "") + tip
            except Exception as exc:
                res.ok = False
                res.error = str(exc)
            self.results.append(res)
        self.sig_done.emit(self.results)


# ---------------------------------------------------------------- 小控件


class TrafficButton(QPushButton):
    def __init__(self, color: str, hover: str, tip: str = ""):
        super().__init__()
        self.setFixedSize(13, 13)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tip)
        self.setStyleSheet(f"""
            QPushButton {{ background: {color}; border: none; border-radius: 6px; }}
            QPushButton:hover {{ background: {hover}; }}
        """)


class ChipLabel(QLabel):
    def __init__(self, text: str, color: str = C["accent"]):
        super().__init__(text)
        self.setStyleSheet(f"""
            QLabel {{ background: {color}22; color: {color}; border-radius: 7px;
                      padding: 2px 8px; font-size: 11px; font-weight: 700; }}
        """)


class LangButton(QPushButton):
    """语言切换按钮，当前语言高亮。"""

    def __init__(self, lang_code: str, label: str):
        super().__init__(label)
        self.lang_code = lang_code
        self.setProperty("class", "seg")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


# ---------------------------------------------------------------- 主窗口


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.scans: dict[str, scanner.FileScan] = {}
        self.agg: dict[str, AggItem] = {}
        self.selection: dict[str, bool] = {}
        self.worker: QThread | None = None
        self._dest_dir = ""

        scr = QGuiApplication.primaryScreen()
        self._scale = max(0.85, min(1.6, scr.logicalDotsPerInch() / 96.0))

        self.setWindowTitle(t("app_title"))
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)

        self._build_ui()
        self._init_geometry()
        QTimer.singleShot(0, self._apply_glass)

    # ------------------------------------------------------------ 界面搭建
    def _build_ui(self):
        root = QVBoxLayout(self)
        s = int(14 * self._scale)
        root.setContentsMargins(s, s, s, s)
        root.setSpacing(0)

        frame = QWidget(objectName="appframe")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(0)
        fl.addWidget(self._make_titlebar())

        body = QWidget()
        bl = QHBoxLayout(body)
        bl.setContentsMargins(14, 4, 14, 14)
        bl.setSpacing(12)
        bl.addWidget(self._make_left())
        bl.addWidget(self._make_right(), 1)
        fl.addWidget(body, 1)
        root.addWidget(frame)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(38)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(20, 34, 64, 110))
        frame.setGraphicsEffect(shadow)

        self.setStyleSheet(qss(self._scale))

    def _make_titlebar(self) -> QWidget:
        bar = QWidget(objectName="titlebar")
        bar.setFixedHeight(CAPTION_H)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(18, 0, 16, 0)
        lay.setSpacing(9)

        self.btn_close = TrafficButton("#FF5F57", "#FF3B30", t("close"))
        self.btn_min = TrafficButton("#FEBC2E", "#F5A623", t("minimize"))
        self.btn_max = TrafficButton("#28C840", "#1DAF35", t("maximize"))
        self.btn_close.clicked.connect(self.close)
        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_max.clicked.connect(self._toggle_max)
        for b in (self.btn_close, self.btn_min, self.btn_max):
            lay.addWidget(b)
        lay.addSpacing(12)

        self.title_lbl = QLabel(t("title"))
        self.title_lbl.setObjectName("t")
        self.title_lbl.setProperty("class", "h1")
        self.title_lbl.setStyleSheet("font-size: 14px; font-weight: 700;")
        lay.addWidget(self.title_lbl)
        self.chip_subtitle = ChipLabel(t("subtitle"))
        lay.addWidget(self.chip_subtitle)
        lay.addStretch(1)

        self.btn_lang_zh = LangButton("zh", t("lang_zh"))
        self.btn_lang_en = LangButton("en", t("lang_en"))
        self.btn_lang_zh.clicked.connect(lambda: self._change_lang("zh"))
        self.btn_lang_en.clicked.connect(lambda: self._change_lang("en"))
        lay.addWidget(self.btn_lang_zh)
        lay.addWidget(self.btn_lang_en)

        self.btn_about = QPushButton(t("about"))
        self.btn_about.setProperty("class", "seg")
        self.btn_about.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_about.clicked.connect(self._about)
        lay.addWidget(self.btn_about)
        self._sync_lang_buttons()
        return bar

    def _make_left(self) -> QWidget:
        card = QFrame(objectName="c1", )
        card.setProperty("class", "card")
        card.setMinimumWidth(int(250 * self._scale))
        card.setMaximumWidth(int(400 * self._scale))
        lay = QVBoxLayout(card)
        lay.setContentsMargins(13, 12, 13, 12)
        lay.setSpacing(9)

        head = QHBoxLayout()
        self.lbl_images_title = QLabel(t("panel_images"))
        self.lbl_images_title.setProperty("class", "h1")
        self.lbl_count = QLabel(t("count_fmt", 0))
        self.lbl_count.setProperty("class", "count")
        head.addWidget(self.lbl_images_title)
        head.addWidget(self.lbl_count)
        head.addStretch(1)
        lay.addLayout(head)

        row = QHBoxLayout()
        row.setSpacing(6)
        self.btn_add_images = QPushButton(t("add_images"))
        self.btn_add_folder = QPushButton(t("add_folder"))
        self.btn_clear = QPushButton(t("clear"))
        for b in (self.btn_add_images, self.btn_add_folder, self.btn_clear):
            b.setProperty("class", "small")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            row.addWidget(b)
        self.btn_add_images.clicked.connect(self._pick_files)
        self.btn_add_folder.clicked.connect(self._pick_folder)
        self.btn_clear.clicked.connect(self._clear_files)
        lay.addLayout(row)

        self.list = FileList()
        self.list.itemSelectionChanged.connect(self._on_select_file)
        lay.addWidget(self.list, 1)

        self.lbl_drop_tip = QLabel(t("drop_tip"))
        self.lbl_drop_tip.setProperty("class", "dimmer")
        self.lbl_drop_tip.setWordWrap(True)
        lay.addWidget(self.lbl_drop_tip)
        return card

    def _make_right(self) -> QWidget:
        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        # ---- 元数据卡片
        meta = QFrame()
        meta.setProperty("class", "card")
        ml = QVBoxLayout(meta)
        ml.setContentsMargins(13, 11, 13, 11)
        ml.setSpacing(9)

        head = QHBoxLayout()
        self.lbl_meta_title = QLabel(t("panel_meta"))
        self.lbl_meta_title.setProperty("class", "h1")
        self.lbl_meta = QLabel(t("meta_not_imported"))
        self.lbl_meta.setProperty("class", "dim")
        head.addWidget(self.lbl_meta_title)
        head.addWidget(self.lbl_meta)
        head.addStretch(1)
        self.search = QLineEdit()
        self.search.setPlaceholderText(t("search_placeholder"))
        self.search.setFixedWidth(int(190 * self._scale))
        self.search.textChanged.connect(self._filter)
        head.addWidget(self.search)
        ml.addLayout(head)

        prow = QHBoxLayout()
        prow.setSpacing(6)
        self.preset_defs: list[tuple[str, set[str] | None]] = [
            ("preset_recommended", None),
            ("preset_remove_all", {"ai", "gps", "time", "device", "software", "desc", "author",
                          "thumb", "xmp", "iptc", "comment", "shoot", "other", "unknown"}),
            ("preset_privacy", {"ai", "gps", "time", "device", "software", "thumb"}),
            ("preset_keep_all", set()),
        ]
        self.preset_btns: list[QPushButton] = []
        for key, cats in self.preset_defs:
            b = QPushButton(t(key))
            b.setProperty("class", "seg")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, c=cats, k=key: self._preset(c, k))
            prow.addWidget(b)
            self.preset_btns.append(b)
        prow.addStretch(1)
        self.lbl_remove = QLabel("")
        self.lbl_remove.setProperty("class", "dim")
        prow.addWidget(self.lbl_remove)
        ml.addLayout(prow)

        self.tree = MetaTree()
        self.tree.setHeaderLabels([t("tree_col_item"), t("tree_col_value"), t("tree_col_hits")])
        self.tree.selectionChanged.connect(self._update_stats)
        ml.addWidget(self.tree, 1)

        self.lbl_meta_note = QLabel(t("meta_note"))
        self.lbl_meta_note.setProperty("class", "dimmer")
        ml.addWidget(self.lbl_meta_note)
        lay.addWidget(meta, 1)

        # ---- 输出卡片
        out = QFrame()
        out.setProperty("class", "card")
        ol = QVBoxLayout(out)
        ol.setContentsMargins(13, 11, 13, 12)
        ol.setSpacing(9)

        head2 = QHBoxLayout()
        self.lbl_output_title = QLabel(t("panel_output"))
        self.lbl_output_title.setProperty("class", "h1")
        head2.addWidget(self.lbl_output_title)
        head2.addStretch(1)
        ol.addLayout(head2)

        self.rb_over = QRadioButton(t("rb_overwrite"))
        self.rb_dir = QRadioButton(t("rb_folder"))
        self.rb_suf = QRadioButton(t("rb_suffix"))
        self.rb_over.setChecked(True)
        for rb in (self.rb_over, self.rb_dir, self.rb_suf):
            rb.setCursor(Qt.CursorShape.PointingHandCursor)
            rb.toggled.connect(self._sync_output_mode)

        line1 = QHBoxLayout()
        line1.setSpacing(8)
        line1.addWidget(self.rb_over)
        line1.addStretch(1)
        ol.addLayout(line1)

        line2 = QHBoxLayout()
        line2.setSpacing(8)
        line2.addWidget(self.rb_dir)
        self.ed_dir = QLineEdit()
        self.ed_dir.setPlaceholderText(t("dir_placeholder"))
        self.ed_dir.setReadOnly(True)
        self.btn_browse = QPushButton(t("browse"))
        self.btn_browse.setProperty("class", "small")
        self.btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_browse.clicked.connect(self._pick_dir)
        line2.addWidget(self.ed_dir, 1)
        line2.addWidget(self.btn_browse)
        ol.addLayout(line2)

        line3 = QHBoxLayout()
        line3.setSpacing(8)
        line3.addWidget(self.rb_suf)
        self.ed_suffix = QLineEdit(t("suffix_default"))
        self.ed_suffix.setFixedWidth(96)
        line3.addWidget(self.ed_suffix)
        line3.addStretch(1)
        ol.addLayout(line3)

        opts = QHBoxLayout()
        opts.setSpacing(16)
        self.cb_backup = QCheckBox(t("cb_backup"))
        self.cb_backup.setChecked(True)
        self.cb_open = QCheckBox(t("cb_open"))
        self.cb_open.setChecked(True)
        for cb in (self.cb_backup, self.cb_open):
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            opts.addWidget(cb)
        opts.addStretch(1)
        ol.addLayout(opts)

        run = QHBoxLayout()
        run.setSpacing(12)
        self.btn_run = QPushButton(t("btn_run"))
        self.btn_run.setProperty("class", "primary")
        self.btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_run.setMinimumHeight(40)
        self.btn_run.clicked.connect(self._run)
        self.progress = QProgressBar()
        self.progress.setFixedWidth(int(200 * self._scale))
        self.progress.setTextVisible(False)
        self.lbl_status = QLabel(t("status_ready"))
        self.lbl_status.setProperty("class", "dim")
        run.addWidget(self.btn_run)
        run.addWidget(self.progress, 0)
        run.addWidget(self.lbl_status, 1)
        ol.addLayout(run)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(80)
        self.log.setPlaceholderText(t("log_placeholder"))
        ol.addWidget(self.log)

        lay.addWidget(out)
        self._sync_output_mode()
        return wrap

    def _init_geometry(self):
        scr = QGuiApplication.primaryScreen()
        geo = scr.availableGeometry()
        w = min(max(int(geo.width() * 0.78), 1000), 1460)
        h = min(max(int(geo.height() * 0.84), 660), 980)
        w = min(w, geo.width() - 20)
        h = min(h, geo.height() - 20)
        self.resize(w, h)
        self.setMinimumSize(min(940, max(520, geo.width() - 30)),
                            min(620, max(420, geo.height() - 30)))
        fg = self.frameGeometry()
        fg.moveCenter(geo.center())
        self.move(fg.topLeft())

    def _apply_glass(self):
        if not effects.IS_WIN:
            return
        hwnd = int(self.winId())
        effects.apply_window_theme(hwnd)
        effects.apply_acrylic(hwnd, (243, 246, 251, 200), extend_frame=True)

    # ------------------------------------------------------------ 语言切换
    def _change_lang(self, lang: str):
        if current_lang() == lang:
            return
        set_lang(lang)
        self._refresh_texts()

    def _sync_lang_buttons(self):
        self.btn_lang_zh.setChecked(current_lang() == "zh")
        self.btn_lang_en.setChecked(current_lang() == "en")
        self.btn_lang_zh.setProperty("active", current_lang() == "zh")
        self.btn_lang_en.setProperty("active", current_lang() == "en")
        for b in (self.btn_lang_zh, self.btn_lang_en):
            b.style().unpolish(b)
            b.style().polish(b)

    def _refresh_texts(self):
        self.setWindowTitle(t("app_title"))
        self.title_lbl.setText(t("title"))
        self.chip_subtitle.setText(t("subtitle"))
        self.btn_about.setText(t("about"))
        self.btn_lang_zh.setText(t("lang_zh"))
        self.btn_lang_en.setText(t("lang_en"))
        self._sync_lang_buttons()

        self.lbl_images_title.setText(t("panel_images"))
        self.lbl_count.setText(t("count_fmt", len(self.scans)))
        self.btn_add_images.setText(t("add_images"))
        self.btn_add_folder.setText(t("add_folder"))
        self.btn_clear.setText(t("clear"))
        self.lbl_drop_tip.setText(t("drop_tip"))

        self.lbl_meta_title.setText(t("panel_meta"))
        self.search.setPlaceholderText(t("search_placeholder"))
        self.tree.setHeaderLabels([t("tree_col_item"), t("tree_col_value"), t("tree_col_hits")])
        self.lbl_meta_note.setText(t("meta_note"))
        for i, (key, _cats) in enumerate(self.preset_defs):
            self.preset_btns[i].setText(t(key))
        self._update_stats()
        self._update_meta_summary()

        self.lbl_output_title.setText(t("panel_output"))
        self.rb_over.setText(t("rb_overwrite"))
        self.rb_dir.setText(t("rb_folder"))
        self.rb_suf.setText(t("rb_suffix"))
        self.ed_dir.setPlaceholderText(t("dir_placeholder"))
        self.btn_browse.setText(t("browse"))
        self.cb_backup.setText(t("cb_backup"))
        self.cb_open.setText(t("cb_open"))
        self.btn_run.setText(t("btn_run"))
        self.log.setPlaceholderText(t("log_placeholder"))
        if not self.worker or not self.worker.isRunning():
            self.lbl_status.setText(t("status_ready"))

    # ------------------------------------------------------------ 事件
    def _toggle_max(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _is_interactive(self, w: QWidget | None) -> bool:
        while w is not None:
            if isinstance(w, (QAbstractButton, QLineEdit, QComboBox, QCheckBox,
                              QRadioButton, QPlainTextEdit, FileList, MetaTree)):
                return True
            w = w.parent() if isinstance(w.parent(), QWidget) else None
        return False

    def nativeEvent(self, eventType, message):
        if effects.IS_WIN and eventType in ("windows_generic_MSG", "windows_dispatcher_MSG"):
            try:
                msg = effects.msg_from_address(int(message))
            except Exception:
                return super().nativeEvent(eventType, message)
            if msg.message == effects.WM_NCHITTEST:
                x = effects.c_short(msg.lParam & 0xFFFF)
                y = effects.c_short((msg.lParam >> 16) & 0xFFFF)
                pos = self.mapFromGlobal(QPoint(x, y))
                if self.isMaximized():
                    return True, effects.HTCLIENT
                b = 6
                w, h = self.width(), self.height()
                left, right = pos.x() < b, pos.x() > w - b
                top, bottom = pos.y() < b, pos.y() > h - b
                if left and top:
                    return True, effects.HTTOPLEFT
                if right and top:
                    return True, effects.HTTOPRIGHT
                if left and bottom:
                    return True, effects.HTBOTTOMLEFT
                if right and bottom:
                    return True, effects.HTBOTTOMRIGHT
                if left:
                    return True, effects.HTLEFT
                if right:
                    return True, effects.HTRIGHT
                if top:
                    return True, effects.HTTOP
                if bottom:
                    return True, effects.HTBOTTOM
                if pos.y() < CAPTION_H and not self._is_interactive(self.childAt(pos)):
                    return True, effects.HTCAPTION
                return True, effects.HTCLIENT
            if msg.message == 0x00A3:  # WM_NCLBUTTONDBLCLK
                self._toggle_max()
                return True, 0
        return super().nativeEvent(eventType, message)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.toLocalFile()]
        self._add_paths(paths)
        e.acceptProposedAction()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        compact = self.width() < 900
        self.list.setIconSize(QSize(THUMB if not compact else 38, THUMB if not compact else 38))

    # ------------------------------------------------------------ 文件导入
    def _add_paths(self, paths: list[str]):
        found: list[str] = []
        for p in paths:
            ap = os.path.abspath(p)
            if os.path.isdir(ap):
                for root, _dirs, files in os.walk(ap):
                    for f in files:
                        if os.path.splitext(f)[1].lower() in EXTS:
                            found.append(os.path.join(root, f))
            elif os.path.isfile(ap) and os.path.splitext(ap)[1].lower() in EXTS:
                found.append(ap)
        new = [p for p in found if p not in self.scans]
        if not new:
            return
        for p in new:
            self.scans[p] = None  # 占位，避免重复
        self.lbl_status.setText(t("status_scanning", len(new)))
        self.worker = ScanWorker(new)
        self.worker.sig_file.connect(self._on_scanned)
        self.worker.sig_done.connect(self._on_scan_done)
        self.worker.start()

    def _on_scanned(self, fs: scanner.FileScan):
        self.scans[fs.path] = fs
        from PySide6.QtWidgets import QListWidgetItem

        li = QListWidgetItem(fs.name)
        li.setSizeHint(QSize(200, 58))
        li.setData(Qt.ItemDataRole.UserRole, fs.path)
        li.setData(Qt.ItemDataRole.DecorationRole, rounded_pixmap(load_thumb(fs.path, THUMB)))
        meta = t("meta_count_fmt", fs.meta_count) if fs.ok else fs.error
        li.setData(Qt.ItemDataRole.UserRole + 2, f"{human_size(fs.size)} · {fs.fmt} · {meta}")
        li.setData(Qt.ItemDataRole.UserRole + 3, "ok" if fs.ok else "bad")
        li.setToolTip(f"{fs.path}\n{fs.fmt} · {human_size(fs.size)}\n{meta}")
        self.list.addItem(li)

    def _on_scan_done(self, ok: int, total: int):
        self.scans = {k: v for k, v in self.scans.items() if v is not None}
        self._rebuild_agg()
        n = len(self.scans)
        self.lbl_count.setText(t("count_fmt", n))
        self.lbl_status.setText(t("status_imported", n) if total == ok else t("status_imported_err", n, total - ok))
        if self.list.count() and self.list.currentItem() is None:
            self.list.setCurrentRow(0)

    def _clear_files(self):
        self.list.clear()
        self.scans.clear()
        self.agg.clear()
        self.selection.clear()
        self.tree.clear()
        self.lbl_count.setText(t("count_fmt", 0))
        self.lbl_meta.setText(t("meta_not_imported"))
        self.lbl_remove.setText("")
        self.log.clear()
        self.lbl_status.setText(t("status_cleared"))

    def _pick_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, t("dlg_pick_images"), "",
            t("file_filter"))
        if paths:
            self._add_paths(paths)

    def _pick_folder(self):
        d = QFileDialog.getExistingDirectory(self, t("dlg_pick_folder"))
        if d:
            self._add_paths([d])

    def _pick_dir(self):
        d = QFileDialog.getExistingDirectory(self, t("dlg_pick_output"), self._dest_dir)
        if d:
            self._dest_dir = d
            self.ed_dir.setText(d)
            self.rb_dir.setChecked(True)

    # ------------------------------------------------------------ 聚合
    def _cat_label(self, key: str) -> tuple[str, str, str]:
        """返回 (label, hint, color) 的翻译。"""
        mapping = {
            "image": (t("cat_image"), t("cat_image_hint"), C["text"]),
            "ai": (t("cat_ai"), t("cat_ai_hint"), "#AF52DE"),
            "gps": (t("cat_gps"), t("cat_gps_hint"), "#FF3B30"),
            "time": (t("cat_time"), t("cat_time_hint"), "#FF9500"),
            "device": (t("cat_device"), t("cat_device_hint"), "#007AFF"),
            "software": (t("cat_software"), t("cat_software_hint"), "#5E5CE6"),
            "desc": (t("cat_desc"), t("cat_desc_hint"), "#00A3A3"),
            "author": (t("cat_author"), t("cat_author_hint"), "#34C759"),
            "thumb": (t("cat_thumb"), t("cat_thumb_hint"), "#8E8E93"),
            "xmp": (t("cat_xmp"), t("cat_xmp_hint"), "#5856D6"),
            "iptc": (t("cat_iptc"), t("cat_iptc_hint"), "#C77CFF"),
            "comment": (t("cat_comment"), t("cat_comment_hint"), "#A2845E"),
            "shoot": (t("cat_shoot"), t("cat_shoot_hint"), "#0A84FF"),
            "color": (t("cat_color"), t("cat_color_hint"), "#30B0C7"),
            "other": (t("cat_other"), t("cat_other_hint"), "#6E6E73"),
            "unknown": (t("cat_unknown"), t("cat_unknown_hint"), "#8E8E93"),
        }
        return mapping.get(key, (key, "", C["text3"]))

    def _rebuild_agg(self):
        total = max(1, len(self.scans))
        agg: dict[str, AggItem] = {}
        for fs in self.scans.values():
            if not fs or not fs.ok:
                continue
            for it in fs.items:
                a = agg.get(it.key)
                if a is None:
                    agg[it.key] = AggItem(it.key, it.label, it.value, it.category,
                                          it.default_remove, it.note, 1, False)
                else:
                    a.hits += 1
                    if a.value != it.value:
                        a.multi = True
        self.agg = agg
        self.defaults = {k: a.default_remove for k, a in agg.items()}

        groups = []
        # 图像数据（锁定，永不可移除）
        img_items = []
        for fs in self.scans.values():
            if fs and fs.ok:
                img_items.append(AggItem(
                    f"img:{fs.path}", fs.name,
                    f"{fs.width}×{fs.height} · {fs.fmt} · {human_size(fs.size)}",
                    "image", False, t("cat_image_hint"), 1, False))
        if img_items:
            groups.append(("image", t("cat_image"), t("cat_image_hint"), C["text"], img_items, True))

        for key, _label, _hint, _d, _color in scanner.CATEGORIES:
            if key == "image":
                continue
            items = sorted([a for a in agg.values() if a.category == key],
                           key=lambda a: (-a.hits, a.label))
            for a in items:
                if a.multi:
                    a.value = a.value + " · " + ("多值" if current_lang() == "zh" else "multi")
            if items:
                label, hint, color = self._cat_label(key)
                groups.append((key, label, hint, color, items, False))

        self.tree.load(groups, self.selection, len(self.scans))
        self._update_stats()
        self._update_meta_summary()

    def _update_meta_summary(self):
        m = len(self.agg)
        self.lbl_meta.setText(t("meta_fmt", len(self.scans), m))

    def _update_stats(self):
        self.selection = self.tree.collect()
        removed = sum(1 for k, v in self.selection.items() if v)
        total = len(self.selection)
        self.lbl_remove.setText(t("remove_fmt", removed, total))

    def _preset(self, cats: set[str] | None, key: str):
        if cats is None:
            self.tree.apply_defaults(self.defaults)
        else:
            self.tree.set_all(True if key == "preset_remove_all" else False, cats)
            if key == "preset_keep_all":
                self.tree.set_all(False)
            elif key == "preset_privacy":
                self.tree.set_all(False)
                self.tree.set_all(True, cats)
        for b, (k, _c) in zip(self.preset_btns, self.preset_defs):
            b.setProperty("active", k == key)
            b.style().unpolish(b)
            b.style().polish(b)

    def _filter(self, text: str):
        self.tree.filter_rows(text)

    def _on_select_file(self):
        pass

    # ------------------------------------------------------------ 输出模式
    def _sync_output_mode(self):
        d = self.rb_dir.isChecked()
        s = self.rb_suf.isChecked()
        self.ed_dir.setEnabled(d)
        self.ed_suffix.setEnabled(s)
        self.cb_backup.setEnabled(self.rb_over.isChecked())

    # ------------------------------------------------------------ 执行
    def _run(self):
        paths = [p for p, fs in self.scans.items() if fs and fs.ok]
        if not paths:
            GlassDialog.info(self, t("dlg_info"), t("msg_no_files"), self._scale)
            return
        mode = "overwrite" if self.rb_over.isChecked() else ("folder" if self.rb_dir.isChecked() else "suffix")
        dest = self._dest_dir
        if mode == "folder":
            if not dest:
                GlassDialog.warn(self, t("dlg_warn"), t("msg_no_folder"), self._scale)
                return
        if mode == "overwrite" and not self.cb_backup.isChecked():
            ok = GlassDialog.ask(
                self, t("dlg_confirm_overwrite"), t("msg_overwrite_no_backup", len(paths)),
                t("btn_yes"), t("btn_no"), "warn", self._scale)
            if not ok:
                return

        plan = Plan(
            remove={k for k, v in self.selection.items() if v},
            xmp_ai=any(k.startswith("xmpai:") and v for k, v in self.selection.items()),
            iptc_ai=bool(self.selection.get("iptc:ai")),
        )
        self.btn_run.setEnabled(False)
        self.progress.setRange(0, len(paths))
        self.progress.setValue(0)
        self.log.clear()

        self.worker = CleanWorker(paths, plan, mode, dest, self.ed_suffix.text() or "_clean",
                                  self.cb_backup.isChecked(), "")
        self.worker.sig_progress.connect(self._on_progress)
        self.worker.sig_done.connect(self._on_clean_done)
        self.worker.start()

    def _on_progress(self, i, total, msg):
        self.progress.setValue(i)
        self.lbl_status.setText(msg)

    def _on_clean_done(self, results: list[CleanResult]):
        ok = [r for r in results if r.ok]
        bad = [r for r in results if not r.ok]
        before = sum(r.before for r in ok)
        after = sum(r.after for r in ok)
        items = sum(r.removed_items for r in ok)
        verified = sum(1 for r in ok if r.payload_ok)

        for r in ok:
            self.log.appendPlainText(
                t("log_ok", os.path.basename(r.src), human_size(max(0, r.before - r.after)),
                  r.removed_items, r.verify_note))
        for r in bad:
            self.log.appendPlainText(t("log_err", os.path.basename(r.src), r.error))

        self.lbl_status.setText(
            t("status_done", len(ok), len(bad), items, human_size(max(0, before - after)), verified, len(ok)))
        self.btn_run.setEnabled(True)
        self.progress.setValue(len(results))

        if self.cb_open.isChecked() and ok:
            import subprocess

            folder = os.path.dirname(ok[0].dst) or os.path.dirname(ok[0].src)
            try:
                os.startfile(folder)  # noqa
            except Exception:
                try:
                    subprocess.Popen(["explorer", folder])
                except Exception:
                    pass

        # 覆盖模式下刷新元数据
        if self.rb_over.isChecked():
            keep = list(self.scans.keys())
            self.list.clear()
            self.scans.clear()
            self._add_paths(keep)

    # ------------------------------------------------------------ 关于
    def _about(self):
        d = QDialog(self)
        d.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        d.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        d.setStyleSheet(qss(self._scale))
        outer = QVBoxLayout(d)
        outer.setContentsMargins(16, 16, 16, 16)
        f = QWidget(objectName="appframe")
        l = QVBoxLayout(f)
        l.setContentsMargins(22, 20, 22, 18)
        l.setSpacing(10)
        title_lbl = QLabel(t("about_title"))
        title_lbl.setProperty("class", "h1")
        l.addWidget(title_lbl)
        body = QLabel(t("about_body"))
        body.setProperty("class", "dim")
        body.setWordWrap(True)
        l.addWidget(body)
        ok_btn = QPushButton(t("btn_ok"))
        ok_btn.setProperty("class", "primary")
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.clicked.connect(d.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(ok_btn)
        l.addLayout(btn_row)
        outer.addWidget(f)
        d.exec()
