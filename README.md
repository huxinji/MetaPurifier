# MetaPurifier

> 无损图片元数据清理器 · Lossless Image Metadata Cleaner

一个用于移除图片中的元数据（AI 标记、C2PA 内容凭证、拍照时间、GPS 经纬度、设备信息等），并可自定义选择保留/移除哪些项。**完全不损害画质、像素与色彩**——采用字节级手术，只改元数据段，图像压缩数据原样保留，并用 SHA256 像素指纹逐张校验。

A **standalone desktop app (no browser required)** that strips image metadata (AI markers, C2PA provenance, capture time, GPS coordinates, device info, etc.) while letting you choose precisely what to keep or remove. **Image quality, pixels, and colors are never touched**—a byte-level operation edits only metadata segments and keeps the compressed image data intact, verified per-file with a SHA256 pixel fingerprint.

---

## 功能特性 · Features

- **真正无损 · Truly lossless**：仅剥离元数据段（JPEG 的 APP1 EXIF/XMP、APP13 IPTC、COM、APP11 C2PA；PNG 的 eXIf/tEXt/iTXt；WebP 的 EXIF/XMP），图像扫描流（SOS / IDAT / VP8）原样保留，处理前后像素哈希一致。
- **广泛支持 · Broad coverage**：可识别并清除 AI 生成声明与 C2PA 凭证、GPS 经纬度与海拔、拍摄时间、设备厂商/型号/序列号/镜头、软件与编辑记录、作者与版权、缩略图、XMP、IPTC、注释、拍摄参数、色彩配置等。
- **精细控制 · Fine-grained control**：按「AI 标记 / 位置 / 时间 / 设备 / 软件 / 描述 / 作者 / 缩略图 / XMP / IPTC / 拍摄参数 / 色彩」分组，**勾选即移除**，支持单条、整类、三态勾选。
- **一键预设 · Presets**：推荐清理 / 全部移除 / 仅隐私项 / 全部保留。
- **多图批量 · Batch**：支持多选、拖拽、整文件夹导入，缩略图列表管理。
- **灵活输出 · Output options**：直接覆盖原图（覆盖前自动备份）、另存到指定目录、或原目录加后缀副本。
- **Apple Liquid Glass 风格 · Apple Liquid Glass UI**：无边框窗口 + Windows 亚克力毛玻璃、圆角玻璃卡片、浅色科技风配色、自定义标题栏、高分屏自适应。
- **中英双语 · Bilingual UI**：界面可一键在中文 / 英文之间切换，默认中文。
- **独立程序 · Standalone**：单文件可执行程序，双击即用，不联网、不依赖浏览器。

---

## 支持的格式 · Supported Formats

| 格式 Format | 扩展名 Extensions | 说明 Notes |
| --- | --- | --- |
| JPEG | `.jpg` `.jpeg` `.jpe` | EXIF / XMP / IPTC / C2PA / 注释 |
| PNG  | `.png` | eXIf / tEXt / iTXt / iCCP |
| WebP | `.webp` | EXIF / XMP |
| TIFF | `.tif` `.tiff` | IFD / EXIF / GPS |

---

## 安装与运行 · Install & Run

### 方式一：直接下载（推荐）· Download (Recommended)

前往 **Releases** 页面下载 `MetaPurifier.exe`，双击即可运行，无需安装 Python 或任何依赖。

Go to the **Releases** page and download `MetaPurifier.exe`—just double-click to run. No Python or dependencies required.

### 方式二：从源码运行 · Run from Source

```bash
# 需要 Python 3.10+
git clone https://github.com/huxinji/MetaPurifier.git
cd MetaPurifier
pip install -r requirements.txt
python main.py
```

### 方式三：自行打包 · Build Yourself

```bash
pip install -r requirements.txt
python -m PyInstaller --windowed --onefile --name MetaPurifier main.py
# 生成的单文件程序位于 dist/MetaPurifier.exe
```

---

## 使用指南 · Usage

1. **添加图片 · Add images**：点击「添加图片 / Add Images」或「添加文件夹 / Add Folder」，或直接把图片拖入左侧列表。
2. **选择要移除的项 · Choose what to remove**：在右侧勾选树中勾选需要移除的元数据（勾选 = 移除）。也可点击上方预设按钮一键选择。
3. **选择输出方式 · Pick output**：覆盖原图（建议保留备份）/ 另存目录 / 加后缀副本。
4. **开始清理 · Run**：点击「开始清理 / Start」，程序逐张处理并在日志中显示结果（移除项数、体积变化、像素校验状态）。

---

## 无损保证 · Lossless Guarantee

每张图片在清理前、后都会计算图像数据的 SHA256 指纹并比对；若不一致则判定为异常并中止，绝不会写出损坏或画质受损的文件。所有测试（JPEG / PNG / WebP）均验证「像素零损失」。

For every image, a SHA256 fingerprint of the pixel data is computed before and after cleaning and compared. Any mismatch aborts the write, so a corrupted or degraded file is never produced. All tests (JPEG / PNG / WebP) verify zero pixel loss.

---

## 开源许可 · License

本项目以 [MIT License](./LICENSE) 开源。

Released under the [MIT License](./LICENSE).
