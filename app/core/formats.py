"""图片容器解析层。

设计原则：**只认识元数据，绝不碰像素**。
所有格式都被拆解为有序的"块"（segment / chunk），
其中结构性块（SOF/DQT/SOS/IDAT/VP8…）标记为 locked，永远原样保留；
清理时只丢弃或重写被用户勾选的元数据块。
因此图像压缩数据与原始文件逐字节一致，画质/像素/色彩零损失。
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------- 数据结构

STRUCTURAL = "struct"  # 图像结构，锁定
EXIF = "exif"
XMP = "xmp"
IPTC = "iptc"
COMMENT = "com"
C2PA = "c2pa"
ICC = "icc"
MPF = "mpf"
TEXT = "text"
TIME = "time"
META = "meta"
UNKNOWN = "unknown"
SOI = "soi"


@dataclass
class Block:
    """文件中的一个块（JPEG 段 / PNG 数据块 / WebP RIFF 块）。"""

    key: str
    kind: str
    name: str
    offset: int
    size: int
    category: str = "other"
    locked: bool = False
    raw: Optional[bytes] = None  # 需要改写时才有值；否则按 offset/size 从原文件切片
    data: bytes = b""  # 有效载荷（EXIF 的 TIFF 流、XMP 文本、chunk data …）
    extra: dict = field(default_factory=dict)

    def bytes_from(self, src: bytes) -> bytes:
        if self.raw is not None:
            return self.raw
        return src[self.offset : self.offset + self.size]


@dataclass
class Parsed:
    fmt: str
    src: bytes
    head: bytes  # 文件头（SOI / PNG 签名 / RIFF 头）
    blocks: list[Block] = field(default_factory=list)
    tail_start: int = 0  # 图像数据起始偏移（JPEG 为首个 SOS）
    exif: Optional[dict] = None
    exif_source: str = ""  # 'jpeg' | 'png' | 'webp' | 'tiff'
    width: int = 0
    height: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def payload(self) -> bytes:
        """用于无损校验的"像素载荷"：只含压缩图像数据。"""
        return self.src[self.tail_start :]

    def rebuild(self, drop: set[str], src: bytes) -> bytes:
        out = bytearray()
        out += self.head
        for b in self.blocks:
            if b.key in drop or b.locked and b.key in drop:
                continue
            out += b.bytes_from(src)
        if 0 <= self.tail_start < len(src):
            out += src[self.tail_start :]
        return bytes(out)


# ---------------------------------------------------------------- 格式识别


def detect(data: bytes) -> str:
    if data[:2] == b"\xff\xd8":
        return "JPEG"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "PNG"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WEBP"
    if data[:2] in (b"II", b"MM") and data[2:4] in (b"*\x00", b"\x00*"):
        return "TIFF"
    if data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand in (b"heic", b"heix", b"hevc", b"heim", b"heis", b"mif1", b"msf1"):
            return "HEIC"
        if brand in (b"avif", b"avis"):
            return "AVIF"
        return "HEIF"
    if data[:2] == b"BM":
        return "BMP"
    if data[:3] == b"GIF":
        return "GIF"
    return "UNKNOWN"


SUPPORTED = ("JPEG", "PNG", "WEBP", "TIFF")


# ---------------------------------------------------------------- JPEG


def _classify_appn(marker: int, payload: bytes) -> tuple[str, str]:
    if marker == 0xE0:
        if payload.startswith(b"JFIF\x00") or payload.startswith(b"JFXX\x00"):
            return STRUCTURAL, "JFIF 头"
        return META, "APP0 数据"
    if marker == 0xE1:
        if payload.startswith(b"Exif\x00\x00"):
            return EXIF, "EXIF (APP1)"
        if payload.startswith(b"http://ns.adobe.com/xap/1.0/\x00"):
            return XMP, "XMP (APP1)"
        if payload[:5] == b"http:":
            return XMP, "XMP 扩展 (APP1)"
        return META, "APP1 数据"
    if marker == 0xE2:
        if payload.startswith(b"ICC_PROFILE\x00"):
            return ICC, "ICC 色彩描述 (APP2)"
        if payload.startswith(b"MPF\x00"):
            return MPF, "MPF 多画面 (APP2)"
        if payload.startswith(b"FPXR\x00"):
            return META, "FlashPix (APP2)"
        return META, "APP2 数据"
    if marker == 0xEB:
        return C2PA, "C2PA 内容凭证 (APP11 JUMBF)"
    if marker == 0xEC:
        return META, "APP12 Picture Info"
    if marker == 0xED:
        if b"Photoshop 3.0\x00" in payload[:64] or b"8BIM" in payload[:64]:
            return IPTC, "IPTC / Photoshop IRB (APP13)"
        return META, "APP13 数据"
    if marker == 0xEE:
        if payload.startswith(b"Adobe"):
            return STRUCTURAL, "Adobe 色彩变换 (APP14)"
        return META, "APP14 数据"
    if payload[:1] == b"<":
        return XMP, f"XML 数据 (APP{marker - 0xE0})"
    return UNKNOWN, f"未知数据段 APP{marker - 0xE0}"


def parse_jpeg(data: bytes) -> Parsed:
    p = Parsed(fmt="JPEG", src=data, head=data[:2], tail_start=len(data))
    n = len(data)
    i = 2
    occ: dict[str, int] = {}
    while i < n - 1:
        if data[i] != 0xFF:
            j = data.find(b"\xff", i)
            if j < 0:
                break
            i = j
            continue
        marker = data[i + 1]
        if marker == 0xD8 or marker == 0x01 or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        if marker == 0xD9:  # EOI（异常位置）
            break
        if i + 4 > n:
            break
        seglen = struct.unpack(">H", data[i + 2 : i + 4])[0]
        end = i + 2 + seglen
        if seglen < 2 or end > n:
            p.notes.append("JPEG 段长度异常，解析提前结束")
            break
        payload = data[i + 4 : end]

        if marker == 0xDA:  # SOS：从这里开始全部是像素数据，原样保留
            p.tail_start = i
            break

        if marker == 0xFE:
            kind, name = COMMENT, "JPEG 注释 (COM)"
        elif 0xE0 <= marker <= 0xEF:
            kind, name = _classify_appn(marker, payload)
        elif 0xC0 <= marker <= 0xCF or marker in (0xDB, 0xDC, 0xDD, 0xDE, 0xDF):
            kind, name = STRUCTURAL, f"图像结构 (0xFF{marker:02X})"
            if 0xC0 <= marker <= 0xC3 and marker not in (0xC4, 0xC8, 0xCC):
                p.height, p.width = struct.unpack(">HH", payload[1:5])
        else:
            kind, name = STRUCTURAL, f"图像结构 (0xFF{marker:02X})"

        occ[kind] = occ.get(kind, 0) + 1
        key = f"blk:{kind}:{occ[kind]}"
        blk = Block(
            key=key,
            kind=kind,
            name=name,
            offset=i,
            size=end - i,
            data=payload,
            category=_jpeg_category(kind, payload),
            locked=(kind == STRUCTURAL),
            extra={"marker": marker},
        )
        if kind == EXIF:
            blk.data = payload[6:]  # 去掉 "Exif\0\0"
            blk.extra["prefix"] = b"Exif\x00\x00"
        if kind == XMP and payload.startswith(b"http://ns.adobe.com/xap/1.0/\x00"):
            blk.data = payload[29:]
            blk.extra["prefix"] = b"http://ns.adobe.com/xap/1.0/\x00"
        elif kind == XMP:
            # 其它 XML：整段就是 XMP（去掉结尾可能的 \0）
            blk.data = payload.rstrip(b"\x00")
            blk.extra["prefix"] = b""
        p.blocks.append(blk)
        i = end
    if p.tail_start >= len(data):
        p.notes.append("未找到 SOS（像素数据起始标记），文件可能已损坏")
    return p


def _jpeg_category(kind: str, payload: bytes) -> str:
    return {
        EXIF: "exifroot",
        XMP: "xmp",
        IPTC: "iptc",
        COMMENT: "comment",
        C2PA: "ai",
        ICC: "color",
        MPF: "thumb",
        META: "other",
        UNKNOWN: "unknown",
    }.get(kind, "other")


# ---------------------------------------------------------------- PNG

PNG_COLOR = {
    "cHRM": "色度坐标",
    "gAMA": "伽马值",
    "iCCP": "ICC 色彩描述",
    "sBIT": "有效位数",
    "sRGB": "sRGB 色彩空间",
    "bKGD": "背景色",
    "hIST": "直方图",
    "sPLT": "调色板",
    "tRNS": "透明信息",
    "pHYs": "物理尺寸",
    "cICP": "HDR 编码参数",
    "mDCv": "主显示色域",
    "cLLi": "亮度信息",
}
PNG_ANIM = {"acTL": "动画控制", "fcTL": "帧控制", "fdAT": "帧数据"}
PNG_STRUCT = {"IHDR": "图像头", "PLTE": "调色板", "IDAT": "图像数据", "IEND": "结束块",
              "sTER": "立体信息", "sCAL": "缩放", "oFFs": "偏移", "pCAL": "校准",
              "gIFg": "GIF 控制", "gIFt": "GIF 文本", "gIFx": "GIF 扩展"}


def _png_text_keyword(payload: bytes) -> str:
    head = payload.split(b"\x00", 1)[0]
    try:
        return head.decode("utf-8", "ignore")
    except Exception:
        return head.decode("latin-1", "ignore")


def _png_ai_keyword(kw: str) -> bool:
    k = kw.lower()
    return any(t in k for t in ("c2pa", "ai", "generated", "firefly", "diffusion", "credential"))


def parse_png(data: bytes) -> Parsed:
    p = Parsed(fmt="PNG", src=data, head=data[:8], tail_start=len(data))
    n = len(data)
    i = 8
    occ: dict[str, int] = {}
    while i + 12 <= n:
        ctype_bytes = data[i + 4 : i + 8]
        try:
            ctype = ctype_bytes.decode("latin-1")
        except Exception:
            break
        clen = struct.unpack(">I", data[i : i + 4])[0]
        if clen > n - i:
            p.notes.append("PNG 数据块长度异常，解析提前结束")
            break
        payload = data[i + 8 : i + 8 + clen]
        end = i + 12 + clen

        if ctype == "IHDR" and clen >= 8:
            p.width, p.height = struct.unpack(">II", payload[:8])

        kind = META
        name = ctype
        category = "other"
        locked = False
        key_extra = ""
        if ctype in PNG_STRUCT:
            kind, name, locked = STRUCTURAL, f"{ctype} {PNG_STRUCT[ctype]}", True
        elif ctype in PNG_ANIM:
            kind, name, locked = STRUCTURAL, f"{ctype} {PNG_ANIM[ctype]}", True
        elif ctype in PNG_COLOR:
            kind, name, category = ICC, f"{ctype} {PNG_COLOR[ctype]}", "color"
        elif ctype == "tIME":
            kind, name, category = TIME, "tIME 最后修改时间", "time"
        elif ctype == "eXIf":
            kind, name, category = EXIF, "EXIF 数据块", "exifroot"
        elif ctype == "caBX":
            kind, name, category = C2PA, "C2PA 内容凭证", "ai"
        elif ctype in ("tEXt", "zTXt", "iTXt"):
            kw = _png_text_keyword(payload)
            key_extra = ":" + kw
            if kw == "XML:com.adobe.xmp":
                kind, name, category = XMP, "XMP 元数据", "xmp"
            elif _png_ai_keyword(kw):
                kind, name, category = C2PA, f"AI 标记文本 <{kw}>", "ai"
            elif kw.lower() in ("creation time", "creation_time", "date", "timestamp"):
                kind, name, category = TIME, f"时间文本 <{kw}>", "time"
            else:
                kind, name, category = TEXT, f"文本块 <{kw}>", "desc"
        else:
            # 辅助块（首字母小写）可安全移除；关键块（大写）必须保留
            if ctype[:1].islower():
                kind, name, category = UNKNOWN, f"辅助块 {ctype}", "other"
            else:
                kind, name, locked = STRUCTURAL, f"关键块 {ctype}", True

        occ[kind] = occ.get(kind, 0) + 1
        blk = Block(
            key=f"blk:{ctype}:{occ[kind]}{key_extra}",
            kind=kind,
            name=name,
            offset=i,
            size=end - i,
            data=payload,
            category=category,
            locked=locked,
            extra={"ctype": ctype, "keyword": key_extra[1:]},
        )
        p.blocks.append(blk)
        if ctype == "IEND":
            break
        i = end
    return p


# ---------------------------------------------------------------- WEBP

WEBP_IMAGE = {"VP8 ": "有损图像数据", "VP8L": "无损图像数据", "ANMF": "动画帧",
              "ANIM": "动画头", "ALPH": "Alpha 通道", "VP8X": "扩展头"}
WEBP_COLOR = {"ICCP": "ICC 色彩描述", "CLLI": "亮度信息", "MDCV": "主显示色域"}


def parse_webp(data: bytes) -> Parsed:
    p = Parsed(fmt="WEBP", src=data, head=data[:12], tail_start=len(data))
    n = len(data)
    i = 12
    occ: dict[str, int] = {}
    while i + 8 <= n:
        fourcc = data[i : i + 4].decode("latin-1", "ignore")
        size = struct.unpack("<I", data[i + 4 : i + 8])[0]
        payload = data[i + 8 : i + 8 + size]
        end = i + 8 + size + (size & 1)
        if end > n:
            end = n
        if fourcc in WEBP_IMAGE:
            kind, name, locked = STRUCTURAL, f"{fourcc.strip()} {WEBP_IMAGE[fourcc]}", True
            category = "other"
            if fourcc == "VP8 ":
                p.width = struct.unpack("<H", payload[6:8])[0] & 0x3FFF
                p.height = struct.unpack("<H", payload[8:10])[0] & 0x3FFF
            if fourcc == "VP8L":
                b0, b1, b2, b3 = payload[1], payload[2], payload[3], payload[4]
                bits = b0 | (b1 << 8) | (b2 << 16) | (b3 << 24)
                p.width = (bits & 0x3FFF) + 1
                p.height = ((bits >> 14) & 0x3FFF) + 1
        elif fourcc in WEBP_COLOR:
            kind, name, category = ICC, f"{fourcc} {WEBP_COLOR[fourcc]}", "color"
        elif fourcc == "EXIF":
            kind, name, category = EXIF, "EXIF 数据块", "exifroot"
        elif fourcc == "XMP ":
            kind, name, category = XMP, "XMP 元数据", "xmp"
        else:
            kind, name, category = UNKNOWN, f"块 {fourcc}", "other"
        occ[kind] = occ.get(kind, 0) + 1
        p.blocks.append(
            Block(
                key=f"blk:{fourcc.strip()}:{occ[kind]}",
                kind=kind,
                name=name,
                offset=i,
                size=end - i,
                data=payload,
                category=category,
                locked=(kind == STRUCTURAL),
                extra={"fourcc": fourcc},
            )
        )
        i = end
    return p


# ---------------------------------------------------------------- TIFF


def parse_tiff(data: bytes) -> Parsed:
    p = Parsed(fmt="TIFF", src=data, head=b"", tail_start=len(data))
    try:
        import piexif  # noqa

        p.exif = piexif.load(data)
        p.exif_source = "tiff"
        ifd = p.exif.get("0th", {})
        p.width = int(ifd.get(256, 0) or 0)
        p.height = int(ifd.get(257, 0) or 0)
    except Exception as exc:  # pragma: no cover
        p.notes.append(f"TIFF 解析失败：{exc}")
    p.blocks.append(
        Block(
            key="blk:tiff:1",
            kind=EXIF,
            name="TIFF / EXIF 元数据",
            offset=0,
            size=len(data),
            data=data,
            category="exifroot",
            extra={"tiff": True},
        )
    )
    return p


# ---------------------------------------------------------------- 入口


def parse(data: bytes) -> Parsed:
    fmt = detect(data)
    if fmt == "JPEG":
        p = parse_jpeg(data)
    elif fmt == "PNG":
        p = parse_png(data)
    elif fmt == "WEBP":
        p = parse_webp(data)
    elif fmt == "TIFF":
        p = parse_tiff(data)
    else:
        p = Parsed(fmt=fmt, src=data, head=b"", tail_start=0)
        p.notes.append(f"暂不支持无损剥离的格式：{fmt}")

    if p.exif is None:
        for b in p.blocks:
            if b.kind == EXIF and b.data:
                raw = b.data
                if raw.startswith(b"Exif\x00\x00"):
                    b.extra["prefix"] = b"Exif\x00\x00"
                    b.data = raw = raw[6:]
                try:
                    import piexif

                    p.exif = piexif.load(raw)
                    p.exif_source = p.fmt.lower()
                except Exception as exc:
                    p.notes.append(f"EXIF 解析失败：{exc}")
                break
    return p
