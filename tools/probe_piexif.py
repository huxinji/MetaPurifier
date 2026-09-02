# -*- coding: utf-8 -*-
"""piexif 行为探针：确认 dump/load 的字节格式，供无损重写方案使用。"""
import piexif

d = {
    "0th": {271: b"Canon", 272: b"Canon EOS R6", 274: 1, 306: b"2026:09:01 10:00:00"},
    "Exif": {33434: (1, 125), 33437: (28, 10), 36867: b"2026:09:01 10:00:00"},
    "GPS": {1: b"N", 2: ((22, 1), (32, 1), (1080, 100)), 3: b"E"},
    "Interop": {},
    "1st": {},
    "thumbnail": None,
}

raw = piexif.dump(d)
print("dump prefix :", raw[:12])
print("dump len    :", len(raw))

payload = raw[6:] if raw.startswith(b"Exif\x00\x00") else raw
back = piexif.load(payload)
print("0th keys    :", sorted(back["0th"].keys()))
print("GPS keys    :", sorted(back["GPS"].keys()))
print("thumbnail   :", back["thumbnail"])

# 只保留 Orientation
d2 = {"0th": {274: 1}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}
r2 = piexif.dump(d2)
b2 = piexif.load(r2[6:] if r2.startswith(b"Exif\x00\x00") else r2)
print("filtered 0th:", b2["0th"], "len:", len(r2))

# 全空
d3 = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}
try:
    r3 = piexif.dump(d3)
    print("empty dump  : ok", r3[:16], len(r3))
except Exception as exc:
    print("empty dump  : ERR", type(exc).__name__, exc)

# 带缩略图
thumb = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 200 + b"\xff\xd9"
d4 = dict(d)
d4["1st"] = {513: 300, 514: len(thumb)}
d4["thumbnail"] = thumb
r4 = piexif.dump(d4)
b4 = piexif.load(r4[6:] if r4.startswith(b"Exif\x00\x00") else r4)
print("with thumb  : 1st=", sorted(b4["1st"].keys()), "thumb bytes:", len(b4["thumbnail"] or b""))

# 去掉缩略图后
d5 = dict(d)
d5["1st"] = {}
d5["thumbnail"] = None
r5 = piexif.dump(d5)
b5 = piexif.load(r5[6:] if r5.startswith(b"Exif\x00\x00") else r5)
print("no thumb    : 1st=", b5["1st"], "thumb:", b5["thumbnail"])
