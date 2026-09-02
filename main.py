"""元像 MetaPurifier —— 独立桌面程序入口。

不依赖浏览器、不联网。双击 main.py（或打包后的 exe）即可使用。
"""

from __future__ import annotations

import os
import sys

# 让打包后也能从 exe 所在目录解析 app 包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from app.ui.theme import GlassStyle
    from app.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyle(GlassStyle("Fusion"))
    app.setApplicationName("元像 MetaPurifier")
    app.setApplicationDisplayName("元像 MetaPurifier · 无损元数据清理")

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
