"""一键打包为独立 exe（单文件、无控制台窗口）。

用法（在 venv 的 python 下运行）：
    python build_exe.py
产物： dist/MetaPurifier.exe  （双击即可使用，无需安装、不依赖浏览器）
"""

import os
import sys

from PyInstaller.__main__ import run

HERE = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    sys.argv = [
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onefile",
        "--name", "MetaPurifier",
        "--paths", HERE,
        os.path.join(HERE, "main.py"),
    ]
    run()
