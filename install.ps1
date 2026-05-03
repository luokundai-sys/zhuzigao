$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "================================================"
Write-Host "  逐字稿提取工具 . Windows 一键安装"
Write-Host "================================================"
Write-Host ""

$GistRaw   = "https://raw.githubusercontent.com/luokundai-sys/zhuzigao/main/whisper_app.py"
$pythonExe = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
$installDir = "$env:USERPROFILE\WhisperApp"

# 1. 安装 Python 3.11
if (-not (Test-Path $pythonExe)) {
    Write-Host "[1/4] 安装 Python 3.11..."
    $url = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    $out = "$env:TEMP\python_installer.exe"
    Invoke-WebRequest -Uri $url -OutFile $out
    Start-Process $out -ArgumentList "/quiet InstallAllUsers=0 PrependPath=0 Include_test=0" -Wait
    Remove-Item $out
    if (-not (Test-Path $pythonExe)) {
        Write-Host "[错误] Python 3.11 安装失败，请重启电脑后重试"
        pause
        exit 1
    }
} else {
    Write-Host "[1/4] Python 3.11 已安装"
}

# 2. 准备目录 + 下载 ffmpeg
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

# 3. 安装 Whisper + PyTorch（智能选 CUDA / CPU）
Write-Host "[3/4] 安装 Whisper 和 PyTorch（首次约 5-15 分钟）..."

$hasNvidia = $false
try {
    $hasNvidia = (Get-CimInstance Win32_VideoController | Where-Object {$_.Name -like "*NVIDIA*"}) -ne $null
} catch {}

if ($hasNvidia) {
    Write-Host "    检测到 Nvidia 显卡，安装 CUDA 版 PyTorch..."
    & $pythonExe -m pip install torch openai-whisper --index-url https://download.pytorch.org/whl/cu121 --extra-index-url https://pypi.org/simple
} else {
    Write-Host "    未检测到 Nvidia 显卡，安装 CPU 版 PyTorch..."
    & $pythonExe -m pip install torch openai-whisper
}

# 4. 下载主程序
Write-Host "[4/4] 下载主程序..."
Invoke-WebRequest -Uri $GistRaw -OutFile "$installDir\whisper_app.py"

# 创建桌面快捷方式
$desktop = [Environment]::GetFolderPath("Desktop")
$bat = "$desktop\WhisperTranscript.bat"
@"
@echo off
chcp 65001 >nul
set PATH=%USERPROFILE%\WhisperApp;%PATH%
"%LOCALAPPDATA%\Programs\Python\Python311\python.exe" "%USERPROFILE%\WhisperApp\whisper_app.py"
if %errorlevel% neq 0 (
    echo.
    echo [Error] Code: %errorlevel%
    pause
)
"@ | Out-File -FilePath $bat -Encoding ASCII

Write-Host ""
Write-Host "================================================"
Write-Host "          安装完成！"
Write-Host "================================================"
Write-Host ""
Write-Host "  双击桌面「WhisperTranscript.bat」即可使用"
Write-Host ""
pause
