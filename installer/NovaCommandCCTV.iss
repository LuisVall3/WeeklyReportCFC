#define AppName "NovaCommand CCTV"
#define AppVersion "1.0.0"
#define AppExe "NovaCommandCCTV.exe"

[Setup]
AppId={{A1B9FA0D-59ED-4A73-B87C-5F6B973AD33A}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=NovaSource Power Services
DefaultDirName={autopf}\NovaCommand CCTV
DefaultGroupName={#AppName}
OutputDir=..\installer_output
OutputBaseFilename=NovaCommand_CCTV_Setup_v1.0.0
SetupIconFile=..\assets\favicon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#AppExe}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
Source: "..\dist\NovaCommandCCTV\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Abrir {#AppName}"; Flags: nowait postinstall skipifsilent
