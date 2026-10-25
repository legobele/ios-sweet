#!/usr/bin/env python3
"""Build the minimal Apple Device Tree that the MILANF xnu needs to boot.

Sibling of mkadt.py (same structure, same node layout) for the Moto G
Stylus 5G (2022) — "milanf", Qualcomm SM6375. Node names and compatible
strings that the in-kernel drivers match literally ('sweet-io',
'sweet,display', 'sweet-fbcon', 'sweet-ufs', and the 'xiaomi,sweet'
platform-expert match token in the root compatible) are carried over
UNCHANGED on purpose: patches 0016/0061 and the Sweet* drivers key on
those strings. Renaming them is a separate, later patch; see BRINGUP.md.

VALUE PROVENANCE — read before editing:
  CITED   value taken from mainline Linux arch/arm64/boot/dts/qcom/
          sm6375.dtsi (kernel.org, torvalds/linux master, read
          2026-10-21). Always subordinate to the unit's own DTB.
  UNKNOWN value set to None below. build() REFUSES to emit an ADT
          while any required UNKNOWN is unresolved, unless
          --allow-placeholders is passed (which zeroes them and stamps
          the tree DO-NOT-BOOT). Never fill an UNKNOWN from memory:
          resolve it from the unit's stock DTB dump (recon pack,
          ../recon/, decompile.sh report) or the stock firmware
          package, and note the source next to the value.

Usage:  mkadt-milanf.py OUT.adt [--dump] [--highmem] [--allow-placeholders]
"""
import hashlib, os, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adt  # noqa: E402
from mkadt import d22ap_product, node, u32, u64, cstr  # noqa: E402

# --- Memory map -------------------------------------------------------------
# RESOLVED from the unit's own DTB /memory node, cross-checked against the
# running Android kernel's /proc/iomem. Both agree, which is the point of
# checking: the DTB says what the bootloader declared, iomem says what a
# real kernel actually managed to use.
#
# /memory has three banks:
#   0x080000000 .. 0x0bbb00000   955 MB   shredded by firmware carveouts
#   0x0c0000000 .. 0x180000000  3072 MB   first 0x7100000 is removed_region
#   0x180000000 .. 0x280000000  4096 MB   entirely free
# and there is a genuine hole at 0xbbb00000..0xc0000000 (69 MB) that is not
# RAM at all, so the naive "8GB starting at 0x80000000" is wrong.
#
# Sweet's shape transfers, though: a low window below 4GB plus a separate
# --highmem tree, both hole-free, both 256MB-aligned, both with the early
# framebuffer BELOW dram-base. iomem confirms these two windows contain no
# reserved children:
#   0xd0000000 .. 0xf0800000   520 MB   (the 0xbf00000 above it is reserved)
#   0x200000000 .. 0x280000000 2048 MB  (four contiguous 512MB chunks)
# That is 2.5GB to bring up on, which is an iPhone 8's worth - enough, and
# it can be grown later once a boot tells us what the firmware tolerates.
# Keeping the framebuffer below dram-base also means the FB block no longer
# overlaps kernel-managed RAM, which is the situation 0086 documented.
PHYS_BASE = 0xd0000000
MEM_SIZE = 0x20800000
# Panic log buffer, carved from the TOP of the dram range (policy, same
# as sweet; without it the kernel hangs after "kdp_core zlib memory").
PANIC_LOG_SIZE = 0x100000
# --highmem: a hole-free 2GB window well above the 32-bit line.
HIGH_PHYS_BASE = 0x200000000
HIGH_MEM_SIZE = 0x80000000
# /arm-io children are relative to this; it must not be 0 (serial_init
# bails). ADT bookkeeping, not a hardware fact; same value as sweet.
SOC_BASE = 0x01000000

