# Download Open-Source PyMOL
Current version: **{{ version }}**

## Windows
Requires Windows 10 (version 22H2) or Windows 11, 64-bit.

- Installer: [{{ file_name("_x64_setup.exe") }}]({{ download_url("_x64_setup.exe") }})
- Portable (no installation, extract and run): [{{ file_name("_x64_portable.zip") }}]({{ download_url("_x64_portable.zip") }})

To access a step-by-step installation guide, click [here](install_windows.md).

## macOS
Requires macOS 12 (Monterey) or newer.

- Apple Silicon (M1, M2, M3, ...): [{{ file_name("_macOS_AppleSilicon.dmg") }}]({{ download_url("_macOS_AppleSilicon.dmg") }})
- Intel: [{{ file_name("_macOS_Intel.dmg") }}]({{ download_url("_macOS_Intel.dmg") }})

Not sure which Mac you have? Open the Apple menu and choose _About This Mac_:
"Chip: Apple M..." means Apple Silicon, "Processor: ... Intel ..." means Intel.

To access a step-by-step guide, click [here](install_macos.md).

## Linux
Requires a 64-bit (x86_64) distribution. Tested on Ubuntu 22.04 and 24.04, Debian 12,
Fedora, Rocky Linux 9, AlmaLinux 8, openSUSE Leap 15.6 and Tumbleweed.

- Debian, Ubuntu (.deb): [{{ file_name("_amd64.deb") }}]({{ download_url("_amd64.deb") }})
- Fedora, RHEL, openSUSE (.rpm): [{{ file_name("_x86_64.rpm") }}]({{ download_url("_x86_64.rpm") }})
- Portable (.tar.gz): [{{ file_name(".tar.gz") }}]({{ download_url(".tar.gz") }})

To access an installation guide, click [here](install_linux.md).

All versions are available on the [releases page]({{ repository_url }}/releases).
