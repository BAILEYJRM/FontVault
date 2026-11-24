; Optional Inno Setup script for FontVault (if ISCC.exe is installed)
[Setup]
AppId={{7B6F19B2-7A4D-49C6-9A2D-7F5D8C109A41}
AppName=FontVault
AppVersion=1.1.0
AppPublisher=FontVault Project
DefaultDirName={localappdata}\Programs\FontVault
DefaultGroupName=FontVault
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=FontVault-Setup-Inno-win64
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\FontVault.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "..\build\payload\FontVault.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\assets\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\FontVault"; Filename: "{app}\FontVault.exe"; IconFilename: "{app}\FontVault.ico"
Name: "{autodesktop}\FontVault"; Filename: "{app}\FontVault.exe"; IconFilename: "{app}\FontVault.ico"

[Run]
Filename: "{app}\FontVault.exe"; Description: "Ejecutar FontVault"; Flags: nowait postinstall skipifsilent
