param([switch]$SkipInstall, [string]$IsccPath)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Create the Python 3.12 x64 .venv first; see README.md.' }
if (-not $IsccPath) {
    $compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($compiler) { $IsccPath = $compiler.Source }
    else {
        foreach ($candidate in @('tools\InnoSetup\ISCC.exe', "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe")) {
            if (Test-Path -LiteralPath $candidate) { $IsccPath = (Resolve-Path -LiteralPath $candidate).Path; break }
        }
    }
}
if (-not $IsccPath) { throw 'Install Inno Setup 6.7+ from https://jrsoftware.org/isdl.php, or pass -IsccPath.' }
if (-not $SkipInstall) {
    & $python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
& $python assets\generate_icons.py
if ($LASTEXITCODE -ne 0) { throw 'Icon validation failed.' }
& $python -m pytest tests -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
$previousMode = $env:JOYKEYBOARD_INSTALLER
try {
    $env:JOYKEYBOARD_INSTALLER = '1'
    & $python -m PyInstaller --noconfirm --clean --distpath dist\0.4.5 --workpath build\installer JoyKeyboard.spec
    if ($LASTEXITCODE -ne 0) { throw 'App packaging failed.' }
} finally { $env:JOYKEYBOARD_INSTALLER = $previousMode }
& $IsccPath installer.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
Get-FileHash -Algorithm SHA256 -LiteralPath dist\0.4.5\JoyKeyboard-Setup.exe | Format-List
Write-Host "Installer: $PSScriptRoot\dist\0.4.5\JoyKeyboard-Setup.exe"
