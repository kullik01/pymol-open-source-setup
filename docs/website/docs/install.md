# Download Open-Source PyMOL
Current version: **{{ version }}** (the application shows the version of its PyMOL core, e.g. 3.2.0a)

## Windows
Requires Windows 10 (version 22H2) or Windows 11, 64-bit.

- Installer: {{ download_link("_x64_setup.exe") }}
- Portable (no installation, extract and run): {{ download_link("_x64_portable.zip") }}

To access a step-by-step installation guide, click [here](install_windows.md).

## macOS
Requires macOS 12 (Monterey) or newer.

- Apple Silicon (M1, M2, M3, ...): {{ download_link("_macOS_AppleSilicon.dmg") }}
- Intel: {{ download_link("_macOS_Intel.dmg") }}

Not sure which Mac you have? Open the Apple menu and choose _About This Mac_:
"Chip: Apple M..." means Apple Silicon, "Processor: ... Intel ..." means Intel.

To access a step-by-step guide, click [here](install_macos.md).

## Linux
Requires a 64-bit (x86_64) distribution. Tested on Ubuntu 22.04 and 24.04, Debian 12,
Fedora, Rocky Linux 9, AlmaLinux 8, openSUSE Leap 15.6 and Tumbleweed.

- Debian, Ubuntu (.deb): {{ download_link("_amd64.deb") }}
- Fedora, RHEL, openSUSE (.rpm): {{ download_link("_x86_64.rpm") }}
- Portable (.tar.gz): {{ download_link(".tar.gz") }}

To access an installation guide, click [here](install_linux.md).

All versions are available on the [releases page]({{ repository_url }}/releases).
