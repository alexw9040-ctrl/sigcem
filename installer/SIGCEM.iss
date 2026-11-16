#define MyAppName "SIGCEM"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Prefeitura Municipal"
#define MyAppExeName "SIGCEM.exe"

[Setup]
AppId={{8F2B6A4D-0C49-4E7A-9A32-6B3C8A2D9D11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\SIGCEM
DefaultGroupName=SIGCEM
OutputDir=installer\output
OutputBaseFilename=SIGCEM-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "dist\SIGCEM\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\SIGCEM"; Filename: "{app}\start_sigcem.bat"; WorkingDir: "{app}"
Name: "{group}\SIGCEM"; Filename: "{app}\start_sigcem.bat"; WorkingDir: "{app}"

[Run]
Filename: "{app}\start_sigcem.bat"; Description: "Executar o SIGCEM"; Flags: postinstall nowait skipifsilent
