# C005 tests (Windows Powershell 5.1), test only temporary fixtures.
$ErrorActionPreference = "Stop"
$scriptPath = Join-Path (Split-Path $PSScriptRoot -Parent) "tools\C005_Video_Backup.ps1"
$testRoot = Join-Path $env:TEMP ("nvs_c005_test_" + [guid]::NewGuid().ToString("N"))
$source = Join-Path $testRoot "original"
$dest = Join-Path $testRoot "backup"
New-Item -ItemType Directory -Path (Join-Path $source "lake") -Force | Out-Null
try {
    $a = Join-Path $source "lake\winter.mp4"
    $b = Join-Path $source "spring.mov"
    $skip = Join-Path $source "ignored.txt"
    [IO.File]::WriteAllBytes($a,[byte[]](1,2,3,4,5))
    [IO.File]::WriteAllBytes($b,[byte[]](10,11,12))
    [IO.File]::WriteAllText($skip,"ignore this")
    $srcA = (Get-FileHash -LiteralPath $a -Algorithm SHA256).Hash
    $audit = & $scriptPath -Mode Audit -SourceDirs @($source) -BackupDir $dest
    if (($audit -notcontains "C005_AUDIT_PASS") -or ($audit -notcontains "VIDEO_COUNT: 2")) {
        throw "Audit test failed: $($audit -join '; ')"
    }
    if (Test-Path $dest) { throw "Audit created backup directory." }

    $backup = & $scriptPath -Mode Backup -SourceDirs @($source) -BackupDir $dest
    if (($backup -notcontains "C005_BACKUP_PASS") -or ($backup -notcontains "HASH_VERIFIED: 2")) {
        throw "Backup test failed: $($backup -join '; ')"
    }
    $copyA=Join-Path $dest "SOURCE_01\lake\winter.mp4"
    if (-not (Test-Path $copyA) -or (Get-FileHash $copyA -Algorithm SHA256).Hash -ne $srcA) {
        throw "Source/backup hash differs."
    }
    $again = & $scriptPath -Mode Backup -SourceDirs @($source) -BackupDir $dest
    if (($again -notcontains "ALREADY_MATCHED: 2")) {
        throw "Idempotent re-run failed: $($again -join '; ')"
    }
    # A conflicting backup is NEVER overwritten.
    [IO.File]::WriteAllBytes($copyA,[byte[]](9,8,7,6))
    $mismatchBefore=(Get-FileHash $copyA -Algorithm SHA256).Hash
    $mismatch = & $scriptPath -Mode Backup -SourceDirs @($source) -BackupDir $dest
    if (($mismatch -notcontains "C005_FAIL") -or (Get-FileHash $copyA -Algorithm SHA256).Hash -ne $mismatchBefore) {
        throw "A conflicting backup was overwritten or not detected."
    }
    if ((Get-FileHash -LiteralPath $a -Algorithm SHA256).Hash -ne $srcA) { throw "Original changed." }
    Write-Output "C005_TESTS_PASS"
} finally {
    Remove-Item -LiteralPath $testRoot -Recurse -Force -ErrorAction SilentlyContinue
}
