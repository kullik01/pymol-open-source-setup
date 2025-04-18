; Script generated by the Inno Script Studio Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
WizardImageFile=compiler:WizClassicImage.bmp
;WizardImageFile=customInnoSetupImage.bmp
AppName=PyMOL-open-source
AppVersion=3.1.0a0
AppCopyright=Hannah Kullik, Schrodinger LLC
AppId={{192F52C3-D86D-4735-9929-C7DF593CB534}
DefaultDirName={userappdata}\PyMOL-Open-Source
AppPublisher=Hannah Kullik
VersionInfoProductName=PyMOL-open-source
MinVersion=10.0.19045
OutputDir=..\..\dist
OutputBaseFilename=PyMOL_Open_source_v3.1.0a0_WINx64_setup
; VersionInfoCopyright=GNU GPL-3.0
DisableDirPage=True
DisableProgramGroupPage=True
DisableReadyPage=True
WizardStyle=modern
UninstallDisplayName=PyMOL-open-source
UninstallDisplayIcon={app}\assets\logo.ico
LicenseFile=LICENSE.txt
; This is necessary if the setup will exceed 2 GB
DiskSpanning=no
; DiskSliceSize=2100000000
PrivilegesRequired=none

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Dirs]
Name: "{app}"
Name: "{app}\assets"
Name: "{app}\bin"

[Files]
Source: "..\..\..\inno-build-release\inno-assets\logo.ico"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs;
Source: "..\..\..\inno-build-release\inno-sources\*"; DestDir: "{app}\bin"; Flags: ignoreversion recursesubdirs createallsubdirs;

[Icons]
Name: "{commondesktop}\Open-Source PyMOL"; Filename: "{app}\bin\Open-Source-PyMOL.exe"; IconFilename: "{app}\assets\logo.ico"
Name: "{commonstartmenu}\Open-Source PyMOL"; Filename: "{app}\bin\Open-Source-PyMOL.exe"; IconFilename: "{app}\assets\logo.ico"

[Run]
Filename: "{app}\bin\VC_redist.x64.exe"; Parameters: "/quiet /norestart"; Flags: runhidden waituntilterminated

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