# --- Interrupt controller ---------------------------------------------------
# CITED (mainline sm6375.dtsi, node intc: interrupt-controller@f200000):
#   reg = <0x0 0x0f200000 0x0 0x10000>   GICD
#         <0x0 0x0f240000 0x0 0x100000>  GICR x8, redistributor-stride 0x20000
# NOTE: SM6375's GIC is NOT at SM7150's 0x17a00000. Confirm vs unit DTB.
GICD, GICD_SIZE = 0x0f200000, 0x10000
GICR, GICR_SIZE = 0x0f240000, 0x100000

# --- Splash framebuffer -----------------------------------------------------
# RESOLVED for geometry from the unit's own DTB. Whether Moto ABL leaves a
# LIVE buffer there (SPEC §13 unknown 1) is still only settled by the §1.1
# probe, which needs a boot - so these values are right for the ADT and the
# console, and liveness stays open.
#
# reserved-memory: cont_splash_region@0x85200000, size 0xc00000 (12MB),
# ending exactly where dfps_data_region@0x85e00000 (1MB) begins.
#   1080 x 2460 x 4 = 10627200 bytes, which fits in the carveout.
#   stride 4320 corroborated by the DTB's panel-width = 0x438 = 1080.
#   height 2460 is from the live device; the DTB's static panel list only
#   reaches 2340, but the carveout is sized for 2460 and the panel reports it.
# Sweet's 0x9c000000 / 1080x2400 are the SM7150 unit's and are not reused.
FB, FB_SIZE = 0x85200000, 0x00c00000   # cont_splash_region; size = carveout
FB_W, FB_H, FB_STRIDE = 1080, 2460, 1080 * 4

MILANF_ECID = 0x4d494c414e460001  # 'MILANF' + 1, synthetic (fork choice)

# --- UFS host ---------------------------------------------------------------
# RESOLVED - the unit's own DTB. /soc/ufshc@4804000 declares three banks,
# reg-names "ufs_mem", "ufs_ice", "ufs_ice_hwkm"; the UFSHCI register
# window is the first one, 0x4804000 for 0x3000 bytes. Mainline
# sm6375.dtsi has no UFS node at all (only SDHCI), so this comes off the
# device and nowhere else.
UFS, UFS_SIZE = 0x04804000, 0x3000

# CITED: 19.2 MHz XO is the Qualcomm platform timebase (mainline
# sm6375.dtsi XO clock); CNTFRQ itself is set by ABL. Confirm vs DTB.
TIMEBASE = 19200000
# CITED: mainline sm6375.dtsi `timer` node lists the architected timer
# PPIs as 1/2/3/0 (secure phys, phys, virt, hyp), so CNTV = INTID 19,
# same as sweet. Confirm vs unit DTB.
VTIMER_INTID = 19

BOOT_MANIFEST_HASH = hashlib.sha384(b'milanf boot manifest').digest()

# CITED (mainline sm6375.dtsi /cpus + cpufreq opp tables): cores 0-5 are
# the little Kryo 660 (Cortex-A55) cluster, max 1804800000; cores 6-7
# the big Kryo 660 (Cortex-A78) cluster, max 2208000000. CPU reg values
# in the dtsi are 0x0,0x100,...,0x700, i.e. MPIDR Aff1 = core index,
# so reg = core << 8 exactly as in mkadt.py. Confirm vs unit DTB.
CPU_COMPATIBLE = 'qcom,kryo660'
CPU_FREQ_LITTLE = 1804800000
CPU_FREQ_BIG = 2208000000

# Every hardware value this file needs is now taken from the unit itself -
# its DTB, cross-checked against the running Android kernel's iomem. The
# gate stays: it is what stops a future edit from quietly reintroducing a
# guess and shipping a DO-NOT-BOOT tree that looks finished.
UNKNOWNS = []
HIGHMEM_UNKNOWNS = []


def _check_unknowns(highmem, allow_placeholders):
    missing = [(n, src) for n, src in UNKNOWNS if globals()[n] is None]
    if highmem:
        missing += [(n, src) for n, src in HIGHMEM_UNKNOWNS if globals()[n] is None]
    if missing and not allow_placeholders:
        lines = '\n'.join(f'  {n}: UNKNOWN — resolve from {src}' for n, src in missing)
        raise SystemExit(
            'mkadt-milanf: refusing to build an ADT with unresolved hardware values:\n'
            f'{lines}\n'
            'The unit\'s own DTB is the authority (see ../recon/). '
            'Pass --allow-placeholders only for host-side ADT structure tests.')
    return [n for n, _ in missing]


