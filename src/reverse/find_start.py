# -*- coding: utf-8 -*-
"""向前扫描定位函数真实起点（prologue）。"""
import struct
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

def rva_to_raw(secs, rva):
    for s in secs:
        if s['vaddr'] <= rva < s['vaddr'] + s['vsize']:
            return s['raddr'] + (rva - s['vaddr'])
    return None

PROLOG = ('push', 'endbr64', 'mov', 'sub', 'xor', 'lea', 'nop', 'jmp', 'int3')

def is_prologue_start(md, code, raw, rva, maxlen=24):
    """从 raw 反汇编几条，判断是否像函数开头。"""
    chunk = code[raw:raw+maxlen]
    ins = list(md.disasm(chunk, IMAGE_BASE+rva))
    if not ins:
        return False
    first = ins[0]
    # 典型 prologue
    if first.mnemonic in ('push', 'endbr64', 'pop'):
        return True
    if first.mnemonic == 'mov' and first.op_str.startswith('rbp'):
        return True
    if first.mnemonic == 'sub' and first.op_str.startswith('rsp'):
        return True
    return False

def find_start(secs, code, rva, back=0x80):
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    # 从 rva-back 到 rva 逐字节试
    for off in range(back, -1, -1):
        cand = rva - off
        raw = rva_to_raw(secs, cand)
        if raw is None:
            continue
        if is_prologue_start(md, code, raw, cand):
            # 向前多验证：继续反汇编几条看是否全部合法
            chunk = code[raw:raw+30]
            ins = list(md.disasm(chunk, IMAGE_BASE+cand))
            if len(ins) >= 3:
                return cand, ins[:3]
    return rva, None

def main():
    pe, secs = pe_secs(PE_PATH)
    text = next(s for s in secs if s['name'] == '.text')
    code = pe[text['raddr']:text['raddr']+text['rsize']]
    funcs = [('main',0x46E1),('home',0x19DE),('hint',0x1D7C),
             ('win',0x24B7),('AI',0x32DF),('game',0x3B7A)]
    for name, rva in funcs:
        start, ins = find_start(secs, code, rva)
        print(f"{name}: symbol@0x{rva:X}  start@0x{start:X}")
        if ins:
            for i in ins[:3]:
                print(f"    0x{i.address:X}: {i.mnemonic} {i.op_str}")
        else:
            # 也反汇编 symbol 处的几条
            raw = rva_to_raw(secs, rva)
            md = Cs(CS_ARCH_X86, CS_MODE_64)
            for i in list(md.disasm(code[raw:raw+24], IMAGE_BASE+rva))[:3]:
                print(f"    0x{i.address:X}: {i.mnemonic} {i.op_str}")

if __name__ == '__main__':
    main()
