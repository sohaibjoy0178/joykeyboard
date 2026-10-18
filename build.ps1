param([switch]$SkipInstall)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    & py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 x64 to build JoyKeyboard.' }
}
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
& $python -c "import struct,sys; assert sys.platform == 'win32' and struct.calcsize('P') == 8, 'Build requires Windows x64 Python'"
if ($LASTEXITCODE -ne 0) { throw 'Unsupported build interpreter.' }
if (-not $SkipInstall) {
    & $python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
& $python assets\generate_icons.py
if ($LASTEXITCODE -ne 0) { throw 'Icon validation failed.' }
& $python -m pytest tests -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed; build cancelled.' }
& $python -m PyInstaller --noconfirm --clean JoyKeyboard.spec
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed.' }
& $python -m pip freeze | Set-Content -LiteralPath 'requirements-lock.txt' -Encoding utf8
Get-FileHash -Algorithm SHA256 -LiteralPath 'dist\JoyKeyboard.exe' | Format-List
Write-Host "Standalone app: $PSScriptRoot\dist\JoyKeyboard.exe"
