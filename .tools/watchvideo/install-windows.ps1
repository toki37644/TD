$ErrorActionPreference = "Stop"
$source = $PSScriptRoot
$destination = Join-Path $env:LOCALAPPDATA "Programs/watchvideo"
$ffmpeg = Join-Path $destination "ffmpeg"
$ffmpegSource = @(Get-ChildItem -LiteralPath (Join-Path $source "vendor/ffmpeg") -Filter "ffmpeg.exe" -Recurse -File)
if ($ffmpegSource.Count -ne 1) { throw "Expected one verified FFmpeg build" }
$ffmpegSource = $ffmpegSource[0].Directory.FullName
$python = (Get-Command python.exe -ErrorAction Stop).Source
$wheels = Join-Path $source "vendor/wheels"
$magick = Join-Path $source "vendor/imagemagick"

foreach ($name in @("ffmpeg.exe", "ffprobe.exe")) {
    if (-not (Test-Path -LiteralPath (Join-Path $ffmpegSource $name))) {
        throw "Executable not found in the verified build: $name"
    }
}
$null = New-Item -ItemType Directory -Path $destination -Force
$null = New-Item -ItemType Directory -Path $ffmpeg -Force
foreach ($name in @("ffmpeg.exe","ffprobe.exe")) {
    Copy-Item -LiteralPath (Join-Path $ffmpegSource $name) -Destination $ffmpeg
}
$ffmpegLicense = Join-Path (Split-Path $ffmpegSource -Parent) "LICENSE"
if (Test-Path -LiteralPath $ffmpegLicense) {
    Copy-Item -LiteralPath $ffmpegLicense -Destination $ffmpeg
}
foreach ($name in @("watchvideo.py", "ppocr_rec.py", "README.md", "LICENSE")) {
    Copy-Item -LiteralPath (Join-Path $source $name) -Destination (Join-Path $destination $name)
}
$magickDestination = Join-Path $destination "imagemagick"
$null = New-Item -ItemType Directory -Path $magickDestination -Force
Get-ChildItem -LiteralPath $magick | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $magickDestination -Recurse
}

$environment = Join-Path $destination "venv"
$interpreter = Join-Path $environment "Scripts/python.exe"
if (-not (Test-Path -LiteralPath $interpreter)) {
    & $python -m venv $environment
    if ($LASTEXITCODE -ne 0) { throw "Virtual environment creation failed" }
}
& $interpreter -m pip install --no-index --find-links $wheels --disable-pip-version-check yt-dlp
if ($LASTEXITCODE -ne 0) { throw "yt-dlp installation failed" }

$entry = Join-Path $destination "watchvideo.cmd"
$launcher = @"
@echo off
setlocal
set "PYTHONUTF8=1"
set "PATH=%~dp0venv\Scripts;%~dp0imagemagick;%~dp0ffmpeg;%PATH%"
"%~dp0venv\Scripts\python.exe" "%~dp0watchvideo.py" %*
exit /b %errorlevel%
"@
Set-Content -LiteralPath $entry -Value $launcher -Encoding ascii

$testDirectory = Join-Path $source "smoke-test"
$null = New-Item -ItemType Directory -Path $testDirectory -Force
$testVideo = Join-Path (Split-Path (Split-Path $source -Parent) -Parent) "音乐星球Demo/金星·节拍演示.webm"
& $entry $testVideo -F 4 -o $testDirectory
if ($LASTEXITCODE -ne 0) { throw "Contact sheet test failed" }
& $entry $testVideo -z 0:01 -o $testDirectory
if ($LASTEXITCODE -ne 0) { throw "Frame zoom test failed" }
$outputs = Get-ChildItem -LiteralPath $testDirectory -Filter "*.jpg"
if (-not ($outputs.Name -match "\.sheet") -or -not ($outputs.Name -match "\.zoom-")) {
    throw "Smoke test did not produce the expected JPG outputs"
}
$subtitleFile = Join-Path $testDirectory "字幕验证.srt"
$subtitleVideo = Join-Path $testDirectory "字幕验证.mkv"
Set-Content -LiteralPath $subtitleFile -Encoding utf8 -Value @(
    "1","00:00:00,500 --> 00:00:02,200","字幕提取验证",""
)
& (Join-Path $ffmpeg "ffmpeg.exe") -loglevel error -y -i $testVideo -i $subtitleFile -map 0:v:0 -map 1:s:0 -c:v copy -c:s srt $subtitleVideo
if ($LASTEXITCODE -ne 0) { throw "Subtitle test clip could not be created" }
& $entry $subtitleVideo --no-frames -o $testDirectory
if ($LASTEXITCODE -ne 0) { throw "Embedded subtitle test failed" }
$subtitleText = Get-Content -Encoding utf8 -LiteralPath (Join-Path $testDirectory "字幕验证.track-1.und.txt")
if ($subtitleText -notmatch "字幕提取验证") { throw "Incorrect subtitle text" }

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$segment = $userPath -split ";" | Where-Object { $_.TrimEnd("\") -eq $destination }
if (-not $segment) {
    $updated = if ($userPath) { $userPath.TrimEnd(";") + ";" + $destination } else { $destination }
    [Environment]::SetEnvironmentVariable("Path",$updated,"User")
}
$env:Path = "$destination;$env:Path"
Get-Command watchvideo | Select-Object Name,Source
$outputs | Select-Object Name,Length
"PASS source dependencies, contact sheet, timed zoom, embedded subtitles, user PATH"
