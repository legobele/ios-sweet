#!/bin/bash
# Build the MILANF shim boot image. Sibling of build.sh with the
# milanf-specific gates wired in; see BRINGUP.md §4.
#
# This script REFUSES to build until, in order:
#   1. shim/milanf-config.h has no UNKNOWN entries left, and the use
#      sites (console.h, shim.c, ufs.c) have been pointed at it;
#   2. MILANF_DTB points at the DTB extracted from THIS unit's stock
#      boot image (recon pack step 1 -> tools/unpack_bootv2.py);
#   3. the mkbootimg header variables below have been verified
#      against that stock boot image's header (unpack_bootv2.py
#      prints them) and MILANF_HEADER_VERIFIED=1 is set.
# Sweet's header values in build.sh came from sweet's stock image;
# they do NOT automatically transfer to Motorola's ABL.
set -euo pipefail
cd "$(dirname "$0")"

# --- Gate 1: no unresolved hardware values -------------------------------
if grep -q 'STATUS: UNKNOWN' milanf-config.h; then
	echo "error: milanf-config.h still has UNKNOWN values:" >&2
	grep -B1 -A3 'STATUS: UNKNOWN' milanf-config.h >&2 || true
	echo "Resolve them from the unit's DTB (../recon/ decompile report) first." >&2
	exit 1
fi

# --- Gate 2: the unit's own stock DTB ------------------------------------
: "${MILANF_DTB:?set MILANF_DTB to the DTB unpacked from the milanf stock boot image}"
[ -f "$MILANF_DTB" ] || { echo "error: MILANF_DTB=$MILANF_DTB not found" >&2; exit 1; }

# --- Gate 3: stock boot-image header values ------------------------------
# UNKNOWN until read off the unit's stock boot.img with
# tools/unpack_bootv2.py. Fill from THAT output, then set
# MILANF_HEADER_VERIFIED=1.
KERNEL_OFFSET="${MILANF_KERNEL_OFFSET:-}"
RAMDISK_OFFSET="${MILANF_RAMDISK_OFFSET:-}"
TAGS_OFFSET="${MILANF_TAGS_OFFSET:-}"
DTB_OFFSET="${MILANF_DTB_OFFSET:-}"
PAGESIZE="${MILANF_PAGESIZE:-}"
if [ "${MILANF_HEADER_VERIFIED:-0}" != "1" ] || [ -z "$KERNEL_OFFSET" ] || \
   [ -z "$RAMDISK_OFFSET" ] || [ -z "$TAGS_OFFSET" ] || [ -z "$DTB_OFFSET" ] || \
   [ -z "$PAGESIZE" ]; then
	echo "error: mkbootimg header values not verified against the milanf stock boot image." >&2
	echo "Run tools/unpack_bootv2.py on the stock boot.img, export the" >&2
	echo "MILANF_*_OFFSET / MILANF_PAGESIZE values it reports, then set" >&2
	echo "MILANF_HEADER_VERIFIED=1." >&2
	exit 1
fi

# --- Build (mirrors build.sh) ---------------------------------------------
CC=aarch64-linux-gnu-gcc
OBJCOPY=aarch64-linux-gnu-objcopy
CFLAGS="-O2 -ffreestanding -nostdlib -fno-pic -mgeneral-regs-only -mstrict-align -fno-stack-protector -Wall -Wextra"
mkdir -p out
for f in start.S shim.c console.c mmu.c fdt.c loader.c ufs.c; do
	$CC $CFLAGS -c $f -o out/${f%.*}.o
done
abs=$(aarch64-linux-gnu-readelf -r out/shim.o out/console.o out/mmu.o out/fdt.o out/loader.o out/ufs.o | grep -c ABS64 || true)
[ "$abs" = 0 ] || { echo "error: $abs absolute relocations in C objects" >&2; exit 1; }
$CC $CFLAGS -static -T shim.ld -Wl,--build-id=none -Wl,--no-warn-rwx-segments -Wl,-N \
	out/start.o out/shim.o out/console.o out/mmu.o out/fdt.o out/loader.o out/ufs.o -o out/shim.elf
$OBJCOPY -O binary out/shim.elf out/Image
size=$(aarch64-linux-gnu-nm out/shim.elf | awk '$3=="_end"{print strtonum("0x"$1)}')
truncate -s "$size" out/Image
if [ -n "${1:-}" ]; then
	cp "$1" out/ramdisk.bin
else
	(cd out && rm -rf rd && mkdir rd && cd rd && find . | cpio -o -H newc --quiet | gzip -9 > ../ramdisk.bin)
fi
mkbootimg --header_version 2 --kernel out/Image --ramdisk out/ramdisk.bin \
	--dtb "$MILANF_DTB" --base 0 --kernel_offset "$KERNEL_OFFSET" --ramdisk_offset "$RAMDISK_OFFSET" \
	--tags_offset "$TAGS_OFFSET" --dtb_offset "$DTB_OFFSET" --pagesize "$PAGESIZE" \
	--os_version 17.0.0 --os_patch_level 2035-06 \
	--cmdline "console=null" -o out/shim-boot-milanf.img
gcc -O1 -Wall -o out/host_test console.c host_test.c && ./out/host_test
ls -l out/Image out/shim-boot-milanf.img
