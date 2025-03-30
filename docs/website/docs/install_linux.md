# Installation for Linux
There are three different packages available to install
Open-Source PyMOL under Linux.

## Debian-based distros (Ubuntu, PopOS!)
To install the DEB package, run the following command:
```shell
sudo dpkg -i open-source-pymol_3.1.0.4_amd64.deb
```
You can uninstall the DEB package with this command:
```shell
sudo dpkg -r open-source-pymol_3.1.0.4_amd64.deb
```

## Red-Hat-based distros (Fedora, Suse, AlmaLinux)
To install the RPM package, run the following command:
```shell
sudo rpm -i open-source-pymol-3.1.0.4-1.x86_64.rpm
```
You can uninstall the RPM package with this command:
```shell
sudo rpm -e open-source-pymol-3.1.0.4-1.x86_64.rpm
```

## Generic
Besides the DEB and RPM package it is possible to install
Open-Source PyMOL using a .tar.gz file.
That archive contains a portable installation and can be
extracted using this command:
```shell
tar -xvf Open-Source-PyMOL-3.1.0.4.tar.gz
```
This will extract the archive in the current working directory.
Feel free to move the extracted files anywhere you want.