# Unofficial PyMOL(TM) Setup
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-blue.svg)](https://GitHub.com/kullik01/pymol-open-source-setup/graphs/commit-activity)
[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![GitHub issues](https://img.shields.io/github/issues/kullik01/pymol-open-source-setup)](https://GitHub.com/kullik01/pymol-open-source-setup/issues/)

### Supported Platforms

![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![macOS](https://img.shields.io/badge/mac%20os-000000?style=for-the-badge&logo=macos&logoColor=F0F0F0)
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)

This repository offers **unofficial** setups/packages for the open-source version of PyMOL(TM)
for **all major** operating systems.

## <img src='https://github.com/primer/octicons/blob/main/icons/download-24.svg' width='32'/> [Quick Installation](https://kullik01.github.io/pymol-open-source-setup/)

## Contents of this document
* [About PyMOL](#About-PyMOL)
* [Contents of this repository](#Contents-of-this-repository)
    * [Scripts](#Scripts)
* [From source](#From-source)
    * [Prerequisites](#Prerequisites)
    * [Step-by-step guide](#Step-by-step-guide)
* [License](#License)
* [Acknowledgements](#Acknowledgements)
<!--* [References and useful links](#References-and-useful-links) -->

## About PyMOL
[PyMOL™](https://pymol.org/) is a powerful visualization software for rendering and animating 3D molecular structures. PyMOL is a trademark of Schrödinger, LLC.

Please note that the files provided here are **unofficial**. They are informal, unrecognized, and unsupported, offered for testing and evaluation purposes only. No warranty or liability is provided, and the software is made available "as-is."

## Contents of this repository
"Insert some more information here"

## From source
The following information is about building a platform dependent package/setup from source.

### Prerequisites for Windows
- Inno Setup compiler 6
  - Install location must be: `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`

### Prerequisites for Linux
- Ruby (**only** if fpm is used for packaging)
  - apt (Debian or Ubuntu): `sudo apt-get install ruby-full`
  - yum (CentOS, Fedora, or RHEL): `sudo yum install ruby`

### Step-by-step guide
1. Create a new Python virtual environment
2. Install build dependencies using the requirements.txt of your platform
3. Build the app package:

#### Windows
If you are on Windows run:
```shell
.\win_automator.bat build app
```
```shell
.\win_automator.bat build inno_setup
```

#### macOS
If you are on macOS:
```shell
chmod +x ./automator.sh && ./automator.sh build app
```
To build the DMG use a tool like [create-dmg](https://github.com/create-dmg/create-dmg) or fork the repository 
and run the GitHub action build_app.yaml.

#### Linux
If you are on Linux:
```shell
chmod +x ./automator.sh && ./automator.sh build app
```
To build the tar.gz run:
```shell
mkdir -p packaged/build/Open-Source-PyMOL-<version-number>
cp -r ./dist/exe.linux*/* packaged/build/Open-Source-PyMOL-<version-number>/
mkdir -p packaged/bin
tar czvf packaged/bin/Open-Source-PyMOL-<version-number>.tar.gz packaged/build/Open-Source-PyMOL-<version-number>
```
If you want to build a .deb or .rpm package, you could use the Ruby gem called fpm:
```shell
sudo gem install fpm
mkdir -p package-root/opt/Open-Source-PyMOL-<version-number>
cp -r ./dist/exe.linux*/* package-root/opt/Open-Source-PyMOL-<version-number>/
mkdir -p package-root/usr/bin
ln -s /opt/Open-Source-PyMOL-<version-number>/Open-Source-PyMOL package-root/usr/bin/Open-Source-PyMOL
mkdir -p package-root/usr/share/applications
cp os_specific/linux/open-source-pymol.desktop package-root/usr/share/applications

fpm -s dir -t deb \
-n open-source-pymol \
-v <version-number> \
-a amd64 \
-C package-root \
--description "PyMOL installation for debian-based distros" \
--license "BSD-3-Clause" \
```

## License
Copyright (c) [Schrodinger, LLC](https://www.schrodinger.com/)

Published under a BSD-like license, see [LICENSE](LICENSE).

## Acknowledgements
**Schrödinger** for being the driving force behind the continued development of PyMOL after Warren's passing, ensuring that the open-source version remained alive and well.

**NOTE**: the following list has not been updated since Fall 2003 and was originally created by Warren himself.

Since then, the PyMOL effort has grown to such an extent that it is no longer
practical to recognize everyone individually.  Fortunately, a public
record of participation exists and can be appreciated on the internet,
and especially via the PyMOL mailing list archives.  Suffice it to say
that the PyMOL user community now numbers well into the thousands and
includes scientists, students, and educators worldwide, spread
throughout academia and the biotechnology and pharmaceutical
industries.  Though DeLano Scientific LLC specifically supports and
maintains the PyMOL code base, the project can only continue to
succeed through the sponsorship and participation of the broader
community.

**Founder and Principal Author**:

      Warren L. DeLano 

Major Authors (5000+ lines of code):

      Ralf W. Grosse-Kunstleve (SGLite Module)

Minor Authors (500+ lines of code):

      Scott Dixon (Metaphorics CEX support)
      Filipe Maia (Slice Objects)

Other Contributors: These are the people who have gone out of
their way to help the project with their ideas, actions,
advice, hardware donations, testing, information, sponsorship,
peer support, or code snippets.

      Daan van Aalten
      Paul Adams 
      Stephen Adler
      Jun Aishima 
      Dennis Allison
      Ricardo Aparicio
      Daniel Appelman   
      Diosdado "Rey" Banatao
      Michael Banck
      Ulrich Baumann
      Joseph Becker
      Balaji Bhyravbhatla
      Jeff Bizzaro
      Jeff Blaney 
      Juergen Bosch 
      Michael Bower
      Sarina Bromberg
      Axel Brunger
      Robert Campbell
      Bronwyn Carlisle 
      Duilio Cascio
      Julien Chiron 
      Shawn Christensen
      Scott Classen
      David Cooper
      Larry Coopet
      Jacob Corn
      Ben Cornett
      Andrew Dalke 
      Koen van der Drift 
      Harry Dailey
      Byron DeLaBarre
      Bill DeGrado
      Thomas Earnest
      Nathaniel Echols
      John Eksterowicz
      Erik Evensen
      David Fahrney
      Tim Fenn
      Thierry Fischmann
      Michael Ford
      Esben Peter Friis
      Kevin Gardner
      R. Michael Garavito
      John Gerig
      Jonathan Greene
      Michael Goodman  
      Joel Harp
      Reece Hart
      Richard Hart
      Peter Haebel
      Matt Henderson
      Douglas Henry 
      Possu Huang 
      Uwe Hoffmann
      Jenny Hinshaw
      Carly Huitema
      Bjorn Kauppi
      Greg Landrum
      Robert Lawrence Kehrer 
      Tom Lee
      Eugen Leitl
      Ken Lind
      Jules Jacobsen
      Luca Jovine
      Andrey Khavryuchenko
      David Konerding
      Greg Landrum
      Michael Love 
      Tadashi Matsushita
      Genevieve Matthews 
      Gerry McDermott 
      Robert McDowell
      Gustavo Mercier      
      Naveen Michaud-Agrawal
      Aaron Miller
      Holly Miller
      Tim Moore
      Kelley Moremen
      Hideaki Moriyama
      Nigel Moriarty 
      Geoffrey Mueller
      Cameron Mura
      Florian Nachon 
      Hanspeter Niederstrasser 
      Michael Nilges
      Hoa Nguyen
      Shoichiro Ono
      Chris Oubridge
      Andre Padilla
      Jay Pandit
      Ezequiel "Zac" Panepucci
      Robert Phillips
      Hans Purkey
      Rama Ranganathan
      Michael Randal
      Daniel Ricklin 
      Ian Robinson
      Eric Ross
      Kristian Rother
      Marc Saric
      Bill Scott
      Keana Scott
      Denis Shcherbakov
      Goede Schueler
      Paul Sherwood
      Ward Smith
      John Somoza
      David van der Spoel
      Paul Sprengeler
      Matt Stephenson 
      Peter Stogios
      John Stone
      Charlie Strauss
      Michael Summers
      Brian Sutton
      Hanna and Abraham Szoke
      Rod Tweten
      Andras Varadi
      Scott Walsh
      Pat Walters
      Mark White
      Michael Wilson
      Dave Weininger
      Chris Wiesmann
      Charles Wolfus
      Richard Xie

Miscellaneous Code Snippets Lifted From:

      Thomas Malik (fast matrix-multiply code)
      John E. Grayson (Author of "Python and Tkinter")
      Doug Hellmann (Wrote code that JEG later modified.)

Open-Source "Enablers" (essential, but not directly involved):

      Brian Paul (Mesa)
      Mark Kilgard (GLUT)
      Guido van Rossum (Python)
      Linus Torvalds (Linux Kernel)

      Precision Insight (DRI)
      The XFree86 Project (Free Windowing System)
      VA Linux (CVS Hosting)
      Richard Stallman/Free Software Foundation (GNU Suite)
      The unknown authors of EISPACK (Linear Algebra)

Graphics Technology "Enablers" (essential!)

      3dfx (RIP)
      nVidia 
      ATI

### Specific Acknowledgments:

* Thanks to Joni W. Lam for making the business work.

* Thanks to John Stone and John Furr for being such excellent
  colleagues.

* Thanks to Ragu Bharadwaj and Marcin Joachimiak for Java expertise
  and encouragement.

* Thanks to Apple Computer for continued encouragement, assistance,
  and HLAs in support of Mac development.  Thanks especially to
  Robert Kehrer for creating so many fun opportunities over the years.

* Thanks to Aaron Miller (GlaxoSmithKline) for a continuous stream of
  thoughtful opinions and suggestions.

* Thanks to Dave Weininger for suggesting the "roving" feature and for
  being such an inspirational friend and mentor.

* Thanks to Matt Hahn and Dave Rogers for proving that it can also be
  done, again.

* Thanks to Mick Savage for providing experienced practical advice on
  the marketing of scientific software.

* Thanks to Ian Matthew for 3D experience and perspective.

* Thanks for Jeff Blaney for numerous insightful discussions.

* Thanks to Elizabeth Pehrson for making this a team effort.

* Thanks to Erin Bradley for schooling in focus and vision.

* Thanks to Vera Povolona for catalytic clarity and introspection.

* Thanks to Anthony Nichols for proving that it can be done, yet again.

* Thanks to Thompson Doman for timely Open-Source validation.

* Thanks to Manfred Sippl for making it all seem so simple.

* Thanks to Kristian Rother for all his excellent work building on the
  PyMOL foundation, and in helping others learn to use the software.

* Thanks to Dave Weininger, Scott Dixon, Roger Sayle, Andrew Dalke,
  Anthony Nichols, Dick Cramer, and David Miller, as well as rest of
  the Daylight and OpenEye teams for thoughtful discussions on PyMOL
  and open-source software during my 2002 pilgrimage to Sante Fe, NM.

* Thanks to Ralf Grosse-Kunstleve for his contribution of the "sglite"
  space group and symmetry handling module.

* Thanks to the scientists and management of Sunesis Pharmaceuticals
  for supporting PyMOL development since program inception.

* Thanks to the Computational Crystallography Initiative (LBNL)
  developers for their encouragement, ideas, and support.

* Thanks to Scott Walsh for being the first individual to provide
  financial support for PyMOL.

* Thanks to the hundreds of individuals, companies, and institutions
  that have provided financial support for the project.

* Thanks to Brian Paul and the Precision Insight team for development
  of Mesa/DRI which greatly assisted in the early development of PyMOL.

* Thanks to Michael Love for the first major outside port of PyMOL
  (to GNU-Darwin/OSX) and for believing in the cause.

* Thanks for Paul Sherwood for making a concerted effort to develop
  using PyMOL long before the software and vision had matured.

* Thanks to Jay Ponder for thoughtful email discussions on Tinker and
  the role of open-source scientific software.

* Thanks to hundreds of PyMOL users for the many forms of feedback,
  bug sightings, and encouragement they've provided.