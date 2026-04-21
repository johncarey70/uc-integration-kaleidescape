# Kaleidescape Integration for Unfolded Circle Remotes

[![GitHub Release](https://img.shields.io/github/v/release/johncarey70/uc-integration-kaleidescape?style=flat-square)](https://github.com/johncarey70/uc-integration-kaleidescape/releases)
![License](https://img.shields.io/badge/license-MPL--2.0-blue?style=flat-square)
[![GitHub issues](https://img.shields.io/github/issues/johncarey70/uc-integration-kaleidescape?style=flat-square)](https://github.com/johncarey70/uc-integration-kaleidescape/issues)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/johncarey70/uc-integration-kaleidescape/total?style=flat-square)

Control your **Kaleidescape Video Player** directly from your Unfolded Circle Remote Two or Remote 3.  
A media player and remote entity are exposed to the Remote core.

> ⚠️  This software may contain bugs that could affect system stability. Use at your own risk.

> **Note:**  
> The integration supports Kaleidescape systems with multiple players.  
> Servers are discovered automatically, and associated players are available for individual configuration.

---

## Architecture

This integration consists of two components:

### 1. Python Integration (this repository)
- Handles UC API integration
- Manages entities (media player + remote)
- Processes events and updates UI state

### 2. Backend Service (`ksd`, included in release package)
- Handles Kaleidescape Control Protocol communication
- Maintains a persistent connection to the player
- Processes events and provides structured data to Python via a local socket

> ⚠️  **Important:**  
> The `ksd` service is proprietary software and is distributed only as a compiled binary in official releases.  
> Its source code is not included in this repository.

## Supported Features

### Media Player

- Power control (On / Off)
- Playback control:
  - Play / Pause / Stop
  - Next / Previous
  - Fast Forward / Rewind
  - Replay
- Navigation:
  - Directional controls (Up / Down / Left / Right / Select)
  - Back / Menu
  - Page Up / Page Down (press / hold / release)
- Media browsing:
  - Movie collections, covers, and list views
  - Search
  - Store access
- Playback options:
  - Subtitles
  - Intermission
  - Shuffle / Alphabetize cover art

### Remote

- Full remote control interface with:
  - Button mappings (D-pad, transport, menu, etc.)
  - Custom UI pages
- Power control (On / Standby)
- On-screen navigation and control
- Direct access to key Kaleidescape functions:
  - Collections / Covers / List / Store
  - Search / Subtitles / Replay / Intermission

### Sensors

- Aspect Ratio
- Movie Location (Main content, Intermission, Credits, etc.)

### Media Attributes

- Power state (On / Off / Unknown)
- Media title
- Media type
- Media duration
- Media position
- Media artwork (image URL)

## Installation

### Option 1: Integration Manager (Recommended)

Install directly from the community registry using the Integration Manager:

- Open the Integration Manager on your Remote
- Browse the community integrations
- Select **Kaleidescape**
- Install with a single click

More information:  
https://github.com/JackJPowell/uc-intg-manager

---

### Option 2: Manual Installation

#### 1. Download Integration Driver
Download the `uc-intg-kaleidescape-x.x.x-aarch64.tar.gz` archive from the  
[latest release](https://github.com/johncarey70/uc-integration-kaleidescape/releases/latest).

#### 2. Upload & Install
Upload via the Web Configurator:
- Go to **Integrations**
- Click **Add new / Install custom**
- Select the downloaded `.tar.gz`

#### 3. Configuration
Run setup from the integration:

- Kaleidescape systems are discovered automatically
- Players associated with each system are presented for selection

#### 4. Updating
- Remove the existing version (both configuration and integration)
- Reinstall using the new package

---

## Development Notes

This repository contains the Python integration layer only.

A complete, working integration requires the proprietary `ksd` daemon, which is included in official release packages.

### Important

- Official release archives include:
  - Compiled Python driver
  - `ksd` daemon binary (aarch64)

- A complete working build cannot be produced from this repository alone.

### Recommendation

End users should install the prebuilt release package from the latest release:

https://github.com/johncarey70/uc-integration-kaleidescape/releases/latest

---

## License

This repository (Python integration code) is licensed under the  
[**Mozilla Public License 2.0**](https://choosealicense.com/licenses/mpl-2.0/).

See [LICENSE](LICENSE) for details.

### Proprietary Components

The `ksd` daemon included in release packages is **not covered by the MPL license**.

- `ksd` is proprietary software  
- Source code is not provided  
- Redistribution and use are restricted  
- Reverse engineering, decompilation, or disassembly of the `ksd` daemon is not permitted  
- The `ksd` daemon is provided solely for use with this integration  