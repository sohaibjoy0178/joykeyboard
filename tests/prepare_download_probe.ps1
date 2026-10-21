param(
    [Parameter(Mandatory=$true)][string]$Executable,
    [ValidateSet('Complete','Cancel','Quit','Reproduce')][string]$Mode='Complete'
)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public class JoyPrepareWindow { [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr hwnd, uint msg, IntPtr w, IntPtr l); }'
$profileDir=Join-Path $env:TEMP ('joy-prepare-ui-'+[Guid]::NewGuid().ToString('N'))
$dataDir=Join-Path $profileDir 'JoyKeyboard'
New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
$utf8=New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText((Join-Path $dataDir 'settings.json'),'{"engine":"sherpa","auto_updates":false,"theme":"dark"}',$utf8)
$env:LOCALAPPDATA=$profileDir
$env:HF_HOME=Join-Path $profileDir 'hf-empty'
$env:PATH=Join-Path $env:SystemRoot 'System32'
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue
$child=Start-Process -FilePath (Resolve-Path -LiteralPath $Executable).Path -WindowStyle Hidden -PassThru
$condition=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty,$child.Id)
$prepareName='Prepare Sherpa Bangla (~90 MiB)'
$report=@{mode=$Mode; executable=$Executable; profile=$profileDir; passed=$false; forced_kill=$false}

function OwnedWindows {
    return [System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children,$condition)
}
function Named([string]$name) {
    $filter=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,$name)
    foreach($top in (OwnedWindows)) {
        $item=$top.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$filter)
        if($null -ne $item) { return $item }
    }
    return $null
}
function WaitNamed([string]$name) {
    $deadline=[DateTime]::UtcNow.AddSeconds(15)
    do {
        $item=Named $name
        if($null -ne $item) { return $item }
        if($child.HasExited) { throw 'App exited before expected control appeared.' }
        Start-Sleep -Milliseconds 100
    } while([DateTime]::UtcNow -lt $deadline)
    throw "Control missing: $name"
}
function InvokeNamed([string]$name) {
    $item=WaitNamed $name
    $pattern=$null
    if($item.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern,[ref]$pattern)) { $pattern.Select() }
    else { $item.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke() }
}
function WaitReady {
    $deadline=[DateTime]::UtcNow.AddSeconds(150)
    do {
        $prepare=Named $prepareName
        if((Named 'Offline model ready') -and $prepare -and $prepare.Current.IsEnabled) { return }
        if(Named 'Needs attention') { throw 'Prepare failed in actual EXE.' }
        if($child.HasExited) { throw 'App exited during Prepare.' }
        Start-Sleep -Milliseconds 100
    } while([DateTime]::UtcNow -lt $deadline)
    throw 'Prepare never completed.'
}
function WaitProgress {
    $deadline=[DateTime]::UtcNow.AddSeconds(45)
    do {
        foreach($top in (OwnedWindows)) {
            foreach($item in $top.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)) {
                if($item.Current.Name -match '^encoder\.onnx.*[1-9][0-9]*%') { return $item.Current.Name }
            }
        }
        if(Named 'Needs attention') { throw 'Prepare failed before progress appeared.' }
        Start-Sleep -Milliseconds 100
    } while([DateTime]::UtcNow -lt $deadline)
    throw 'No encoder download progress appeared.'
}
function CloseBar {
    foreach($top in (OwnedWindows)) {
        if($top.Current.Name -like '*Floating bar') {
            [JoyPrepareWindow]::PostMessage([IntPtr]$top.Current.NativeWindowHandle,0x10,[IntPtr]::Zero,[IntPtr]::Zero) | Out-Null
            return
        }
    }
    throw 'Owned floating bar not found.'
}
try {
    InvokeNamed 'Open JoyKeyboard workspace'
    InvokeNamed 'Preferences'
    InvokeNamed $prepareName
    if($Mode -eq 'Reproduce') {
        WaitNamed 'Needs attention' | Out-Null
        $deadline=[DateTime]::UtcNow.AddSeconds(5)
        while(-not (Named $prepareName).Current.IsEnabled -and [DateTime]::UtcNow -lt $deadline) { Start-Sleep -Milliseconds 100 }
        InvokeNamed $prepareName
        Start-Sleep -Seconds 2
        CloseBar
        if($child.WaitForExit(8000)) { throw 'Old retry hang did not reproduce.' }
        $child.Kill()
        $child.WaitForExit()
        $report.forced_kill=$true
        $report.first_console_error_then_retry_quit_hang=$true
    } else {
        if($Mode -ne 'Complete') {
            $report.progress_seen=WaitProgress
            $watch=[Diagnostics.Stopwatch]::StartNew()
            if($Mode -eq 'Quit') {
                CloseBar
                if(-not $child.WaitForExit(12000)) { throw 'Quit did not complete during download.' }
                $report.quit_seconds=$watch.Elapsed.TotalSeconds
            } else {
                InvokeNamed 'Cancel and discard voice recording'
                $deadline=[DateTime]::UtcNow.AddSeconds(12)
                while(-not (Named $prepareName).Current.IsEnabled -and [DateTime]::UtcNow -lt $deadline) { Start-Sleep -Milliseconds 100 }
                if(-not (Named $prepareName).Current.IsEnabled) { throw 'Cancel did not release Prepare.' }
                $report.cancel_to_ready_seconds=$watch.Elapsed.TotalSeconds
                InvokeNamed $prepareName
                WaitReady
                $report.cancel_then_retry_succeeded=$true
            }
        } else {
            WaitReady
            InvokeNamed $prepareName
            WaitReady
            $report.two_prepare_clicks_succeeded=$true
        }
        if($Mode -ne 'Quit') {
            $manifest=Get-Content -LiteralPath (Join-Path $PSScriptRoot '..\assets\models\sherpa-channel.json') -Raw | ConvertFrom-Json
            foreach($file in $manifest.files.PSObject.Properties) {
                $path=Join-Path $dataDir ('models\sherpa-bn\'+$file.Name)
                if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $file.Value.sha256) { throw 'Prepared model hash mismatch.' }
            }
            $report.prepared_hashes_verified=$true
            CloseBar
            if(-not $child.WaitForExit(12000)) { throw 'Quit after preparation failed.' }
        }
        $parts=@(Get-ChildItem -LiteralPath $dataDir -Recurse -Filter '*.part' -ErrorAction SilentlyContinue)
        if($parts.Count -ne 0) { throw 'Cancelled/finished download left partial files.' }
        $report.no_partial_files=$true
    }
    $report.passed=$true
    $report | ConvertTo-Json -Depth 5
} finally {
    if(-not $child.HasExited) {
        try { CloseBar } catch {}
        if(-not $child.WaitForExit(2000)) { $child.Kill(); $child.WaitForExit() }
    }
}
