# ios-sweet: milanf fork

## iOS 16 on a Moto G Stylus 5G 2022, a phone that identifies as a Samsung Galaxy Note7

Upstream [ios-sweet](https://github.com/dipa-studio/ios-sweet) put Apple's iOS 16 (XNU kernel plus the unmodified iPhone X userland) on a Redmi Note 10 Pro. This fork moves the whole operation to `milanf`, the Moto G Stylus 5G 2022 (Qualcomm SM6375 / Snapdragon 695).

And about that Note7 thing: it is not a typo, and it is not (only) a joke. Per the port's design spec (§4), this build's enrolled model name is "Samsung Galaxy Note7", and the physical unit's stock Android already enrolls under the same name, so the phone now presents as an infamous Samsung on both operating systems. Internally it still makes every decision as an iPhone X (`iPhone10,3` / `D22AP`), because MobileGestalt has no sense of humor. Any log anywhere that ever records this enrollment will show a Galaxy Note7 running iOS 16.7.16 in Puerto Rico, unexplained, forever. We have made our peace with this.

## What this fork adds

Upstream skips Setup Assistant entirely. This fork re-enables it and fills it with custom panes, plus the root-tweaks layer that runs them. All of it lives in the companion tweaks repo (not yet published) and is assembled into the root image at build time. Every state machine below is implemented in dependency-free C99 and host-tested: **87 checks, 0 failures**, including an identity verifier that fails the build if the internal iPhone identity is touched or the presentation identity leaks into it.

- **The Gay Gate.** Setup opens with two buttons. Both read "gay". One continues to Wi-Fi. The other wipes the setup state and reboots the phone back into Setup. Nothing on screen tells you which is which. Which button continues is recorded in exactly one builder-only private header, so the builder can cheat at 2 AM instead of playing roulette.
- **The sexuality ledger.** The phone writes down every position you state, with which pane you stated it on. It keeps receipts. Contradictions have consequences (see: court).
- **The Consistency Court.** Press "im gay" on the microwave pane, then claim "im straight" one pane later, and the court convenes: "no fuck you you said you were gay just now??" Three ways out. "i reject the premise" sends you to start over. "im straight" (doubling down) sends you to start over. "im bi (or sm else) mbmbmb" is the only answer that survives: setup proceeds, and the court lets you keep your recorded allegiance. The phone accepts ambiguity and punishes flip-flopping.
- **Allegiance install math.** The Amodei-Altman pane ("would you fuck: dario amodei or sam altman") turns your slider position into install policy for exactly two bundle IDs in the universe: `com.anthropic.claude` and `com.openai.chatgpt`. Full dario lean: ChatGPT fails to install with probability 1.00 and Claude always installs. Full sam lean: the mirror image. Between center and an endpoint, the non-chosen side fails with probability proportional to the lean: a 0.25 lean makes ChatGPT fail half its installs, a 0.75 lean does the same to Claude. A weak preference is a flaky installer; a strong preference is a blockade. Dead center ("samrio altmodei"): both always install, because the phone regards both companies as itself and will not discriminate against itself. Everything else on Earth installs fine.
- **Battery health roulette.** During calibration, a twelve-segment wheel decides your battery health: 0.1%, 55%, 60%, 65%, 70%, 75%, 80%, 85%, 90%, 95%, 100%, and "your mom". Where it stops is the number the battery daemon reports, until a recalibration re-spins the wheel. Fairness is tested, not vibes: over 12,000 spins, every segment landed between 850 and 1,150 hits, "your mom" included (1,032). And for the record: exactly zero behavior was invented for "your mom". It is an outcome with a name and no consequences, because the spec defines none. The only way to get an honest battery health is the refusal button, which makes the daemon compute the real number from the fuel gauge. Rejecting the premise is the truth path.
- **The fake USPS tracker.** Finish Setup and there is a chance the phone does not go home. It goes full USPS instead: a tracking page for the phone itself, generated from your own setup run, with facilities named after the panes you passed (GAY GATE, WI-FI, and onward to ACTIVATION), an expected delivery window of 9:00 AM to 1:00 PM, and 21 events built from 7 milestones in the tested run. It blocks the phone, across reboots, until delivery. Release comes at a random time up to a week out (496,085 seconds in the tested run), as six scans in 2.8 seconds followed by "Delivered". Anyone who has watched a real parcel sit motionless for days and then receive six scans in one minute knows this is documentary realism.
- **The gender slider and its tint system.** One slider, labeled "gender", drives a float that interpolates the OS-wide accent from stock iOS blue (#007AFF) at 0.0 to full pink (#FF2D55) at 1.0. Park it on the exact center detent and the accent stops being a flat color and becomes an animated nonbinary flag glow (yellow, white, purple, black; 4 second cycle). Press "i reject the premise" and the entire OS renders in grayscale until the slider moves again. Refusal is a color scheme.
- **p(doom).** A slider asking "how much do you think is the p(doom) of this ios port??" Left endpoint: "its apple it cant destroy humanity". Right endpoint: "samsung galaxy note7", which, per the identity decision above, is no longer a metaphor but this device's legal identity. The float drives the thermal throttling thresholds and the PMIC charge ceiling: conservative and charge-capped on the left; limits off, clocks uncorked, full charge rate on the right. Note 7 mode.
- **The compass.** A political compass that starts dead center, because the phone's factory assumption about every user is perfect centrism until proven otherwise. Drag your point, then retype it in graphing notation, because the pane demands the coordinates typed as well as dragged. What the axes do to the OS is still an open design item. The phone records your position regardless.
- **The labor policy pane (Foxconn).** "would you like to work at foxconn" Answers include "call the pope" (the pope is not called; there is no pope infrastructure in this build) and "yes daddy enslave me", whose one decided consequence is mommy ASMR at full volume for the remainder of Setup. The labor policy itself is still proposed, not decided.
- **The rest of the docket.** A microwave pane ("could this phone be a microwave"; the verdict on the Vsauce path is "yes. a 0.1 watt one.", and the "im gay" answer is what routes you to the Amodei-Altman pane in the first place). A Terms of Service whose complete text is "gay", with a printing option that prints nothing, ever. A recurring update pane offering "ios 2" forever, dismissible only by tapping the one fully true statement in the entire UI ("erm actually 🤓 this is an android phone"), after which the update returns later, unbothered. A migration pane that replaces the stock transfer offer with "no fuck you were not migrating jackshit". Fifteen Setup panes in canonical order in total, plus the tracker waiting past the finish line. And when the flow finally exhausts itself, the last screen reads "you may kiss the bride", because activation was a wedding and the phone is the bride. It is also an Android phone. The marriage does not change that.

## The glorious Face ID bullshittery

The iPhone X userland arrives expecting a TrueDepth camera array and a Secure Enclave. milanf has neither; it has a punch-hole camera and its dignity. So the port keeps the stock Face ID surface (SpringBoard, the enrollment UI, LocalAuthentication prompts, all unmodified) and builds a replacement backend behind it: one matcher daemon answering through a BiometricKit-facing shim. Templates live in the filesystem because there is no Enclave to vault them; the spec states that once and moves on. The backends ship in order: the fingerprint sensor hiding in the power button first (a modest SPI peripheral, works in the dark, needs no camera pipeline), then a 2D camera matcher, then the main event below.

- **The geometry registry.** Every optical feature stands on one calibration artifact (SPEC §8.2): intrinsics for each camera from ChArUco board captures, extrinsics between every camera pair from simultaneous stereo captures, caliper measurements of the module as ground truth, the display catalogued as an optical device in the same registry, and the display-to-front-camera transform (the Face ID baseline) solved with a front-surface mirror while the screen shows calibration patterns. On genuine Apple hardware this data is per-unit factory calibration, which is why swapping a camera without transferring its calibration breaks Portrait mode. Here it is bench work, done once, consumed by everything optical.
- **The display is the projector.** There is no IR dot projector, so the panel does the job. At auth time the entire base Dynamic Island interior is the projection window: sinusoidal phase-shifting patterns play across it while the front camera (720p class, up to 120 fps in a windowed readout, so a four-pattern phase set completes in about 33 ms) reads how the fringes bend across the face, and per-pixel phase plus the calibrated baseline triangulates a depth map. Photometric stereo runs in parallel, lighting the face from different panel regions to recover surface normals, which is decisive as liveness: a photograph produces flat normals and fails the depth channel outright. Matches fuse the measured depth with an RGB embedding matcher, and depth templates are stored in a canonical face frame, in millimeters. The physics limits are recorded, not hidden: LCD pixel response caps clean patterns at roughly 30 to 60 per second (a 120 Hz refresh is not 120 crisp patterns), sunlight collapses pattern contrast (this is an indoor and evening rig), and the short display-to-camera baseline yields coarse depth, which is sufficient for liveness plus template matching. The research anchor is real: Face Flashing (Tang et al., 2018) published an LCD-flashing liveness protocol at 98.8% reported accuracy, and its known implementation difficulty, precise screen-camera sync through a normal phone stack, is exactly the constraint this port's driver-level control removes. The specific combination, a phone panel as a phase-shifting projector building the depth template that is itself the biometric, was not found in the literature as of 2026-10-21. Novel composition of published parts.
- **The island, shrunk to fit its secret.** The genuine System Aperture shipped in every iOS 16 build from 16.1 onward, capability-gated off on the iPhone X identity. DynamicCow lit it on stock X-class hardware by spoofing MobileGestalt to iPhone 15,2; in this port Gestalt is a build-time edit, no exploit required. Whether 16.7.16 added further gating is UNKNOWN until the first root image tries it; extra checks are patchable, and the fallback is a DynamicPeninsula-class tweak reimplementing the aperture around the cutout. Giulia's shrink spec: the 14 Pro's pill is large because it hides a speaker slot and a sensor array, while milanf hides one camera, so the idle island hugs the punch hole at about 60 x 28 pt, the hole centered with a black margin ring. Expanded states shrink less or not at all, sized by per-state layout overrides rather than a transform scale (scaling shrinks text; overrides let content reflow), with final alignment done by the framebuffer copy offset and touch compensating the inverse. During a Face ID session the island expands to the full base size, plays the stock unlock animation, and grows a 2 pt white outline for the duration of capture: a legible active boundary on a panel where black-on-black is meaningless, and a target that puts the face in the calibrated zone. On match the outline dies and the island collapses back to its ring. Total ritual: about a second.
- **One island, both biometrics.** One matcher daemon, two backends, one shim reporting a single logical biometric (reported type: faceID), so apps get stock LocalAuthentication semantics and cannot tell which modality matched. On an auth request the island splits into a selector, face glyph one side, fingerprint glyph the other. Do nothing and face capture arms automatically. Touch the power button and the wake-on-touch sensor makes the touch the selection and the authentication in a single gesture; press-and-hold is confirm plus authenticate in one. Tap a half to choose deliberately. If the face fails twice, the fingerprint half pulses: the island suggests the fallback instead of surrendering to passcode. The stock iPhone X identity ships no Touch ID enrollment UI at all, so a tweak adds a fingerprint section to the Face ID & Passcode page, and the presentation layer titles the combined page as one biometrics page.
- **Holy enrollment.** The custom enrollment pane puts a viewfinder under the island and instructs: "place your face in the camera thingy". Four options. "the pope said face id is bad and i dont wanna get killed by the anti ai police" is the conscientious-objector path: it declines Face ID and routes to Touch ID and passcode, and the pope's jurisdiction over this operating system is not explained anywhere in the UI. "js use touch id i dont wanna have a seizure" is the accessibility path, offered inside the enrollment screen rather than buried in Settings: it routes to the fingerprint and sets the capture side to its non-flashing configuration, persistently. "can i authenticate with my dick" is present on the pane, and per Giulia's explicit ruling it is a button, not a promise: alternate-anatomy authentication is NOT implemented, is not a feature, and is not planned. "Cancel" is stock. Once capture begins, the whole top band of the screen is labeled "AREA TO FLASH" and the island visually disappears, submerged, because enrollment uses the wide projection area where unlock-time auth uses only the island: enrollment is the one capture that should be maximal. A dotted circle asks you to "move your face in a circle", the stock choreography, kept because the circling is what feeds the depth template its angles. Progress is rendered as the opacity of a photograph of a rotisserie chicken: chicken opacity equals face-coverage fraction, no face means no chicken, and at 100% you complete your biometric enrollment looking at an entirely opaque rotisserie chicken. The chicken is a real photograph, per the standing no-AI-images rule.
- **Safety is a headline, not a footnote (SPEC §10.4).** Flashing patterns in roughly the 3 to 30 Hz band at high contrast are a photosensitive epilepsy hazard, so these are requirements, not vibes. A single-shot mode replaces temporal phase shifting with one static coded pattern and one capture: zero flashing, slightly coarser depth, selectable permanently with a Reduce Flashing toggle; if iOS Dim Flashing Lights or Reduce Motion is already on, single-shot is the default with no toggle hunt. In strobing mode, for everyone: no saturated red in any pattern, ever; patterns are sinusoids around a mid-gray mean, never full black-to-white; per-pixel luminance swing is capped; and the flashing area is the island only, a small patch of the visual field. Enrollment discloses all of it in plain language and presents the non-flashing alternative and Touch ID as equals. And the structural point the design is proudest of: the dual-biometric architecture means the safe path is a full-speed fingerprint, not a downgrade to passcode-only.

## Status, honestly (2026-10-21)

- **Nothing has booted on milanf hardware yet.** This README will keep saying that until the day it does not have to.
- Kernel CI is live on GitHub's macos-14 runners, and the MILANF machine config (patch `xnu/patches/0082-milanf-machine-config.patch`) is currently faceplanting: the patch is corrupt at line 56, CI skips it, and the build stops at "Unsupported CURRENT_MACHINE_CONFIG MILANF". Repair is queued. First CI run: [39691962059](https://github.com/legobele/ios-sweet/actions/runs/39691962059).
- 12 of 23 hardware values (memory map, framebuffer parameters, UFS base, and friends) are UNKNOWN, pending the target unit's stock DTB. The tooling refuses to lie about this: `tools/mkadt-milanf.py` will not emit a device tree while placeholders are unresolved, and if you force it with `--allow-placeholders`, the output is stamped `milanf-shim-PLACEHOLDERS-DO-NOT-BOOT`.
- The device recon pack is written and deliberately read-only: it captures the DTB and partition data without flashing or unlocking anything. The plug-in session has not happened yet, and it gates every hardware value above.
- The bring-up runbook is [BRINGUP.md](BRINGUP.md) (SPEC steps 1 to 4 as an executable plan, including the ABL splash framebuffer probe). Fork decisions and deviations from upstream live in [FORK.md](FORK.md).

A Nivelato Labs project. Fork of [dipa-studio/ios-sweet](https://github.com/dipa-studio/ios-sweet); all upstream credit belongs to its authors. Everything below this section is the upstream README, and it describes `sweet`, the Redmi Note 10 Pro, not milanf.

---

# ios-sweet

**Apple's iOS 16 running on a Redmi Note 10 Pro.**

This project ports Apple's open-source XNU kernel (xnu-8796, the iOS 16 generation) to the Xiaomi Redmi Note 10 Pro (`sweet`, Qualcomm SM7150 / Snapdragon 732G). On top of it runs the **unmodified iOS 16.7.16 (20H392) userland of the iPhone X**: launchd, the system daemons, backboardd, SpringBoard and the stock apps.

As of **2026-10-18** the phone boots to the **iOS home screen**. You can unlock it, open Settings, pull down Control Center and the notification center, and use the touchscreen and the hardware buttons. Rendering runs entirely on the CPU; there is no GPU driver.

> Experimental bring-up, not a usable phone OS. Many things are missing or stubbed (see below), and Apple's security model is mostly switched off. It installs into the `userdata` partition and so **erases Android's user data**.

## What works

| Area | State |
| --- | --- |
| Boot | Stock Xiaomi bootloader → `fastboot boot` of our shim → XNU. Nothing is flashed to the boot partitions |
| CPU | 6 of the 8 cores (the six Cortex-A55s) via PSCI, 16K pages, GICv3 interrupts, timers |
| Memory | About 3.95 GiB of the upper DDR bank |
| Storage | Own UFS host driver; the iOS root is a journaled HFS+ volume in `userdata`, read/write |
| iOS userland | Real iPhone X 16.7.16 root filesystem and shared cache; launchd and the system daemons run |
| Display | Kernel IOSurface + IOMobileFramebuffer (`AppleCLCD`) services; CoreAnimation renders in software; frames are copied into the bootloader's framebuffer. Presented to iOS as an iPhone X panel (1125×2436) |
| GUI | backboardd, SpringBoard, lock screen, home screen, Control Center, notification center, Settings |
| Touch | Goodix GT9896 over I²C (GENI), rail enabled through RPMh, delivered as HID digitizer events |
| Buttons | Power, volume up/down (PMIC through SPMI) as HID consumer keys; lock/wake works |
| Battery | IOPMPowerSource service (static 100 %, charging icon; real fuel-gauge readout prepared) |
| Device identity | iPhone X (`iPhone10,3` / `D22AP`): no Home button, gesture UI |
| Activation | Native "Hactivation" path of mobileactivationd, chosen through device-tree security status. No Apple servers involved |

## What does not work (yet)

- **Navigation:** you cannot leave an app (the home gesture and AssistiveTouch Home do nothing yet).
- **No Wi-Fi, Bluetooth, cellular, audio, camera, sensors, GPS or SEP / Face ID.** Daemons for them start and fail or keep relaunching.
- **No GPU.** Everything is drawn by the CPU at roughly 20–30 fps. The two Cortex-A76 cores are not used yet.
- **Few apps.** The image has only what is on the system volume. There is no App Store, no Apple ID, and some Settings pages are empty.
- **Slow boot:** about 4 minutes on the Apple logo.
- **Security is off:** permissive code signing (AMFI) and sandbox policies, a stub AppleKeyStore, no data protection. Do not put anything personal on it.

## How it boots

```
ABL (stock Xiaomi bootloader, unlocked)
  -> fastboot boot shim-boot.img              (temporary; nothing is flashed to boot)
     -> shim: own MMU setup, reads the live FDT, loads the payload from the ramdisk
        -> XNU Mach-O + generated Apple Device Tree (ADT) + boot-args
           -> XNU -> UFS driver -> HFS+ root in the userdata partition
              -> dyld + shared cache -> launchd -> daemons -> backboardd + SpringBoard
```

There is no serial port (the debug UART is wired as SPI on this board). The kernel draws its console into the framebuffer that ABL leaves at `0x9c000000`, and keeps a persistent 4 MiB log ring at the end of `userdata`. You read that log from OrangeFox recovery with `tools/sweet-log-pull.sh`, so you don't have to film the screen.

## How to do it yourself

You need a Redmi Note 10 Pro (`sweet`, global or Indian variant, SM7150) with an **unlocked bootloader**, a Linux PC, and a GitHub account for the kernel build. This is the exact path used for the screenshots above; other variants or firmware may need changes. **Everything on `userdata` is lost.** Bootloaders, recovery, modem and persist partitions are never touched.

### 0. Back up the phone

Boot OrangeFox (or any recovery with adb root) temporarily and pull at least `persist`, `modemst1`, `modemst2`, `fsg`, `fsc` and `boot`, `dtbo`, `vbmeta`. They contain per-device calibration data. Keep them off git; `.gitignore` already excludes `backup/`, `dtb/` and `recovery/`.

The shim needs the stock DTB. Unpack your phone's stock `boot.img`:

```sh
python3 tools/unpack_bootv2.py backup/boot.img dtb/boot_unpacked   # -> dtb/boot_unpacked/dtb
```

### 1. Build the kernel

The kernel builds on GitHub's macOS runners with [blacktop/darwin-xnu-build](https://github.com/blacktop/darwin-xnu-build). The workflow fetches xnu-8796, applies `xnu/patches/` in order, and also stages the pinned open-source libpthread, HFS and BearSSL sources it needs. Fork the repo (public repos get free macOS minutes) and run:

```sh
gh workflow run xnu.yml -R YOU/ios-sweet
gh run download RUN_ID -R YOU/ios-sweet -n xnu-kernel -D xnu/out
```

To check a patch locally before spending a CI run, `tools/xnu-cc.py` replays the compile commands of a previous CI log for single files.

### 2. Build the iOS root image

Download the iPhone X (iPhone10,3) iOS 16.7.16 (20H392) IPSW from Apple. Then, on Linux, with `apfs-fuse`, `hfsprogs` and sudo:

```sh
# OS, SystemOS and AppOS disk images from the IPSW (see BuildManifest.plist for their names)
tools/mkiosroot.sh OS.dmg SystemOS.dmg AppOS.dmg ios16-root.img 16G
sudo fsck.hfsplus -fy ios16-root.img
sudo mount -t hfsplus -o loop,force ios16-root.img /mnt/iosroot
sudo python3 tools/sweet-root-tweaks.py /mnt/iosroot
sudo umount /mnt/iosroot
img2simg ios16-root.img ios16-root.simg
```

`mkiosroot.sh` copies the OS volume and both cryptexes into one case-sensitive journaled HFS+ volume. It adds the dyld cache links, the plain system keybag and the log directories the daemons expect. `sweet-root-tweaks.py` applies the bring-up changes: it skips Setup, seeds the activation state, removes the baseband daemon, disables the watchdogs that kill slow apps and the crash-looping media paths, and so on. The script's header explains each change.

The device tree builder copies `/product` from the real iPhone X device tree, which MobileGestalt needs. Extract it once, without downloading the whole IPSW:

```sh
python3 tools/remotezip.py IPSW_URL DeviceTree.d22ap.im4p research/ipsw-x/dt
ipsw img4 im4p extract research/ipsw-x/dt/Firmware/all_flash/DeviceTree.d22ap.im4p -o research/ipsw-x/d22ap.adt
```

### 3. Build the boot image

Needs `aarch64-linux-gnu-gcc` and `mkbootimg`.

```sh
python3 tools/mkadt.py shim/out/sweet.adt --highmem
python3 tools/mkpayload.py xnu/out/kernel.development.sweet shim/out/sweet.adt shim/out/payload.bin \
    --cmdline 'debug=0xc serial=3 cpus=6 keepsyms=1 -enable_kprintf_spam -noprogress rd=ufsroot0 unentitled_ios_sim_launch=1 ignition_level=1 wdt_test=no_user_checkin ufsrw=1 rootrw=1 launchd_unsecure_cache=1 wdt=-1 sweetfb_noconsole=1 sweetfb_hz=30'
shim/build.sh ../shim/out/payload.bin      # -> shim/out/shim-boot.img
```

What the less obvious boot-args do:

| Boot-arg | Effect |
| --- | --- |
| `rd=ufsroot0 ufsrw=1 rootrw=1` | Root on the `userdata` partition, writable |
| `cpus=6` | Start the six A55 cores; `cpus=1` is the safe fallback |
| `launchd_unsecure_cache=1` | launchd accepts its job cache without AMFI |
| `wdt=-1 wdt_test=no_user_checkin` | No hardware watchdog |
| `sweetfb_noconsole=1` | Stop drawing kernel text over the GUI. It still goes to the persistent log; panics are drawn |
| `sweetfb_hz=30` | Panel refresh rate of the CPU copy |
| `sweettouch=0`, `sweetkeys=0` | Disable the touch or button driver |

### 4. Flash the root and boot

```sh
fastboot -S 512M flash userdata ios16-root.simg   # ~7 minutes; do not unplug
# Xiaomi's fastboot often hangs after a large flash: re-enter fastboot with Power + Volume down
fastboot boot shim/out/shim-boot.img
```

The first boot takes about 4–5 minutes on the Apple logo, then the lock screen appears. Swipe up to unlock. To get back to fastboot, hold Power + Volume down.

### 5. Read the kernel log

```sh
fastboot boot recovery/recovery.img        # OrangeFox, temporary
tools/sweet-log-pull.sh logs/boot.txt      # 4 MiB console ring from the end of userdata
adb reboot bootloader
```

The log contains crash reports with backtraces (`CRASH name ...`), IOKit traces of backboardd and SpringBoard, and the drivers' `SWEET ...` lines. `tools/sweet-crash.py` symbolicates them against the shared cache.

### QEMU

`tools/qemu-sweet.py` boots the same kernel on QEMU `virt` with a test RAM-disk root. It is useful for kernel-only changes; see `NOTES.md`.

## Repository layout

| Path | What |
| --- | --- |
| `shim/` | Bare-metal boot shim (C + asm) packed as an Android boot.img v2 |
| `xnu/patches/` | The XNU patch series (applied in order by CI), plus staging scripts for libpthread, HFS and BearSSL |
| `.github/workflows/xnu.yml` | Kernel CI build |
| `tools/mkadt.py` | Generates the Apple Device Tree from sweet's MMIO layout and the iPhone X identity |
| `tools/mkpayload.py` | Packs kernel + ADT + boot-args into the shim payload |
| `tools/mkiosroot.sh` | Builds the HFS+ iOS root from the IPSW images |
| `tools/sweet-root-tweaks.py` | Bring-up changes to the root (Setup skip, activation, daemons) |
| `tools/sweet-log-pull.sh`, `sweet-log.py` | Read the persistent kernel log from recovery |
| `tools/sweet-crash.py` | Symbolicate console crash reports |
| `tools/xnu-cc.py` | Local single-file compile check from a CI log |
| `tools/qemu-sweet.py` | QEMU test boots with framebuffer text decoding |
| `tools/adt.py`, `remotezip.py`, `unpack_bootv2.py`, `sparsediff.py` | Helpers |
| `NOTES.md` | Detailed engineering log: every boot, crash and decision, plus hardware facts |

Not in git: partition backups, live device trees, recovery images, Apple firmware and root images, and downloaded or generated build trees. They contain device serials and calibration data, or Apple's copyrighted files.

## Kernel patches

| # | What |
| --- | --- |
| 0001–0009 | Toolchain compatibility, SWEET machine config, non-PAC arm64, stubs for Apple-internal pieces |
| 0010–0018 | Early framebuffer console, physmap fix, PRNG without corecrypto, device-tree platform expert, timer PPI, boot CPU driver |
| 0019–0020 | Apple open-source libpthread kernel provider; BearSSL AES |
| 0021–0027 | RAM-disk root, mockfs, SHA-256, minimal AMFI, Apple open-source HFS+, MD5 |
| 0028–0034 | UFS host driver and root device, read/write root, DMA above 4 GiB |
| 0035–0045 | Entitlements, bindfs, AppleKeyStore stub, IOWatchdog, console crash reports |
| 0046 | IOSurface (IOCoreSurfaceRoot) and IOMobileFramebuffer (AppleCLCD) services |
| 0047–0055 | Diagnostics: persistent log, /dev/null tee, IOKit trace, heap strings and user stack sampler on crash; permissive Sandbox policy; HFS rename-swap; AppleKeyStore selectors |
| 0056–0057 | Throttled panel copy; no external identity resolver |
| 0058 | HID event services. Apple's IOHIDFamily-1915.140.3 user client and event queue, matching the iOS 16.7 userland |
| 0059 | iPhone X identity (`hw.product` / `hw.target` from the device tree) |
| 0060 | Power and volume keys over SPMI; touch over GENI I²C |
| 0061 | Present the display as 1125×2436 |
| 0062 | RPMh regulator vote for the touch rail; battery power source |
| 0063 | GENI FIFO packing fix and the Goodix GT9896 protocol |
| 0064 | Grant PRIV_WORK_INTERVAL (UIKit's CoreAnimation work interval) |
| 0065 | SMP: secondary A55 cores via PSCI CPU_ON |
| 0066–0067 | Fault-region crash info; console mute |
| 0068 | IOSurface lookup semantics for already-mapped surfaces |
| 0069 | Batched persistent-log flushes |

## Key hardware facts

- RAM: payloads use the upper bank, `0x100000000` + `0xfcc00000` (about 3.95 GiB), above Qualcomm's protected carve-outs.
- GICv3 with security extensions: the timer goes through Group 1 IRQ (virtual timer INTID 19), not FIQ as on Apple silicon.
- PSCI through `smc`, 19.2 MHz timer, ARMv8.2 without pointer authentication. MPIDR uses Aff1 for the core number.
- Panel: 1080×2400 DSC video mode, continuous splash from ABL, no refresh kick needed.
- Touch: Goodix GT9896 at I²C `0x5d` on QUP SE7 (`0xa84000`), powered by PM6150L LDO11 through RPMh.
- Buttons: power and volume down on the PM6150 PON block, volume up on PM6150L GPIO2 (SPMI SID 4).

More in [`NOTES.md`](NOTES.md).

## Credits

Built on Apple's open-source releases (xnu, IOHIDFamily, libpthread, hfs), [BearSSL](https://bearssl.org), [blacktop/darwin-xnu-build](https://github.com/blacktop/darwin-xnu-build), [ipsw](https://github.com/blacktop/ipsw), Qualcomm/Xiaomi's published Linux kernel sources for the hardware details, and [OrangeFox Recovery](https://orangefox.download). iOS itself is Apple's and is not distributed here.
