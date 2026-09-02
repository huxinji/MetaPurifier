"""GUI 冒烟测试：offscreen 下构造主窗口、导入图片、构建勾选树、生成计划。"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

from PIL import Image

from app.core import cleaner, formats, scanner
from app.core.cleaner import Plan
from app.ui.i18n import set_lang, t
from app.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()  # offscreen 下不会真正显示，但会触发布局/样式

    # 造一张带 EXIF 的测试图
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "smoke.jpg")
        Image.new("RGB", (32, 24), (9, 9, 9)).save(p, "JPEG", quality=90)
        import piexif
        exif = piexif.dump({"0th": {271: b"TestCam", 306: b"2026:01:01 00:00:00"},
                            "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None})
        piexif.insert(exif, p)

        fs = scanner.scan_file(p)
        assert fs.ok, fs.error
        win._on_scanned(fs)
        win._on_scan_done(1, 1)
        # 树应已构建
        assert win.tree.topLevelItemCount() > 0, "元数据树为空"
        # 验证语言切换：预设按钮应随语言变化
        btn_texts_cn = [b.text() for b in win.preset_btns]
        assert "推荐清理" in btn_texts_cn and "仅隐私项" in btn_texts_cn, f"中文预设按钮异常: {btn_texts_cn}"
        set_lang("en")
        win._refresh_texts()
        btn_texts_en = [b.text() for b in win.preset_btns]
        assert "Recommended" in btn_texts_en and "Privacy Only" in btn_texts_en, f"英文预设按钮异常: {btn_texts_en}"
        set_lang("zh")
        win._refresh_texts()
        # 统计项
        sel = win.tree.collect()
        assert sel, "未收集到勾选项"
        # 预设：仅隐私项
        win._preset({"ai", "gps", "time", "device", "software", "thumb"}, "preset_privacy")
        sel2 = win.tree.collect()
        on = sum(1 for v in sel2.values() if v)
        print(f"树分组数={win.tree.topLevelItemCount()} 可勾选项={len(sel)} 仅隐私项勾选={on}")
        # 生成计划并执行（复用核心，确保 UI->计划链路正确）
        plan = Plan(remove={k for k, v in sel2.items() if v})
        data = open(p, "rb").read()
        parsed = formats.parse(data)
        out, res = cleaner.apply_plan(data, parsed, plan)
        assert res.ok and res.payload_ok, (res.error, res.verify_note)
        print(f"计划执行 OK | 移除 {res.removed_items} 项 | 校验 {res.verify_note}")
    print("\nGUI 冒烟测试通过 ✓")


if __name__ == "__main__":
    main()
