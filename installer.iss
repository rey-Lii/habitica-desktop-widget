#define AppVersion "0.7.5"
[Setup]
AppId=HabiticaProgressBoard.rey-Lii
AppName=Habitica Progress Board
AppVersion={#AppVersion}
AppPublisher=rey-Lii
AppPublisherURL=https://github.com/rey-Lii/habitica-progress-board
DefaultDirName={localappdata}\Programs\Habitica Progress Board
DefaultGroupName=Habitica Progress Board
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=release
OutputBaseFilename=HabiticaProgressBoard-v{#AppVersion}-Windows-x64-Setup
SetupIconFile=HabiticaBoard.ico
UninstallDisplayIcon={app}\HabiticaProgressBoard.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"
[Files]
Source: "dist\HabiticaProgressBoard\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{userprograms}\Habitica Progress Board"; Filename: "{app}\HabiticaProgressBoard.exe"; WorkingDir: "{app}"
Name: "{userdesktop}\Habitica Progress Board"; Filename: "{app}\HabiticaProgressBoard.exe"; WorkingDir: "{app}"; Tasks: desktopicon
[Run]
Filename: "{app}\HabiticaProgressBoard.exe"; Description: "Launch Habitica Progress Board"; Flags: nowait postinstall skipifsilent
