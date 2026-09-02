"""无损清理执行器：只重写 / 丢弃元数据块，像素数据逐字节不动。"""

from __future__ import annotations

import hashlib
import re
import struct
import zlib
from dataclasses import dataclass, field

from . import formats as F
from . import scanner as S

# ---------------------------------------------------------------- 计划


@dataclass
class Plan:
    remove: set[str] = field(default_factory=set)
    xmp_ai: bool = False
    iptc_ai: bool = False


@dataclass
class CleanResult:
    ok: bool = False
    src: str = ""
    dst: str = ""
    before: int = 0
    after: int = 0
    removed_items: int = 0
    payload_ok: bool = False
    verify_note: str = ""
    note: str = ""
    error: str = ""


# ---------------------------------------------------------------- 指纹校验


def fingerprint(p: F.Parsed) -> tuple[bytes, str]:
    """计算"只与像素有关"的指纹，用于证明画质未被改动。"""
    h = hashlib.sha256()
    if p.fmt == "JPEG":
        h.update(p.src[p.tail_start :])
        return h.digest(), "JPEG 压缩扫描数据（含色彩量化/Huffman/SOF）"
    if p.fmt == "PNG":
        keep = ("IHDR", "PLTE", "IDAT", "fdAT", "acTL", "fcTL", "tRNS", "sBIT")
        for b in p.blocks:
            if b.extra.get("ctype") in keep:
                h.update(b.extra["ctype"].encode())
                h.update(b.data)
        return h.digest(), "PNG 图像头 + 全部 IDAT 像素流"
    if p.fmt == "WEBP":
        for b in p.blocks:
            if b.locked:
                h.update(b.extra.get("fourcc", "").encode())
                h.update(b.data)
        return h.digest(), "WebP VP8/VP8L/ALPH 像素块"
    if p.fmt == "TIFF":
        h.update(b"TIFF")
        return h.digest(), "TIFF（整表重建，校验维度与结构）"
    return h.digest(), "未知格式"


# ---------------------------------------------------------------- EXIF 重建


def _empty(d: dict) -> bool:
    return not any(d.get(k) for k in ("0th", "Exif", "GPS", "Interop", "1st")) and not d.get("thumbnail")


def _strip_pointers(d: dict) -> dict:
    out = {}
    for ifd, tags in d.items():
        if ifd == "thumbnail":
            out[ifd] = tags
            continue
        out[ifd] = {t: v for t, v in (tags or {}).items() if t not in (0x8769, 0x8825, 0xA005)}
    return out


def _exif_tiff_bytes(d: dict) -> bytes:
    import piexif

    raw = piexif.dump(_strip_pointers(d))
    if raw.startswith(b"Exif\x00\x00"):
        raw = raw[6:]
    return raw


def filter_exif(d: dict, remove: set[str]) -> tuple[dict, int]:
    """返回（过滤后的 exif dict, 被移除的标签数）。"""
    new: dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}
    n = 0
    for ifd in ("0th", "Exif", "GPS", "Interop"):
        for tag, val in (d.get(ifd) or {}).items():
            if tag in (0x8769, 0x8825, 0xA005):
                continue
            key = f"exif:{ifd}:{tag}"
            if key in remove:
                n += 1
                continue
            new[ifd][int(tag)] = val
    if "exif:1st:*" in remove:
        tags = d.get("1st") or {}
        n += len(tags)
        if d.get("thumbnail"):
            n += 1
    else:
        new["1st"] = dict(d.get("1st") or {})
        new["thumbnail"] = d.get("thumbnail")
    return new, n


# ---------------------------------------------------------------- XMP 定向剥离

_AI_TOKENS = [
    b"DigitalSourceType", b"digitalSourceType", b"DigitalSourceFileType",
    b"TrainedAlgorithmicMedia", b"trainedAlgorithmicMedia", b"GenerativeAi",
    b"generativeAi", b"GenerativeAI", b"AITool", b"AIInfo", b"Algorithm",
]


