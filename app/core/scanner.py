"""把解析出的结构转换为"人能看懂、可勾选"的元数据条目。"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from . import formats as F

# ---------------------------------------------------------------- 分类定义

CATEGORIES: list[tuple[str, str, str, bool, str]] = [
    # key, 名称, 说明, 默认移除, 强调色
    ("ai", "AI 标记 / 内容凭证", "C2PA 凭证、AI 生成声明、合成来源类型", True, "#AF52DE"),
    ("gps", "位置信息", "经纬度、海拔、航向、GPS 时间", True, "#FF3B30"),
    ("time", "时间与日期", "拍摄时间、数字化时间、修改时间、时区", True, "#FF9500"),
    ("device", "设备与镜头", "厂商、型号、序列号、镜头型号与固件", True, "#007AFF"),
    ("software", "软件与编辑记录", "处理软件、主机信息、编辑历史", True, "#5E5CE6"),
    ("desc", "描述与关键词", "标题、说明、注释、关键词", True, "#00A3A3"),
    ("author", "作者与版权", "艺术家、版权、署名（移除后无法追溯归属）", False, "#34C759"),
    ("thumb", "缩略图", "内嵌缩略图与 MPF 多画面数据", True, "#8E8E93"),
    ("xmp", "XMP 数据块", "Adobe XMP 整块（含编辑历史与 AI 声明）", True, "#5856D6"),
    ("iptc", "IPTC 数据块", "标题、来源、数字来源类型、版权声明", True, "#C77CFF"),
    ("comment", "注释段", "JPEG COM 注释", True, "#A2845E"),
    ("shoot", "拍摄参数", "曝光、光圈、ISO、焦距、白平衡、闪光灯", False, "#0A84FF"),
    ("color", "色彩与显示", "ICC 描述、色彩空间、方向、伽马（建议保留）", False, "#30B0C7"),
    ("unknown", "未知数据段", "无法识别的元数据段，默认保留以免损坏文件", False, "#8E8E93"),
    ("other", "其他元数据", "可安全移除的其余元数据", True, "#6E6E73"),
    ("image", "图像数据", "压缩像素数据与结构段 —— 程序永不修改", False, "#1C1C1E"),
]

CAT = {c[0]: c for c in CATEGORIES}
CAT_ORDER = [c[0] for c in CATEGORIES]

# ---------------------------------------------------------------- EXIF 归类

_DEVICE = {
    "Make", "Model", "Software", "BodySerialNumber", "LensMake", "LensModel",
    "LensSerialNumber", "CameraOwnerName", "BodySerialNumber", "Firmware",
    "SerialNumber", "InternalSerialNumber", "UniqueCameraModel", "CameraFirmwareVersion",
    "LensFirmwareVersion", "ImageNumber", "UniqueImageID", "CameraSerialNumber",
    "LensInfo", "ImageUniqueID", "DeviceSettingDescription", "MakerNote",
    "MakerNoteSafety", "RawDevelopmentIdentifier", "OwnerName", "CameraOwnerName",
}
_SOFTWARE = {
    "Software", "ProcessingSoftware", "HostComputer", "ApplicationNotes",
    "ProfileName", "ImageHistory", "PhotoshopSettings", "MSDocumentText",
    "MSPropertySetStorage", "GDALMetadata", " croppingHistory",
}
_DESC = {
    "ImageDescription", "XPTitle", "XPSubject", "XPComment", "XPKeywords",
    "UserComment", "PictureInfo", "WinTitle", "WinComment", "WinKeywords",
    "Caption", "CaptionAbstract", "ObjectName", "Keywords", "Headline",
}
_AUTHOR = {
    "Artist", "Copyright", "XPAuthor", "ByLine", "ByLineTitle", "Credit",
    "CopyrightNotice", "Rights", "Creator", "OwnerName",
}
_TIME = {
    "DateTime", "DateTimeOriginal", "DateTimeDigitized", "SubSecTime",
    "SubSecTimeOriginal", "SubSecTimeDigitized", "OffsetTime", "OffsetTimeOriginal",
    "OffsetTimeDigitized", "TimeCreated", "DigitalCreationDateTime",
    "DateTimeCreated", "ModifyDate", "CreateDate", "GPSDateStamp", "GPSTimeStamp",
    "SubSecTimeOriginal", "SubSecTimeDigitized",
}
_COLOR = {
    "Orientation", "ColorSpace", "ComponentsConfiguration", "YCbCrPositioning",
    "YCbCrCoefficients", "YCbCrSubSampling", "TransferFunction",
    "ReferenceBlackWhite", "Gamma", "WhitePoint", "PrimaryChromaticities",
    "Chromaticities", "ColorSpaceTransform", "InteroperabilityIndex",
    "InteroperabilityVersion", "ExifVersion", "FlashpixVersion",
    "SensingMethod", "ResolutionUnit", "XResolution", "YResolution",
    "SamplesPerPixel", "PlanarConfiguration", "Compression", "PhotometricInterpretation",
}
_SHOOT = {
    "ExposureTime", "FNumber", "ExposureProgram", "ISOSpeedRatings", "ISOSpeed",
    "PhotographicSensitivity", "SensitivityType", "RecommendedExposureIndex",
    "ShutterSpeedValue", "ApertureValue", "BrightnessValue", "ExposureBiasValue",
    "MaxApertureValue", "SubjectDistance", "MeteringMode", "LightSource", "Flash",
    "FocalLength", "FlashEnergy", "SpatialFrequencyResponse", "SubjectLocation",
    "ExposureIndex", "FocalLengthIn35mmFilm", "SceneCaptureType", "GainControl",
    "Contrast", "Saturation", "Sharpness", "SubjectDistanceRange", "DigitalZoomRatio",
    "FocalPlaneXResolution", "FocalPlaneYResolution", "ExposureMode", "WhiteBalance",
    "SceneType", "CustomRendered", "SubjectArea", "Temperature", "Humidity",
    "Pressure", "WaterDepth", "Acceleration", "CameraElevationAngle", "CompositeImage",
    "FocusDistance", "FocusMode", "ImageStabilization", "RecommendedExposureIndex",
}

AI_PATTERNS = [
    "c2pa", "content credentials", "contentcredential", "jumbf",
    "trainedalgorithmicmedia", "digitalsourcetype", "digitalsourcefiletype",
    "generativeai", "generative ai", "ai generated", "ai-generated",
    "made with ai", "firefly", "adobe firefly", "stable diffusion", "midjourney",
    "dall-e", "dalle", "comfyui", "novelai", "sdxl", "fooocus", "invokeai",
    "automatic1111", "imagen", "flux.1", "gpt-4o image", "seedream",
    "即梦", "通义万相", "文心一格", "可灵", "智谱清言", "纳米香蕉",
]


def looks_like_ai(text: str) -> str | None:
    low = text.lower()
    for pat in AI_PATTERNS:
        if pat in low:
            return pat
    return None


def exif_category(ifd: str, name: str) -> str:
    if ifd == "GPS":
        return "gps"
    if ifd == "1st":
        return "thumb"
    if name in _TIME:
        return "time"
    if name == "MakerNote":
        return "device"
    if name in _SOFTWARE:
        return "software"
    if name in _DEVICE:
        return "device"
    if name in _DESC:
        return "desc"
    if name in _AUTHOR:
        return "author"
    if name in _COLOR:
        return "color"
    if name in _SHOOT:
        return "shoot"
    if name.startswith("DateTime") or name.startswith("SubSec") or name.startswith("OffsetTime"):
        return "time"
    if name.startswith("GPS"):
        return "gps"
    if name.startswith("Lens") or name.startswith("Camera"):
        return "device"
    if name.startswith("XP"):
        return "desc"
    if ifd == "Exif":
        return "shoot"
    return "other"


# ---------------------------------------------------------------- 值格式化


def _ratio(v) -> float | None:
    try:
        if isinstance(v, tuple) and len(v) == 2:
            num, den = v
            return float(num) / float(den) if den else None
        if isinstance(v, (int, float)):
            return float(v)
    except Exception:
        return None
    return None


def _dms(v) -> str | None:
    if isinstance(v, tuple) and len(v) == 3:
        out = []
        for r in v:
            f = _ratio(r)
            if f is None:
                return None
            out.append(f)
        return "{:.0f}°{:.0f}′{:.2f}″".format(*out)
    return None


def _decode_bytes(raw: bytes, name: str) -> str:
    if name.startswith("XP") or (len(raw) > 1 and raw[1:2] == b"\x00" and raw[::2] == b"\x00" * (len(raw) // 2)):
        try:
            return raw.decode("utf-16-le").rstrip("\x00")
        except Exception:
            pass
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc).rstrip("\x00")
        except Exception:
            continue
    return repr(raw[:40])


def fmt_value(ifd: str, tag: int, val, name: str) -> str:
    if isinstance(val, bytes):
        if name == "MakerNote":
            return f"厂商私有数据 · {len(val):,} 字节"
        if len(val) > 48:
            return f"二进制数据 · {len(val):,} 字节"
        return _decode_bytes(val, name)
    if name in ("GPSLatitude", "GPSLongitude", "GPSDestLatitude", "GPSDestLongitude"):
        d = _dms(val)
        if d:
            return d
    if isinstance(val, tuple):
        if len(val) > 8:
            return f"{len(val)} 个数值：{str(val[:4])[:-1]} …)"
        return ", ".join(str(x) for x in val)
    s = str(val)
    return s if len(s) <= 120 else s[:117] + "…"


# ---------------------------------------------------------------- 条目


@dataclass
class MetaItem:
    key: str
    label: str
    value: str
    category: str
    default_remove: bool
    locked: bool = False
    size: int = 0
    note: str = ""


@dataclass
class FileScan:
    path: str
    name: str
    size: int
    fmt: str
    width: int
    height: int
    parsed: F.Parsed | None = None
    items: list[MetaItem] = field(default_factory=list)
    ok: bool = True
    error: str = ""
    thumb_bytes: bytes = b""

    @property
    def meta_count(self) -> int:
        return len(self.items)


# ---------------------------------------------------------------- XMP / IPTC 探测

_XMP_AI_RE = re.compile(
    rb"([A-Za-z0-9_.\-]+:)?(DigitalSourceType|digitalSourceType|TrainedAlgorithmicMedia|"
    rb"trainedAlgorithmicMedia|GenerativeAi|generativeAi|AITool|AIInfo|GenerativeAI|"
    rb"DigitalSourceFileType)\s*(?:=\s*\"([^\"]*)\"|>([^<]*)<)"
)
_XMP_NS_RE = re.compile(rb"xmlns:([A-Za-z0-9_.\-]+)=\"([^\"]*(?:c2pa|adobe:xmp)[^\"]*)\"", re.I)


def scan_xmp_ai(raw: bytes) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for m in _XMP_AI_RE.finditer(raw):
        val = (m.group(3) or m.group(4) or b"").decode("utf-8", "ignore").strip()
        name = (m.group(2) or b"").decode()
        found.append((name, val or "（已声明）"))
    if b"c2pa" in raw.lower():
        found.append(("C2PA 声明", f"XMP 中检测到 c2pa 命名空间 · {len(raw):,} 字节"))
    if b"jumbf" in raw.lower():
        found.append(("JUMBF 凭证", "XMP 中检测到 JUMBF 凭证引用"))
    # 去重
    seen, out = set(), []
    for n, v in found:
        if n in seen:
            continue
        seen.add(n)
        out.append((n, v))
    return out


def scan_iptc_ai(raw: bytes) -> bool:
    # IPTC IIM 2:160 Digital Source Type  或 明文 AI 关键字
    if b"\x1c\x02\xa0" in raw:
        return True
    low = raw.lower()
    return any(t in low for t in (b"trainedalgorithmicmedia", b"c2pa", b"generative ai"))


# ---------------------------------------------------------------- 扫描


def _tag_name(ifd: str, tag: int) -> str:
    try:
        import piexif

        table = {
            "0th": "Image",
            "1st": "Thumbnail",
            "Exif": "Exif",
            "GPS": "GPS",
            "Interop": "Interop",
        }.get(ifd, ifd)
        return piexif.TAGS.get(table, {}).get(tag, {}).get("name", f"标签 0x{tag:04X}")
    except Exception:
        return f"标签 0x{tag:04X}"


def build_items(p: F.Parsed) -> list[MetaItem]:
    items: list[MetaItem] = []

    # 1) EXIF 标签
    if p.exif:
        for ifd in ("0th", "Exif", "GPS", "Interop"):
            tags = p.exif.get(ifd) or {}
            for tag, val in tags.items():
                if tag in (0x8769, 0x8825, 0xA005):  # IFD 指针，由写入器重建
                    continue
                name = _tag_name(ifd, int(tag))
                value = fmt_value(ifd, int(tag), val, name)
                cat = exif_category(ifd, name)
                default = CAT[cat][3]
                note = ""
                hit = looks_like_ai(f"{name} {value}")
                if hit:
                    cat, default, note = "ai", True, f"疑似 AI 生成标记（匹配 “{hit}”）"
                items.append(
                    MetaItem(
                        key=f"exif:{ifd}:{tag}",
                        label=name,
                        value=value,
                        category=cat,
                        default_remove=default,
                        note=note,
                    )
                )
        thumb_tags = p.exif.get("1st") or {}
        thumb = p.exif.get("thumbnail") or b""
        if thumb_tags or thumb:
            n = len(thumb_tags) + (1 if thumb else 0)
            items.append(
                MetaItem(
                    key="exif:1st:*",
                    label="内嵌缩略图 (IFD1)",
                    value=f"{n} 项标签 / {len(thumb):,} 字节缩略图",
                    category="thumb",
                    default_remove=True,
                    size=len(thumb),
                    note="缩略图可能携带与原图相同的隐私信息",
                )
            )

    # 2) 其它块
    for b in p.blocks:
        if b.locked:
            continue
        if b.kind == F.EXIF:
            continue  # 由 EXIF 标签条目控制；整块是否丢弃在清理阶段判断
        cat = b.category
        size = b.size
        value = f"{size:,} 字节"
        note = ""
        default = CAT.get(cat, ("", "", "", True, ""))[3]
        if b.kind == F.XMP:
            try:
                text = b.data.decode("utf-8", "ignore")
            except Exception:
                text = ""
            preview = " ".join(text.strip().split())[:80]
            value = f"{size:,} 字节 · {preview}…"
            for nm, val in scan_xmp_ai(b.data):
                items.append(
                    MetaItem(
                        key=f"xmpai:{nm}",
                        label=f"XMP · {nm}",
                        value=val[:100],
                        category="ai",
                        default_remove=True,
                        size=size,
                        note="从 XMP 中定向移除该字段，其余 XMP 保留",
                    )
                )
        elif b.kind == F.IPTC:
            if scan_iptc_ai(b.data):
                items.append(
                    MetaItem(
                        key="iptc:ai",
                        label="IPTC · 数字来源类型 / AI 声明",
                        value=f"IPTC 内含 AI 生成声明（{size:,} 字节）",
                        category="ai",
                        default_remove=True,
                        size=size,
                        note="IPTC 为二进制结构，移除该声明会连带移除整块 IPTC",
                    )
                )
        elif b.kind == F.C2PA:
            value = f"内容凭证 · {size:,} 字节"
        elif b.kind == F.TEXT:
            kw = b.extra.get("keyword", "")
            try:
                payload = b.data.split(b"\x00", 1)[1] if b"\x00" in b.data else b.data
                if b.extra.get("ctype") == "zTXt":
                    import zlib

                    payload = zlib.decompress(payload[1:])
                value = payload.decode("utf-8", "ignore")[:100]
            except Exception:
                value = f"{size:,} 字节"
            if looks_like_ai(f"{kw} {value}"):
                cat, default = "ai", True
        elif b.kind == F.UNKNOWN:
            note = "无法识别的数据段，默认保留以避免损坏文件"

        items.append(
            MetaItem(
                key=b.key,
                label=b.name,
                value=value,
                category=cat,
                default_remove=default,
                size=size,
                note=note,
            )
        )
    return items


def scan_file(path: str, with_thumb: bool = True) -> FileScan:
    name = os.path.basename(path)
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except Exception as exc:
        return FileScan(path=path, name=name, size=0, fmt="?", width=0, height=0,
                        ok=False, error=f"读取失败：{exc}")
    try:
        size = len(data)
        p = F.parse(data)
        fs = FileScan(
            path=path, name=name, size=size, fmt=p.fmt,
            width=p.width, height=p.height, parsed=p, ok=p.fmt in F.SUPPORTED,
            error="; ".join(p.notes) if p.fmt not in F.SUPPORTED else "",
        )
        if p.fmt in F.SUPPORTED:
            fs.items = build_items(p)
        else:
            fs.error = f"暂不支持无损剥离的格式：{p.fmt}"
        return fs
    except Exception as exc:
        return FileScan(path=path, name=name, size=len(data), fmt="?", width=0,
                        height=0, ok=False, error=f"解析失败：{exc}")
