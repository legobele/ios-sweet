#!/usr/bin/env python3
"""Read an Android boot image header, v0 through v4, and report what matters.

Written because milanf's boot images are header v3 and unpack_bootv2.py only
knows v0-v2. Handing it a v3 image does not error - it reads the fields at the
v0 offsets and prints a 512 MB ramdisk, because v3 puts ramdisk_size at offset
12 where v0 keeps kernel_addr. This script picks the layout from the
header_version field instead of assuming one.

The two layouts that matter here:

  v0/v1/v2   kernel_size@8  kernel_addr@12  ramdisk_size@16  ramdisk_addr@20
             second_size@24 second_addr@28  tags_addr@32     page_size@36
             header_version@40  os_version@44  name@48  cmdline@64
             header_size@1644 (v1+), dtb_size@1648 dtb_addr@1652 (v2)

  v3/v4      kernel_size@8  ramdisk_size@12  os_version@16  header_size@20
             reserved@24..39  header_version@40  cmdline@44..1579
             v4 adds a 4096-byte signature immediately after the header.

v3/v4 carry no page size, no load addresses, no second stage and no dtb
section: sections are 4096-aligned, and the dtb lives in the dtbo partition,
handed to the kernel by the bootloader rather than embedded here.

Usage:
  py tools/bootinfo.py IMAGE            human-readable
  py tools/bootinfo.py --emit-sh IMAGE   shell assignments for a builder
"""
import struct
import sys

USAGE = __doc__
argv = sys.argv[1:]
emit_sh = '--emit-sh' in argv
args = [a for a in argv if not a.startswith('--')]
if len(args) != 1:
    sys.stderr.write(USAGE)
    raise SystemExit(2)

path = args[0]
b = open(path, 'rb').read()

if len(b) < 1664 or b[:8] != b'ANDROID!':
    sys.stderr.write('%s: not an Android boot image (need "ANDROID!" magic)\n' % path)
    raise SystemExit(1)

u32 = lambda off: struct.unpack_from('<I', b, off)[0]
u64 = lambda off: struct.unpack_from('<Q', b, off)[0]
roundup = lambda n, p: (n + p - 1) // p * p

header_version = u32(40)
kernel_size = u32(8)
info = {}

if header_version in (0, 1, 2):
    page_size = u32(36)
    if page_size == 0:
        sys.stderr.write('%s: header_version %d but page_size is 0\n'
                         % (path, header_version))
        raise SystemExit(1)
    ramdisk_size = u32(16)
    os_version_raw = u32(44)
    header_size = u32(1644) if header_version >= 1 else page_size
    kernel_off = page_size
    ramdisk_off = kernel_off + roundup(kernel_size, page_size)
    info['second_size'] = u32(24)
    info['second_offset'] = ramdisk_off + roundup(ramdisk_size, page_size)
    info['tag_addr'] = u32(32)
    info['page_size'] = page_size
    info['kernel_addr'] = u32(12)
    info['ramdisk_addr'] = u32(20)
    if header_version >= 2:
        info['dtb_size'] = u32(1648)
        info['dtb_offset'] = ramdisk_off + roundup(ramdisk_size, page_size)
else:
    if header_version not in (3, 4):
        sys.stderr.write('%s: unknown header_version %d\n' % (path, header_version))
        raise SystemExit(1)
    ramdisk_size = u32(12)
    os_version_raw = u32(16)
    header_size = u32(20)
    if not 1580 <= header_size <= 4096:
        sys.stderr.write('%s: implausible v%d header_size %d\n'
                         % (path, header_version, header_size))
        raise SystemExit(1)
    kernel_off = 4096 + (4096 if header_version == 4 else 0)
    ramdisk_off = kernel_off + roundup(kernel_size, 4096)
    info['page_size'] = 0
    info['kernel_addr'] = 0
    info['ramdisk_addr'] = 0
    info['tag_addr'] = 0
    cmdline = b[44:44 + 1536].split(b'\0')[0]
    info['cmdline'] = cmdline

