/*
 * Milestone 4: act as iBoot for xnu.
 *
 * mkpayload.py already resolved the kernel's chained fixups and built the
 * ADT, so this only has to: find the payload in the ABL ramdisk, copy the
 * segments to phys_base + (vmaddr - virt_base), place the ADT and
 * boot_args behind the kernel, and jump to the entry point with the MMU
 * and caches off, x0 = boot_args (physical).
 */
#include <stdint.h>
#include "console.h"
#include "fdt.h"
#include "loader.h"

#define BOOT_LINE_LENGTH	608
#define PAGE_16K		0x4000UL

struct payload_seg {
	uint64_t vmaddr, vmsize, file_off, file_size;
};

struct payload {
	char magic[8];
	uint32_t version, nsegs;
	uint64_t virt_base, entry_va, adt_off, adt_size, kernel_end;
	uint64_t phys_base, mem_size;
	char cmdline[BOOT_LINE_LENGTH];
	struct payload_seg segs[];
};

/* pexpert/pexpert/arm64/boot.h, Revision/Version 2 */
struct boot_video {
	uint64_t v_baseAddr, v_display, v_rowBytes, v_width, v_height, v_depth;
};

struct boot_args {
	uint16_t Revision, Version;
	uint64_t virtBase, physBase, memSize, topOfKernelData;
	struct boot_video Video;
	uint32_t machineType;
	uint64_t deviceTreeP;
	uint32_t deviceTreeLength;
	char CommandLine[BOOT_LINE_LENGTH];
	uint64_t bootFlags, memSizeActual;
};

_Static_assert(__builtin_offsetof(struct payload, segs) == 0x2a8, "payload header layout");
_Static_assert(__builtin_offsetof(struct boot_args, Video) == 40, "boot_args layout");
_Static_assert(__builtin_offsetof(struct boot_args, CommandLine) == 108, "boot_args layout");
_Static_assert(sizeof(struct boot_args) == 736, "boot_args layout");

/* MMU off: everything is Device memory, so copy in aligned 8-byte words. */
static void copy64(uintptr_t dst, uintptr_t src, uint64_t n)
{
	volatile uint64_t *d = (volatile uint64_t *)dst;
	volatile const uint64_t *s = (volatile const uint64_t *)src;
	for (uint64_t i = 0; i < (n + 7) / 8; i++)
		d[i] = s[i];
}

static void zero64(uintptr_t dst, uint64_t n)
{
	volatile uint64_t *d = (volatile uint64_t *)dst;
	for (uint64_t i = 0; i < n / 8; i++)
		d[i] = 0;
}

/*
 * Copies with the source possibly only 4-byte aligned: a payload found
 * mid-initrd (behind ABL's prepended vendor ramdisk) can sit at a
 * 4-mod-8 base, and unaligned 64-bit accesses to Device memory fault
 * with the MMU off. Same round-up-to-8 total copy64 copies.
 */
static void copy_auto(uintptr_t dst, uintptr_t src, uint64_t n)
{
	uint64_t total = (n + 7) & ~7UL;

	if (!((dst | src) & 7)) {
		copy64(dst, src, n);
		return;
	}
	if (!((dst | src) & 3)) {
		volatile uint32_t *d = (volatile uint32_t *)dst;
		volatile const uint32_t *s = (volatile const uint32_t *)src;
		for (uint64_t i = 0; i < total / 4; i++)
			d[i] = s[i];
		return;
	}
	volatile uint8_t *d = (volatile uint8_t *)dst;
	volatile const uint8_t *s = (volatile const uint8_t *)src;
	for (uint64_t i = 0; i < total; i++)
		d[i] = s[i];
}

static void zero_auto(uintptr_t dst, uint64_t n)
{
	if (!(dst & 7)) {
		zero64(dst, n);
		volatile uint8_t *d = (volatile uint8_t *)dst;
		for (uint64_t i = n & ~7UL; i < n; i++)
			d[i] = 0;
		return;
	}
	volatile uint8_t *d = (volatile uint8_t *)dst;
	for (uint64_t i = 0; i < n; i++)
		d[i] = 0;
}

