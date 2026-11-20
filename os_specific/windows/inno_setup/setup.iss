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
; A 64-bit installer (Inno Setup 7) for the 64-bit app
SetupArchitecture=x64
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
UninstallDisplayName=PyMOL-Open-Source
UninstallDisplayIcon={app}\assets\logo.ico
LicenseFile=LICENSE.txt
DiskSpanning=no
; Installs per user (into AppData\Roaming), no administrator rights needed
PrivilegesRequired=lowest
; Tells Windows about the file types registered below
ChangesAssociations=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Dirs]
Name: "{app}"
Name: "{app}\assets"
Name: "{app}\bin"

[InstallDelete]
; On an upgrade, files of older versions must not stay in the frozen application
Type: filesandordirs; Name: "{app}\bin"

[Files]
Source: "..\logo.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "{#AppSourceDir}\*"; DestDir: "{app}\bin"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\Open-Source PyMOL"; Filename: "{app}\bin\Open-Source-PyMOL.exe"; IconFilename: "{app}\assets\logo.ico"
Name: "{autoprograms}\Open-Source PyMOL"; Filename: "{app}\bin\Open-Source-PyMOL.exe"; IconFilename: "{app}\assets\logo.ico"

[Registry]
; File types (per-user, HKA = HKCU for this per-user installation). PyMOL is offered in "Open with"
; for .pdb and .cif files without taking them over from other programs, and it opens its own
; session files (.pse) by double-click. The uninstaller removes the keys that are left empty
; (the uninstaller works through the entries in reverse order, so .pse comes before its subkey).
Root: HKA; Subkey: "Software\Classes\OpenSourcePyMOL.File"; ValueType: string; ValueName: ""; ValueData: "PyMOL file"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\OpenSourcePyMOL.File\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\assets\logo.ico"
Root: HKA; Subkey: "Software\Classes\OpenSourcePyMOL.File\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\bin\Open-Source-PyMOL.exe"" ""%1"""
Root: HKA; Subkey: "Software\Classes\.pdb\OpenWithProgids"; ValueType: string; ValueName: "OpenSourcePyMOL.File"; ValueData: ""; Flags: uninsdeletevalue uninsdeletekeyifempty
Root: HKA; Subkey: "Software\Classes\.cif\OpenWithProgids"; ValueType: string; ValueName: "OpenSourcePyMOL.File"; ValueData: ""; Flags: uninsdeletevalue uninsdeletekeyifempty
Root: HKA; Subkey: "Software\Classes\.pse"; ValueType: string; ValueName: ""; ValueData: "OpenSourcePyMOL.File"; Flags: uninsdeletevalue uninsdeletekeyifempty
Root: HKA; Subkey: "Software\Classes\.pse\OpenWithProgids"; ValueType: string; ValueName: "OpenSourcePyMOL.File"; ValueData: ""; Flags: uninsdeletevalue uninsdeletekeyifempty

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
