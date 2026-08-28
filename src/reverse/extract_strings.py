# -*- coding: utf-8 -*-
"""从 PE 文件的节中提取 ASCII / UTF-8 / UTF-16 字符串并写入 UTF-8 文件。"""
import sys

def ascii_strings(buf, minlen=4):
    import re
    out = []
    for m in re.finditer(rb'[\x20-\x7e]{%d,}' % minlen, buf):
        out.append(m.group().decode('latin1'))
    return out

def utf8_strings(buf):
    out = []
    cur = bytearray()
    def flush():
        nonlocal cur
        if len(cur) >= 4:
            try:
                s = bytes(cur).decode('utf-8')
                if any(ord(ch) > 0x7f for ch in s):
                    out.append(s)
            except Exception:
                pass
        cur = bytearray()
    for b in buf:
        if 0x20 <= b <= 0x7e or b >= 0x80:
            cur.append(b)
        else:
            flush()
    flush()
    return list(dict.fromkeys(out))

def utf16_strings(buf):
    out = []
    n = (len(buf) // 2) * 2
    cur = bytearray()
    def flush():
        nonlocal cur
        pairs = bytes(cur)
        if len(pairs) >= 4:
            try:
                s = pairs.decode('utf-16le')
                if any(ord(ch) > 0x7f for ch in s) and all(0x20 <= ord(ch) <= 0xffff for ch in s):
                    out.append(s)
            except Exception:
                pass
        cur = bytearray()
    i = 0
    while i < n:
        cp = int.from_bytes(buf[i:i+2], 'little')
        if 0x20 <= cp < 0xffff:
            cur += buf[i:i+2]
        else:
            flush()
        i += 2
    flush()
    return list(dict.fromkeys(out))

def main(path):
    data = open(path, 'rb').read()
    pe = int.from_bytes(data[0x3C:0x40], 'little')
    nsec = int.from_bytes(data[pe+6:pe+8], 'little')
    opt = int.from_bytes(data[pe+0x14:pe+0x16], 'little')
    sec_off = pe + 0x18 + opt
    lines = []
    secs = []
    for i in range(nsec):
        s = sec_off + i*40
        name = data[s:s+8].rstrip(b'\x00').decode('latin1')
        vsize = int.from_bytes(data[s+8:s+12], 'little')
        vaddr = int.from_bytes(data[s+12:s+16], 'little')
        rsize = int.from_bytes(data[s+16:s+20], 'little')
        raddr = int.from_bytes(data[s+20:s+24], 'little')
        secs.append((name, vaddr, vsize, raddr, rsize))
    for (name, vaddr, vsize, raddr, rsize) in secs:
        if name not in ('.rdata', '.data'):
            continue
        raw = data[raddr:raddr+rsize] if raddr else b''
        lines.append("=" * 70)
        lines.append(f"## SECTION {name}  raw=0x{raddr:X} size=0x{rsize:X} VSz=0x{vsize:X}")
        lines.append("=" * 70)
        a = ascii_strings(raw)
        u8 = utf8_strings(raw)
        u16 = utf16_strings(raw)
        lines.append(f"--- ASCII ({len(a)}) ---")
        for s in a: lines.append("  " + s)
        lines.append(f"--- UTF-8 中文 ({len(u8)}) ---")
        for s in u8: lines.append("  " + s)
        lines.append(f"--- UTF-16 中文 ({len(u16)}) ---")
        for s in u16: lines.append("  " + s)
    with open('reverse/strings_full.txt', 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    print("done, lines:", len(lines))

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '二中棋.exe')