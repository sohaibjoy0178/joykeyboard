; One installer EXE; installed runtime avoids one-file extraction at every launch.
#ifndef AppVersion
  #define AppVersion "0.4.6"
#endif
#ifndef PayloadDir
  #define PayloadDir "dist\0.4.6\JoyKeyboard"
#endif

[Setup]
AppId={{51281235-DF17-48AE-AE18-445279EB0C4E}
AppName=JoyKeyboard
AppVersion={#AppVersion}
AppPublisher=Sohaib Islam Joy
AppPublisherURL=https://www.facebook.com/sohaib.islam1997
AppSupportURL=https://www.facebook.com/sohaib.islam1997
AppCopyright=Developed by Sohaib Islam Joy
DefaultDirName={localappdata}\Programs\JoyKeyboard
DefaultGroupName=JoyKeyboard
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
WizardStyle=modern
WizardSizePercent=110
SetupIconFile=assets\joykeyboard.ico
UninstallDisplayIcon={app}\JoyKeyboard.exe
OutputDir=dist\{#AppVersion}
OutputBaseFilename=JoyKeyboard-Setup
Compression=lzma2/normal
SolidCompression=yes
LZMANumBlockThreads=2
LZMADictionarySize=8192
CloseApplications=no
RestartApplications=no
DisableWelcomePage=no
UninstallDisplayName=JoyKeyboard
VersionInfoVersion={#AppVersion}.0

[Messages]
WelcomeLabel2=This will install [name/ver] on your computer.%n%nDeveloped by Sohaib Islam Joy%nFacebook: https://www.facebook.com/sohaib.islam1997%n%nClose other copies of JoyKeyboard before continuing.

[Tasks]
Name: "autostart"; Description: "Start JoyKeyboard when I sign in to Windows"; GroupDescription: "Startup:"
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\JoyKeyboard"; Filename: "{app}\JoyKeyboard.exe"; WorkingDir: "{app}"
Name: "{userdesktop}\JoyKeyboard"; Filename: "{app}\JoyKeyboard.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "JoyKeyboard"; ValueData: """{app}\JoyKeyboard.exe"""; Tasks: autostart
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "JoyKeyboard"; Flags: deletevalue; Tasks: not autostart

[Run]
Filename: "{app}\JoyKeyboard.exe"; Description: "Open JoyKeyboard"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  StartupCommand: String;
begin
  if CurUninstallStep = usUninstall then
    if RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'JoyKeyboard', StartupCommand) then
      if CompareText(StartupCommand, '"' + ExpandConstant('{app}\JoyKeyboard.exe') + '"') = 0 then
        RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'JoyKeyboard');
end;
