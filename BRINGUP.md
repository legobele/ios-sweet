# BRINGUP.md — MILANF boot-phase runbook

Desk-phase preparation for SPEC §14 steps 1–4 on the Moto G Stylus 5G
(2022) ("milanf", SM6375, Giulia's XT2215-family unit). Written
2026-10-21. **Nothing in this document has run on hardware yet.** Every
command that touches the device belongs to the hardware phase and
needs Giulia's confirmation at the time (AGENTS.md).

Companion artifacts from this desk pass:

- `xnu/patches/0082-milanf-machine-config.patch` — the MILANF machine
  config, sibling of upstream's 0004 SWEET config.
- `tools/mkadt-milanf.py` — the MILANF ADT builder, sibling of
  `tools/mkadt.py`, with a hard gate against unresolved values.
- `shim/milanf-config.h` - the shim-side hardware value ledger.
- `tools/bootinfo.py` - boot image header reader, v0 through v4. milanf's
  images are v3, which `tools/unpack_bootv2.py` would silently misparse.
- `shim/build-milanf.sh` - the shim build, gated on resolved values + a
  boot image dumped from the unit (`MILANF_REF_BOOT`, read by
  `tools/bootinfo.py`).
- `../recon/` — the read-only device recon pack (runs on the Windows
  laptop; produces the DTB dump everything below consumes).

## 0. Value provenance policy

Every hardware value in this port is one of:

- **CITED** — taken from mainline Linux `arch/arm64/boot/dts/qcom/
  sm6375.dtsi` (kernel.org, torvalds/linux master, read 2026-10-21),
  always with "to be confirmed against the unit's own DTB".
- **UNKNOWN** — an explicit placeholder. Resolution source is always
  named: the unit's stock DTB dump (recon pack) or the matching stock
  firmware package. **No address is ever filled in from memory.**

The unit's own DTB is the authority. Mainline is a first draft: the
SoC `.dtsi` deliberately leaves memory sizes, carve-outs, panel,
touch, and cameras to board files and the bootloader.

Headline CITED corrections vs sweet (do not carry SM7150 numbers over):

| Value | Sweet (SM7150) | Milanf (SM6375, mainline-cited) |
|---|---|---|
| GICD | 0x17a00000 | **0x0f200000** (intc@f200000) |
| GICR | 0x17a60000 | **0x0f240000**, size 0x100000, stride 0x20000 |
| Big cores | 2x A76 @ 2.304 GHz | 2x A78 @ 2.208 GHz (opp table max) |
| Little cores | 6x A55 @ 1.8048 GHz | 6x A55 @ 1.8048 GHz (same) |
| CPU compatible | qcom,kryo470 | qcom,kryo660 |
| UFS host | 0x01d84000 | **UNKNOWN** — mainline sm6375.dtsi has no UFS node at all |
| Timer INTID (CNTV) | 19 | 19 (timer PPIs listed 1/2/3/0, same scheme) |

## 1. Audit summary (how upstream's machinery works)

**Machine selection.** XNU builds are parameterized by
`MACHINE_CONFIG`. Upstream's patch 0004 adds `SWEET` in four places:
`makedefs/MakeInc.def` (supported list, `-DARM64_BOARD_CONFIG_SWEET
-march=armv8.2-a+crypto`, and an exemption from the default `arm64e`
arch string so the build stays plain arm64 — Kryo has no PAC), a
board header `pexpert/pexpert/arm64/SWEET.h` (generic-ARM feature
defines, GICv3 register offsets, `SWEET_VTIMER_INTID 19`,
`SWEET_IPI_SGI 1`), a `board_config.h` block (MAX_CPUS 8, cline 6),
and `#if defined(SWEET)` code paths in `sleh.c` (Group-1 IRQ routing:
TrustZone owns Group 0, so the vtimer and IPIs arrive as IRQs),
`pe_fiq.c` (Group-1 GIC setup), `proc_reg.h` (cache lines), and
`start.s` (skip the SCTLR_EL1_DEFAULT hang check). Patch 0082 mirrors
all of it for MILANF, sharing the sleh/pe_fiq code paths.

**Patch series.** `xnu/patches/` holds 84 patches (0001–0081 + stage
scripts), applied in order by the build tooling; 0082 is appended,
not yet applied or built anywhere.

**Shim contract with the bootloader.** The shim is an ARM64 Linux
Image (magic `ARM\x64`) wrapped in an Android boot image v2. ABL
enters it at EL1 with MMU/D-caches off and x0 = DTB pointer. The shim
(`shim/start.S`, `shim.c`, `loader.c`) finds the payload via the FDT
`/chosen` `linux,initrd-start/end` properties, expects the payload
magic `SWEETXNU` (built by `tools/mkpayload.py`: kernel segments + ADT
+ cmdline), copies segments to `phys_base + (vmaddr - virt_base)`,
places the ADT and a v2 boot_args (736 bytes) behind the kernel,
programs the video boot args from the compile-time FB constants, and
jumps to the kernel with caches off and x0 = boot_args. The shim's
console paints to a **hardcoded** framebuffer (it does not parse the
DTB for one), and `shim.c` already contains the probe battery the
§1.1 probe reuses: SMCCC/PSCI version + feature probes, PSCI CPU_ON
of secondaries with MPIDR readout, a GICv3 Group-1 vtimer IRQ test,
a UFS probe, a blue panic screen on exception, and reset via IMEM
restart-reason + PSCI SYSTEM_RESET + PSHOLD.

**Build system.** Shim + Python tools build on Linux
(aarch64-linux-gnu-gcc, mkbootimg). The root image builds on Linux
(`tools/mkiosroot.sh`; apfs-fuse/hfsprogs/img2simg). **XNU itself
builds only on macOS** (darwin-xnu-build; see §6). The ADT `/product`
node is copied from the real D22AP tree extracted from the iPhone X
IPSW, kept out of git under `research/`.

## 2. Step 1 — step-0 backups and dumps (SPEC §14.1)

Goal: everything needed to restore the unit and to resolve the
UNKNOWN values. Two halves: the recon pack (no bootloader involved)
and the partition backups (needs a booted recovery — still no
flashing).

1. Run the recon pack on the laptop: `../recon/recon.ps1`. It
   captures getprop (incl. build fingerprint), the live device tree
   (raw `/sys/firmware/fdt` blob if readable, else a per-node mirror
   of `/sys/firmware/devicetree/base`), the by-name partition table
   with sizes, panel/touch/display dumps. Output lands in
   `../recon/out/recon-<timestamp>/` (gitignored; contains the
   serial).
2. Run `../recon/decompile.sh <run-dir>` on this VM. It produces
   `milanf.dts` + `report.txt` resolving SPEC §13 unknowns 2 (panel),
   3 (touch IC), 4 (front camera), 6 (boot partition size), plus the
   memory banks, reserved-memory list, ufshc reg, and GIC reg
   cross-check that feed `tools/mkadt-milanf.py` and
   `shim/milanf-config.h`.
3. Dump the boot image from the unit and read its header:
   `adb exec-out dd if=/dev/block/by-name/boot_b status=none > boot_b.img`
   then `tools/bootinfo.py boot_b.img`. That image is **header v3**
   (`header_size` 1580, `os_version` 16.0.0 / patch 2026-08), so there is
   no DTB inside it and no load addresses to copy - v3 dropped all of that.
   `build-milanf.sh` takes the header version and `os_version` from it via
   `MILANF_REF_BOOT`. The device tree a kernel sees comes from the dtbo
   partition, which ABL merges and passes in x0.
4. Partition backups (SPEC §3 restore set): temp-boot a recovery
   image (**`fastboot boot`, never flash**; which recovery supports
   milanf is itself confirmed here), then `dd` out: boot (both
   slots), dtbo, vbmeta, persist, modemst1, modemst2, fsg, fsc.
   Store under `backup/` (gitignored — persist/modemst hold IMEI and
   calibration). Hash every image (sha256) into a manifest.
   Decision point: if no milanf recovery image exists, the fallback
   is backups from a rooted stock boot — that changes the afternoon's
   shape; stop and reassess rather than improvising.

Exit criteria: decompile report on file, DTB extracted, backup
manifest complete. Unknowns 2, 3, 4, 6 resolved.

## 3. Step 2 — the §1.1 probe (SPEC §14.2; resolves unknown 1)

The probe answers two questions: (1) does Moto ABL leave a
continuous splash framebuffer we can paint on, and (2) does Moto
fastboot happily `fastboot boot` a temporary image on the unlocked
unit. Procedure per SPEC §1.1: **unlock, dump, boot a test shim that
paints the framebuffer and writes the persistent log ring.**

Prerequisites: step 1 complete; bootloader unlocked (the unlock
itself — Motorola key request via `../recon/unlock-data.ps1`, then
`fastboot oem unlock <key>` typed by Giulia, **not** in any pack —
wipes the device; that is why backups come first); FB values filled
into `shim/milanf-config.h` from the step-1 DTB and wired into
`console.h` (the only UNKNOWNs the probe build needs; UFS_BASE is
needed only for the log-ring writer — if the DTB gave no ufshc node,
the ring write is deferred and the probe is paint-only, noted as a
partial probe).

Desk work queued for this step (small, written at probe time):
`shim.c` gains a log-ring writer reusing `ufs.c` primitives to store
the probe results into the same tail-of-userdata ring patch 0047
later uses for the kernel console (last 1025 blocks of userdata),
so results survive a hung or unpaintable boot.

Run:

1. `shim/build-milanf.sh` with no payload → diagnostics image
   `out/shim-boot-milanf.img` (shim runs its probe battery and paints
   its milestone screen: PSCI version/features, secondary MPIDRs,
   vtimer IRQ test result, UFS probe result).
2. `fastboot boot out/shim-boot-milanf.img` — temporary boot only.
3. Photograph the screen. Read the milestones. Note ABL behavior:
   accepted/refused, any hang after the boot command (Xiaomi's ABL
   hangs after large transfers; Moto's is unmeasured), time to first
   paint.
4. Reboot to recovery; pull the log ring (same dd offsets
   `tools/sweet-log-pull.sh` uses) and confirm the shim's written
   results match the photograph.

Decision table:

| Observation | Conclusion |
|---|---|
| Pattern + milestones visible | Splash FB exists at the DTB address; display path is a port. Proceed to step 3. |
| Screen black, log ring written, probes pass | ABL kills/never had a splash FB, or address wrong: cross-check DTB reserved regions; if truly none, display becomes a research item (DPU init) and bring-up proceeds log-only via the ring + recovery pulls. |
| `fastboot boot` refused | Unlock state or Moto policy gate; resolve before anything else — the whole tethered model depends on it. |
| Shim probes fail at PSCI/GIC | SM6375 firmware quirk; the probe battery's per-test results say which assumption broke (Group-1 routing is the first suspect). |

## 4. Step 3 — shim + MILANF config + first kernel boot (SPEC §14.3)

1. **Fill the values.** From the step-1 decompile report, fill:
   `tools/mkadt-milanf.py` (PHYS_BASE/MEM_SIZE, HIGH_*, FB_*, UFS_*)
   and `shim/milanf-config.h` (FB_*, UFS_BASE, IMEM/PSHOLD), wiring
   the shim use sites (console.h, shim.c, ufs.c) to the config.
   Record each value's source next to it. `mkadt-milanf.py` refuses
   to emit an ADT while a required value is None — that refusal is
   the checklist.
2. **Build the kernel** (host routes in §6), `MACHINE_CONFIG=MILANF`,
   `KERNEL_CONFIG=DEVELOPMENT`. Single-file sanity first with
   `tools/xnu-cc.py` against the touched files, per upstream habit.
   Artifact: `kernel.development.milanf` (+ SHA256SUMS from CI).
   Expect first-build patch fallout: 0082 is desk-authored against
   0004's post-image; fix context drift in the patch, not the tree.
3. **Build the ADT:** `tools/mkadt-milanf.py out/milanf.adt --dump`
   and eyeball the dump against the decompile report (GIC reg,
   memory, ufshc).
4. **Build the payload:** `tools/mkpayload.py` with the kernel, the
   ADT, and boot args. First boot uses the conservative set (upstream
   canonical line, `cpus=1` first, raised once the console lives):
   `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam
   -noprogress rd=ufsroot0 unentitled_ios_sim_launch=1
   ignition_level=1 wdt_test=no_user_checkin ufsrw=1 rootrw=1
   launchd_unsecure_cache=1 wdt=-1`
5. **Build the boot image:** `shim/build-milanf.sh out/payload.bin`.
6. **Boot:** `fastboot boot shim/out/shim-boot-milanf.img`.
   Success = framebuffer console (patch 0003 fbcon) scrolling to the
   persistent-log handoff, and the ring readable afterwards via
   recovery pull. Failure triage, upstream order: no paint at all →
   shim/FB; paint then hang after "kdp_core zlib memory" → panic-log
   carve (PANIC_LOG_SIZE) missing; early hang with no kprintf →
   `serial=3` + early fb markers (the start.s band technique in
   NOTES.md); SMP weirdness → stay at `cpus=1` until step 5.

Decision point carried from the desk phase: the ADT root compatible
retains `xiaomi,sweet` purely as the SweetPlatformExpert match token
(patch 0016 keys on it) alongside `motorola,milanf`. Dropping it
requires teaching the platform expert the milanf string first.
Similarly the driver-matched node names (`sweet-io`, `sweet-fbcon`,
`sweet-ufs`, `sweet,display`) are unchanged until a rename patch
updates every match site at once.

## 5. Step 4 — UFS root, launchd, SpringBoard, tethered (SPEC §14.4)

1. Build the root image: `tools/mkiosroot.sh` from the iPhone X
   16.7.16 (20H392) IPSW, then the root-tweaks pass. (Milanf's own
   tweaks from `../root-tweaks/` integrate at step 7; step 4 uses the
   upstream bring-up image recipe.)
2. Flash the root into `userdata` — **a write step, hardware phase,
   Giulia confirms at the time** (AGENTS.md; the Android install is
   expendable per her 2026-10-15 ruling, backups from step 1 are
   the way back):
   `fastboot flash -S 512M userdata <image>.simg` (upstream timing:
   ~7 minutes; expect to re-enter fastboot manually if ABL stalls).
3. Boot tethered with the step-4 boot args (canonical line, `cpus=6`
   once step 3 is stable at 1, `sweetfb_noconsole=1 sweetfb_hz=30`
   for GUI boots).
4. Milestones, in order: kernel mounts `rd=ufsroot0`; launchd up;
   backboardd up; SpringBoard to the home screen. Log channels: fbcon
   on screen, the persistent ring via recovery pull after any hang,
   and (once the USB stack lands, upstream 0072+) the live UDP log.
   **Every boot in this step is `fastboot boot`; nothing is flashed
   to boot until step 6.**

## 6. Build hosts

XNU does not build on this Linux VM (no macOS toolchain — upstream's
build is darwin-xnu-build on macOS, full stop). Two real routes:

### Route A — GitHub macOS CI (upstream's route)

Verified present: `.github/workflows/xnu.yml` — `workflow_dispatch`
with inputs `macos_version` (default `13.5` = xnu-8796),
`kernel_config` (DEVELOPMENT), `machine_config` (default `SWEET`;
a MILANF build is this input set to `MILANF` once 0082 is in the
series), `keep_going`. Runs on `macos-14` (Xcode 15.x required:
Xcode 16's iig emits IORPC.kernelContent this xnu lacks), uses
blacktop/darwin-xnu-build pinned at commit
`663906528d1cd5ea8fde7de6f16de73db9511549`, stubs `xcodes`, installs
`jq gum bash cmake ninja` via brew. Artifacts: `xnu-kernel`
(kernel.* + SHA256SUMS) and the build tree (7-day retention).
Upstream iteration loop: edit → numbered patch → push → ~8 min run →
`gh run download <id> -n xnu-kernel`.

**This fork is currently local-only.** Publishing it to GitHub is
what turns Route A on (upstream made their repo public on
2026-10-17 because private macOS minutes ran out; public repos get
free runners). Nothing has been pushed; publishing is Giulia's
decision (§7).

### Route B — local build on the M1 Max MacBook

Her 16" M1 Max (64 GB / 1 TB, delivered 2026-10-21) runs the same
darwin-xnu-build locally:

- Xcode 15.x (NOT 16 — the iig incompatibility above), selected via
  `xcode-select`; the CI's `xcodes` stub trick applies if multiple
  Xcodes coexist.
- `brew install jq gum bash cmake ninja`
- Clone blacktop/darwin-xnu-build at the same pinned commit the CI
  uses; copy `xnu/patches/*.patch` + `*.sh` from this fork into its
  `patches/`; build with `MACOS_VERSION=13.5`,
  `MACHINE_CONFIG=MILANF`, `KERNEL_CONFIG=DEVELOPMENT`.
- Single-file iteration without full builds: `tools/xnu-cc.py`
  replays a captured build log's compile commands.
- Shim, ADT, payload, and root image build on the MacBook too (they
  build on Linux; on macOS they need the aarch64 cross tools /
  mkbootimg equivalents) — or keep them on this VM and only move
  the kernel build. Simplest split: VM does shim/ADT/root, MacBook
  (or CI) does XNU only.

Route A vs B is not exclusive: CI for the edit loop, MacBook for
offline iteration. The deciding factor is whether the fork goes
public.

## 7. Decisions Giulia owes

1. **Phone plug-in session.** Steps 1–2 need the unit on the laptop:
   run `../recon/` (read-only), then the unlock sequence (Motorola
   key; wipes the device — backups first, same session). Scheduling
   this afternoon is the whole critical path; every later step is
   downstream of the DTB it produces.
2. **Build host.** Publish the fork to GitHub (enables the macos-14
   CI above, free on a public repo, exactly upstream's move) **or**
   keep it private and build XNU locally on the M1 Max MacBook
   (Route B). Both work; CI is the faster iteration loop, the
   MacBook keeps the code unpublished.

Smaller, non-blocking: the `xiaomi,sweet` match-token retention
(§4) and when to light the A78 cluster as its own topology
(step 5) — both have safe defaults already chosen above.

## Appendix A — MILANF value ledger (as of this desk pass)

Across `tools/mkadt-milanf.py`, `shim/milanf-config.h`, and the
kernel board header (patch 0082):

| Status | Count | Values |
|---|---|---|
| CITED (mainline sm6375.dtsi) | 11 | GICD base+size, GICR base+size, GICR redistributor stride, VTIMER INTID 19, TIMEBASE 19.2 MHz, CPU count/topology (6+2, reg=Aff1), kryo660 compatible, little-cluster max clock, big-cluster max clock, DRAM base 0x80000000 |
| Architectural / fork choice | 6 | cache cline 6 (A78/A55), MAX_CPUS 8, IPI SGI 1, SOC_BASE, PANIC_LOG_SIZE, synthetic ECID |
| RESOLVED - unit DTB | 11 | PHYS_BASE, MEM_SIZE, HIGH_PHYS_BASE, HIGH_MEM_SIZE, FB base, FB size, FB width, FB height, FB stride, UFS base+size, IMEM restart-reason |
| DELIBERATELY ABSENT - unit DTB | 1 | PSHOLD: the DTB has no `pshold` node at all, and `reset()` issues PSCI `SYSTEM_RESET` first, so the fallback write is compiled out behind `HAVE_PSHOLD` rather than given an invented address |
| RESOLVED - unit boot image | 1 (group) | the image is header v3, which has no load addresses or page size at all (`tools/bootinfo.py`); the group turned out not to exist |

All twelve hardware values now come from the unit itself - its DTB,
cross-checked against the running kernel's `/proc/iomem` - and the
boot-image "group" resolved to "there is nothing to fill in". Sources are
recorded where the values sit, and both `tools/mkadt-milanf.py` and
`shim/build-milanf.sh` still refuse to proceed if one goes missing again.
