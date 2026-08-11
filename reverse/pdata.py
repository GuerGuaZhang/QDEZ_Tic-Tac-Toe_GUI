# -*- coding: utf-8 -*-
"""从 PE 的 .pdata（RUNTIME_FUNCTION 异常处理表）精确枚举全部函数边界。

这是最可靠的函数定位方式：编译器为每个函数生成一条
{RVA_Begin, RVA_End, RVA_UnwindInfo} 记录，.pdata 即该表。
相比 find_start.py 的 prologue 启发式，它不会把函数尾/数据误判为起点。
"""
import struct

PE_PATH = '二中棋.exe'
IMAGE_BASE = 0x400000

KEY_SYMS = [
    ('main', 0x46E1), ('home', 0x19DE), ('hint', 0x1D7C), ('win', 0x24B7),
    ('player1', 0x319D), ('puthint', 0x321C), ('AI', 0x32DF), ('game', 0x3B7A),
]

def pe_secs(exe):
    pe = open(exe, 'rb').read()
    peoff = struct.unpack_from('<I', pe, 0x3C)[0]
    nsec = struct.unpack_from('<H', pe, peoff + 6)[0]
    opt = struct.unpack_from('<H', pe, peoff + 0x14)[0]
    off = peoff + 0x18 + opt
    secs = []
    for i in range(nsec):
        s = off + i * 40
        name = pe[s:s + 8].rstrip(b'\x00').decode('latin1')
        vsize = struct.unpack_from('<I', pe, s + 8)[0]
        vaddr = struct.unpack_from('<I', pe, s + 12)[0]
        rsize = struct.unpack_from('<I', pe, s + 16)[0]
        raddr = struct.unpack_from('<I', pe, s + 20)[0]
        secs.append({'name': name, 'vaddr': vaddr, 'vsize': vsize,
                     'raddr': raddr, 'rsize': rsize})
    return pe, secs

def main():
    pe, secs = pe_secs(PE_PATH)
    pdata = next(s for s in secs if s['name'] == '.pdata')
    raw = pe[pdata['raddr']:pdata['raddr'] + pdata['rsize']]
    n = len(raw) // 12
    funcs = []
    for i in range(n):
        beg, end, uw = struct.unpack_from('<III', raw, i * 12)
        funcs.append((beg, end, uw))
    funcs.sort()
    print(f".pdata 函数数: {n}")
    print(f"{'name':<10}{'symbol':>10}{'start':>10}{'end':>10}{'size':>8}")
    for name, rva in KEY_SYMS:
        hit = [f for f in funcs if f[0] <= rva < f[1]]
        if hit:
            beg, end, uw = hit[0]
            print(f"{name:<10}0x{rva:08X}  0x{beg:08X}  0x{end:08X}  {end - beg:6d}")
        else:
            print(f"{name:<10}0x{rva:08X}  (未命中 .pdata)")
    # 相邻函数间隙（帮助确认各函数之间的连续填充）
    print("\n关键符号所在函数的前后邻居:")
    for name, rva in KEY_SYMS:
        idx = next((i for i, f in enumerate(funcs) if f[0] <= rva < f[1]), None)
        if idx is None:
            continue
        for j in (idx - 1, idx, idx + 1):
            if 0 <= j < len(funcs):
                beg, end, uw = funcs[j]
                print(f"  #{j:5d}  0x{beg:08X}..0x{end:08X}  ({end - beg:5d}B)  {'<-- ' + name if j == idx else ''}")

if __name__ == '__main__':
    main()
