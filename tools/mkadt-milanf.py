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
# UNKNOWN: kernel-managed RAM window. Sweet's 0xb0000000 does NOT
# transfer: SM6375 DRAM starts at 0x80000000 (CITED: mainline memory
# node memory@80000000; the bootloader fills in the size) and the
# carve-out layout differs. Resolve from the unit's live FDT: the
# /memory node bank(s) minus every reserved-memory region, exactly
# the way upstream derived sweet's from its live FDT.
PHYS_BASE = None  # UNKNOWN — unit DTB (recon decompile report)
MEM_SIZE = None   # UNKNOWN — unit DTB (recon decompile report)
# Panic log buffer, carved from the TOP of the dram range (policy, same
# as sweet; without it the kernel hangs after "kdp_core zlib memory").
PANIC_LOG_SIZE = 0x100000
# --highmem: the whole upper DDR bank.
# UNKNOWN: bank split on the 8 GB unit. Resolve from the unit's live
# FDT /memory node (recon decompile report).
HIGH_PHYS_BASE = None  # UNKNOWN — unit DTB
HIGH_MEM_SIZE = None   # UNKNOWN — unit DTB
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
# UNKNOWN: whether Moto ABL leaves a splash framebuffer at all is SPEC
# §13 unknown 1 (the §1.1 probe); its address/size/geometry come from
# the unit DTB's reserved-memory (look for a cont_splash / framebuffer
# region or a simple-framebuffer node). Sweet's 0x9c000000 / 1080x2400
# values are the SM7150 unit's and must not be copied here.
FB = None        # UNKNOWN — unit DTB + §1.1 probe
FB_SIZE = None   # UNKNOWN — unit DTB
FB_W = None      # UNKNOWN — unit DTB (panel native width)
FB_H = None      # UNKNOWN — unit DTB (panel native height)
FB_STRIDE = None  # UNKNOWN — unit DTB (bytes per row; sweet was W*4)

MILANF_ECID = 0x4d494c414e460001  # 'MILANF' + 1, synthetic (fork choice)

# --- UFS host ---------------------------------------------------------------
# UNKNOWN: mainline sm6375.dtsi has NO UFS node at all (only SDHCI), so
# there is nothing to cite. Resolve from the unit DTB's ufshc@ node
# (recon decompile report) or the downstream SM6375 kernel source.
UFS = None       # UNKNOWN — unit DTB ufshc reg
UFS_SIZE = None  # UNKNOWN — unit DTB ufshc reg

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

UNKNOWNS = [
    ('PHYS_BASE', 'unit DTB /memory banks minus reserved-memory (recon decompile report)'),
    ('MEM_SIZE', 'unit DTB /memory banks minus reserved-memory (recon decompile report)'),
    ('FB', 'unit DTB reserved-memory splash region + SPEC §1.1 probe'),
    ('FB_SIZE', 'unit DTB reserved-memory splash region'),
    ('FB_W', 'unit DTB panel node / splash region'),
    ('FB_H', 'unit DTB panel node / splash region'),
    ('FB_STRIDE', 'unit DTB splash region (expect W*4, verify)'),
    ('UFS', 'unit DTB ufshc@ node reg (mainline sm6375.dtsi has no UFS node)'),
    ('UFS_SIZE', 'unit DTB ufshc@ node reg'),
]
HIGHMEM_UNKNOWNS = [
    ('HIGH_PHYS_BASE', 'unit DTB /memory second bank'),
    ('HIGH_MEM_SIZE', 'unit DTB /memory second bank'),
]


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
