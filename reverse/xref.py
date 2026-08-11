# -*- coding: utf-8 -*-
"""全量反汇编 .text，解析数据引用(lea/mov [rip+X])指向的字符串 + call 调用图。"""
import struct, io, sys
from capstone import *

PE_PATH = '二中棋.exe'
IMAGE_BASE = 0x400000

def pe_secs(exe):
    pe = open(exe, 'rb').read()
    peoff = struct.unpack_from('<I', pe, 0x3C)[0]
    nsec = struct.unpack_from('<H', pe, peoff+6)[0]
    opt = struct.unpack_from('<H', pe, peoff+0x14)[0]
    off = peoff + 0x18 + opt
    secs = []
    for i in range(nsec):
        s = off + i*40
        name = pe[s:s+8].rstrip(b'\x00').decode('latin1')
        vsize = struct.unpack_from('<I', pe, s+8)[0]
        vaddr = struct.unpack_from('<I', pe, s+12)[0]
        rsize = struct.unpack_from('<I', pe, s+16)[0]
        raddr = struct.unpack_from('<I', pe, s+20)[0]
        secs.append({'name': name, 'vaddr': vaddr, 'vsize': vsize,
                     'raddr': raddr, 'rsize': rsize})
    return pe, secs

def rva_from_abs(abs_addr):
    return abs_addr - IMAGE_BASE

def raw_at(pe, secs, rva):
    for s in secs:
        if s['vaddr'] <= rva < s['vaddr'] + s['vsize']:
            return s['raddr'] + (rva - s['vaddr'])
    return None

def read_string(pe, secs, rva, maxlen=128):
    """从 rva 读一个可打印 ASCII 字符串。"""
    off = raw_at(pe, secs, rva)
    if off is None:
        return None, None
    chunk = pe[off:off+maxlen]
    s_latin = b''
    i = 0
    while i < len(chunk) and chunk[i] != 0:
        s_latin += bytes([chunk[i]])
        i += 1
    if len(s_latin) < 2:
        return None, None
    # 尝试 GBK 解码得到中文（若含非 ascii 字节）
    try:
        s = s_latin.decode('gbk')
    except Exception:
        s = s_latin.decode('latin1')
    return s, False

def main():
    pe, secs = pe_secs(PE_PATH)
    text = next(s for s in secs if s['name'] == '.text')
    code = pe[text['raddr']:text['raddr']+text['rsize']]
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = True

    refs = []       # (instr_abs, str)
    calls = []      # caller_abs -> target_abs
    n_ins = 0
    for i in md.disasm(code, IMAGE_BASE + text['vaddr']):
        n_ins += 1
        if i.mnemonic == 'call' and i.operands and i.operands[0].type == CS_OP_IMM:
            calls.append((i.address, i.operands[0].imm))
            continue
        # lea reg, [rip+X]
        if i.mnemonic == 'lea' and 'rip' in i.op_str:
            # 提取 disp
            import re
            m = re.search(r'\[rip \+ (0x[0-9a-fA-F]+)\]', i.op_str)
            if m:
                disp = int(m.group(1), 16)
                sign = None
                if m is not None:
                    pass
                # 也可能是负偏移：[rip - X]
                target = i.address + i.size + disp
                tv = rva_from_abs(target)
                s, dotted = read_string(pe, secs, tv)
                if s is not None:
                    refs.append((i.address, tv, s))
    print("total ins:", n_ins, " string refs:", len(refs), " calls:", len(calls))
    with open('reverse/xref_strings.txt', 'w', encoding='utf-8') as f:
        f.write("; 字符串交叉引用  (指令地址 -> 目标RVA : 字符串)\n")
        for a, tv, s in refs:
            f.write(f"0x{a:X} -> 0x{tv:X} : {s!r}\n")
    from collections import Counter
    cnt = Counter(t for _, t in calls)
    print("调用关系 top 40:")
    for (c, n) in cnt.most_common(40):
        print(f"  0x{c:08X}  x{n}")

if __name__ == '__main__':
    main()