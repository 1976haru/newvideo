# Synthetic Windows regression: update/launch marker/rollback in SAME V2 install.
# No actual D: paths, user credentials or user video/DB are ever accessed.
$ErrorActionPreference='Stop'
if ($env:CI -ne 'true' -or !$env:RUNNER_TEMP) { throw 'CI-only fixture test' }
$script=Join-Path (Split-Path $PSScriptRoot -Parent) 'tools\NVS_V2_Update_Existing.ps1'
$sha='501fe01209f2e2a2a75f863e4aa938d56415fdf4'
$oldsha='10206483d704af57e3c13df2b58b4e1548f66163'
$testRoot=Join-Path $env:RUNNER_TEMP ('nvs_existing_install_'+[Guid]::NewGuid().ToString('N'))
$install=Join-Path $testRoot 'NVS_V2_Trial_App\C011_Titlebar_10206483'
$sourceBase=Join-Path $install ('source\newvideo-'+$oldsha)
$active=Join-Path $sourceBase 'src'
$zipRoot=Join-Path $testRoot ('newvideo-'+$sha)
$zip=Join-Path $testRoot 'fixture_source.zip'
$python=(Get-Command python -ErrorAction Stop).Source
$canary=Join-Path $testRoot 'protected_fake_user_media.dat'
try {
 New-Item -ItemType Directory -Path $sourceBase -Force | Out-Null
 Copy-Item -LiteralPath (Join-Path (Split-Path $PSScriptRoot -Parent) 'src') -Destination $active -Recurse -ErrorAction Stop
 [IO.File]::WriteAllText((Join-Path $active 'nvs_old_code_sentinel.txt'),'SAFE_OLD_V2_CODE')
 [IO.File]::WriteAllText($canary,'FAKE_USER_DATA_MUST_NOT_CHANGE')
 $canaryBefore=(Get-FileHash -LiteralPath $canary -Algorithm SHA256).Hash
 New-Item -ItemType Directory -Path $zipRoot | Out-Null
 Copy-Item -LiteralPath (Join-Path (Split-Path $PSScriptRoot -Parent) 'src') -Destination (Join-Path $zipRoot 'src') -Recurse -ErrorAction Stop
 Compress-Archive -LiteralPath $zipRoot -DestinationPath $zip -CompressionLevel Optimal -ErrorAction Stop
 $args=@{
    InstallRoot=$install
    FixtureMode=$true
    PythonExe=$python
    SourceZip=$zip
    TargetCommit=$sha
    NoLaunch=$true
 }
 $audit=& $script -Mode Audit @args
 if ($audit -notcontains 'NVS_V2_EXISTING_INSTALL_AUDIT_PASS' -or !(Test-Path -LiteralPath $active)) {
    throw 'Existing installation audit failed.'
 }
 $installLog=& $script -Mode Update @args
 if ($installLog -notcontains 'NVS_V2_EXISTING_INSTALL_UPDATE_PASS' -or
     $installLog -notcontains 'C024_LOCAL_SEARCH_TABS_SMOKE_PASS') {
    throw ('Source update/smoke did not pass: '+($installLog -join '; '))
 }
 if (!(Test-Path -LiteralPath (Join-Path $active 'nature_video_studio\search_tabs.py'))) {
    throw 'New search tabs are not in original active source path.'
 }
 if ((Get-Content -LiteralPath (Join-Path $install 'NVS_V2_Current_SHA.txt') -TotalCount 1) -ne $sha) {
    throw 'Installed source SHA marker missing.'
 }
 $cmd=Join-Path $install 'NVS_V2_Start.cmd'
 if (!(Test-Path -LiteralPath $cmd -PathType Leaf)) { throw 'Same-path launcher missing.' }
 $cmdData=[IO.File]::ReadAllText($cmd)
 if (!$cmdData.Contains('NVS_V2_Updater.ps1') -or !$cmdData.Contains('-Mode Launch')) {
    throw 'Launcher is not pointing at the existing trial install.'
 }
 $backups=@(Get-ChildItem -LiteralPath $sourceBase -Directory |
    Where-Object { $_.Name -like 'src.nvs-backup-*' })
 if ($backups.Count -ne 1 -or
     !(Test-Path -LiteralPath (Join-Path $backups[0].FullName 'nvs_old_code_sentinel.txt'))) {
    throw 'Previous code was not backed up inside the SAME installation.'
 }
 $again=& $script -Mode Update @args
 if ($again -notcontains 'NVS_V2_ALREADY_UPDATED') {
    throw 'Rerun was not idempotent.'
 }
 $backupsAfter=@(Get-ChildItem -LiteralPath $sourceBase -Directory |
    Where-Object { $_.Name -like 'src.nvs-backup-*' })
 if ($backupsAfter.Count -ne 1) { throw 'Rerun made unnecessary duplicate backup.' }

 # Deliberately wrong source ZIP should refuse replacement and preserve active.
 $badZip=Join-Path $testRoot 'invalid_sha.zip'
 New-Item -ItemType Directory -Path (Join-Path $testRoot 'wrong_contents') | Out-Null
 [IO.File]::WriteAllText((Join-Path $testRoot 'wrong_contents\fake.txt'),'not a code archive')
 Compress-Archive -Path (Join-Path $testRoot 'wrong_contents') -DestinationPath $badZip
 $blocked=$false
 try {
    & $script -Mode Update -InstallRoot $install -FixtureMode -PythonExe $python -SourceZip $badZip -TargetCommit ('a'*40) -NoLaunch | Out-Null
 } catch { $blocked=$true }
 if (!$blocked -or !(Test-Path (Join-Path $active 'nature_video_studio\search_tabs.py'))) {
    throw 'Invalid upgrade was accepted or corrupted current install.'
 }

 $rollback=& $script -Mode Rollback @args
 if ($rollback -notcontains 'NVS_V2_EXISTING_INSTALL_ROLLBACK_PASS' -or
     !(Test-Path -LiteralPath (Join-Path $active 'nvs_old_code_sentinel.txt'))) {
    throw 'Rollback did not restore old active source at identical path.'
 }
 if (!(Test-Path -LiteralPath (Join-Path $install 'NVS_V2_Updater.ps1')) -or
     !(Test-Path -LiteralPath $cmd)) {
    throw 'Rollback removed the stable launcher.'
 }
 if ((Get-FileHash -LiteralPath $canary -Algorithm SHA256).Hash -ne $canaryBefore) {
    throw 'Fixture user-data canary was modified.'
 }
 if (Test-Path -LiteralPath (Join-Path $testRoot 'NVS_V2_Trial_App\C024_SearchTabs_8482a070')) {
    throw 'Updater created a second user-facing version install folder.'
 }
 Write-Output 'NVS_V2_EXISTING_INSTALL_UPDATE_ROLLBACK_TEST_PASS'
 Write-Output 'NO_NEW_PROGRAM_INSTALL_FOLDER_PASS'
 Write-Output 'SYNTHETIC_USER_DATA_NONMUTATION_PASS'
} finally {
 # Only synthetic CI files under RUNNER_TEMP are cleaned, never user data.
 if ($testRoot.StartsWith((([IO.Path]::GetFullPath($env:RUNNER_TEMP)).TrimEnd('\')+'\'),
    [StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $testRoot)) {
    Remove-Item -LiteralPath $testRoot -Recurse -Force -ErrorAction SilentlyContinue
 }
}
