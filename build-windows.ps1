$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
function Run-Native { param([string]$Command, [string[]]$Arguments) & $Command @Arguments; if ($LASTEXITCODE -ne 0) { throw "$Command exited with code $LASTEXITCODE" } }
$python = if (Test-Path '.venv-build\Scripts\python.exe') { (Resolve-Path '.venv-build\Scripts\python.exe').Path } else { Run-Native 'python' @('-m','venv','.venv-build') | Out-Host; (Resolve-Path '.venv-build\Scripts\python.exe').Path }
Run-Native $python @('-m','pip','install','-r','requirements.txt','PyInstaller>=6.11,<7')
Run-Native $python @('-m','unittest','discover','-v')
Run-Native $python @('-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed','--name','HabiticaProgressBoard','--icon','HabiticaBoard.ico','--add-data','HabiticaBoard.ico;.','--add-data','HabiticaBoard.png;.','--copy-metadata','PySide6-Essentials','--copy-metadata','shiboken6','HabiticaProgressBoard.pyw')
$exe = (Resolve-Path 'dist\HabiticaProgressBoard\HabiticaProgressBoard.exe').Path
$oldLocal = $env:LOCALAPPDATA
$tempLocal = Join-Path ([System.IO.Path]::GetTempPath()) ('HabiticaSmoke-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $tempLocal | Out-Null
try {
    $env:LOCALAPPDATA = $tempLocal
    $p = Start-Process -FilePath $exe -ArgumentList '--demo' -PassThru
    Start-Sleep -Seconds 6
    $p.Refresh()
    if ($p.HasExited) { throw "Packaged demo exited early: $($p.ExitCode)" }
} finally {
    if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force; $p.WaitForExit() }
    $env:LOCALAPPDATA = $oldLocal
    Remove-Item -LiteralPath $tempLocal -Recurse -Force -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Force -Path release | Out-Null
Compress-Archive -Path 'dist\HabiticaProgressBoard' -DestinationPath 'release\HabiticaProgressBoard-v0.7.5-Windows-x64-portable.zip' -Force
$iscc = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'
if (-not (Test-Path $iscc)) { throw 'Inno Setup 6 is required. Install it from https://jrsoftware.org/isdl.php and run again.' }
Run-Native $iscc @('installer.iss')
Get-ChildItem release -File | Where-Object { $_.Extension -in '.exe','.zip' } | Get-FileHash -Algorithm SHA256 | ForEach-Object { "$($_.Hash.ToLower())  $([System.IO.Path]::GetFileName($_.Path))" } | Set-Content release\SHA256SUMS.txt -Encoding ascii