def build(seed=None, highmem=False, allow_placeholders=False):
    placeholders = _check_unknowns(highmem, allow_placeholders)
    z = lambda v: 0 if v is None else v  # noqa: E731 — placeholder zeroing, gated above
    phys_base = z(HIGH_PHYS_BASE if highmem else PHYS_BASE)
    mem_size = z(HIGH_MEM_SIZE if highmem else MEM_SIZE)
    if placeholders:
        # Keep the carve arithmetic sane in the DO-NOT-BOOT tree.
        if phys_base == 0:
            phys_base = 0x80000000
        if mem_size <= PANIC_LOG_SIZE:
            mem_size = PANIC_LOG_SIZE + 0x100000
    panic_base = phys_base + mem_size - PANIC_LOG_SIZE
    mem_size -= PANIC_LOG_SIZE
    seed = seed if seed is not None else os.urandom(64)
    phandle = iter(range(1, 1000))
    ph = lambda: ('AAPL,phandle', u32(next(phandle)))  # noqa: E731
    fwver = 'milanf-shim-PLACEHOLDERS-DO-NOT-BOOT' if placeholders else 'milanf-shim'

    chosen = node('chosen', [
        ph(),
        ('dram-base', u64(phys_base)),
        ('dram-size', u64(mem_size)),
        ('random-seed', seed),
        ('debug-enabled', u32(1)),
        ('embedded-panic-log-size', u32(PANIC_LOG_SIZE)),
        ('firmware-version', cstr(fwver)),
        ('system-firmware-version', cstr(fwver)),
        # Same stand-ins as mkadt.py; see its comments for why each exists.
        ('boot-manifest-hash', BOOT_MANIFEST_HASH),
        ('crypto-hash-method', cstr('sha2-384')),
        # Presented display stays the iPhone X class (1125x2436 @3x), as
        # on sweet (patch 0061); the physical panel geometry is FB_*.
        ('display-scale', u32(3)),
        ('unique-chip-id', struct.pack('<Q', MILANF_ECID)),
        ('chip-id', u32(0x8015)),  # A11: what the iPhone X userland expects
        ('certificate-production-status', u32(0)),
        ('effective-production-status-ap', u32(0)),
        ('certificate-security-mode', u32(1)),
        ('effective-security-mode-sep', u32(1)),
    ], [node('memory-map', [ph()]),
        node('asmb', [ph(), ('lp-sip0', u64(0x6f)), ('lp-sip1', u32(1))])])

    # MILANF SMP: all eight cores in physical-core order (0-5 Cortex-A55,
    # 6-7 Cortex-A78), one homogeneous cluster — same bring-up topology
    # as sweet; per-cluster handling is a later step (SPEC §14 step 5).
    cpu_nodes = []
    for core in range(8):
        cpu_nodes.append(node(f'cpu{core}', [
            ph(),
            ('device_type', cstr('cpu')),
            ('compatible', cstr(CPU_COMPATIBLE) + cstr('ARM,v8')),
            ('reg', u32(core << 8)),  # MPIDR Aff1:Aff0 (CITED: dtsi cpu reg)
            ('cpu-id', u32(core)),
            ('cluster-id', u32(0)),
            ('cluster-type', u32(0)),  # homogeneous CLUSTER_TYPE_SMP
            ('die-cluster-id', u32(0)),
            ('cluster-core-id', u32(core)),
            ('l2-cache-id', u32(core)),
            ('l3-cache-id', u32(0)),     # shared L3 (CITED: dtsi cpu-map)
            ('state', cstr('running' if core == 0 else 'stopped')),
            ('timebase-frequency', u32(TIMEBASE)),
            ('clock-frequency', u32(CPU_FREQ_BIG if core >= 6 else CPU_FREQ_LITTLE)),
            ('bus-frequency', u32(100000000)),
            ('memory-frequency', u32(1866000000)),  # sweet's value; DTB-check at step 5
            ('peripheral-frequency', u32(TIMEBASE)),
            ('fixed-frequency', u32(TIMEBASE)),
        ]))
    cpus = node('cpus', [ph(), ('#address-cells', u32(1)),
                         ('#size-cells', u32(0))], cpu_nodes)

    gic = node('gic', [
        ph(),
        ('compatible', cstr('arm,gic-v3')),
        ('interrupt-controller', b''),
        ('virtual-timer-intid', u32(VTIMER_INTID)),
        ('reg', u64(GICD - SOC_BASE, GICD_SIZE, GICR - SOC_BASE, GICR_SIZE)),
    ])
    arm_io = node('arm-io', [
        ph(),
        ('device_type', cstr('sweet-io')),  # driver match string, see header
        ('compatible', cstr('sweet-io') + cstr('arm-io')),
        ('#address-cells', u32(2)),
        ('#size-cells', u32(2)),
        ('ranges', u64(0, SOC_BASE, 0x100000000 - SOC_BASE)),
    ], [gic,
        node('wdt', [ph(), ('no-pmu', u32(1))]),
        node('disp0', [
            ph(),
            ('device_type', cstr('display-subsystem')),
            ('compatible', cstr('sweet,display')),  # driver match string
            ('canvas-width', u32(1125)),
            ('canvas-height', u32(2436)),
        ])])

    fbcon = node('sweet-fbcon', [  # node name is a driver match string
        ph(),
        ('reg', u64(z(FB), z(FB_SIZE))),
        ('width', u32(z(FB_W))),
        ('height', u32(z(FB_H))),
        ('stride', u32(z(FB_STRIDE))),
    ])

    ufs = node('sweet-ufs', [  # node name is a driver match string
        ph(),
        ('compatible', cstr('qcom,ufshc')),
        ('reg', u64(z(UFS), z(UFS_SIZE))),
    ])

    defaults = node('defaults', [ph(), ('no-effaceable-storage', u32(1))])

    buttons = node('buttons', [
        ph(),
        ('button-names', cstr('volup') + cstr('voldown') + cstr('hold')),
        ('home-button-type', u32(2)),
        ('opposed-power-vol-buttons', u32(1)),
    ])

    product_props = d22ap_product()
    product = [node('product', [ph()] + product_props)] if product_props else []

    pram = node('pram', [ph(), ('reg', u64(panic_base) + u64(PANIC_LOG_SIZE))])

    # Root identity is the iPhone X userland's (D22AP / iPhone10,3), as
    # in mkadt.py. 'motorola,milanf' + 'qcom,sm6375' name the hardware;
    # 'xiaomi,sweet' is retained ONLY as the SweetPlatformExpert match
    # token (patch 0016 keys on it) until the expert learns milanf —
    # flagged as a decision point in BRINGUP.md.
    return node('device-tree', [
        ph(),
        ('compatible', cstr('D22AP') + cstr('iPhone10,3') + cstr('motorola,milanf') + cstr('qcom,sm6375') + cstr('xiaomi,sweet') + cstr('AppleARM')),
        ('model', cstr('iPhone10,3')),
        ('target-type', cstr('D22')),
        ('target-sub-type', cstr('D22AP')),
        ('manufacturer', cstr('Apple Inc.')),
        ('#address-cells', u32(2)),
        ('#size-cells', u32(2)),
    ], [chosen, defaults, cpus, arm_io, fbcon, buttons, pram] + product + [ufs])


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    root = build(highmem='--highmem' in sys.argv,
                 allow_placeholders='--allow-placeholders' in sys.argv)
    blob = adt.serialize(root)
    open(args[0], 'wb').write(blob)
    if '--dump' in sys.argv:
        adt.dump(adt.parse(blob)[0])
    print(f'{args[0]}: {len(blob)} bytes', file=sys.stderr)
