# NVS V2: update the SAME existing C011 trial installation in place.
# ASCII/PowerShell 5.1. No writes to V1, keys, data DB, media or recovery.
[CmdletBinding()]
param(
 [ValidateSet('Update','Launch','Audit','Rollback')][string]$Mode='Update',
 [string]$InstallRoot='D:\NVS_V2_Trial_App\C011_Titlebar_10206483',
 [string]$TargetCommit='501fe01209f2e2a2a75f863e4aa938d56415fdf4',
 [switch]$NoLaunch,
 [string]$SourceZip,
 [switch]$FixtureMode,
 [string]$PythonExe
)
$ErrorActionPreference='Stop'
$oldCommit='10206483d704af57e3c13df2b58b4e1548f66163'
function Canon([string]$p) { [IO.Path]::GetFullPath($p).TrimEnd('\') }
function IsOverlap([string]$a,[string]$b) {
 $a=Canon $a; $b=Canon $b
 return ($a.Equals($b,[StringComparison]::OrdinalIgnoreCase) -or
 $a.StartsWith($b+'\',[StringComparison]::OrdinalIgnoreCase) -or
 $b.StartsWith($a+'\',[StringComparison]::OrdinalIgnoreCase))
}
function AssertNoLink([string]$p) {
 if (((Get-Item -LiteralPath $p -Force -ErrorAction Stop).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
  throw 'NVS_V2_BLOCKED_REPARSE_POINT'
 }
}
function AssertSource([string]$p) {
 if (!(Test-Path -LiteralPath $p -PathType Container)) { throw 'NVS_V2_BLOCKED_SOURCE_MISSING' }
 AssertNoLink $p
 $pkg=Join-Path $p 'nature_video_studio'
 if (!(Test-Path -LiteralPath $pkg -PathType Container)) { throw 'NVS_V2_BLOCKED_BAD_SOURCE' }
 foreach ($name in @('__init__.py','__main__.py','trial_gui.py','version_identity.py')) {
  $file=Join-Path $pkg $name
  if (!(Test-Path -LiteralPath $file -PathType Leaf)) { throw 'NVS_V2_BLOCKED_BAD_SOURCE' }
 }
 foreach ($entry in @(Get-ChildItem -LiteralPath $p -Recurse -Force -ErrorAction Stop)) { AssertNoLink $entry.FullName }
}
function Inventory([string]$p) {
 $items=@(Get-ChildItem -LiteralPath $p -Recurse -File -Force -ErrorAction Stop)
 $rows=@(foreach($f in $items){
   $rel=$f.FullName.Substring($p.TrimEnd('\').Length).TrimStart('\')
   $hash=(Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash
   $rel.ToLowerInvariant()+'|'+$hash
 })
 return @($rows | Sort-Object)
}
function VerifyCopy([string]$from,[string]$to) {
 $a=@(Inventory $from); $b=@(Inventory $to)
 if ($a.Count -ne $b.Count) { throw 'NVS_V2_BLOCKED_COPY_COUNT' }
 for ($i=0;$i -lt $a.Count;$i++) {
  if ($a[$i] -cne $b[$i]) { throw 'NVS_V2_BLOCKED_COPY_HASH' }
 }
}
# R1 live source adapters need requests and read-only Windows keyring.
# Resolve them in the already-existing, validated V2-only venv BEFORE code swap.
# Never install dependencies for the fixture Python, V1, user SQLite or media.
function EnsureLiveDependencies([string]$python) {
 $check="import requests, keyring;print('NVS_V2_LIVE_DEPENDENCIES_PASS')"
 & $python -c $check
 if ($LASTEXITCODE -eq 0) { return }
 if ($FixtureMode) { throw 'NVS_V2_BLOCKED_FIXTURE_DEPENDENCIES' }
 $expected=Canon (Join-Path $root '.venv\Scripts\python.exe')
 if (!( (Canon $python).Equals($expected,[StringComparison]::OrdinalIgnoreCase) )) {
  throw 'NVS_V2_BLOCKED_WRONG_PYTHON'
 }
 $drive=[IO.DriveInfo]::new([IO.Path]::GetPathRoot($expected))
 if ($drive.AvailableFreeSpace -lt 536870912) {
  throw 'NVS_V2_BLOCKED_INSUFFICIENT_VENV_SPACE'
 }
 Write-Output 'NVS_V2_INSTALL_LIVE_DEPS_EXISTING_VENV_ONLY'
 & $python -m pip --isolated install --no-cache-dir --disable-pip-version-check --index-url https://pypi.org/simple 'requests>=2.32,<3' 'keyring>=25,<27'
 if ($LASTEXITCODE -ne 0) { throw 'NVS_V2_BLOCKED_LIVE_DEPENDENCY_INSTALL' }
 & $python -c $check
 if ($LASTEXITCODE -ne 0) { throw 'NVS_V2_BLOCKED_LIVE_DEPENDENCY_IMPORT' }
}

function RunSmoke([string]$python,[string]$src,[switch]$RequireC024) {
 $prior=$env:PYTHONPATH
 try {
  $env:PYTHONPATH=$src
  & $python -m nature_video_studio --smoke
  if ($LASTEXITCODE -ne 0) { throw 'NVS_V2_BLOCKED_PYTHON_SMOKE' }
  if ($RequireC024) {
   $probe="from PySide6.QtWidgets import QApplication,QTabWidget,QPushButton;from nature_video_studio.trial_gui import build_window;app=QApplication([]);w=build_window();t=w.findChild(QTabWidget,'searchModeTabs');assert t and t.count()==2 and w.findChild(QPushButton,'longSwitchMode') and w.findChild(QPushButton,'shortSwitchMode');print('C024_LOCAL_SEARCH_TABS_SMOKE_PASS')"
   & $python -c $probe
   if ($LASTEXITCODE -ne 0) { throw 'NVS_V2_BLOCKED_C024_TABS_SMOKE' }
  }
 } finally { $env:PYTHONPATH=$prior }
}
function RunGUI([string]$python,[string]$src) {
 $prior=$env:PYTHONPATH
 try {
  $env:PYTHONPATH=$src
  & $python -m nature_video_studio
  if ($LASTEXITCODE -ne 0) { throw 'NVS_V2_GUI_EXIT_FAILED' }
 } finally { $env:PYTHONPATH=$prior }
}
# The real user cannot choose a different location; fixtures are only on CI temp.
$root=Canon $InstallRoot
if ($FixtureMode) {
 if ($env:CI -ne 'true' -or !$env:RUNNER_TEMP -or
     !$root.StartsWith((Canon $env:RUNNER_TEMP)+'\',[StringComparison]::OrdinalIgnoreCase)) {
  throw 'NVS_V2_BLOCKED_TEST_ONLY'
 }
 if (!$SourceZip -or !$PythonExe) { throw 'NVS_V2_BLOCKED_BAD_TEST_SETUP' }
} else {
 if (!$root.Equals((Canon 'D:\NVS_V2_Trial_App\C011_Titlebar_10206483'),[StringComparison]::OrdinalIgnoreCase)) {
  throw 'NVS_V2_BLOCKED_NOT_EXISTING_INSTALL'
 }
 if ($SourceZip -or $PythonExe) { throw 'NVS_V2_BLOCKED_TEST_ARGUMENTS' }
}
foreach ($p in @('D:\NatureVideoStudio','D:\NatureVideoStudio_V2_Data',
                 'D:\NVS_Recovery')) {
 if (IsOverlap $root $p) { throw 'NVS_V2_BLOCKED_PROTECTED_PATH' }
}
if (!(Test-Path -LiteralPath $root -PathType Container)) { throw 'NVS_V2_BLOCKED_INSTALL_NOT_FOUND' }
AssertNoLink $root
AssertNoLink (Split-Path -Path $root -Parent)
$top=Join-Path $root 'source'
$base=Join-Path $top ('newvideo-'+$oldCommit)
AssertNoLink $top
AssertNoLink $base
$active=Join-Path $base 'src'
AssertSource $active
$python=if($FixtureMode){$PythonExe}else{Join-Path $root '.venv\Scripts\python.exe'}
if (!(Test-Path -LiteralPath $python -PathType Leaf)) { throw 'NVS_V2_BLOCKED_PYTHON_MISSING' }
$marker=Join-Path $root 'NVS_V2_Current_SHA.txt'
if ($Mode -eq 'Audit') {
 Write-Output 'NVS_V2_EXISTING_INSTALL_AUDIT_PASS'
 Write-Output ('INSTALL_ROOT: '+$root)
 Write-Output ('CURRENT_COMMIT: '+$(if(Test-Path $marker){Get-Content $marker -TotalCount 1}else{'C011_OLD'}))
 Write-Output 'V1_DATA_KEYS_MEDIA_TOUCHED: NO'
 exit 0
}
if ($Mode -eq 'Launch') {
 RunGUI $python $active
 Write-Output 'NVS_V2_EXISTING_INSTALL_LAUNCH_PASS'
 exit 0
}
if (!$FixtureMode) {
 $running=@(Get-CimInstance Win32_Process -Filter "name = 'python.exe' or name = 'pythonw.exe'" -ErrorAction Stop)
 foreach ($proc in $running) {
  $processCommand=[string]$proc.CommandLine
  if ($processCommand -and $processCommand.IndexOf($root,[StringComparison]::OrdinalIgnoreCase) -ge 0) {
   throw 'NVS_V2_BLOCKED_CLOSE_APP_FIRST'
  }
 }
}
if ($Mode -eq 'Rollback') {
 $backups=@(Get-ChildItem -LiteralPath $base -Directory -Force |
    Where-Object {$_.Name -like 'src.nvs-backup-*'} | Sort-Object Name -Descending)
 if (!$backups.Count) { throw 'NVS_V2_ROLLBACK_NO_BACKUP' }
 $chosen=$backups[0].FullName
 AssertSource $chosen
 $failed=Join-Path $base ('src.nvs-replaced-'+[Guid]::NewGuid().ToString('N'))
 Move-Item -LiteralPath $active -Destination $failed -ErrorAction Stop
 try { Move-Item -LiteralPath $chosen -Destination $active -ErrorAction Stop }
 catch {
  if (!(Test-Path -LiteralPath $active)) {
   Move-Item -LiteralPath $failed -Destination $active -ErrorAction Stop
  }
  throw 'NVS_V2_ROLLBACK_FAILED'
 }
 [IO.File]::WriteAllText($marker,$oldCommit+[char]13+[char]10,[Text.Encoding]::ASCII)
 Write-Output 'NVS_V2_EXISTING_INSTALL_ROLLBACK_PASS'
 Write-Output 'V1_DATA_KEYS_MEDIA_TOUCHED: NO'
 exit 0
}
if ($TargetCommit -notmatch '^[0-9a-fA-F]{40}$') { throw 'NVS_V2_BLOCKED_UNPINNED_SHA' }
if (Test-Path $marker) {
 if ((Get-Content -LiteralPath $marker -TotalCount 1).Trim() -eq $TargetCommit) {
  RunSmoke $python $active -RequireC024
  Write-Output 'NVS_V2_ALREADY_UPDATED'
  if (!$NoLaunch) { RunGUI $python $active }
  exit 0
 }
}
$download=$SourceZip
$ownsDownload=(!$SourceZip)
if ($ownsDownload) {
 $download=Join-Path $env:TEMP ('nvs_v2_code_'+[Guid]::NewGuid().ToString('N')+'.zip')
}
$unpack=Join-Path $base ('src.nvs-unpack-'+[Guid]::NewGuid().ToString('N'))
$stage=Join-Path $base ('src.nvs-stage-'+[Guid]::NewGuid().ToString('N'))
$backup=Join-Path $base ('src.nvs-backup-'+(Get-Date -Format 'yyyyMMddHHmmss')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8))
$oldMoved=$false
$newMoved=$false
try {
 if ($ownsDownload) {
  Write-Output 'NVS_V2_FETCH_PINNED_COMMIT'
  Invoke-WebRequest -Uri ('https://github.com/1976haru/newvideo/archive/'+$TargetCommit+'.zip') -OutFile $download -UseBasicParsing -TimeoutSec 90
 }
 $info=Get-Item -LiteralPath $download -ErrorAction Stop
 if ($info.Length -lt 200 -or $info.Length -gt 32MB) { throw 'NVS_V2_BLOCKED_BAD_ARCHIVE_SIZE' }
 New-Item -ItemType Directory -Path $unpack -ErrorAction Stop | Out-Null
 Expand-Archive -LiteralPath $download -DestinationPath $unpack -ErrorAction Stop
 $extracted=Join-Path $unpack ('newvideo-'+$TargetCommit)
 if (!(Test-Path -LiteralPath $extracted -PathType Container)) { throw 'NVS_V2_BLOCKED_ARCHIVE_SHA' }
 AssertNoLink $extracted
 $newSource=Join-Path $extracted 'src'
 AssertSource $newSource
 if (!(Test-Path -LiteralPath (Join-Path $newSource 'nature_video_studio\search_tabs.py'))) {
  throw 'NVS_V2_BLOCKED_C024_NOT_PRESENT'
 }
 Copy-Item -LiteralPath $newSource -Destination $stage -Recurse -ErrorAction Stop
 AssertSource $stage
 VerifyCopy $newSource $stage
 # Real live GUI imports requests immediately; correct only this V2 venv
 # before moving the working source into a backup directory.
 if (!$FixtureMode -and
     (Test-Path -LiteralPath (Join-Path $stage 'nature_video_studio\live_sources.py') -PathType Leaf)) {
  EnsureLiveDependencies $python
 }
 RunSmoke $python $stage -RequireC024
 Move-Item -LiteralPath $active -Destination $backup -ErrorAction Stop
 $oldMoved=$true
 Move-Item -LiteralPath $stage -Destination $active -ErrorAction Stop
 $newMoved=$true
 RunSmoke $python $active -RequireC024
 $self=Join-Path $root 'NVS_V2_Updater.ps1'
 if ($PSCommandPath -ne $self) { Copy-Item -LiteralPath $PSCommandPath -Destination $self -ErrorAction Stop }
 $cmd=Join-Path $root 'NVS_V2_Start.cmd'
 $lines=@('@echo off','setlocal','set "ROOT=%~dp0"',
   'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT%NVS_V2_Updater.ps1" -Mode Launch',
   'exit /b %ERRORLEVEL%')
 [IO.File]::WriteAllText($cmd,($lines -join ([char]13+[char]10))+[char]13+[char]10,[Text.Encoding]::ASCII)
 [IO.File]::WriteAllText($marker,$TargetCommit+[char]13+[char]10,[Text.Encoding]::ASCII)
 Write-Output 'NVS_V2_EXISTING_INSTALL_UPDATE_PASS'
 Write-Output 'C024_LOCAL_SEARCH_TABS_SMOKE_PASS'
 Write-Output ('ACTIVE_COMMIT: '+$TargetCommit)
 Write-Output ('START_CMD: '+$cmd)
 Write-Output 'V1_DATA_KEYS_MEDIA_TOUCHED: NO'
} catch {
 if ($oldMoved) {
  if ($newMoved -and (Test-Path $active)) {
   $failed=Join-Path $base ('src.nvs-failed-'+[Guid]::NewGuid().ToString('N'))
   Move-Item -LiteralPath $active -Destination $failed -ErrorAction Stop
  }
  if (!(Test-Path $active) -and (Test-Path $backup)) {
   Move-Item -LiteralPath $backup -Destination $active -ErrorAction Stop
   Write-Output 'NVS_V2_AUTOMATIC_SOURCE_ROLLBACK_PASS'
  }
 }
 Write-Output 'NVS_V2_UPDATE_FAILED'
 throw 'NVS_V2_UPDATE_ABORTED'
} finally {
 if ($ownsDownload -and (Test-Path -LiteralPath $download)) {
  Remove-Item -LiteralPath $download -Force -ErrorAction SilentlyContinue
 }
 # Clean ONLY temporary code unpacked by this invocation inside existing V2.
 if ((Test-Path -LiteralPath $unpack) -and $unpack.StartsWith($base+'',[StringComparison]::OrdinalIgnoreCase)) {
  Remove-Item -LiteralPath $unpack -Recurse -Force -ErrorAction SilentlyContinue
 }
 if ((Test-Path -LiteralPath $stage) -and $stage.StartsWith($base+'',[StringComparison]::OrdinalIgnoreCase)) {
  Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
 }
}
if (!$NoLaunch) { RunGUI $python $active }
