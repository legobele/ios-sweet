#!/usr/bin/env python3
"""Dump the CPU topology from a raw FDT.

Reads the /cpus subtree the way the port's other FDT tools do (per-node
`#address-cells`/`#size-cells`, nameoff resolved against the strings block),
and prints what XNU's topology code will actually see: each cpu node's `reg`,
its `compatible`, and the `enable-method`. Use this instead of assuming the
sweet layout, which is Kryo 470 (A55 at MPIDR Aff1 0x0-0x5, A76 at 0x6/0x7).

Usage:
  py tools/fdt-cpus.py DTB
"""
import struct
import sys

if len(sys.argv) < 2:
    sys.stderr.write(__doc__)
    raise SystemExit(2)

blob = open(sys.argv[1], 'rb').read()
magic, totalsize, off_struct, off_strings = struct.unpack_from('>IIII', blob, 0)
if magic != 0xD00DFEED:
    raise SystemExit('%s: not a raw FDT (magic %#x)' % (sys.argv[1], magic))
size_strings, size_struct = struct.unpack_from('>II', blob, 32)
strings = blob[off_strings:off_strings + size_strings]

pos = off_struct
stack = []
nodes = []


def nameof(off):
    return strings[off:strings.index(b'\0', off)].decode('ascii', 'replace')


def cells(node_props, key, default):
    raw = node_props.get(key)
    return default if raw is None else struct.unpack('>I', raw)[0]


def norm(path):
    while '//' in path:
        path = path.replace('//', '/')
    return path


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
            nodes.append((norm('/' + '/'.join([n for n, stack_props in stack] + [name])), props))
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


def u32s(raw):
    if not raw or len(raw) % 4:
        return []
    return list(struct.unpack('>%dI' % (len(raw) // 4), raw))


def strings_of(raw):
    return [s.decode('ascii', 'replace') for s in raw.split(b'\0') if s]


cpus = [(p, pr) for p, pr in nodes if p.startswith('/cpus')]
print('%d nodes under /cpus in %s' % (len(cpus), sys.argv[1]))
print()

for path, props in sorted(cpus):
    reg = u32s(props.get('reg', b''))
    compat = strings_of(props.get('compatible', b''))
    meth = strings_of(props.get('enable-method', b''))
    print('  %s' % path)
    if reg:
        # A cpu node's reg is <mpidr> or <aff1 aff0> depending on #address-cells
        print('      reg            %s' % ' '.join('0x%x' % w for w in reg))
        if len(reg) >= 2:
            print('      implied MPIDR  %s' % ('0x%x' % (((reg[0] & 0xff) << 8) | (reg[1] & 0xff))))
        elif len(reg) == 1:
            print('      implied MPIDR  %s' % ('0x%x' % reg[0]))
    if compat:
        print('      compatible     %s' % ' | '.join(compat))
    if meth:
        print('      enable-method  %s' % ' | '.join(meth))
    for k in ('device_type', 'regulator-allow-set-load'):
        if k in props:
            print('      %-14s %r' % (k, props[k][:48]))
    print()

print('=== cpu-map / cluster nodes (logical CPU -> physical) ===')
found = False
for path, props in sorted(nodes):
    if 'cpu-map' in path or '/cpus/cpu-map' in path:
        found = True
        print('  %-40s reg=%s' % (path, ' '.join('0x%x' % w for w in u32s(props.get('reg', b'')))))
if not found:
    print('  (none: this tree has no cpu-map, so ml_topology derives clusters from MPIDR)')
