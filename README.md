<div align="center">

# ⚡ Galaxy XR Forge

**Every community repo for the Samsung Galaxy XR (SM-I610) in one place: root tools, KernelSU modules, streaming drivers, app patches, ports and diagnostics.**

[![community repos](https://img.shields.io/badge/community_repos-66-orange?style=flat-square)](#catalog)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-2ea44f?style=flat-square)](#suggest-a-repo)
[![GitHub stars](https://img.shields.io/github/stars/AngelDark92/GalaxyXR-Forge?style=flat-square&label=star)](https://github.com/AngelDark92/GalaxyXR-Forge)
[![last commit](https://img.shields.io/github/last-commit/AngelDark92/GalaxyXR-Forge?style=flat-square)](https://github.com/AngelDark92/GalaxyXR-Forge/commits/main)

<sub>[🛡️ Root & Kernel](#root-kernel) · [🧩 KernelSU Modules](#kernelsu-modules) · [👁️ Face & Eye Tracking](#face-eye) · [🖥️ PC VR & Streaming](#pcvr-drivers) · [📱 App Patches & Ports](#app-patches) · [🎮 Games & Emulation](#games) · [🔧 Tools & Diagnostics](#tools) · [🧪 Apps & Samples](#apps-samples) · [🏗️ Foundations & Upstreams](#foundations)</sub>

⭐ **[Star this repo](https://github.com/AngelDark92/GalaxyXR-Forge)** — it helps other Galaxy XR owners find the index.

📰 **[News](https://angeldark92.github.io/GalaxyXR-Forge/#news)** — releases, guides and site updates from the community.

</div>

---

Community-maintained index of projects built for the **Samsung Galaxy XR** (`SM-I610`, Android XR): root and kernel tooling, KernelSU modules, PC VR streaming drivers, patched and ported apps, emulation, and diagnostics. Curated `2026-10-29` — 66 repos in 9 groups.

<a id="catalog"></a>

<a id="root-kernel"></a>

## 🛡️ Root & Kernel

> Root the headset and keep it: managers, loaders and kernel research.

| Repository | What it does |
| --- | --- |
| **[4uva4ek/KernelSU-GXR](https://github.com/4uva4ek/KernelSU-GXR)**<br>![stars](https://img.shields.io/github/stars/4uva4ek/KernelSU-GXR?style=flat-square) ![release](https://img.shields.io/github/v/release/4uva4ek/KernelSU-GXR?include_prereleases&style=flat-square&label=release) | KernelSU manager and daemon built for the Galaxy XR: module installer and signed self-update. |
| **[compdoge/gxr-ghostlock](https://github.com/compdoge/gxr-ghostlock)**<br>![stars](https://img.shields.io/github/stars/compdoge/gxr-ghostlock?style=flat-square) | GhostLock (CVE-2026-43499) root port for firmware AZF3: source, runbook and prebuilt binaries. |
| **[diabl0w/DFRoot](https://github.com/diabl0w/DFRoot)**<br>![stars](https://img.shields.io/github/stars/diabl0w/DFRoot?style=flat-square) ![release](https://img.shields.io/github/v/release/diabl0w/DFRoot?include_prereleases&style=flat-square&label=release) | Kernel-module loader that loads KernelSU-GXR without flashing a boot image. |

<a id="kernelsu-modules"></a>

## 🧩 KernelSU Modules

> Runtime device patches for tracking, haptics and thermals; every package installs disabled.

| Repository | What it does |
| --- | --- |
| **[4uva4ek/galaxyxr-modules](https://github.com/4uva4ek/galaxyxr-modules)**<br>![stars](https://img.shields.io/github/stars/4uva4ek/galaxyxr-modules?style=flat-square) | Tracking and haptic fixes: whitening, timestamp precision, OpenXR velocity, OTA control. |
| **[BlueScorpioVR/galaxyxr-modules](https://github.com/BlueScorpioVR/galaxyxr-modules)**<br>![stars](https://img.shields.io/github/stars/BlueScorpioVR/galaxyxr-modules?style=flat-square) | Experimental personal KernelSU modules for the Galaxy XR. |
| **[BreadDoesStuff/galaxy-xr-modules](https://github.com/BreadDoesStuff/galaxy-xr-modules)**<br>![stars](https://img.shields.io/github/stars/BreadDoesStuff/galaxy-xr-modules?style=flat-square) | Fan control, passthrough anywhere, camera debug stream and mic gain modules. |
| **[compdoge/gxr-ksu-modules](https://github.com/compdoge/gxr-ksu-modules)**<br>![stars](https://img.shields.io/github/stars/compdoge/gxr-ksu-modules?style=flat-square) | KernelSU module source for the Galaxy XR: add it in the manager's Sources screen. |
| **[stearnsbq/questlhsync-galaxy-xr](https://github.com/stearnsbq/questlhsync-galaxy-xr)**<br>![stars](https://img.shields.io/github/stars/stearnsbq/questlhsync-galaxy-xr?style=flat-square) ![release](https://img.shields.io/github/v/release/stearnsbq/questlhsync-galaxy-xr?include_prereleases&style=flat-square&label=release) | KernelSU module aligning Lighthouse trackers with the XR's camera tracking (QuestLHSync PC side required). |

<a id="face-eye"></a>

## 👁️ Face & Eye Tracking

> Face and eye tracking for PC VR: relays, bridges and fixes.

| Repository | What it does |
| --- | --- |
| **[compdoge/gxr-face-bridge](https://github.com/compdoge/gxr-face-bridge)**<br>![stars](https://img.shields.io/github/stars/compdoge/gxr-face-bridge?style=flat-square) ![release](https://img.shields.io/github/v/release/compdoge/gxr-face-bridge?include_prereleases&style=flat-square&label=release) | OpenXR face-tracking bridge for Steam Link VR on the Galaxy XR. |
| **[compdoge/gxr-root-ft](https://github.com/compdoge/gxr-root-ft)**<br>![stars](https://img.shields.io/github/stars/compdoge/gxr-root-ft?style=flat-square) ![release](https://img.shields.io/github/v/release/compdoge/gxr-root-ft?include_prereleases&style=flat-square&label=release) | Headset-side face and eye relay plus a KernelSU module for PC VR face tracking. |
| **[compdoge/LinkFT](https://github.com/compdoge/LinkFT)**<br>![stars](https://img.shields.io/github/stars/compdoge/LinkFT?style=flat-square) ![release](https://img.shields.io/github/v/release/compdoge/LinkFT?include_prereleases&style=flat-square&label=release) | Maps the five transported Galaxy XR tongue values to the VRCFT unified expressions TongueOut, TongueLeft, TongueRight, TongueUp, and TongueDown. |
| **[compdoge/VRCFT-ALVR-UE](https://github.com/compdoge/VRCFT-ALVR-UE)**<br>![stars](https://img.shields.io/github/stars/compdoge/VRCFT-ALVR-UE?style=flat-square) ![release](https://img.shields.io/github/v/release/compdoge/VRCFT-ALVR-UE?include_prereleases&style=flat-square&label=release) | VRCFaceTracking module that receives ALVR eye and face tracking on the PC. |
| **[SinonVT/GalaxyXR-EyeTracking-Fix-Virtual-Desktop](https://github.com/SinonVT/GalaxyXR-EyeTracking-Fix-Virtual-Desktop)**<br>![stars](https://img.shields.io/github/stars/SinonVT/GalaxyXR-EyeTracking-Fix-Virtual-Desktop?style=flat-square) ![release](https://img.shields.io/github/v/release/SinonVT/GalaxyXR-EyeTracking-Fix-Virtual-Desktop?include_prereleases&style=flat-square&label=release) | Fixes eye-gaze drift on head tilt in Virtual Desktop's VRCFaceTracking module. |
| **[Tony-Klink/GabbleXR-server](https://github.com/Tony-Klink/GabbleXR-server)**<br>![stars](https://img.shields.io/github/stars/Tony-Klink/GabbleXR-server?style=flat-square) | Bridges Galaxy XR face and eye tracking into Resonite via OSC. |

<a id="pcvr-drivers"></a>

## 🖥️ PC VR & Streaming

> SteamVR drivers, streaming stacks and PC-side VR tooling for the XR.

| Repository | What it does |
| --- | --- |
| **[4uva4ek/galaxy-xr-game-link](https://github.com/4uva4ek/galaxy-xr-game-link)**<br>![stars](https://img.shields.io/github/stars/4uva4ek/galaxy-xr-game-link?style=flat-square) ![release](https://img.shields.io/github/v/release/4uva4ek/galaxy-xr-game-link?include_prereleases&style=flat-square&label=release) | Patched Samsung Game Link (XR Link) PC driver for the Galaxy XR, with crash fixes. |
| **[AngelDark92/GalaxyXR-Driver](https://github.com/AngelDark92/GalaxyXR-Driver)**<br>![stars](https://img.shields.io/github/stars/AngelDark92/GalaxyXR-Driver?style=flat-square) ![release](https://img.shields.io/github/v/release/AngelDark92/GalaxyXR-Driver?include_prereleases&style=flat-square&label=release) | SteamVR driver: native headset identity, controller and throw fixes, image processing; Companion GUI. |
| **[AngelDark92/steamlink-androidxr-patched](https://github.com/AngelDark92/steamlink-androidxr-patched)**<br>![stars](https://img.shields.io/github/stars/AngelDark92/steamlink-androidxr-patched?style=flat-square) ![release](https://img.shields.io/github/v/release/AngelDark92/steamlink-androidxr-patched?include_prereleases&style=flat-square&label=release) | Already patched SteamLink apks to be used in tandem with the Galaxy XR driver. |
| **[BlueScorpioVR/androidInputForwarder](https://github.com/BlueScorpioVR/androidInputForwarder)**<br>![stars](https://img.shields.io/github/stars/BlueScorpioVR/androidInputForwarder?style=flat-square) ![release](https://img.shields.io/github/v/release/BlueScorpioVR/androidInputForwarder?include_prereleases&style=flat-square&label=release) | Root-only app forwarding a Bluetooth controller, keyboard and mouse to an Apollo PC. |
| **[DienerTech/vectorxr](https://github.com/DienerTech/vectorxr)**<br>![stars](https://img.shields.io/github/stars/DienerTech/vectorxr?style=flat-square) ![release](https://img.shields.io/github/v/release/DienerTech/vectorxr?include_prereleases&style=flat-square&label=release) | Windows OpenXR layer and app for stereo depth, pivot and foveated-rendering tuning. |
| **[djules75/OFXR-Bridge](https://github.com/djules75/OFXR-Bridge)**<br>![stars](https://img.shields.io/github/stars/djules75/OFXR-Bridge?style=flat-square) ![release](https://img.shields.io/github/v/release/djules75/OFXR-Bridge?include_prereleases&style=flat-square&label=release) | OFXR fork adding 2X/3X frame generation, DLSS Hybrid, D3D11/Vulkan and Linux support. |
| **[elliotttate/OFXR-Bridge](https://github.com/elliotttate/OFXR-Bridge)**<br>![stars](https://img.shields.io/github/stars/elliotttate/OFXR-Bridge?style=flat-square) ![release](https://img.shields.io/github/v/release/elliotttate/OFXR-Bridge?include_prereleases&style=flat-square&label=release) | OFXR fork adding native DLSS-G frame generation, adaptive presenter pacing and per-game controls. |
| **[Gilleece/moonlight-android-xr](https://github.com/Gilleece/moonlight-android-xr)**<br>![stars](https://img.shields.io/github/stars/Gilleece/moonlight-android-xr?style=flat-square) ![release](https://img.shields.io/github/v/release/Gilleece/moonlight-android-xr?include_prereleases&style=flat-square&label=release) | Moonlight fork: native OpenXR client with on-headset 2D-to-3D conversion. |
| **[mbucchia/PimaxMagic4All](https://github.com/mbucchia/PimaxMagic4All)**<br>![stars](https://img.shields.io/github/stars/mbucchia/PimaxMagic4All?style=flat-square) ![release](https://img.shields.io/github/v/release/mbucchia/PimaxMagic4All?include_prereleases&style=flat-square&label=release) | Brings Pimax dynamic foveated rendering to non-Pimax headsets in SteamVR apps. |
| **[Mr-Nlce/PCVR-Mods-Installer-Hub](https://github.com/Mr-Nlce/PCVR-Mods-Installer-Hub)**<br>![stars](https://img.shields.io/github/stars/Mr-Nlce/PCVR-Mods-Installer-Hub?style=flat-square) ![release](https://img.shields.io/github/v/release/Mr-Nlce/PCVR-Mods-Installer-Hub?include_prereleases&style=flat-square&label=release) | Portable installer and launcher for publicly available PC VR game mods. |
| **[Nyabsi/OpenVR-SpaceOverride](https://github.com/Nyabsi/OpenVR-SpaceOverride)**<br>![stars](https://img.shields.io/github/stars/Nyabsi/OpenVR-SpaceOverride?style=flat-square) | Uses Lighthouse devices on non-Lighthouse headsets like the Galaxy XR. |
| **[ReverVR/OFXR-Bridge-Rever](https://github.com/ReverVR/OFXR-Bridge-Rever)**<br>![stars](https://img.shields.io/github/stars/ReverVR/OFXR-Bridge-Rever?style=flat-square) | Rever VR OFXR fork adding an opt-in binding queue for DLSS-NR layers on every OpenXR runtime. |
| **[shinyflvre/OpenVR-SpaceSync](https://github.com/shinyflvre/OpenVR-SpaceSync)**<br>![stars](https://img.shields.io/github/stars/shinyflvre/OpenVR-SpaceSync?style=flat-square) | Syncs Lighthouse devices to an SLAM headset's pose in SteamVR (Follow SLAM HMD mode). |
| **[Terminal-ennui/galaxy-xr-alvr-pyrowave-444](https://github.com/Terminal-ennui/galaxy-xr-alvr-pyrowave-444)**<br>![stars](https://img.shields.io/github/stars/Terminal-ennui/galaxy-xr-alvr-pyrowave-444?style=flat-square) | Full-chroma 4:4:4 wireless PC VR streaming via patched ALVR and the PyroWave codec. |
| **[Terminal-ennui/Galaxy_XR_ALVR_USB](https://github.com/Terminal-ennui/Galaxy_XR_ALVR_USB)**<br>![stars](https://img.shields.io/github/stars/Terminal-ennui/Galaxy_XR_ALVR_USB?style=flat-square) ![release](https://img.shields.io/github/v/release/Terminal-ennui/Galaxy_XR_ALVR_USB?include_prereleases&style=flat-square&label=release) | Streams SteamVR over USB 3 using stock ALVR 20.14.1 with a patched headset client. |
| **[tig3rmast3r/OFXR-Bridge](https://github.com/tig3rmast3r/OFXR-Bridge)**<br>![stars](https://img.shields.io/github/stars/tig3rmast3r/OFXR-Bridge?style=flat-square) ![release](https://img.shields.io/github/v/release/tig3rmast3r/OFXR-Bridge?include_prereleases&style=flat-square&label=release) | Original OFXR Bridge: experimental OpenXR layer inserting optical-flow frames between rendered VR frames. |
| **[timkhronos/CustomHeadsetOpenVrGxR](https://github.com/timkhronos/CustomHeadsetOpenVrGxR)**<br>![stars](https://img.shields.io/github/stars/timkhronos/CustomHeadsetOpenVrGxR?style=flat-square) ![release](https://img.shields.io/github/v/release/timkhronos/CustomHeadsetOpenVrGxR?include_prereleases&style=flat-square&label=release) | Original Galaxy XR SteamVR driver fork: pose fixes, colour pipeline, distortion tuner. |
| **[wooyounsoft/WYGxrControllerFix](https://github.com/wooyounsoft/WYGxrControllerFix)**<br>![stars](https://img.shields.io/github/stars/wooyounsoft/WYGxrControllerFix?style=flat-square) ![release](https://img.shields.io/github/v/release/wooyounsoft/WYGxrControllerFix?include_prereleases&style=flat-square&label=release) | SteamVR add-on that tunes Samsung Galaxy XR controllers for PCVR through Virtual Desktop. |

<a id="app-patches"></a>

## 📱 App Patches & Ports

> Quest and PICO apps patched or converted to run natively on Android XR.

| Repository | What it does |
| --- | --- |
| **[4uva4ek/overport-galaxyxr](https://github.com/4uva4ek/overport-galaxyxr)**<br>![stars](https://img.shields.io/github/stars/4uva4ek/overport-galaxyxr?style=flat-square) ![release](https://img.shields.io/github/v/release/4uva4ek/overport-galaxyxr?include_prereleases&style=flat-square&label=release) | APK converter with a Galaxy XR preset: 3552x3840 per eye, BOOST, 90 Hz, Unity EGL fix. |
| **[AngelDark92/xr-porting-hub](https://github.com/AngelDark92/xr-porting-hub)**<br>![stars](https://img.shields.io/github/stars/AngelDark92/xr-porting-hub?style=flat-square) ![release](https://img.shields.io/github/v/release/AngelDark92/xr-porting-hub?include_prereleases&style=flat-square&label=release) | Morphe patches for Steam Link VR on Galaxy XR: resolution, colour, mic, tracking, face bridge. |
| **[logkim1/4XVR-GalaxyXR](https://github.com/logkim1/4XVR-GalaxyXR)**<br>![stars](https://img.shields.io/github/stars/logkim1/4XVR-GalaxyXR?style=flat-square) ![release](https://img.shields.io/github/v/release/logkim1/4XVR-GalaxyXR?include_prereleases&style=flat-square&label=release) | 4XVR video player patched for GXR: HDR tone mapping, memory fix, subtitle controls. |
| **[Molier/openxr-dispatcher-open](https://github.com/Molier/openxr-dispatcher-open)**<br>![stars](https://img.shields.io/github/stars/Molier/openxr-dispatcher-open?style=flat-square) | Open-source drop-in replacement for the closed OpenXR dispatcher in converted Quest apps. |

<a id="games"></a>

## 🎮 Games & Emulation

> Games running on the headset or beside it.

| Repository | What it does |
| --- | --- |
| **[evertec82/AstroQuest](https://github.com/evertec82/AstroQuest)**<br>![stars](https://img.shields.io/github/stars/evertec82/AstroQuest?style=flat-square) ![release](https://img.shields.io/github/v/release/evertec82/AstroQuest?include_prereleases&style=flat-square&label=release) | ASTRO BOT Rescue Mission via shadPS4 on standalone headsets and PC VR. |
| **[RJNY/Obtainium-Emulation-Pack](https://github.com/RJNY/Obtainium-Emulation-Pack)**<br>![stars](https://img.shields.io/github/stars/RJNY/Obtainium-Emulation-Pack?style=flat-square) ![release](https://img.shields.io/github/v/release/RJNY/Obtainium-Emulation-Pack?include_prereleases&style=flat-square&label=release) | Obtainium import list bundling Android emulator apps for one-shot install. |
| **[Shift-Foundry/project-hazard](https://github.com/Shift-Foundry/project-hazard)**<br>![stars](https://img.shields.io/github/stars/Shift-Foundry/project-hazard?style=flat-square) | Room-scale mixed-reality roguelite for Android XR glasses, including Galaxy XR. |
| **[WinlatorXR/WinlatorXR](https://github.com/WinlatorXR/WinlatorXR)**<br>![stars](https://img.shields.io/github/stars/WinlatorXR/WinlatorXR?style=flat-square) | Windows x86 games and apps emulator for standalone Android XR headsets. |

<a id="tools"></a>

## 🔧 Tools & Diagnostics

> Diagnostics, sensors, capture and utility tools for the headset.

| Repository | What it does |
| --- | --- |
| **[aali195/steamvr-addon-manager](https://github.com/aali195/steamvr-addon-manager)**<br>![stars](https://img.shields.io/github/stars/aali195/steamvr-addon-manager?style=flat-square) ![release](https://img.shields.io/github/v/release/aali195/steamvr-addon-manager?include_prereleases&style=flat-square&label=release) | A lightweight Windows tool for managing SteamVR drivers and startup overlays by editing SteamVR's config files (before SteamVR is run). |
| **[AmeChanRain/MicDotDisabler](https://github.com/AmeChanRain/MicDotDisabler)**<br>![stars](https://img.shields.io/github/stars/AmeChanRain/MicDotDisabler?style=flat-square) | Hides the Android privacy indicator dot, built for Android XR devices. |
| **[AngelDark92/SteamVRColourLab](https://github.com/AngelDark92/SteamVRColourLab)**<br>![stars](https://img.shields.io/github/stars/AngelDark92/SteamVRColourLab?style=flat-square) ![release](https://img.shields.io/github/v/release/AngelDark92/SteamVRColourLab?include_prereleases&style=flat-square&label=release) | In-headset colour test suite: gradients, dark scenes, 8-bit vs 10-bit comparison. |
| **[CurvSurf/PointCloudRecorder-GalaxyXR](https://github.com/CurvSurf/PointCloudRecorder-GalaxyXR)**<br>![stars](https://img.shields.io/github/stars/CurvSurf/PointCloudRecorder-GalaxyXR?style=flat-square) | Records point clouds from Galaxy XR ARCore depth maps. |
| **[dli7319/galaxy-xr-rx-qr-code-generator](https://github.com/dli7319/galaxy-xr-rx-qr-code-generator)**<br>![stars](https://img.shields.io/github/stars/dli7319/galaxy-xr-rx-qr-code-generator?style=flat-square) | Generates the QR code for Galaxy XR prescription (RX) lens inserts. |
| **[ImranR98/Obtainium](https://github.com/ImranR98/Obtainium)**<br>![stars](https://img.shields.io/github/stars/ImranR98/Obtainium?style=flat-square) ![release](https://img.shields.io/github/v/release/ImranR98/Obtainium?include_prereleases&style=flat-square&label=release) | Android app updater that installs and tracks APKs straight from their sources. |
| **[ngocthanhgl/morphe-audit-bot](https://github.com/ngocthanhgl/morphe-audit-bot)**<br>![stars](https://img.shields.io/github/stars/ngocthanhgl/morphe-audit-bot?style=flat-square) | Diff-only security audit bot for Morphe patch repos. |
| **[perillamint/galaxy-xr-lenscal](https://github.com/perillamint/galaxy-xr-lenscal)**<br>![stars](https://img.shields.io/github/stars/perillamint/galaxy-xr-lenscal?style=flat-square) | Lens calibration QR builder for Galaxy XR. |
| **[tw0b33rs/xr-native-sensor-access](https://github.com/tw0b33rs/xr-native-sensor-access)**<br>![stars](https://img.shields.io/github/stars/tw0b33rs/xr-native-sensor-access?style=flat-square) | Raw low-latency IMU sensor access for Galaxy XR apps (NDK/C++ sample). |
| **[whyorean/AuroraStore](https://github.com/whyorean/AuroraStore)**<br>![stars](https://img.shields.io/github/stars/whyorean/AuroraStore?style=flat-square) | Google Play client: search, download and update Play apps and APKs on device. |

<a id="apps-samples"></a>

## 🧪 Apps & Samples

> Small apps, players and dev samples built for the XR.

| Repository | What it does |
| --- | --- |
| **[andreylukin/mind-castle](https://github.com/andreylukin/mind-castle)**<br>![stars](https://img.shields.io/github/stars/andreylukin/mind-castle?style=flat-square) | Streams Mac windows into the Galaxy XR over USB. |
| **[BlueScorpioVR/ScreenStreamerXR](https://github.com/BlueScorpioVR/ScreenStreamerXR)**<br>![stars](https://img.shields.io/github/stars/BlueScorpioVR/ScreenStreamerXR?style=flat-square) ![release](https://img.shields.io/github/v/release/BlueScorpioVR/ScreenStreamerXR?include_prereleases&style=flat-square&label=release) | Android XR screen-streaming app for Twitch, YouTube, custom RTMP and OmniStream, with chat, alerts and recording. |
| **[hyunaseo/OpenAI-for-Galaxy-XR](https://github.com/hyunaseo/OpenAI-for-Galaxy-XR)**<br>![stars](https://img.shields.io/github/stars/hyunaseo/OpenAI-for-Galaxy-XR?style=flat-square) | Showcase: passthrough capture with OpenAI multimodal voice queries on Galaxy XR. |
| **[HyunsooleePG/GalaxyXR_Passthrough_WebCamTexture](https://github.com/HyunsooleePG/GalaxyXR_Passthrough_WebCamTexture)**<br>![stars](https://img.shields.io/github/stars/HyunsooleePG/GalaxyXR_Passthrough_WebCamTexture?style=flat-square) | Unity sample: access the passthrough camera texture on Galaxy XR. |
| **[mathewvarghesemanu/android-xr-immersive-video-player](https://github.com/mathewvarghesemanu/android-xr-immersive-video-player)**<br>![stars](https://img.shields.io/github/stars/mathewvarghesemanu/android-xr-immersive-video-player?style=flat-square) | 180° SBS 3D VR video player for Galaxy XR with pitch reposition. |

<a id="foundations"></a>

## 🏗️ Foundations & Upstreams

> The base projects everything above builds on.

| Repository | What it does |
| --- | --- |
| **[CreoleVR/QuestLHSync](https://github.com/CreoleVR/QuestLHSync)**<br>![stars](https://img.shields.io/github/stars/CreoleVR/QuestLHSync?style=flat-square) ![release](https://img.shields.io/github/v/release/CreoleVR/QuestLHSync?include_prereleases&style=flat-square&label=release) | QuestLHSync project aligning Lighthouse devices to a headset's own camera tracking, with Galaxy XR support. |
| **[diabl0w/KernelSU](https://github.com/diabl0w/KernelSU)**<br>![stars](https://img.shields.io/github/stars/diabl0w/KernelSU?style=flat-square) ![release](https://img.shields.io/github/v/release/diabl0w/KernelSU?include_prereleases&style=flat-square&label=release) | KernelSU fork with the samsung-v1.0 branch that KernelSU-GXR builds on. |
| **[JICA98/Bachata-S4](https://github.com/JICA98/Bachata-S4)**<br>![stars](https://img.shields.io/github/stars/JICA98/Bachata-S4?style=flat-square) ![release](https://img.shields.io/github/v/release/JICA98/Bachata-S4?include_prereleases&style=flat-square&label=release) | Bachata S4 releases, compatibility reports, and public community portal |
| **[MorpheApp/morphe-manager](https://github.com/MorpheApp/morphe-manager)**<br>![stars](https://img.shields.io/github/stars/MorpheApp/morphe-manager?style=flat-square) ![release](https://img.shields.io/github/v/release/MorpheApp/morphe-manager?include_prereleases&style=flat-square&label=release) | The on-device Morphe patcher that applies .mpp patch bundles. |
| **[MorpheApp/morphe-patches](https://github.com/MorpheApp/morphe-patches)**<br>![stars](https://img.shields.io/github/stars/MorpheApp/morphe-patches?style=flat-square) ![release](https://img.shields.io/github/v/release/MorpheApp/morphe-patches?include_prereleases&style=flat-square&label=release) | Morphe's base patch library; the groundwork for Galaxy XR patch bundles. |
| **[ovrport/app](https://github.com/ovrport/app)**<br>![stars](https://img.shields.io/github/stars/ovrport/app?style=flat-square) ![release](https://img.shields.io/github/v/release/ovrport/app?include_prereleases&style=flat-square&label=release) | Upstream Overport: patches Quest-targeting Android games; base of the Galaxy XR fork. |
| **[sboys3/CustomHeadsetOpenVR](https://github.com/sboys3/CustomHeadsetOpenVR)**<br>![stars](https://img.shields.io/github/stars/sboys3/CustomHeadsetOpenVR?style=flat-square) ![release](https://img.shields.io/github/v/release/sboys3/CustomHeadsetOpenVR?include_prereleases&style=flat-square&label=release) | Base custom-headset SteamVR driver framework; both Galaxy XR drivers fork from it. |
| **[shadps4-emu/shadPS4](https://github.com/shadps4-emu/shadPS4)**<br>![stars](https://img.shields.io/github/stars/shadps4-emu/shadPS4?style=flat-square) ![release](https://img.shields.io/github/v/release/shadps4-emu/shadPS4?include_prereleases&style=flat-square&label=release) | PlayStation 4 emulator; the base the headset PS4 porting projects build on. |
| **[Terminal-ennui/pyrowave](https://github.com/Terminal-ennui/pyrowave)**<br>![stars](https://img.shields.io/github/stars/Terminal-ennui/pyrowave?style=flat-square) | PyroWave wavelet codec fork used by the headset's ALVR 4:4:4 streaming builds. |
| **[Vauzi-17/mesa-tu8](https://github.com/Vauzi-17/mesa-tu8)**<br>![stars](https://img.shields.io/github/stars/Vauzi-17/mesa-tu8?style=flat-square) | Turnip (Mesa) Vulkan driver build used by the headset emulation stack. |
| **[zenithblue-oss/shadps4-arm64](https://github.com/zenithblue-oss/shadps4-arm64)**<br>![stars](https://img.shields.io/github/stars/zenithblue-oss/shadps4-arm64?style=flat-square) | ARM64 shadPS4 build with FEX integration that runs on the headset itself. |

---

## Suggest a repo

**Fastest:** use the **Suggest a repo** button on the [site](https://angeldark92.github.io/GalaxyXR-Forge/#suggest-a-repo) — paste the link, pick a group. CI prepares the card and a pull request; nothing is added until a maintainer reviews and merges it.

Or run it locally, one command:

```sh
python tools/add-repo.py https://github.com/owner/name --group apps-samples
```

The tool refuses private or already-listed repos, reads the license and latest release, writes the entry with today's `added` date, appends a changelog entry, regenerates every generated file and runs both link checks. `--dry-run` prints the entry without writing anything.

Manual edits still work: add a file under `catalog.d/<group>/` and one under `changelog.d/`, run `python tools/build.py`, then `python tools/check-links.py` and `python tools/check-repos.py`. One file per repo is why two pending additions never conflict.

CI gates every pull request on all four checks, so a PR with stale or hand-edited generated files cannot merge. See [`.agents/skills/`](.agents/skills/) for the full procedure.

## For agents

This repo is agent-ready. Start with [`AGENTS.md`](AGENTS.md); [`catalog.json`](catalog.json) is the machine-readable index; [`.agents/skills/`](.agents/skills/) maps every Galaxy XR repo and its local checkout.

## Changelog

- `2026-10-29` — News tab and a rebuilt site navigation
- `2026-10-28` — LinkFT added
- `2026-10-26` — Kernel modules tab
- `2026-10-25` — WYGxrControllerFix added
- `2026-10-23` — Duplicate stearnsbq/QuestLHSync entry removed
- `2026-10-23` — OFXR Bridge family added

Full history: [`CHANGELOG.md`](CHANGELOG.md) · [site Changelog tab](https://angeldark92.github.io/GalaxyXR-Forge/#changelog).

## Notes

- Unofficial community hub — not affiliated with Samsung. Each catalogued project keeps its own license.
- Rooting and module installation carry risk; read the owning project's docs first.
- No game files, firmware dumps or proprietary binaries are distributed here.

<div align="center"><sub>Curated 2026-10-29 · 66 repos</sub></div>