if header_version in (0, 1, 2):
    cmdline = (b[64:64 + 512] + b[608:608 + 1024]).split(b'\0')[0]
    info['cmdline'] = cmdline

# os_version packs a.b.c in bits 31..11 and yyyy-mm in bits 10..0.
osver = '%d.%d.%d' % ((os_version_raw >> 25) & 0x7f,
                      (os_version_raw >> 18) & 0x7f,
                      (os_version_raw >> 11) & 0x7f)
ospatch = '%d-%02d' % (((os_version_raw >> 4) & 0x7f) + 2000, os_version_raw & 0xf)

note = ''
if header_version >= 3:
    note = ' (v3/v4: 4096-aligned sections, dtb lives in dtbo)'

if emit_sh:
    lines = [
        ('BOOT_HEADER_VERSION', header_version),
        ('BOOT_HEADER_SIZE', header_size),
        ('BOOT_KERNEL_SIZE', kernel_size),
        ('BOOT_RAMDISK_SIZE', ramdisk_size),
        ('BOOT_KERNEL_OFFSET', kernel_off),
        ('BOOT_RAMDISK_OFFSET', ramdisk_off),
        ('BOOT_PAGE_SIZE', info['page_size'] if info['page_size'] else ''),
        ('BOOT_OS_VERSION', osver),
        ('BOOT_OS_PATCH_LEVEL', ospatch),
        ('BOOT_CMDLINE', info['cmdline'].decode('ascii', 'replace')),
    ]
    for key, value in lines:
        # Double-quoted so sourcing the output is safe for empty values.
        sys.stdout.write('%s="%s"\n' % (key, str(value).replace('"', '\\"')))
    sys.stderr.write('%s: header v%d, kernel %d @ %#x, ramdisk %d @ %#x\n'
                     % (path, header_version, kernel_size, kernel_off,
                        ramdisk_size, ramdisk_off))
    raise SystemExit(0)

print('file            %s  (%d bytes)' % (path, len(b)))
print('header_version  %d%s' % (header_version, note))
print('header_size     %d' % header_size)
print('kernel          %d bytes @ %#x' % (kernel_size, kernel_off))
print('ramdisk         %d bytes @ %#x' % (ramdisk_size, ramdisk_off))
print('os_version      %s   patch %s' % (osver, ospatch))
print('cmdline         %r' % info['cmdline'])
if header_version in (0, 1, 2):
    print('page_size       %d' % info['page_size'])
    print('kernel_addr     %#x' % info['kernel_addr'])
    print('ramdisk_addr    %#x' % info['ramdisk_addr'])
    print('second          %d bytes @ %#x' % (info['second_size'], info['second_offset']))
    print('tags_addr       %#x' % info['tag_addr'])
    if header_version >= 2:
        print('dtb             %d bytes @ %#x' % (info['dtb_size'], info['dtb_offset']))

# Payload sanity: the image should actually contain the sections it claims.
image_end = roundup(ramdisk_off + ramdisk_size, info['page_size'] or 4096)
print('image end       %#x  %s' % (image_end,
                                   'ok' if image_end <= len(b) else 'TRUNCATED'))
head = b[kernel_off:kernel_off + 0x40]
if head[:2] == b'MZ' and head[0x38:0x3c] == b'ARMd':
    print('kernel format   arm64 Linux Image (MZ + ARMd@0x38)')
else:
    print('kernel format   not an uncompressed arm64 Image (head %r)' % head[:8])
rd = b[ramdisk_off:ramdisk_off + 4]
magic = None
for sig, name in ((b'\x1f\x8b', 'gzip'), (b'\x02\x21\x4c\x18', 'lz4'),
                  (b'\xfd7zX', 'xz'), (b'\x28\xb5\x2f\xfd', 'zstd'),
                  (b'BZh', 'bzip2')):
    if rd[:len(sig)] == sig:
        magic = name
        break
print('ramdisk format  %s' % (magic or 'unknown (%s)' % rd.hex()))