static int magic_ok(const char *m)
{
	static const char want[] = "SWEETXNU";
	for (int i = 0; i < 8; i++)
		if (m[i] != want[i])
			return 0;
	return 1;
}

/* The header sanity loader_boot applies on the direct path. */
static int header_ok(const struct payload *p, uint64_t base)
{
	return p->version == 1 && !(p->adt_off & 7) && !(base & 7);
}

/*
 * A payload found by scanning may sit at a 4-but-not-8-aligned base
 * (milanf: ABL prepends the 3,743,908-byte vendor ramdisk, so the
 * payload lands at rd_start + 3,743,908, which is 4 mod 8), so its
 * 64-bit header fields must never be dereferenced in place: unaligned
 * accesses to Device memory fault with the MMU off. Copy the header
 * into an aligned buffer with byte reads and validate the copy.
 */
#define MAX_SEGS	64
#define HDR_BUF_BYTES	(0x2a8 + 32 * MAX_SEGS)
static uint64_t hdr_buf[HDR_BUF_BYTES / 8];

static void read_dev(void *dst, uint64_t src, uint64_t n)
{
	uint8_t *d = (uint8_t *)dst;

	for (uint64_t i = 0; i < n; i++)
		d[i] = *(volatile const uint8_t *)(src + i);
}

static int probe_payload(uint64_t at, uint64_t rd_end, struct payload **out)
{
	struct payload *h = (struct payload *)hdr_buf;

	if (at + 16 > rd_end)
		return 0;
	read_dev(h, at, 16);
	if (h->version != 1 || !h->nsegs || h->nsegs > MAX_SEGS)
		return 0;
	if (at + 0x2a8 + 32ULL * h->nsegs > rd_end)
		return 0;
	read_dev(h, at, 0x2a8 + 32ULL * h->nsegs);
	if ((h->adt_off & 7) || at + h->adt_off + h->adt_size > rd_end)
		return 0;
	*out = h;
	return 1;
}

static uint64_t scan_step(uint64_t rd_start, uint64_t rd_end, uint64_t step,
			  struct payload **out)
{
	for (uint64_t at = rd_start; at + 8 <= rd_end; at += step) {
		if (magic_ok((const char *)at) && probe_payload(at, rd_end, out))
			return at;
	}
	return 0;
}

/*
 * ABL does not deliver the ramdisk contents starting exactly at
 * linux,initrd-start on milanf: it concatenates the vendor ramdisk
 * (3,743,908 bytes, the vendor_boot partition's ramdisk size) in front
 * of the boot image's ramdisk and reports the combined range, so the
 * payload sits at rd_start + 3,743,908, flush at the end. When the
 * magic is not at rd_start, scan the whole range for a payload whose
 * header passes the same sanity checks as the direct path. Coarse 4K
 * steps first, then 8, 4, and 1-byte steps: the concatenation offset
 * is only 4-byte aligned, so finer steps are not optional.
 */
static uint64_t find_payload(uint64_t rd_start, uint64_t rd_end,
			     struct payload **out)
{
	uint64_t at = scan_step(rd_start, rd_end, 4096, out);

	if (!at)
		at = scan_step(rd_start, rd_end, 8, out);
	if (!at)
		at = scan_step(rd_start, rd_end, 4, out);
	if (!at)
		at = scan_step(rd_start, rd_end, 1, out);
	return at;
}

typedef void (*xnu_entry_t)(uint64_t boot_args_pa);