def strip_xmp_ai(raw: bytes) -> tuple[bytes | None, str]:
    text = raw
    for tok in _AI_TOKENS:
        text = re.sub(rb"\s*[A-Za-z0-9_.\-]*(?:[:.])?" + tok + rb'\s*=\s*"[^"]*"', b"", text)
        text = re.sub(rb"<([A-Za-z0-9_.\-]+:)?" + tok + rb"\b[^>]*(?:/>|>.*?</([A-Za-z0-9_.\-]+:)?" + tok + rb">)", b"", text, flags=re.S)
    # C2PA 命名空间与元素
    text = re.sub(rb'\s+xmlns:[A-Za-z0-9_.\-]+="[^"]*c2pa[^"]*"', b"", text, flags=re.I)
    text = re.sub(rb"<([A-Za-z0-9_.\-]*c2pa[A-Za-z0-9_.\-]*):([A-Za-z0-9_.\-]+)\b[^>]*(?:/>|>.*?</\1:\2>)", b"", text, flags=re.S | re.I)
    text = re.sub(rb"<[A-Za-z0-9_.\-:]*jumb[A-Za-z0-9_.\-:]*\b[^>]*(?:/>|>.*?</[A-Za-z0-9_.\-:]*jumb[A-Za-z0-9_.\-:]*>)", b"", text, flags=re.S | re.I)

    if b"c2pa" in text.lower() or b"jumbf" in text.lower():
        return None, "XMP 中残留 C2PA 结构，已整块移除以确保清理彻底"
    stripped = text.strip()
    if not stripped.startswith(b"<"):
        return None, "XMP 已不再合法，整块移除"
    # 内容是否还有实质属性（排除纯命名空间壳）
    body = re.sub(rb"<[?]xpacket[^>]*>", b"", stripped)
    body = re.sub(rb"<[?]xpacket[^>]*\?>", b"", body, flags=re.S)
    body = re.sub(rb"</?x:xmpmeta[^>]*>", b"", body)
    body = re.sub(rb"\s+", b"", body)
    body = re.sub(rb"<rdf:RDF[^>]*>|</rdf:RDF>", b"", body)
    if len(body) < 8:
        return None, "剥离后 XMP 已为空，整块移除"
    return text, "已定向移除 XMP 中的 AI 生成声明字段"


# ---------------------------------------------------------------- 块重建


def _jpeg_seg(marker: int, payload: bytes) -> bytes:
    return bytes([0xFF, marker]) + struct.pack(">H", len(payload) + 2) + payload


def _png_chunk(ctype: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + ctype + data + struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)


def _webp_chunk(fourcc: bytes, data: bytes) -> bytes:
    return fourcc + struct.pack("<I", len(data)) + data + (b"\x00" if len(data) & 1 else b"")


def _rebuild_block(p: F.Parsed, b: F.Block, newdata: bytes | None) -> bytes | None:
    """按容器格式把改写后的载荷重新封装成块；None 表示丢弃。"""
    if newdata is None:
        return None
    if p.fmt == "JPEG":
        prefix = b.extra.get("prefix", b"")
        payload = prefix + newdata
        if len(payload) + 2 > 0xFFFF:
            raise ValueError("元数据超过 JPEG 段最大长度（64KB），已放弃重写该段")
        return _jpeg_seg(0xE1 if b.kind in (F.EXIF, F.XMP) else (b.extra.get("marker", 0xE1)), payload)
    if p.fmt == "PNG":
        return _png_chunk(b.extra.get("ctype", "eXIf").encode("latin-1"), newdata)
    if p.fmt == "WEBP":
        return _webp_chunk(b.extra.get("fourcc", b"EXIF"), newdata)
    return newdata  # TIFF


# ---------------------------------------------------------------- 主流程


def clean_bytes(path: str) -> tuple[bytes, F.Parsed]:
    with open(path, "rb") as fh:
        data = fh.read()
    return data, F.parse(data)


