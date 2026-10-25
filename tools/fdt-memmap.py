#!/usr/bin/env python3
"""Report /memory banks and the free spans between them and /reserved-memory.

This is how mkadt-milanf.py's PHYS_BASE / MEM_SIZE / HIGH_* were derived:
take the unit's own DTB, subtract every reserved-memory carveout, and read
off the hole-free spans. Cross-check the answer against the running device
with `adb shell cat /proc/iomem` - the DTB says what the bootloader
declared, iomem says what a real Linux kernel actually claimed, and a span
that both agree on is a span worth putting in an ADT.

Usage:  py tools/fdt-memmap.py ../recon/milanf-fdt.bin [--min-mb 4]
"""
import struct
import sys

MIN_MB = 4
args = [a for a in sys.argv[1:] if not a.startswith('--')]
for a in sys.argv[1:]:
    if a.startswith('--min-mb='):
        MIN_MB = int(a.split('=', 1)[1])
if not args:
    raise SystemExit(__doc__)

blob = open(args[0], 'rb').read()
magic, totalsize, off_struct, off_strings = struct.unpack_from('>IIII', blob, 0)
size_strings, size_struct = struct.unpack_from('>II', blob, 32)
if magic != 0xD00DFEED:
    raise SystemExit('%s: not a raw FDT (magic %#x)' % (args[0], magic))
strings = blob[off_strings:off_strings + size_strings]

pos, frames = off_struct, []
banks, reserved = [], []


def path_of():
    return '/' + '/'.join(n for n, _ in frames if n)


def cells(data):
    """reg entries are four cells each: base hi/lo, size hi/lo."""
    out = []
    for i in range(0, len(data) - 15, 16):
        bh, bl, sh, sl = struct.unpack_from('>IIII', data, i)
        out.append(((bh << 32) | bl, (sh << 32) | sl))
    return out


while pos < off_struct + size_struct:
    tok = struct.unpack_from('>I', blob, pos)[0]
    pos += 4
    if tok == 1:
        end = blob.index(b'\0', pos)
        frames.append((blob[pos:end].decode('ascii', 'replace'), {}))
        pos = (end + 4) & ~3
    elif tok == 2:
        if frames:
            # path_of() still includes the node being closed, which is the
            # one whose properties were just collected.
            path, props = path_of(), frames[-1][1]
            if path == '/memory' and 'reg' in props:
                banks += cells(props['reg'])
            elif path.startswith('/reserved-memory/') and 'reg' in props:
                for base, size in cells(props['reg'])[:1]:
                    reserved.append((base, size, path))
            frames.pop()
    elif tok == 3:
        length, nameoff = struct.unpack_from('>II', blob, pos)
        pos += 8
        data = blob[pos:pos + length]
        pos = (pos + length + 3) & ~3
        if frames:
            name = strings[nameoff:strings.index(b'\0', nameoff)].decode('ascii', 'replace')
            frames[-1][1][name] = data
    elif tok == 4:
        continue
    elif tok == 9:
        break

print('=== /memory banks ===')
total = 0
for base, size in banks:
    total += size
    print('  0x%011x .. 0x%011x  %8.1f MB' % (base, base + size, size / 1048576.0))
print('  total %.1f MB' % (total / 1048576.0))

print('\n=== free spans >= %d MB (banks minus reserved-memory) ===' % MIN_MB)
for base, size in banks:
    cuts = sorted((b, s) for b, s, _ in reserved if base <= b < base + size)
    cur = base
    for rbase, rsize in cuts:
        if rbase - cur >= MIN_MB << 20:
            print('  0x%011x .. 0x%011x  %8.1f MB' % (cur, rbase, (rbase - cur) / 1048576.0))
        cur = max(cur, rbase + rsize)
    if base + size - cur >= MIN_MB << 20:
        print('  0x%011x .. 0x%011x  %8.1f MB' % (cur, base + size, (base + size - cur) / 1048576.0))
