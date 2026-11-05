# Nature Video Studio C005 - safe video audit and optional copy-only backup.
# PowerShell 5.1 compatible. Original files are never modified, moved, or removed.
[CmdletBinding()]
param(
    [ValidateSet("Audit", "Backup")][string]$Mode = "Audit",
    [string[]]$SourceDirs = @("D:\NatureVideoStudio", "D:\03 자연풍경 비디오"),
    [string]$BackupDir = "D:\NVS_Recovery\C005_VIDEOS"
)

$ErrorActionPreference = "Stop"
$mediaExt = @(".mp4",".mov",".mkv",".webm",".avi",".m4v",".wmv",".mts",".m2ts",".mpg",".mpeg",".ts")
$rootRecords = @()
$files = New-Object 'System.Collections.Generic.List[object]'
$seen = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)

function Get-Hash([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256 -ErrorAction Stop).Hash.ToUpperInvariant()
}

try {
    $backupFull = [IO.Path]::GetFullPath($BackupDir).TrimEnd('\')
    $j = 0

    foreach ($entry in $SourceDirs) {
        if ([string]::IsNullOrWhiteSpace($entry)) { continue }
        if (-not (Test-Path -LiteralPath $entry -PathType Container)) {
            Write-Output ("SKIPPED_NOT_FOUND: " + $entry)
            continue
        }

        $sourceFull = [IO.Path]::GetFullPath($entry).TrimEnd('\')
        if ($backupFull.Equals($sourceFull, [StringComparison]::OrdinalIgnoreCase) -or
            $backupFull.StartsWith($sourceFull + "\", [StringComparison]::OrdinalIgnoreCase) -or
            $sourceFull.StartsWith($backupFull + "\", [StringComparison]::OrdinalIgnoreCase)) {
            throw "Backup folder and source folder must not overlap."
        }
        $j++
        $rootRecords += [pscustomobject]@{ Index = $j; Root = $sourceFull }
        $items = Get-ChildItem -LiteralPath $sourceFull -Recurse -File -Force -ErrorAction Stop

        foreach ($item in $items) {
            $extension = [IO.Path]::GetExtension($item.FullName).ToLowerInvariant()
            if ($mediaExt -notcontains $extension) { continue }
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { continue }
            if (-not $seen.Add($item.FullName)) { continue }
            $relative = $item.FullName.Substring($sourceFull.Length).TrimStart([char]'\',[char]'/')
            $files.Add([pscustomobject]@{
                Source = $item.FullName
                Group = ("SOURCE_{0:00}" -f $j)
                Relative = $relative
                Bytes = [long]$item.Length
            })
        }
    }

    $sorted = @($files | Sort-Object Source)
    [long]$total = 0
    foreach ($item in $sorted) { $total += $item.Bytes }

    Write-Output "===== C005 VIDEO AUDIT ====="
    Write-Output ("MODE: " + $Mode.ToUpperInvariant())
    foreach ($r in $rootRecords) { Write-Output ("SOURCE_{0:00}: {1}" -f $r.Index, $r.Root) }
    Write-Output ("VIDEO_COUNT: " + $sorted.Count)
    Write-Output ("VIDEO_BYTES: " + $total)
    Write-Output ("VIDEO_GIB: " + [math]::Round(($total / 1GB), 3))
    Write-Output ("BACKUP_DIR: " + $backupFull)
    foreach ($i in (0..2)) {
        if ($i -ge $sorted.Count) { break }
        Write-Output ("SOURCE_HASH_SAMPLE_{0}: {1}" -f ($i + 1), (Get-Hash $sorted[$i].Source))
    }

    if ($Mode -eq "Audit") {
        if ($sorted.Count -eq 0) {
            Write-Output "C005_NO_MEDIA_FOUND_IN_SCANNED_FOLDERS"
        } else {
            Write-Output "C005_AUDIT_PASS"
        }
        Write-Output "===== C005 REPORT END ====="
        return
    }

    if ($sorted.Count -eq 0) {
        Write-Output "C005_NO_MEDIA_FOUND_IN_SCANNED_FOLDERS"
        Write-Output "===== C005 REPORT END ====="
        return
    }

    $driveRoot = [IO.Path]::GetPathRoot($backupFull)
    $drive = New-Object System.IO.DriveInfo($driveRoot)
    if (-not $drive.IsReady) { throw "Backup volume is not ready." }

    [long]$needed = 0
    foreach ($entry in $sorted) {
        $target = Join-Path (Join-Path $backupFull $entry.Group) $entry.Relative
        if (Test-Path -LiteralPath $target -PathType Leaf) {
            if ((Get-Item -LiteralPath $target).Length -ne $entry.Bytes -or
                (Get-Hash $target) -ne (Get-Hash $entry.Source)) {
                throw ("Existing backup differs: " + $target + ". Refusing overwrite.")
            }
        } else {
            $needed += $entry.Bytes
        }
    }

    $reserve = [long](5GB)
    if ($drive.AvailableFreeSpace -lt ($needed + $reserve)) {
        Write-Output "C005_INSUFFICIENT_SPACE"
        Write-Output ("NEEDED_BYTES: " + $needed)
        Write-Output ("FREE_BYTES: " + $drive.AvailableFreeSpace)
        Write-Output ("RESERVED_BYTES: " + $reserve)
        return
    }

    New-Item -ItemType Directory -Path $backupFull -Force | Out-Null
    $entries = New-Object 'System.Collections.Generic.List[object]'
    $copied = 0
    $matched = 0

    foreach ($entry in $sorted) {
        $target = Join-Path (Join-Path $backupFull $entry.Group) $entry.Relative
        $srcHash = Get-Hash $entry.Source
        if (Test-Path -LiteralPath $target -PathType Leaf) {
            $matched++
        } else {
            $parent = Split-Path -Path $target -Parent
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
            $partial = $target + "." + [guid]::NewGuid().ToString("N") + ".part"
            try {
                Copy-Item -LiteralPath $entry.Source -Destination $partial -ErrorAction Stop
                if ((Get-Item -LiteralPath $partial).Length -ne $entry.Bytes -or
                    (Get-Hash $partial) -ne $srcHash) {
                    throw "Copy checksum mismatch; leaving original unchanged."
                }
                # Refuse destination replacement, even in races.
                if (Test-Path -LiteralPath $target) {
                    throw "Destination appeared during copy; refusing overwrite."
                }
                Move-Item -LiteralPath $partial -Destination $target -ErrorAction Stop
                $copied++
            } finally {
                if (Test-Path -LiteralPath $partial) {
                    Remove-Item -LiteralPath $partial -Force -ErrorAction SilentlyContinue
                }
            }
        }
        if ((Get-Hash $target) -ne $srcHash) {
            throw "Final backup checksum mismatch."
        }
        $entries.Add([pscustomobject]@{
            group = $entry.Group
            relative_path = $entry.Relative
            bytes = $entry.Bytes
            sha256 = $srcHash
        })
    }

    $stamp = (Get-Date).ToString("yyyyMMdd_HHmmss")
    $manifest = Join-Path $backupFull ("C005_manifest_" + $stamp + "_" + [guid]::NewGuid().ToString("N").Substring(0,8) + ".json")
    $data = [ordered]@{
        checklist = "C005"
        status = "PASS"
        created_at = (Get-Date).ToString("s")
        video_count = $sorted.Count
        video_bytes = $total
        copied_count = $copied
        already_matched_count = $matched
        hash_verified_count = $entries.Count
        source_roots = @($rootRecords | ForEach-Object { $_.Root })
        files = @($entries)
        note = "Copy-only backup; source untouched. Separate-device backup still advised."
    }
    $data | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifest -Encoding UTF8

    Write-Output "C005_BACKUP_PASS"
    Write-Output ("COPIED_FILES: " + $copied)
    Write-Output ("ALREADY_MATCHED: " + $matched)
    Write-Output ("HASH_VERIFIED: " + $entries.Count)
    Write-Output ("MANIFEST: " + $manifest)
    Write-Output "===== C005 REPORT END ====="
} catch {
    Write-Output "C005_FAIL"
    Write-Output ("ERROR: " + $_.Exception.Message)
    Write-Output "===== C005 REPORT END ====="
    exit 1
}
