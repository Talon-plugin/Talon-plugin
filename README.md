<div align="center">

# 🦅 Talons

**Universal Media Extractor Plugin for [Grabbit](https://github.com/grabbit)**  
*Engineered specifically for macOS Apple Silicon (ARM64)*

[![CI](https://img.shields.io/badge/CI-passing-brightgreen.svg?style=flat-square)](https://github.com/grabbit/grabbit-ytdlp-plugin/actions)
[![Website](https://img.shields.io/badge/website-live-blue.svg?style=flat-square&logo=safari)](https://grabbit.github.io/grabbit-ytdlp-plugin/)
[![Platform](https://img.shields.io/badge/platform-macOS%20Apple%20Silicon-black.svg?style=flat-square&logo=apple)](https://apple.com)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg?style=flat-square&logo=python)](https://python.org)
[![Powered By](https://img.shields.io/badge/powered%20by-yt--dlp-red.svg?style=flat-square&logo=youtube)](https://github.com/yt-dlp/yt-dlp)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg?style=flat-square)](LICENSE)

</div>

---

## Overview

**Talons** is a high-performance media stream extraction plugin for **Grabbit**. It enables universal video, audio, and stream resolution matching across thousands of online media sources by leveraging the latest open-source [yt-dlp](https://github.com/yt-dlp/yt-dlp) engine.

Rather than relying on outdated monolithic binaries, Talons dynamically synchronizes directly with the upstream `yt-dlp` repository, ensuring you always have cutting-edge extractor definitions and stream format support.

---

## ⚡ Key Features

- **macOS Apple Silicon Native**: Optimized for ARM64 architecture on macOS (M1/M2/M3/M4+).
- **Direct Upstream Sync**: Fetches and embeds fresh `yt-dlp` Python package directly from the official repository.
- **Smart Stream Selection**: Automatically chooses the highest quality direct HTTPS streams (MP4/M4A), prioritizing Apple-native containers and hardware-accelerated playback.
- **Audio-Only Mode**: Intelligent audio extraction with bitrate ranking and AAC/M4A/MP3 container preference.
- **Zero Binary Bloat**: Pure Python module execution with negligible storage overhead.
- **Automated Releases**: Built and published automatically via GitHub Actions matching `pincer-engine`.

---

## 📋 Requirements

- **macOS**: macOS 12.0 (Monterey) or higher on **Apple Silicon (ARM64)**
- **Grabbit**: Latest version of Grabbit Download Manager
- **Python**: Python 3.10+ (macOS system Python or Homebrew `/opt/homebrew/bin/python3`)

---

## 🔌 Installing into Grabbit App

You can install `talons.gda` into Grabbit using any of the following methods:

### Method 1: Via Grabbit Settings UI (Recommended)
1. Launch **Grabbit**.
2. Open **Settings** (`Cmd + ,` or click the gear icon in the toolbar).
3. Select the **Extensions** tab from the sidebar.
4. Scroll to the **Installed Plugins** section.
5. Click **"Install Plugin from File..."**.
6. Select the `talons.gda` bundle you downloaded or built.
7. Grabbit will automatically extract the plugin and display **Talons** with its version and description in the list.

### Method 2: Via the Grabbit Menu Bar
1. Open **Grabbit**.
2. In the top macOS menu bar, click **File** → **Install Plugin...** (or click the Grabbit menu bar tray icon and select **Install Plugin...**).
3. Choose `talons.gda`.
4. A notification toast will confirm: *"Plugin installed successfully!"*.

---

## 📦 Building from Source

```bash
# 1. Clone the repository
git clone https://github.com/grabbit/grabbit-ytdlp-plugin.git
cd grabbit-ytdlp-plugin

# 2. Build the talons.gda package
./scripts/make.sh
```
The packaged `talons.gda` plugin bundle will be generated in `build/talons.gda`.

---

## 🛠️ Releasing a New Version (Developer Guide)

Just like `pincer-engine`, releases are managed using the `./scripts/release.sh` script:

```bash
# Cut a new release (e.g. version 1.0.0)
./scripts/release.sh 1.0.0

# Push the release tag to GitHub to trigger the automated build & release
git push origin v1.0.0
```

Once the tag is pushed, GitHub Actions will:
1. Package `talons.gda` using `uv`.
2. Create the GitHub Release and attach `talons.gda` automatically to the Releases tab.

---

## 📁 Repository Structure

```
grabbit-ytdlp-plugin/
├── .github/
│   └── workflows/
│       ├── ci.yml               # CI build & verification on push/PR
│       └── release.yml          # Auto Release workflow triggered on tag push
├── build/
│   └── talons.gda               # Packaged plugin artifact
├── scripts/
│   ├── make.sh                  # Packaging script
│   └── release.sh               # Release tagging script
├── plugin/
│   ├── icon.svg                 # Branded Talons vector icon
│   ├── plugin.json              # Grabbit plugin manifest
│   ├── run.sh                   # Unix runner entrypoint
│   └── extractor.py             # Stream filtering and metadata extraction engine
├── .gitignore                   # Git hygiene & artifact exclusions
├── LICENSE                      # MIT License
└── README.md                    # Project documentation
```

---

## 🔍 Troubleshooting

- **Python Not Found**: Ensure Python 3 is installed and available in PATH (`which python3` or `brew install python`).
- **Site-Specific DRM or Captchas**: Some sites may require browser cookies. Ensure your Grabbit settings allow cookie access if required.
- **Updating Extractors**: Run `uv lock --upgrade-package yt-dlp` from the `plugin/` directory to refresh the yt-dlp version whenever video sites update their player algorithms.

---

## 📄 License

Distributed under the [MIT License](LICENSE). Powered by the open-source [yt-dlp](https://github.com/yt-dlp/yt-dlp) project.
