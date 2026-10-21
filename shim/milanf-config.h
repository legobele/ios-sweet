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

/* --- Framebuffer console (console.h) ----------------------------------
 * STATUS: UNKNOWN (all four).
 * Source: the unit DTB's reserved-memory — look for a cont_splash /
 * framebuffer region, or a simple-framebuffer node; whether Moto ABL
 * leaves a live splash framebuffer at all is SPEC §13 unknown 1,
 * settled by the §1.1 probe (BRINGUP.md §3). Sweet's values
 * (0x9c000000, 1080x2400, stride 4320) are SM7150-unit-specific and
 * must NOT be copied here.
 *   FB_BASE   = ?
 *   FB_W      = ?   (panel native width)
 *   FB_H      = ?   (panel native height)
 *   FB_STRIDE = ?   (expect W*4 for a8r8g8b8; verify)
 */

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
 * STATUS: UNKNOWN.
 * Mainline sm6375.dtsi has NO UFS node (only SDHCI), so there is no
 * citable address. Source: the unit DTB's ufshc@ node reg, or the
 * downstream SM6375 kernel DTS. Sweet's 0x01d84000 must NOT be
 * assumed to carry over.
 *   UFS_BASE = ?
 */

/* --- Restart path (shim.c) ---------------------------------------------
 * STATUS: UNKNOWN (both).
 * SM7150's values (IMEM restart_reason at 0x146aa65c, PSHOLD at
 * 0x0c264000) are SoC-specific register addresses in the
 * qcom,msm-imem / pshold nodes. Sources: the unit DTB's
 * qcom,msm-imem node children and the downstream sm6375 pshold node.
 * Until resolved, the milanf shim's reset path is PSCI SYSTEM_RESET
 * only (the probe code already falls back to it).
 *   IMEM_RESTART_REASON = ?
 *   PSHOLD              = ?
 */
