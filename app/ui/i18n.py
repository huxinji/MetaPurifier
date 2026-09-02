"""中英双语支持。默认中文，切换时重新加载界面文本。"""

from __future__ import annotations

LANG: str = "zh"

_TEXT = {
    "zh": {
        # 标题
        "app_title": "元像 MetaPurifier · 无损元数据清理",
        "title": "元像 MetaPurifier",
        "subtitle": "无损清理",
        # 标题栏
        "close": "关闭",
        "minimize": "最小化",
        "maximize": "最大化 / 还原",
        "about": "关于",
        "lang_zh": "中",
        "lang_en": "EN",
        # 左侧面板
        "panel_images": "图片",
        "count_fmt": "{} 张",
        "add_images": "添加图片",
        "add_folder": "添加文件夹",
        "clear": "清空",
        "drop_tip": "把图片或文件夹拖到窗口任意位置即可导入",
        # 右侧面板 - 元数据
        "panel_meta": "元数据",
        "meta_not_imported": "尚未导入图片",
        "meta_fmt": "共 {} 张 · 检出 {} 项元数据",
        "search_placeholder": "搜索元数据…",
        "preset_recommended": "推荐清理",
        "preset_remove_all": "全部移除",
        "preset_privacy": "仅隐私项",
        "preset_keep_all": "全部保留",
        "remove_fmt": "将移除 <b>{}</b> / {} 项",
        "tree_col_item": "项目",
        "tree_col_value": "值",
        "tree_col_hits": "命中",
        "meta_note": "勾选 = 移除。图像压缩数据、色彩描述与方向默认保留，画质零损伤。",
        # 输出
        "panel_output": "输出",
        "rb_overwrite": "直接覆盖（替换）原图",
        "rb_folder": "保存到文件夹：",
        "rb_suffix": "原目录另存为副本，后缀：",
        "browse": "浏览…",
        "dir_placeholder": "选择一个输出文件夹…",
        "suffix_default": "_clean",
        "cb_backup": "覆盖前备份原图到「原图备份」",
        "cb_open": "处理完成后打开所在文件夹",
        "btn_run": "开始清理",
        "status_ready": "准备就绪",
        "status_scanning": "正在解析 {} 个文件…",
        "status_imported": "已导入 {} 张图片",
        "status_imported_err": "已导入 {} 张图片（{} 个无法处理）",
        "status_cleared": "已清空",
        "progress_fmt": "正在处理 {}",
        "log_placeholder": "处理日志会显示在这里，包含每张图片的像素数据校验结果。",
        # 处理结果
        "log_ok": "✓ {}  −{}  移除 {} 项  {}",
        "log_err": "✗ {}  {}",
        "status_done": "完成：成功 {} 张，失败 {} 张 · 共移除 {} 项元数据 · 体积减少 {} · 像素校验通过 {}/{}",
        "err_unsupported_fmt": "暂不支持无损剥离的格式：{}",
        "err_payload_mismatch": "像素数据校验不一致，已放弃写入以保护原图",
        "meta_count_fmt": "{} 项元数据",
        # 弹窗标题与文本
        "dlg_info": "提示",
        "dlg_warn": "警告",
        "dlg_confirm_overwrite": "确认覆盖",
        "msg_no_files": "请先导入至少一张可处理的图片。",
        "msg_no_folder": "请选择输出文件夹。",
        "msg_overwrite_no_backup": "将直接覆盖 {} 张原图，且未勾选备份。\n此操作不可撤销，是否继续？",
        "btn_yes": "是",
        "btn_no": "否",
        "btn_ok": "确定",
        "btn_cancel": "取消",
        # 文件对话框
        "dlg_pick_images": "选择图片",
        "file_filter": "图片文件 (*.jpg *.jpeg *.jpe *.png *.webp *.tif *.tiff);;所有文件 (*.*)",
        "dlg_pick_folder": "选择包含图片的文件夹",
        "dlg_pick_output": "选择输出文件夹",
        # 关于
        "about_title": "元像 MetaPurifier",
        "about_body": (
            "本地运行的独立桌面程序，不联网、不依赖浏览器。\n\n"
            "· 只操作元数据段，图像压缩数据逐字节保留\n"
            "· 支持 JPEG / PNG / WebP / TIFF\n"
            "· 可识别并清除 C2PA 内容凭证与 AI 生成声明\n"
            "· 每张图片处理后都会做像素数据校验\n\n"
            "覆盖原图前建议保留备份。"
        ),
        # 分类
        "cat_image": "图像数据",
        "cat_image_hint": "永远不会被修改",
        "cat_ai": "AI 标记",
        "cat_ai_hint": "生成式 AI、C2PA 内容凭证",
        "cat_gps": "位置",
        "cat_gps_hint": "经纬度、海拔、地磁场",
        "cat_time": "时间",
        "cat_time_hint": "拍摄、编辑、扫描时间",
        "cat_device": "设备",
        "cat_device_hint": "相机、手机、镜头序列号",
        "cat_software": "软件",
        "cat_software_hint": "编辑软件与版本",
        "cat_desc": "描述",
        "cat_desc_hint": "标题、说明、关键字",
        "cat_author": "作者",
        "cat_author_hint": "版权、摄影师、署名",
        "cat_thumb": "缩略图",
        "cat_thumb_hint": "嵌入预览图",
        "cat_xmp": "XMP",
        "cat_xmp_hint": "可扩展元数据平台",
        "cat_iptc": "IPTC",
        "cat_iptc_hint": "新闻与图片机构元数据",
        "cat_comment": "注释",
        "cat_comment_hint": "JPEG 注释与用户注释",
        "cat_shoot": "拍摄参数",
        "cat_shoot_hint": "光圈、快门、ISO、焦距",
        "cat_color": "色彩",
        "cat_color_hint": "色彩空间、ICC 配置",
        "cat_other": "其他",
        "cat_other_hint": "其他可识别元数据",
        "cat_unknown": "未知",
        "cat_unknown_hint": "未分类段",
    },
    "en": {
        "app_title": "MetaPurifier · Lossless Metadata Cleaner",
        "title": "MetaPurifier",
        "subtitle": "Lossless",
        "close": "Close",
        "minimize": "Minimize",
        "maximize": "Maximize / Restore",
        "about": "About",
        "lang_zh": "中",
        "lang_en": "EN",
        "panel_images": "Images",
        "count_fmt": "{} images",
        "add_images": "Add Images",
        "add_folder": "Add Folder",
        "clear": "Clear",
        "drop_tip": "Drop images or folders anywhere to import",
        "panel_meta": "Metadata",
        "meta_not_imported": "No images imported yet",
        "meta_fmt": "{} images · {} metadata items found",
        "search_placeholder": "Search metadata…",
        "preset_recommended": "Recommended",
        "preset_remove_all": "Remove All",
        "preset_privacy": "Privacy Only",
        "preset_keep_all": "Keep All",
        "remove_fmt": "Will remove <b>{}</b> / {} items",
        "tree_col_item": "Item",
        "tree_col_value": "Value",
        "tree_col_hits": "Hits",
        "meta_note": "Checked = remove. Image data, color profile and orientation are kept by default. Zero quality loss.",
        "panel_output": "Output",
        "rb_overwrite": "Overwrite original images",
        "rb_folder": "Save to folder:",
        "rb_suffix": "Save as copy with suffix:",
        "browse": "Browse…",
        "dir_placeholder": "Choose an output folder…",
        "suffix_default": "_clean",
        "cb_backup": "Backup originals to \"Original Backup\" before overwrite",
        "cb_open": "Open destination folder when finished",
        "btn_run": "Clean Metadata",
        "status_ready": "Ready",
        "status_scanning": "Parsing {} files…",
        "status_imported": "Imported {} images",
        "status_imported_err": "Imported {} images ({} failed)",
        "status_cleared": "Cleared",
        "progress_fmt": "Processing {}",
        "log_placeholder": "Processing logs will appear here, including pixel-data verification for each image.",
        "log_ok": "✓ {}  −{}  removed {} items  {}",
        "log_err": "✗ {}  {}",
        "status_done": "Done: {} succeeded, {} failed · removed {} metadata items · saved {} · pixel verified {}/{}",
        "err_unsupported_fmt": "Format not supported for lossless stripping: {}",
        "err_payload_mismatch": "Pixel-data verification mismatch; original file kept.",
        "meta_count_fmt": "{} metadata items",
        "dlg_info": "Info",
        "dlg_warn": "Warning",
        "dlg_confirm_overwrite": "Confirm Overwrite",
        "msg_no_files": "Please import at least one supported image.",
        "msg_no_folder": "Please select an output folder.",
        "msg_overwrite_no_backup": "This will overwrite {} original images without backup.\nThis action cannot be undone. Continue?",
        "btn_yes": "Yes",
        "btn_no": "No",
        "btn_ok": "OK",
        "btn_cancel": "Cancel",
        "dlg_pick_images": "Select Images",
        "file_filter": "Images (*.jpg *.jpeg *.jpe *.png *.webp *.tif *.tiff);;All Files (*.*)",
        "dlg_pick_folder": "Select Folder Containing Images",
        "dlg_pick_output": "Select Output Folder",
        "about_title": "MetaPurifier",
        "about_body": (
            "A standalone desktop app that runs locally, offline and without a browser.\n\n"
            "· Only touches metadata segments; image compression data is preserved byte-for-byte\n"
            "· Supports JPEG / PNG / WebP / TIFF\n"
            "· Detects and removes C2PA content credentials and AI-generation claims\n"
            "· Pixel-data verification after every image\n\n"
            "It is recommended to keep backups before overwriting originals."
        ),
        "cat_image": "Image Data",
        "cat_image_hint": "Never modified",
        "cat_ai": "AI Markers",
        "cat_ai_hint": "Generative AI, C2PA credentials",
        "cat_gps": "Location",
        "cat_gps_hint": "GPS coordinates, altitude, geomagnetism",
        "cat_time": "Time",
        "cat_time_hint": "Capture, edit and scan times",
        "cat_device": "Device",
        "cat_device_hint": "Camera, phone, lens serial numbers",
        "cat_software": "Software",
        "cat_software_hint": "Editing software and versions",
        "cat_desc": "Description",
        "cat_desc_hint": "Title, caption, keywords",
        "cat_author": "Author",
        "cat_author_hint": "Copyright, photographer, credit",
        "cat_thumb": "Thumbnail",
        "cat_thumb_hint": "Embedded preview",
        "cat_xmp": "XMP",
        "cat_xmp_hint": "Extensible Metadata Platform",
        "cat_iptc": "IPTC",
        "cat_iptc_hint": "Press and photo-agency metadata",
        "cat_comment": "Comments",
        "cat_comment_hint": "JPEG comments and user comments",
        "cat_shoot": "Shooting Parameters",
        "cat_shoot_hint": "Aperture, shutter, ISO, focal length",
        "cat_color": "Color",
        "cat_color_hint": "Color space and ICC profile",
        "cat_other": "Other",
        "cat_other_hint": "Other recognized metadata",
        "cat_unknown": "Unknown",
        "cat_unknown_hint": "Unclassified segments",
    },
}


def set_lang(lang: str) -> None:
    global LANG
    LANG = "zh" if lang.startswith("zh") else "en"


def t(key: str, *args) -> str:
    s = _TEXT.get(LANG, _TEXT["zh"]).get(key, key)
    if args:
        return s.format(*args)
    return s


def current_lang() -> str:
    return LANG