const char *loader_boot(uintptr_t dtb)
{
	uint64_t rd_start, rd_end;

	if (!fdt_chosen_u64(dtb, "linux,initrd-start", &rd_start) ||
	    !fdt_chosen_u64(dtb, "linux,initrd-end", &rd_end))
		return "no initrd in /chosen";
	con_hex2("INITRD", "lo=", rd_start, "hi=", rd_end);

	uint64_t base = rd_start;
	const struct payload *p = (const struct payload *)base;
	int scanned = 0;
	if (!magic_ok(p->magic)) {
		const volatile uint32_t *w = (const volatile uint32_t *)rd_start;

		con_hex2("RDHDR", "w0=", w[0], "w1=", w[1]);
		struct payload *hp = 0;
		base = find_payload(rd_start, rd_end, &hp);
		if (!base)
			return "no SWEETXNU payload";
		con_hex("PAYLOAD", base - rd_start);
		p = hp;	/* aligned header copy, validated by probe_payload */
		scanned = 1;
	}
	if (!scanned && !header_ok(p, base))
		return "bad payload header";

	uint64_t pa_of_va_base = p->phys_base - p->virt_base;	/* pa = va + this */
	con_hex2("PHYS", "base=", p->phys_base, "size=", p->mem_size);
	con_hex("VIRT", p->virt_base);
	con_hex("ENTRY", p->entry_va);

	/* The payload must not overlap where the kernel goes. */
	if (rd_end > p->phys_base && rd_start < p->phys_base + p->mem_size)
		return "ramdisk overlaps kernel memory";

	for (uint32_t i = 0; i < p->nsegs; i++) {
		const struct payload_seg *s = &p->segs[i];
		uintptr_t dst = s->vmaddr + pa_of_va_base;
		copy_auto(dst, base + s->file_off, s->file_size);
		if (s->vmsize > s->file_size)
			zero_auto(dst + ((s->file_size + 7) & ~7UL), s->vmsize - ((s->file_size + 7) & ~7UL));
	}
	con_hex2("SEGS", "n=", p->nsegs, "end=", p->kernel_end + pa_of_va_base);

	/* ADT, then boot_args, behind the kernel; everything below topOfKernelData is ours. */
	uintptr_t adt_pa = p->kernel_end + pa_of_va_base;
	copy_auto(adt_pa, base + p->adt_off, p->adt_size);
	uintptr_t ba_pa = (adt_pa + p->adt_size + PAGE_16K - 1) & ~(PAGE_16K - 1);
	uintptr_t top = ba_pa + PAGE_16K;

	zero_auto(ba_pa, PAGE_16K);
	volatile struct boot_args *ba = (volatile struct boot_args *)ba_pa;
	ba->Revision = 2;
	ba->Version = 2;
	ba->virtBase = p->virt_base;
	ba->physBase = p->phys_base;
	ba->memSize = p->mem_size;
	ba->topOfKernelData = top;
	ba->Video.v_baseAddr = FB_BASE;
	ba->Video.v_display = 1;
	ba->Video.v_rowBytes = FB_STRIDE;
	ba->Video.v_width = FB_W;
	ba->Video.v_height = FB_H;
	ba->Video.v_depth = 32;
	ba->deviceTreeP = adt_pa - pa_of_va_base;	/* xnu reads it with the MMU on: a VA */
	ba->deviceTreeLength = (uint32_t)p->adt_size;
	for (int i = 0; i < BOOT_LINE_LENGTH; i++)
		ba->CommandLine[i] = p->cmdline[i];
	ba->memSizeActual = p->mem_size;
	con_hex2("BOOTARG", "pa=", ba_pa, "top=", top);

	uintptr_t entry_pa = p->entry_va + pa_of_va_base;
	con_hex("JUMP", entry_pa);
	con_str("XNU", "jumping (fbcon clears screen)");

	/* Everything was written with the MMU and caches off; drop any stale I-cache lines too. */
	__asm__ volatile("dsb sy; ic iallu; dsb sy; isb" ::: "memory");
	((xnu_entry_t)entry_pa)(ba_pa);
	return "xnu returned";
}
