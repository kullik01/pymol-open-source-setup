# Installation for Linux
There are three different packages available to install
Open-Source PyMOL under Linux (x86_64).
The DEB and RPM packages install all required system libraries automatically.

Install location: `/opt/{{ app_dir }}`

## Debian-based distros (Debian, Ubuntu, Linux Mint, Pop!_OS)
Download: {{ download_link("_amd64.deb") }}

To install the DEB package, run the following command in the directory of the downloaded file:
```shell
sudo apt install ./{{ file_name("_amd64.deb") }}
```
You can uninstall the DEB package with this command:
```shell
sudo apt remove pymol-open-source
```

## RPM-based distros (Fedora, RHEL, Rocky Linux, AlmaLinux)
Download: {{ download_link("_x86_64.rpm") }}

To install the RPM package, run the following command in the directory of the downloaded file:
```shell
sudo dnf install ./{{ file_name("_x86_64.rpm") }}
```
You can uninstall the RPM package with this command:
```shell
sudo dnf remove PyMOL-Open-Source
```

## openSUSE (Tumbleweed, Leap)
Download: {{ download_link("_x86_64.rpm") }}

To install the RPM package, run the following command in the directory of the downloaded file:
```shell
sudo zypper install --allow-unsigned-rpm ./{{ file_name("_x86_64.rpm") }}
```
You can uninstall the RPM package with this command:
```shell
sudo zypper remove PyMOL-Open-Source
```

## Generic
Besides the DEB and RPM package it is possible to install
Open-Source PyMOL using a .tar.gz file:
{{ download_link(".tar.gz") }}

That archive contains a portable installation and can be
extracted using this command:
```shell
tar -xzf {{ file_name(".tar.gz") }}
```
This will create the directory `{{ app_dir }}` in the current working directory.
Feel free to move it anywhere you want and start PyMOL with:
```shell
./{{ app_dir }}/Open-Source-PyMOL
```
The portable installation uses the OpenGL, X11/XCB and font libraries and the CA certificates
(package `ca-certificates`, needed to fetch structures from the PDB) of your system,
which are part of every common desktop installation.
