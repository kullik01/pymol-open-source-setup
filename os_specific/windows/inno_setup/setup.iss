; Inno Setup script of the PyMOL-Open-Source Windows installer (x64).
; Build it with: win_automator.bat build inno_setup
; which passes the following defines to the compiler (ISCC):
;   MyAppVersion  - version from pyproject.toml
;   AppSourceDir  - directory of the frozen application (dist\exe.win-amd64-<python version>)
#ifndef MyAppVersion
  #error MyAppVersion is not defined. Use: win_automator.bat build inno_setup
#endif
#ifndef AppSourceDir
  #error AppSourceDir is not defined. Use: win_automator.bat build inno_setup
#endif

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
WizardImageFile=compiler:WizClassicImage.bmp
AppName=PyMOL-Open-Source
AppVersion={#MyAppVersion}
AppCopyright=Hannah Kullik, Schrodinger LLC
AppId={{192F52C3-D86D-4735-9929-C7DF593CB534}
DefaultDirName={userappdata}\PyMOL-Open-Source
AppPublisher=Hannah Kullik
VersionInfoProductName=PyMOL-Open-Source
MinVersion=10.0.19045
OutputDir=..\..\dist
OutputBaseFilename=PyMOL-Open-Source_v{#MyAppVersion}_x64_setup
DisableDirPage=True
DisableProgramGroupPage=True
DisableReadyPage=True
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
UninstallDisplayName=PyMOL-Open-Source
UninstallDisplayIcon={app}\assets\logo.ico
LicenseFile=LICENSE.txt
DiskSpanning=no
PrivilegesRequired=none

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Dirs]
Name: "{app}"
Name: "{app}\assets"
Name: "{app}\bin"

[Files]
Source: "..\logo.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "{#AppSourceDir}\*"; DestDir: "{app}\bin"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\..\vendor\microsoft\VC_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{commondesktop}\Open-Source PyMOL"; Filename: "{app}\bin\Open-Source-PyMOL.exe"; IconFilename: "{app}\assets\logo.ico"
Name: "{commonstartmenu}\Open-Source PyMOL"; Filename: "{app}\bin\Open-Source-PyMOL.exe"; IconFilename: "{app}\assets\logo.ico"

[Run]
Filename: "{tmp}\VC_redist.x64.exe"; Parameters: "/quiet /norestart"; Flags: runhidden waituntilterminated

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
