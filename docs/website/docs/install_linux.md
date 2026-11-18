# Installation for Linux
There are three different packages available to install
Open-Source PyMOL under Linux (x86_64).
The DEB and RPM packages install all required system libraries automatically.

Install location: `/opt/PyMOL-Open-Source-3.1.0.4+4`

## Debian-based distros (Debian, Ubuntu, Linux Mint, Pop!_OS)
To install the DEB package, run the following command in the directory of the downloaded file:
```shell
sudo apt install ./PyMOL-Open-Source_v3.1.0.4+4_amd64.deb
```
You can uninstall the DEB package with this command:
```shell
sudo apt remove pymol-open-source
```

## RPM-based distros (Fedora, RHEL, Rocky Linux, AlmaLinux)
To install the RPM package, run the following command in the directory of the downloaded file:
```shell
sudo dnf install ./PyMOL-Open-Source_v3.1.0.4+4_x86_64.rpm
```
You can uninstall the RPM package with this command:
```shell
sudo dnf remove PyMOL-Open-Source
```

## openSUSE (Tumbleweed, Leap)
To install the RPM package, run the following command in the directory of the downloaded file:
```shell
sudo zypper install --allow-unsigned-rpm ./PyMOL-Open-Source_v3.1.0.4+4_x86_64.rpm
```
You can uninstall the RPM package with this command:
```shell
sudo zypper remove PyMOL-Open-Source
```

## Generic
Besides the DEB and RPM package it is possible to install
Open-Source PyMOL using a .tar.gz file.
That archive contains a portable installation and can be
extracted using this command:
```shell
tar -xzf PyMOL-Open-Source_v3.1.0.4+4.tar.gz
```
This will create the directory `PyMOL-Open-Source-3.1.0.4+4` in the current working directory.
Feel free to move it anywhere you want and start PyMOL with:
```shell
./PyMOL-Open-Source-3.1.0.4+4/Open-Source-PyMOL
```
The portable installation uses the OpenGL, X11/XCB and font libraries of your system,
which are part of every common desktop installation.
