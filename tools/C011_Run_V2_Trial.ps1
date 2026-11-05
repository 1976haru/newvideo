param(
    [switch]$NoLaunch
)
$ErrorActionPreference = 'Stop'
$PinnedSourceSha = '10206483d704af57e3c13df2b58b4e1548f66163'
$AppRoot = 'D:\NVS_V2_Trial_App'
$InstallRoot = Join-Path $AppRoot ('C011_Titlebar_' + $PinnedSourceSha.Substring(0, 8))
$Venv = Join-Path $InstallRoot '.venv'
$ZipFile = Join-Path $InstallRoot 'source.zip'
$Extracted = Join-Path $InstallRoot 'source'
$RepoZipUrl = "https://github.com/1976haru/newvideo/archive/$PinnedSourceSha.zip"

if (-not (Test-Path -LiteralPath 'D:\' -PathType Container)) {
    throw 'D drive absent. C011 trial does not change V1 or invent a fallback install location.'
}
foreach ($protected in @(
    'D:\NatureVideoStudio',
    'D:\NVS_Recovery'
)) {
    if ([System.IO.Path]::GetFullPath($InstallRoot).TrimEnd('\') -eq
        [System.IO.Path]::GetFullPath($protected).TrimEnd('\')) {
        throw 'Refusing to install on protected V1 or recovery path.'
    }
}
if (Test-Path -LiteralPath $InstallRoot) {
    throw "Trial directory already exists. Refusing overwrite: $InstallRoot"
}
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'Python launcher py not installed. Existing V1 installation is unchanged.'
}

New-Item -ItemType Directory -Path $InstallRoot -Force:$false | Out-Null
Write-Host 'C011_NEW_V2_TRIAL_FOLDER_CREATED: True'
Write-Host 'C011_DOWNLOADING_PINNED_SOURCE'
Invoke-WebRequest -Uri $RepoZipUrl -OutFile $ZipFile -UseBasicParsing
New-Item -ItemType Directory -Path $Extracted | Out-Null
Expand-Archive -LiteralPath $ZipFile -DestinationPath $Extracted
$Top = Get-ChildItem -LiteralPath $Extracted -Directory
if (@($Top).Count -ne 1) { throw 'Unexpected source archive structure' }
$Src = Join-Path $Top[0].FullName 'src'
if (-not (Test-Path -LiteralPath (Join-Path $Src 'nature_video_studio\trial_gui.py'))) {
    throw 'C011 trial GUI source is absent'
}
Write-Host 'C011_CREATING_ISOLATED_VENV'
& py -3 -m venv $Venv
if ($LASTEXITCODE -ne 0) { throw 'venv initialization failed' }
$Python = Join-Path $Venv 'Scripts\python.exe'
Write-Host 'C011_INSTALLING_PYSIDE6_IN_ISOLATED_VENV'
& $Python -m pip install --disable-pip-version-check 'PySide6>=6.7,<7'
if ($LASTEXITCODE -ne 0) { throw 'Isolated PySide6 install failed' }
$OldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $Src
    Write-Host 'C011_GUI_SMOKE_START'
    & $Python -m nature_video_studio --smoke
    if ($LASTEXITCODE -ne 0) { throw 'C011 GUI smoke failed' }
    if ($NoLaunch) {
        Write-Host 'C011_QT_TITLEBAR_SMOKE_PASS_NO_GUI'
    } else {
        Write-Host 'C011_OPENING_V2_TITLEBAR_WINDOW'
        & $Python -m nature_video_studio
        if ($LASTEXITCODE -ne 0) { throw 'C011 trial GUI failed' }
    }
} finally {
    $env:PYTHONPATH = $OldPythonPath
}
Write-Host 'C011_V1_PROGRAM_AND_DATA_UNMODIFIED_BY_INSTALLER_DESIGN'
Write-Host 'C011_TRIAL_RUN_COMPLETE'
