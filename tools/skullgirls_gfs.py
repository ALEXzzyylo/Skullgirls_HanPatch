#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skullgirls 「Reverge Package File」(.gfs) 工具箱
================================================

格式（由本工具逆向确认，已用 18 个 .gfs 文件校验：所有条目尺寸之和 == 文件正文长度）::

    u32be   dataOffset          # = 4 + 8+len(magic) + 8+len(version) + 8 + Σ(8+len(name)+8+4)
    PascalString(magic)         # u64be 长度 + 字节，实测 "Reverge Package File"
    PascalString(version)       # 实测 "1.1"
    u64be   entryCount
    repeat entryCount:
        PascalString(name)      # u64be 长度 + 字节，例 "core/wordlist.ini"
        u64be   size
        u32be   flags           # 实测恒为 1
    数据区                      # 各条目按表中顺序首尾相接、未压缩

用法::

    python skullgirls_gfs.py list   data01/ui.gfs
    python skullgirls_gfs.py extract data01/ui.gfs -o out_dir [--filter temp/localization]
    python skullgirls_gfs.py pack   out_dir data01/ui_new.gfs [--version 1.1]

说明：`pack` 会把 out_dir 下的所有文件（相对路径即条目名）重新打包成 .gfs，
条目按名字排序，以便复现。
"""

import argparse
import os
import struct
import sys

MAGIC = b"Reverge Package File"
VERSION = b"1.1"


def read_pascal(data, pos):
    n = struct.unpack_from(">Q", data, pos)[0]
    pos += 8
    s = data[pos:pos + n]
    return s, pos + n


def parse(data):
    """返回 (data_offset, entries)，entries = [(name(str), size(int)), ...]"""
    pos = 4
    magic, pos = read_pascal(data, pos)
    version, pos = read_pascal(data, pos)
    count = struct.unpack_from(">Q", data, pos)[0]
    pos += 8
    entries = []
    for _ in range(count):
        name, pos = read_pascal(data, pos)
        size = struct.unpack_from(">Q", data, pos)[0]
        pos += 8
        pos += 4  # flags
        entries.append((name.decode("latin1"), size))
    return pos, magic, version, entries


def iter_files(path):
    """惰性遍历 .gfs 内的条目 -> (name, bytes)"""
    with open(path, "rb") as f:
        data = f.read()
    data_off, magic, version, entries = parse(data)
    if magic != MAGIC:
        raise ValueError("不是 .gfs 文件 (magic=%r)" % magic)
    off = data_off
    for name, size in entries:
        yield name, memoryview(data)[off:off + size]
        off += size


def cmd_list(args):
    with open(args.gfs, "rb") as f:
        data = f.read()
    data_off, magic, version, entries = parse(data)
    total = sum(s for _, s in entries)
    print(f"# {args.gfs}")
    print(f"# magic={magic.decode('latin1')!r} version={version.decode('latin1')!r}")
    print(f"# entries={len(entries)} table_end={data_off} payload={total} filesize={len(data)}")
    for name, size in entries:
        if args.filter and args.filter not in name:
            continue
        print(f"{size:>12}  {name}")


def cmd_extract(args):
    base = args.out
    os.makedirs(base, exist_ok=True)
    n = 0
    for name, blob in iter_files(args.gfs):
        if args.filter and args.filter not in name:
            continue
        dst = os.path.join(base, name.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(blob)
        n += 1
    print(f"extracted {n} files -> {base}")


def build(entries, version=VERSION):
    """entries: [(name, data_bytes)] -> bytes"""
    table = bytearray()
    payload = bytearray()
    for name, blob in entries:
        nb = name.encode("latin1")
        table += struct.pack(">Q", len(nb)) + nb
        table += struct.pack(">Q", len(blob))
        table += struct.pack(">I", 1)
        payload += blob

    head = bytearray()
    head += b"\x00\x00\x00\x00"          # dataOffset, 稍后回填
    head += struct.pack(">Q", len(MAGIC)) + MAGIC
    head += struct.pack(">Q", len(version)) + version
    head += struct.pack(">Q", len(entries))

    data_off = len(head) + len(table)
    struct.pack_into(">I", head, 0, data_off)
    return bytes(head) + bytes(table) + bytes(payload)


def cmd_pack(args):
    entries = []
    for root, _dirs, files in os.walk(args.src):
        for fn in sorted(files):
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, args.src).replace(os.sep, "/")
            entries.append((rel, open(full, "rb").read()))
    entries.sort(key=lambda x: x[0])
    blob = build(entries, args.version.encode("latin1"))
    with open(args.out, "wb") as f:
        f.write(blob)
    print(f"packed {len(entries)} files -> {args.out} ({len(blob)} bytes)")


def main(argv):
    ap = argparse.ArgumentParser(description="Skullgirls .gfs 工具箱")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="列出条目")
    p.add_argument("gfs")
    p.add_argument("--filter", default=None)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("extract", help="解包")
    p.add_argument("gfs")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--filter", default=None)
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("pack", help="打包目录为 .gfs")
    p.add_argument("src")
    p.add_argument("out")
    p.add_argument("--version", default=VERSION.decode())
    p.set_defaults(func=cmd_pack)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
