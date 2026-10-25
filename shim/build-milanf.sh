#!/bin/bash
# Build the MILANF shim boot image. Sibling of build.sh with the
# milanf-specific gates wired in; see BRINGUP.md §4.
#
# This script REFUSES to build until, in order:
#   1. shim/milanf-config.h has no UNKNOWN entries left, and the use
#      sites (console.h, shim.c, ufs.c) have been pointed at it;
#   2. MILANF_REF_BOOT points at a boot image dumped from THIS unit, and
#      tools/bootinfo.py can read its header. The build then matches that
#      image's header version and os_version instead of assuming sweet's.
# Sweet's header values in build.sh are v2 with explicit load addresses;
# milanf is v3, which has none of that, so those numbers do not transfer
# and would not even be meaningful here.
set -euo pipefail
cd "$(dirname "$0")"

# --- Gate 1: no unresolved hardware values -------------------------------
if grep -q 'STATUS: UNKNOWN' milanf-config.h; then
	echo "error: milanf-config.h still has UNKNOWN values:" >&2
	grep -B1 -A3 'STATUS: UNKNOWN' milanf-config.h >&2 || true
	echo "Resolve them from the unit's DTB (../recon/ decompile report) first." >&2
	exit 1
fi

# --- Gate 2: reference boot image from this unit -------------------------
# milanf boots header v3 (read off both slots: header_size 1580,
# header_version 3, os_version 16.0.0 / patch 2026-08). v3 has no page
# size, no load addresses, no second stage and no dtb section at all, so
# the offset variables this script used to demand do not exist on this
# device. Two consequences worth stating, because both used to be gates:
#
#   - the DTB cannot ride in boot.img on v3. It does not need to: ABL
#     hands the merged FDT to the kernel in x0 (shim/start.S: mov x19, x0)
#     and fdt.c only reads /chosen from it, while the ADT the shim boots
#     travels inside the payload (tools/mkpayload.py KERNEL ADT OUT).
#   - mkbootimg needs the header version and the os_version/os_patch_level
#     pair, not offsets, and those are read off the unit rather than
#     hardcoded here.
#
# What is still refused: an image that is not v3, because that means the
# reference is not a boot image this device would accept.
: "${MILANF_REF_BOOT:?set MILANF_REF_BOOT to a boot.img dumped from this unit: adb exec-out dd if=/dev/block/by-name/boot_b status=none > boot_b.img}"
[ -f "$MILANF_REF_BOOT" ] || { echo "error: MILANF_REF_BOOT=$MILANF_REF_BOOT not found" >&2; exit 1; }
PYTHON="${PYTHON:-python3}"
BOOTVARS=$("$PYTHON" ../tools/bootinfo.py --emit-sh "$MILANF_REF_BOOT") || {
	echo "error: $MILANF_REF_BOOT does not parse as an Android boot image" >&2
	exit 1
}
eval "$BOOTVARS"
if [ "$BOOT_HEADER_VERSION" != "3" ]; then
	echo "error: $MILANF_REF_BOOT is header v$BOOT_HEADER_VERSION, but this device boots v3." >&2
	echo "Point MILANF_REF_BOOT at a boot image dumped from the unit itself." >&2
	exit 1
fi
echo "reference: header v$BOOT_HEADER_VERSION, os $BOOT_OS_VERSION patch $BOOT_OS_PATCH_LEVEL," \
	"kernel $BOOT_KERNEL_SIZE bytes, ramdisk $BOOT_RAMDISK_SIZE bytes"

# --- Build (mirrors build.sh) ---------------------------------------------
CC=aarch64-linux-gnu-gcc
OBJCOPY=aarch64-linux-gnu-objcopy
# -DMILANF selects the board branch in console.h (FB geometry) and mmu.h
# (FB_PHYS); without it those files fall back to sweet's SM7150 constants.
CFLAGS="-O2 -ffreestanding -nostdlib -fno-pic -mgeneral-regs-only -mstrict-align -fno-stack-protector -Wall -Wextra -DMILANF=1"
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
mkbootimg --header_version "$BOOT_HEADER_VERSION" \
	--kernel out/Image --ramdisk out/ramdisk.bin \
	--os_version "$BOOT_OS_VERSION" --os_patch_level "$BOOT_OS_PATCH_LEVEL" \
	--cmdline "console=null" -o out/shim-boot-milanf.img
gcc -O1 -Wall -DMILANF=1 -o out/host_test console.c host_test.c && ./out/host_test
ls -l out/Image out/shim-boot-milanf.img
