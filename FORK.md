# FORK.md — ios-sweet → ios-milanf

## Upstream

- URL: https://github.com/dipa-studio/ios-sweet
- Cloned commit: `425b25102b6a9ee4b68fb2b9ca5d6a086b8a4116`
  ("Merge pull request #6 from 2010475745xie/adt-panic-region", 2026-10-21)
- Clone method: `git clone --depth 50` (shallow). Nothing else was skipped:
  upstream has no git submodules and no Git LFS attributes, and the working
  tree is ~2.8 MB complete (shim/, tools/, xnu/patches/, docs/, site/).
- This fork's branch: `milanf`. Upstream default branch: `main`.
- Governing design document: `../SPEC.md` (ios-milanf port spec, 2026-10-21).
  This repo state was produced at a desk, with no hardware work, per the
  spec's own status line.

## What transfers from upstream (SPEC §1)

| Upstream piece | Where it lives here | Transfer status |
|---|---|---|
| XNU patch series (xnu-8796, iOS 16 generation) | `xnu/patches/` | Transfers as-is; needs a MILANF machine config added (not yet written — kernel work is SPEC §14 step 3, hardware phase) |
| Root image build | `tools/mkiosroot.sh` | Transfers; milanf root images will be produced by this once a kernel boots |
| Root-tweaks stage | `tools/sweet-root-tweaks.py` | Transfers; the milanf build-time edits (identity split, Setup panes) are being developed as a separate package in `../root-tweaks/` and will hook into this stage |
| Payload + boot-arg machinery | `tools/mkpayload.py`, `tools/mkinit.py`, `tools/adt.py`, `tools/mkadt.py` | Transfers |
| Boot shim | `shim/` (loader, MMU, FDT, console) | Transfers as a head start; milanf ABL behavior is SPEC unknown #1, resolved by the §1.1 probe |
| Qualcomm-family driver work | `shim/ufs.c` (UFS host), GENI I2C / SPMI PMIC / RPMh work in `xnu/patches/` + `NOTES.md` | Head starts, not finished code (SPEC §1 wording) |
| QEMU test harness | `tools/qemu-sweet.py`, `docs/QEMU_TESTING.md` | Transfers; useful for desk-testing shim changes |

## What is milanf-specific (not upstream, not portable back)

- Target SoC: Snapdragon 695 (SM6375) instead of SM7150. ARMv8.2, no PAC —
  the same non-PAC world the kernel patches assume (SPEC §1, §2).
- A MILANF XNU machine config (to be written; SPEC §14 step 3).
- Motorola boot chain facts: A/B slots, official bootloader unlock, Moto ABL
  splash-framebuffer behavior (UNKNOWN, SPEC §1.1 / §13.1).
- Giulia's unit specifics: warranty-replacement unit, panel type UNKNOWN
  (SPEC §7), front camera part UNKNOWN (SPEC §8.3). All display/camera
  bring-up facts get probed on this unit, not read off retail docs.
- The identity split (SPEC §4) and the entire custom Setup flow (SPEC §12):
  developed in `../root-tweaks/` (sibling package, its own README maps every
  component to its spec section). None of it exists upstream; upstream skips
  Setup entirely.
- The enrolled model name constant (SPEC §4) is "Samsung Galaxy Note7". It
  also matches the unit's current Android enrolled name, per Giulia
  2026-10-21 — so the port's enrolled-name constant isn't an invention; it
  preserves the device's existing cross-OS identity.
- A package-manager layer (added 2026-10-21, in `../root-tweaks/bootstrap/`):
  the official Procursus bootstrap (strap line 1600, the iOS 16 line) and
  Sileo 2.5.1 baked into the root image, pinned by version + size + SHA-256,
  rootful layout, with a first-boot finalize hook ordered so the strap's own
  firmware-package generation precedes Sileo's configure. Upstream has no
  equivalent; its images are bring-up artifacts, not a userland you live in.

## Build order (SPEC §14), annotated with what this repo state satisfies

| # | Step | Status in this repo state |
|---|---|---|
| 1 | Step-0 backups and dumps (boot, dtbo, vbmeta, persist, modem partitions; stock DTB) | NOT satisfied — hardware step, device in hand required. Resolves unknowns 2, 3, 4, 6 |
| 2 | §1.1 probe (splash framebuffer + fastboot boot) | NOT satisfied — hardware step. Resolves unknown 1 |
| 3 | Shim + MILANF machine config + kernel boot to framebuffer console and persistent log | NOT satisfied — shim source present from upstream; MILANF config not yet written |
| 4 | UFS driver, root image boot, launchd, SpringBoard (tethered) | NOT satisfied |
| 5 | Touch, PMIC keys, battery reporting; A78 cores lit | NOT satisfied |
| 6 | Full install (SPEC §3) once SpringBoard is reliable | NOT satisfied |
| 7 | Identity split (SPEC §4) and Setup flow (SPEC §12) | **PARTIALLY satisfied at desk level**: `../root-tweaks/` contains the identity patch/verify scripts, the prefs core, all §12 pane logic + state machines with passing host-side logic tests, and the Procursus/Sileo bootstrap layer with pinned, hash-verified artifacts (`BOOTSTRAP-VERIFY.txt`). NOT yet integrated into `tools/sweet-root-tweaks.py` or a real root image — that integration happens when step 4 produces a bootable image |
| 8 | Camera pipeline (front first), geometry registry calibration (SPEC §8) | NOT satisfied |
| 9 | Fingerprint backend | NOT satisfied (independent of 8) |
| 10 | Island: Gestalt un-gate attempt, tweak fallback, shrink + alignment (SPEC §9) | NOT satisfied |
| 11 | Dual-biometric selector element (SPEC §11) | NOT satisfied |
| 12 | Face rig: 2D matcher, structured-light depth, single-shot safe mode (SPEC §10) | NOT satisfied |
| 13 | GPU rungs 1 and 2 (SPEC §6) | NOT satisfied |
| 14 | Rear camera fusion features on the registry | NOT satisfied |

Desk work that CAN precede hardware and is queued behind this state:
extracting the pinned SpringBoard binary (iPhone10,3, 16.7.16 / 20H392) from
the IPSW and class-dumping the aperture layout methods (SPEC §9.1).
