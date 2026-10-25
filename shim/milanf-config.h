/*
 * milanf-config.h — every shim-side hardware value for the Moto G
 * Stylus 5G (2022) ("milanf", Qualcomm SM6375), in one place.
 *
 * The upstream shim hardcodes its values at the use sites:
 *   shim/console.h  FB_BASE / FB_W / FB_H / FB_STRIDE
 *   shim/shim.c     GICD_BASE / GICR_BASE / GICR_SIZE / GICR_PE_SIZE,
 *                   IMEM_RESTART_REASON, PSHOLD
 *   shim/ufs.c      UFS_BASE
 * Wiring step (SPEC §14 step 3, see BRINGUP.md): point those defines
 * at the values below. Until then this header is the ledger — and
 * build-milanf.sh refuses to build while any entry is still UNKNOWN.
 *
 * Provenance:
 *   CITED   mainline Linux arch/arm64/boot/dts/qcom/sm6375.dtsi
 *           (kernel.org, read 2026-10-21); the unit's own DTB is the
 *           authority and must confirm every CITED value.
 *   UNKNOWN no trustworthy public source. Resolve ONLY from the
 *           unit's stock DTB dump (../recon/ decompile report) or the
 *           downstream SM6375 kernel source. Never from memory.
 */
#pragma once

/* --- Framebuffer console (console.h, mmu.h) ---------------------------
 * STATUS: RESOLVED for geometry (the unit's own DTB). Liveness is still
 * UNVERIFIED — nothing has been booted on this device yet, so "the display
 * engine keeps scanning this buffer out" remains the §1.1 probe
 * (BRINGUP.md §3).
 *
 * cont_splash_region@0x85200000, size 0xc00000 (12MB). It ends exactly
 * where dfps_data_region@0x85e00000 (1MB) begins, which is what a real
 * splash carveout looks like rather than a generic reservation.
 *   1080 x 2460 x 4 = 10627200 bytes, which fits in the 12MB region.
 *   stride 4320 is corroborated by the DTB's panel-width = 0x438 = 1080.
 *   height 2460 is from the live device: the DTB's static panel list only
 *   reaches 2340, but the carveout is sized for 2460 and the panel reports
 *   it. The iOS side maps the same buffer (xnu patch 0086).
 */
#define MILANF_FB_BASE		0x85200000UL
#define MILANF_FB_W		1080
#define MILANF_FB_H		2460
#define MILANF_FB_STRIDE	(MILANF_FB_W * 4)

/* --- GIC (shim.c) ------------------------------------------------------
 * STATUS: CITED — mainline sm6375.dtsi, intc: interrupt-controller@f200000
 *   reg = <0x0 0x0f200000 0x0 0x10000>   GICD
 *         <0x0 0x0f240000 0x0 0x100000>  GICR (8 redistributors)
 *   redistributor-stride = <0 0x20000>
 * NOTE: SM6375's GIC is NOT at SM7150's 0x17a00000.
 */
#define MILANF_GICD_BASE	0x0f200000UL
#define MILANF_GICR_BASE	0x0f240000UL
#define MILANF_GICR_SIZE	0x100000UL
#define MILANF_GICR_PE_SIZE	0x20000UL

/* --- UFS host (ufs.c) --------------------------------------------------
 * STATUS: RESOLVED - the unit's own DTB.
 * /soc/ufshc@4804000  reg = <0x4804000 0x3000  0x4808000 0x8000
 *                            0x4810000 0x9000>
 *                     reg-names = "ufs_mem", "ufs_ice", "ufs_ice_hwkm"
 * The UFSHCI register window is the first (ufs_mem) bank, 0x4804000 for
 * 0x3000 bytes. Mainline sm6375.dtsi indeed has no UFS node, so this
 * comes off the device and nothing else. Sweet's 0x01d84000 does not
 * carry over, as suspected.
 */
#define MILANF_UFS_BASE		0x04804000UL
#define MILANF_UFS_SIZE		0x3000UL

/* --- Restart path (shim.c) ---------------------------------------------
 * IMEM_RESTART_REASON: RESOLVED - the unit's own DTB.
 *   /soc/qcom,msm-imem@c125000  reg = <0xc125000 0x1000>
 *   /soc/qcom,msm-imem@c125000/restart_reason@65c  reg = <0x65c 0x4>
 * so the register is 0xc125000 + 0x65c = 0x0c12565c. (Sweet's 0x146aa65c
 * is the SM7150 IMEM base, not a fixed offset.)
 *
 * PSHOLD: DELIBERATELY ABSENT on milanf, not unknown.
 * The shim's reset sequence is PSCI SYSTEM_RESET first (shim.c reset()),
 * and PSHOLD only as the fallback that runs if the SMC returns. The TZ
 * on this SoC answers SYSTEM_RESET - it is what the stock kernel uses -
 * and no pshold node exists anywhere in the unit's DTB, so there is no
 * value to cite. Leaving the write compiled out is honest; inventing an
 * address to fill the slot is not. If the SMC ever fails to reset the
 * device, this is the line to revisit.
 */
#define MILANF_IMEM_RESTART_REASON	0x0c12565cUL
