# -*- coding: utf-8 -*-
"""用 Windows GDI 把汉字栅格化成 alpha 位图（不依赖 PIL/numpy）。"""
import ctypes
from ctypes import wintypes

gdi32 = ctypes.WinDLL("gdi32")
user32 = ctypes.WinDLL("user32")


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long),
        ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD), ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", ctypes.c_long), ("biYPelsPerMeter", ctypes.c_long),
        ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


def render(chars, font_name, pixel_size, cell_w, cell_h, cols):
    """
    把 chars 栅格化到一张 (cols*cell_w) x (rows*cell_h) 的 8 位灰度图。
    返回 (width, height, bytes) —— 值 0..255 表示覆盖率。
    """
    n = len(chars)
    rows = (n + cols - 1) // cols
    W = cols * cell_w
    H = rows * cell_h

    hdc = gdi32.CreateCompatibleDC(0)
    bi = BITMAPINFO()
    bi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bi.bmiHeader.biWidth = W
    bi.bmiHeader.biHeight = -H          # 自上而下
    bi.bmiHeader.biPlanes = 1
    bi.bmiHeader.biBitCount = 32
    bi.bmiHeader.biCompression = 0      # BI_RGB
    bits = ctypes.c_void_p()
    hbmp = gdi32.CreateDIBSection(hdc, ctypes.byref(bi), 0, ctypes.byref(bits), None, 0)
    old = gdi32.SelectObject(hdc, hbmp)

    # 白字黑底
    buf = ctypes.cast(bits, ctypes.POINTER(ctypes.c_ubyte))
    for i in range(W * H * 4):
        buf[i] = 0

    hfont = gdi32.CreateFontW(
        -pixel_size, 0, 0, 0, 400, 0, 0, 0,
        0x86,          # GB2312_CHARSET
        0, 0, 5,       # CLEARTYPE_QUALITY
        0, font_name)
    oldfont = gdi32.SelectObject(hdc, hfont)
    gdi32.SetBkMode(hdc, 1)          # TRANSPARENT
    gdi32.SetTextColor(hdc, 0x00FFFFFF)

    for idx, ch in enumerate(chars):
        cx = (idx % cols) * cell_w
        cy = (idx // cols) * cell_h
        s = ctypes.c_wchar_p(ch)
        gdi32.TextOutW(hdc, cx, cy, s, 1)

    gdi32.GdiFlush()

    out = bytearray(W * H)
    for y in range(H):
        for x in range(W):
            o = (y * W + x) * 4
            out[y * W + x] = buf[o]        # B 通道（灰度）

    gdi32.SelectObject(hdc, oldfont)
    gdi32.DeleteObject(hfont)
    gdi32.SelectObject(hdc, old)
    gdi32.DeleteObject(hbmp)
    gdi32.DeleteDC(hdc)
    return W, H, bytes(out)


if __name__ == "__main__":
    import sys
    txt = "骷髅女孩永不言弃汉化测试"
    W, H, px = render(list(txt), "SimHei", 32, 34, 34, 10)
    print("rendered %dx%d" % (W, H))
    # 存成 PNG 预览
    sys.path.insert(0, "work")
    from dxt5 import write_png_gray
    write_png_gray("work/gdi_test.png", px, W, H)
    print("saved work/gdi_test.png")
