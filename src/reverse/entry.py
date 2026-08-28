# -*- coding: utf-8 -*-
"""从入口反汇编并展示所有 call 目标。"""
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

def disasm(secs, code, rva, length):
    raw = rva_to_raw(secs, rva)
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = True
    out = []
    for i in md.disasm(code[raw:raw+length], IMAGE_BASE+rva):
        tgt = None
        for op in i.operands:
            if op.type == CS_OP_IMM and i.mnemonic.startswith(('call','j','loop')):
                tgt = op.imm
        out.append((i.address, i.mnemonic, i.op_str, tgt))
    return out

def main():
    pe, secs = pe_secs(PE_PATH)
    text = next(s for s in secs if s['name'] == '.text')
    code = pe[text['raddr']:text['raddr']+text['rsize']]
    entry = 0x1500
    ins = disasm(secs, code, entry, 0x500)
    for a, m, o, t in ins:
        tl = f"  CALL->0x{t:X}" if t else ""
        print(f"0x{a:X}: {m:<7} {o}{tl}")

if __name__ == '__main__':
    main()
