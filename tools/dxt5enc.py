# -*- coding: utf-8 -*-
"""极简 DXT5(BC3) 编码器：输入 8 位 alpha 灰度图，输出 DDS 字节。

字形图集是"白字 + alpha"，颜色通道恒为白，所以颜色块用常量即可，
只需要认真编码 alpha 块。
"""
import struct


def encode_dxt5(alpha, w, h):
    """alpha: bytes (w*h, 0..255)。返回 128 字节头之后的 DDS 数据。"""
    out = bytearray()
    bw = (w + 3) // 4
    for by in range((h + 3) // 4):
        for bx in range(bw):
            vals = []
            for py in range(4):
                y = by * 4 + py
                for px in range(4):
                    x = bx * 4 + px
                    vals.append(alpha[y * w + x] if (x < w and y < h) else 0)
            a0 = max(vals)
            a1 = min(vals)
            if a0 == a1:
                # 全等：用 8 值模式也无所谓，索引全 0
                alphas = [a0] * 8
                bits = 0
            else:
                alphas = [a0, a1]
                for i in range(1, 7):
                    alphas.append(((7 - i) * a0 + i * a1) // 7)
                bits = 0
                for i in range(16):
                    v = vals[i]
                    best = 0
                    bd = 1 << 30
                    for k in range(8):
                        d = abs(alphas[k] - v)
                        if d < bd:
                            bd = d
                            best = k
                    bits |= best << (3 * i)
            out.append(a0)
            out.append(a1)
            out += bits.to_bytes(6, "little")
            # 颜色：常量白 (c0 = c1 = 0xFFFF, 索引全 0)
            out += struct.pack("<HHI", 0xFFFF, 0xFFFF, 0)
    return bytes(out)


def dds_header(w, h, fourcc=b"DXT5"):
    """与原版 Skullgirls 图集完全一致的 DDS 头（含 NVTT 标记）。"""
    hdr = bytearray(128)
    hdr[0:4] = b"DDS "
    struct.pack_into("<I", hdr, 4, 124)
    struct.pack_into("<I", hdr, 8, 0x00081007)     # caps|height|width|pixelformat|linearsize
    struct.pack_into("<I", hdr, 12, h)
    struct.pack_into("<I", hdr, 16, w)
    struct.pack_into("<I", hdr, 20, w * h)         # dwPitchOrLinearSize（DXT5 每像素 1 字节）
    struct.pack_into("<I", hdr, 24, 0)             # depth
    struct.pack_into("<I", hdr, 28, 1)             # mipmap 数
    hdr[60:64] = b"UVER"
    hdr[68:72] = b"NVTT"
    struct.pack_into("<I", hdr, 72, 0x00020100)
    struct.pack_into("<I", hdr, 76, 32)            # ddspf.dwSize
    struct.pack_into("<I", hdr, 80, 0x4)           # DDPF_FOURCC
    hdr[84:88] = fourcc
    struct.pack_into("<I", hdr, 108, 0x1000)       # caps
    return bytes(hdr)


def make_dds(alpha, w, h):
    return dds_header(w, h) + encode_dxt5(alpha, w, h)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "work")
    from gdi_font import render
    from dxt5 import decode_bc3, write_png_gray

    W, H, px = render(list("骷髅女孩汉化测试ABC123"), "SimHei", 32, 36, 36, 8)
    # 放到 256x256 画布上
    S = 256
    canvas = bytearray(S * S)
    for y in range(min(H, S)):
        for x in range(min(W, S)):
            canvas[y * S + x] = px[y * W + x]
    dds = make_dds(bytes(canvas), S, S)
    print("dds size:", len(dds), "(expect", 128 + S * S, ")")
    back = decode_bc3(dds[128:], S, S)
    err = sum(abs(back[i] - canvas[i]) for i in range(S * S))
    print("round-trip avg error: %.2f" % (err / float(S * S)))
    write_png_gray("work/dxt5_roundtrip.png", back, S, S)
    print("saved work/dxt5_roundtrip.png")
