#!/usr/bin/env python3
"""Find which device-tree node owns a physical address range.

The port has a recurring question: driver X hardcodes base Y - is that still
the right block on this SoC? Answering it by eye against an FDT dump is
tedious and easy to get wrong, so this takes the address and prints the node
that contains it, with its compatible strings.

Cell sizes are read per node (`#address-cells` / `#size-cells` from the
parent, defaulting to 2/2 as Qualcomm trees use), so it works on the mixed
1/1 and 2/2 nodes those trees contain.

Usage:
  py tools/fdt-find.py DTB 0x0c440000 [0x18220000 ...]
"""
import struct
import sys

args = sys.argv[1:]
if len(args) < 2:
    sys.stderr.write(__doc__)
    raise SystemExit(2)

path, wanted = args[0], [int(a, 0) for a in args[1:]]
blob = open(path, 'rb').read()
magic, totalsize, off_struct, off_strings = struct.unpack_from('>IIII', blob, 0)
if magic != 0xD00DFEED:
    raise SystemExit('%s: not a raw FDT (magic %#x)' % (path, magic))
size_strings, size_struct = struct.unpack_from('>II', blob, 32)
strings = blob[off_strings:off_strings + size_strings]

pos = off_struct
stack = []          # [(name, {prop: bytes})]
nodes = []          # [(path, regs, compatible)]


def nameof(off):
    return strings[off:strings.index(b'\0', off)].decode('ascii', 'replace')


def cells(node_props, key, default):
    raw = node_props.get(key)
    return default if raw is None else struct.unpack('>I', raw)[0]


while pos < off_struct + size_struct:
    tok = struct.unpack_from('>I', blob, pos)[0]
    pos += 4
    if tok == 1:                                     # BEGIN_NODE
        end = blob.index(b'\0', pos)
        stack.append([blob[pos:end].decode('ascii', 'replace'), {}])
        pos = (end + 4) & ~3
    elif tok == 2:                                   # END_NODE
        if stack:
            name, props = stack.pop()
            parent = stack[-1][1] if stack else {}
            ac = cells(parent, '#address-cells', 2)
            sc = cells(parent, '#size-cells', 2)
            regs = []
            raw = props.get('reg')
            if raw:
                ent = 4 * (ac + sc)
                for i in range(0, len(raw) - ent + 1, ent):
                    vals = struct.unpack_from('>%dI' % (ac + sc), raw, i)
                    base = 0
                    for v in vals[:ac]:
                        base = (base << 32) | v
                    size = 0
                    for v in vals[ac:]:
                        size = (size << 32) | v
                    if size:
                        regs.append((base, size))
            compat = props.get('compatible', b'').split(b'\0')
            nodes.append(('/' + '/'.join([n for n, _ in stack] + [name]),
                          regs, [c.decode('ascii', 'replace') for c in compat if c]))
    elif tok == 3:                                   # PROP
        length, nameoff = struct.unpack_from('>II', blob, pos)
        pos += 8
        data = blob[pos:pos + length]
        pos = (pos + length + 3) & ~3
        if stack:
            stack[-1][1][nameof(nameoff)] = data
    elif tok == 4:                                   # NOP
        continue
    elif tok == 9:                                   # END
        break

print('%d nodes with reg' % len(nodes))
for addr in wanted:
    hits = [(p, r, c) for p, r, c in nodes
            if any(b <= addr < b + s for b, s in r)]
    print('\n%#x' % addr)
    if not hits:
        print('   (no node contains it)')
        continue
    for p, regs, compat in hits:
        for b, s in regs:
            if b <= addr < b + s:
                print('   %s' % (p or '/'))
                print('     reg        %#x .. %#x  (%#x)' % (b, b + s, s))
                print('     compatible %s' % ' | '.join(compat) if compat else '     compatible (none)')
