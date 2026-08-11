# -*- coding: utf-8 -*-
"""综合逆向脚本：
1) 解析 PE 节表
2) 解析 COFF_SYMBOLS 符号（含字符串表），输出关键函数地址
3) 用 capstone 反汇编 .text 指定 RVA
"""
import struct, sys

PE_PATH = '二中棋.exe'
COFF_PATH = 'COFF_SYMBOLS'

def pe_sections(exe):
    pe = open(exe, 'rb').read()
    peoff = struct.unpack_from('<I', pe, 0x3C)[0]
    nsec = struct.unpack_from('<H', pe, peoff+6)[0]
    opt = struct.unpack_from('<H', pe, peoff+0x14)[0]
    sec_off = peoff + 0x18 + opt
    secs = []
    for i in range(nsec):
        s = sec_off + i*40
        name = pe[s:s+8].rstrip(b'\x00').decode('latin1')
        vsize = struct.unpack_from('<I', pe, s+8)[0]
        vaddr = struct.unpack_from('<I', pe, s+12)[0]
        rsize = struct.unpack_from('<I', pe, s+16)[0]
        raddr = struct.unpack_from('<I', pe, s+20)[0]
        secs.append({'name': name, 'vaddr': vaddr, 'vsize': vsize,
                     'raddr': raddr, 'rsize': rsize})
    return pe, secs

def parse_coff(path):
    data = open(path, 'rb').read()
    n = len(data)
    rec = 18
    # 第一遍：收集 long-name 的 strtab 引用，估算 strtab 基址
    syms = []   # dict: pos(raw record offset), name_raw, value, section, typ, storage, naux
    i = 0
    while i + rec <= n:
        r = data[i:i+rec]
        name8 = r[0:8]
        aux = r[17]
        syms.append({'pos': i, 'name8': name8,
                     'value': struct.unpack_from('<I', r, 8)[0],
                     'section': struct.unpack_from('<H', r, 12)[0],
                     'typ': struct.unpack_from('<H', r, 14)[0],
                     'storage': r[16], 'naux': aux})
        i += rec * (1 + aux)
    # 找 strtab 起点：长名(name8[0:4]全0 或 name8[0]=='/')引用的偏移
    refs = []
    for s in syms:
        n8 = s['name8']
        if n8[0:4] == b'\x00\x00\x00\x00':
            val = struct.unpack_from('<I', n8, 4)[0]
            refs.append((s['pos'] + 4, val))
        elif n8[0:1] == b'/':
            try:
                val = int(n8[1:].rstrip(b'\x00').decode('latin1'))
                refs.append((s['pos'] + 1, val))
            except Exception:
                pass
    strtab_base = min(a - v for a, v in refs) if refs else None
    return data, syms, strtab_base

def sym_name(data, s, strtab_base):
    n8 = s['name8']
    if n8[0:4] == b'\x00\x00\x00\x00':
        off = struct.unpack_from('<I', n8, 4)[0]
        return cstr(data, strtab_base, off)
    if n8[0:1] == b'/':
        try:
            off = int(n8[1:].rstrip(b'\x00').decode('latin1'))
            return cstr(data, strtab_base, off)
        except Exception:
            return n8.decode('latin1')
    return n8.rstrip(b'\x00').decode('latin1', 'replace')

def cstr(data, base, off):
    if base is None:
        return '<?>'
    p = base + off
    e = data.find(b'\x00', p)
    if e < 0:
        e = len(data)
    return data[p:e].decode('latin1', 'replace')

def main():
    data, syms, strtab_base = parse_coff(COFF_PATH)
    pe, secs = pe_sections(PE_PATH)
    print("strtab_base =", strtab_base)
    sec_by_idx = [None] + secs   # COFF section 号 1-based
    SC = {2: 'EXT', 3: 'STATIC', 104: 'FILE', 1: 'AUTO'}
    out = []
    for s in syms:
        name = sym_name(data, s, strtab_base)
        idx = s['section']
        if 0 < idx < len(sec_by_idx) and sec_by_idx[idx]:
            va = sec_by_idx[idx]['vaddr']
            rva = va + s['value']
        else:
            rva = s['value']
        out.append({'name': name, 'section': idx, 'value': s['value'],
                    'rva': rva, 'storage': SC.get(s['storage'], s['storage'])})
    print(f"symbols: {len(out)}")
    # 关键函数
    print("\n===== 游戏相关函数 (external/static, in .text) =====")
    for o in out:
        low = o['name'].lower()
        if o['section'] == 1 and ('main' in low or 'game' in low or 'home' in low
                                  or 'hint' in low or 'win' in low or 'draw' in low
                                  or 'ai' == low or 'ai' in low or 'menu' in low
                                  or 'start' in low or 'move' in low or 'check' in low
                                  or 'player' in low or 'comp' in low or 'board' in low):
            print(f"  0x{o['rva']:X}  {o['storage']:6} {o['name']}")
    # 所有 .text external 函数
    print("\n===== 所有 .text 中 EXTERNAL 符号 (函数) =====")
    for o in out:
        if o['section'] == 1 and o['storage'] == 'EXT':
            print(f"  0x{o['rva']:X}  {o['name']}")

if __name__ == '__main__':
    main()
