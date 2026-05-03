$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "================================================"
Write-Host "  逐字稿提取工具 . Windows 一键安装"
Write-Host "================================================"
Write-Host ""

$GistRaw = "https://raw.githubusercontent.com/luokundai-sys/zhuzigao/main/whisper_app.py"
$pythonExe = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "[1/4] 安装 Python 3.11（专用版本）..."
    $url = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    $out = "$env:TEMP\python_installer.exe"
    Invoke-WebRequest -Uri $url -OutFile $out
    Start-Process $out -ArgumentList "/quiet InstallAllUsers=0 PrependPath=0 Include_test=0" -Wait
    Remove-Item $out
    if (-not (Test-Path $pythonExe)) {
        Write-Host "[错误] Python 3.11 安装失败"
        pause
        exit 1
    }
} else {
    Write-Host "[1/4] Python 3.11 已安装"
}

$installDir = "$env:USERPROFILE\WhisperApp"
New-Item -ItemType Directory -Force -Path $installDir | Out-Null

if (-not (Test-Path "$installDir\ffmpeg.exe")) {
    Write-Host "[2/4] 下载 ffmpeg（约 80MB）..."
    $ffUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    $ffZip = "$env:TEMP\ffmpeg.zip"
    Invoke-WebRequest -Uri $ffUrl -OutFile $ffZip -UseBasicParsing
    Expand-Archive -Path $ffZip -DestinationPath "$env:TEMP\ffmpeg_tmp" -Force
    Copy-Item "$env:TEMP\ffmpeg_tmp\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe" "$installDir\ffmpeg.exe"
    Copy-Item "$env:TEMP\ffmpeg_tmp\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe" "$installDir\ffprobe.exe"
    Remove-Item $ffZip
    Remove-Item "$env:TEMP\ffmpeg_tmp" -Recurse -Force
} else {
    Write-Host "[2/4] ffmpeg 已存在"
}

Write-Host "[3/4] 安装 Whisper 和 PyTorch..."
& $pythonExe -m pip ins
