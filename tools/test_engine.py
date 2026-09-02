"""核心引擎无损性 / 剥离正确性测试（无需 GUI）。"""

import io
import os
import struct
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtGui import QImage  # noqa 仅用于验证可解码（不创建窗口）

import piexif
from PIL import Image

from app.core import cleaner, formats, scanner
from app.core.cleaner import Plan


def make_base_jpeg(path, size=(64, 48)):
    img = Image.new("RGB", size, (120, 160, 220))
    img.save(path, "JPEG", quality=92)


def splice_after_app0(path, segments: list[bytes]):
    data = open(path, "rb").read()
    assert data[:2] == b"\xff\xd8"
    marker = data[2:4]
    seglen = struct.unpack(">H", data[4:6])[0]
    insert_at = 2 + 2 + seglen
    out = data[:insert_at] + b"".join(segments) + data[insert_at:]
    open(path, "wb").write(out)


def seg(marker: int, payload: bytes) -> bytes:
    return bytes([0xFF, marker]) + struct.pack(">H", len(payload) + 2) + payload


XMP = (
    b'<x:xmpmeta xmlns:x="adobe:ns:meta/">'
    b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
    b'<rdf:Description xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/" '
    b'xmlns:c2pa="http://c2pa.org/assertions/1.0/" '
    b'photoshop:DigitalSourceType="http://purl.org/dc/dcmitype/StillImage" '
    b'c2pa:alg="TrainedAlgorithmicMedia">'
    b'<photoshop:Authors position="0"/></rdf:Description></rdf:RDF></x:xmpmeta>'
)
C2PA = b"\x00\x00\x00\x10jumb\x00c2pa-assertion-store-marker-test"


def build_exif():
    d = {
        "0th": {271: b"Canon", 272: b"Canon EOS R6", 274: 1, 306: b"2026:09:01 10:00:00"},
        "Exif": {33434: (1, 125), 33437: (28, 10), 36867: b"2026:09:01 10:00:00",
                 36868: b"2026:09:01 10:00:00"},
        "GPS": {1: b"N", 2: ((22, 1), (32, 1), (1080, 100)), 3: b"E", 4: ((114, 1), (3, 1), (0, 1))},
        "Interop": {},
        "1st": {513: 0, 514: 0},
        "thumbnail": None,
    }
    return piexif.dump(d)


def test_jpeg():
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "t.jpg")
        make_base_jpeg(p)
        piexif.insert(build_exif(), p)
        splice_after_app0(p, [
            seg(0xFE, b"hello comment"),
            seg(0xE1, b"http://ns.adobe.com/xap/1.0/\x00" + XMP),
            seg(0xED, b"Photoshop 3.0\x00" + b"8BIM\x04\x04\x00\x00c2pa-iptc-test"),
            seg(0xEB, C2PA),
        ])
        fs = scanner.scan_file(p)
        assert fs.ok, fs.error
        exif_keys = {it.key for it in fs.items if it.key.startswith("exif:")}
        assert any("GPS" in k for k in exif_keys), "GPS 未被扫描到"
        assert any(k.startswith("blk:") and "C2PA" in k for k in [it.key for it in fs.items]) or \
            any(it.category == "ai" for it in fs.items), "C2PA 未被识别"

        # 移除所有可勾选项
        plan = Plan(remove={it.key for it in fs.items if it.default_remove} | {it.key for it in fs.items if it.category in ("ai",)},
                    xmp_ai=True, iptc_ai=True)
        data = open(p, "rb").read()
        parsed = formats.parse(data)
        out, res = cleaner.apply_plan(data, parsed, plan)
        assert res.ok, res.error
        assert res.payload_ok, f"像素校验失败: {res.verify_note}"
        # 输出可正常解码
        im = Image.open(io.BytesIO(out))
        im.load()
        assert im.size == (64, 48)
        # 重新扫描应无 GPS / XMP / C2PA
        p2 = os.path.join(td, "t_out.jpg")
        open(p2, "wb").write(out)
        fs2 = scanner.scan_file(p2)
        remaining = {it.key for it in fs2.items}
        assert not any("GPS" in k for k in remaining), "GPS 未被移除"
        assert not any(it.category == "ai" for it in fs2.items), "AI/C2PA 未被移除"
        print(f"[JPEG] OK  移除 {res.removed_items} 项 | 校验 {res.verify_note} | "
              f"体积 {len(data)}→{len(out)}")


def test_png_webp():
    with tempfile.TemporaryDirectory() as td:
        for fmt, ext in (("PNG", "png"), ("WEBP", "webp")):
            p = os.path.join(td, f"t.{ext}")
            Image.new("RGB", (48, 36), (10, 200, 120)).save(p, fmt)
            fs = scanner.scan_file(p)
            assert fs.ok, fs.error
            plan = Plan(remove={it.key for it in fs.items if it.default_remove})
            data = open(p, "rb").read()
            parsed = formats.parse(data)
            out, res = cleaner.apply_plan(data, parsed, plan)
            assert res.ok, res.error
            assert res.payload_ok, f"{fmt} 像素校验失败: {res.verify_note}"
            im = Image.open(io.BytesIO(out))
            im.load()
            print(f"[{fmt}]  OK  移除 {res.removed_items} 项 | 校验 {res.verify_note} | "
                  f"体积 {len(data)}→{len(out)}")


if __name__ == "__main__":
    test_jpeg()
    test_png_webp()
    print("\n全部核心测试通过 ✓")
