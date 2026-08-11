# -*- coding: utf-8 -*-
"""用 capstone 反汇编 .text 中指定 RVA 的函数，输出到文件。"""
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
            delta = rva - s['vaddr']
            return s['raddr'] + delta
    return None

def disasm_range(secs, code, start_rva, end_rva):
    """反汇编 [start_rva, end_rva)，返回指令列表 [(abs_addr, mnemonic, op_str, size)]"""
    raw = rva_to_raw(secs, start_rva)
    length = end_rva - start_rva
    chunk = code[raw:raw+length]
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = True
    ins = []
    for i in md.disasm(chunk, IMAGE_BASE + start_rva):
        # 计算跳转/调用目标
        target = None
        if i.mnemonic in ('call', 'jmp', 'jz', 'jnz', 'je', 'jne', 'ja', 'jb',
                          'jae', 'jbe', 'jg', 'jl', 'jge', 'jle', 'jo', 'jno',
                          'js', 'jns', 'jp', 'jnp', 'jcxz', 'jecxz', 'jrcxz',
                          'loop', 'loope', 'loopne', 'jecxz'):
            for op in i.operands:
                if op.type == CS_OP_IMM:
                    target = op.imm
        ins.append({'addr': i.address, 'size': i.size,
                    'mnem': i.mnemonic, 'op': i.op_str, 'target': target})
    return ins

def fmt(ins):
    lines = []
    for x in ins:
        t = f"  -> 0x{x['target']:X}" if x['target'] is not None else ""
        lines.append(f"0x{x['addr']:X}:  {x['mnem']:<7} {x['op']}{t}")
    return "\n".join(lines)

BOUND = {
    'main': 0x49E1,
    'home': 0x1D7C,
    'hint': 0x24B7,
    'win':  0x32DF,
    'AI':   0x3B7A,
    'game': 0x46E1,
}
START = {
    'main': 0x4690,
    'home': 0x19DE,
    'hint': 0x1D7C,
    'win':  0x24B7,
    'AI':   0x32C0,
    'game': 0x3B00,
}

def main():
    pe, secs = pe_secs(PE_PATH)
    text = next(s for s in secs if s['name'] == '.text')
    code = pe[text['raddr']:text['raddr']+text['rsize']]
    for name in ('main','home','hint','win','AI','game'):
        start, end = START[name], BOUND[name]
        ins = disasm_range(secs, code, start, end)
        with open(f'reverse/dis_{name}.asm.txt', 'w', encoding='utf-8') as f:
            f.write(f";;; function {name}  0x{start:X} - 0x{end:X} ({len(ins)} ins)\n")
            f.write(fmt(ins))
        print(f"{name}: 0x{start:X}..0x{end:X} -> {len(ins)} ins")

if __name__ == '__main__':
    main()