def apply_plan(data: bytes, p: F.Parsed, plan: Plan) -> tuple[bytes, CleanResult]:
    res = CleanResult(src="", before=len(data))
    src = p.src
    drop: set[str] = set()
    rewrite: dict[str, bytes] = {}
    removed = 0
    notes: list[str] = []

    exif_touched = any(k.startswith("exif:") for k in plan.remove)

    for b in p.blocks:
        if b.locked:
            continue

        if b.kind == F.EXIF:
            if p.exif and exif_touched:
                new_dict, n = filter_exif(p.exif, plan.remove)
                removed += n
                if _empty(new_dict):
                    drop.add(b.key)
                    notes.append(f"已移除整块 {b.name}（内容已清空）")
                else:
                    try:
                        rewrite[b.key] = _exif_tiff_bytes(new_dict)
                    except Exception as exc:
                        notes.append(f"EXIF 重写失败，改为整块移除：{exc}")
                        drop.add(b.key)
            continue

        if b.kind == F.XMP:
            if b.key in plan.remove:
                drop.add(b.key)
                removed += 1
                continue
            if plan.xmp_ai and b.data:
                new, why = strip_xmp_ai(b.data)
                notes.append(why)
                if new is None:
                    drop.add(b.key)
                    removed += 1
                else:
                    rewrite[b.key] = new
                    removed += 1
            continue

        if b.kind == F.IPTC:
            if b.key in plan.remove:
                drop.add(b.key)
                removed += 1
            elif plan.iptc_ai and S.scan_iptc_ai(b.data):
                drop.add(b.key)
                removed += 1
                notes.append("IPTC 为二进制结构，AI 声明需连同整块 IPTC 一起移除")
            continue

        if b.key in plan.remove:
            drop.add(b.key)
            removed += 1

    # 应用改写 / 丢弃
    out = bytearray()
    out += p.head
    for b in p.blocks:
        if b.key in drop:
            continue
        if b.key in rewrite:
            try:
                raw = _rebuild_block(p, b, rewrite[b.key])
            except ValueError as exc:
                notes.append(str(exc))
                raw = None
            if raw is None:
                continue
            out += raw
            continue
        out += b.bytes_from(src)
    if 0 <= p.tail_start < len(src):
        out += src[p.tail_start :]
    out = bytes(out)

    # TIFF：整表重建
    if p.fmt == "TIFF" and p.exif and exif_touched:
        try:
            new_dict, n = filter_exif(p.exif, plan.remove)
            removed += n
            out = _exif_tiff_bytes(new_dict)
        except Exception as exc:  # pragma: no cover
            res.error = f"TIFF 重写失败：{exc}"
            return data, res

    res.removed_items = removed
    res.note = "；".join(dict.fromkeys(notes))

    # 校验
    try:
        p2 = F.parse(out)
        h1, desc = fingerprint(p)
        h2, _ = fingerprint(p2)
        ok = h1 == h2
        if p.fmt == "TIFF":
            ok = bool(p2.exif) and p2.width == p.width and p2.height == p.height
        res.payload_ok = ok
        res.verify_note = f"{desc}：{'一致 ✓' if ok else '不一致 ✗'}"
    except Exception as exc:  # pragma: no cover
        res.payload_ok = False
        res.verify_note = f"校验异常：{exc}"

    res.after = len(out)
    res.ok = True
    return out, res


# ---------------------------------------------------------------- 文件写入


def unique_path(path: str) -> str:
    import os

    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 1
    while os.path.exists(f"{base}({i}){ext}"):
        i += 1
    return f"{base}({i}){ext}"


def write_output(out: bytes, src_path: str, mode: str, dest_dir: str = "",
                 suffix: str = "_clean", backup: bool = False,
                 backup_dir: str = "") -> tuple[str, str]:
    """mode: overwrite | folder | suffix ；返回 (输出路径, 提示)"""
    import os
    import shutil

    name = os.path.basename(src_path)
    base, ext = os.path.splitext(name)

    if mode == "folder":
        os.makedirs(dest_dir, exist_ok=True)
        dst = unique_path(os.path.join(dest_dir, name))
    elif mode == "suffix":
        dst = unique_path(os.path.join(os.path.dirname(src_path), f"{base}{suffix}{ext}"))
    else:
        dst = src_path

    if mode == "overwrite" and backup:
        try:
            bdir = backup_dir if backup_dir else os.path.join(os.path.dirname(src_path), "原图备份")
            os.makedirs(bdir, exist_ok=True)
            shutil.copy2(src_path, unique_path(os.path.join(bdir, name)))
        except Exception as exc:
            raise RuntimeError(f"备份失败，已中止覆盖：{exc}")

    tmp = dst + ".__tmp"
    with open(tmp, "wb") as fh:
        fh.write(out)
        fh.flush()
    import os as _os

    _os.replace(tmp, dst)
    return dst, ("已覆盖原图" if mode == "overwrite" else "已另存")
