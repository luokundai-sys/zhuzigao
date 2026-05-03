# 逐字稿提取 - Windows 一键安装脚本（PowerShell）
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "================================================"
Write-Host "  逐字稿提取工具 . Windows 一键安装"
Write-Host "================================================"
Write-Host ""

$GistRaw = "https://raw.githubusercontent.com/luokundai-sys/zhuzigao/main/whisper_app.py"

# 1. 检测 Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[1/4] 下载并安装 Python 3.11..."
    $url = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    $out = "$env:TEMP\python_installer.exe"
    Invoke-WebRequest -Uri $url -OutFile $out
    Start-Process $out -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0" -Wait
    Remove-Item $out
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","User") + ";" + [System.Environment]::GetEnvironmentVariable("Path","Machine")
} else {
    Write-Host "[1/4] Python 已安装"
}

# 2. 下载 ffmpeg
$installDir = "$env:USERPROFILE\逐字稿提取"
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

# 3. 安装 Whisper + PyTorch（自动选 CUDA / CPU）
Write-Host "[3/4] 安装 Whisper 和 PyTorch..."
python -m pip install --upgrade pip --quiet
python -m pip install openai-whisper --quiet

# 卸载可能存在的旧版 torch
python -m pip uninstall torch -y 2>$null | Out-Null

Write-Host "    检测显卡..."
$hasNvidia = $false
try {
    $hasNvidia = (Get-CimInstance Win32_VideoController | Where-Object {$_.Name -like "*NVIDIA*"}) -ne $null
} catch {}

if ($hasNvidia) {
    Write-Host "    检测到 Nvidia 显卡，安装 CUDA 版 PyTorch（约 2.5GB，需要 5-15 分钟）..."
    python -m pip install torch --index-url https://download.pytorch.org/whl/cu121 --quiet
} else {
    Write-Host "    未检测到 Nvidia 显卡，安装 CPU 版 PyTorch（约 200MB）..."
    python -m pip install torch --quiet
}

# 4. 下载主程序
Write-Host "[4/4] 下载主程序..."
Invoke-WebRequest -Uri $GistRaw -OutFile "$installDir\whisper_app.py"

# 创建桌面快捷方式（带错误保留）
$desktop = [Environment]::GetFolderPath("Desktop")
$bat = "$desktop\逐字稿提取.bat"
@"
@echo off
chcp 65001 >nul
set PATH=%USERPROFILE%\逐字稿提取;%PATH%
python "%USERPROFILE%\逐字稿提取\whisper_app.py"
if %errorlevel% neq 0 (
    echo.
    echo [错误] 程序运行失败，错误代码：%errorlevel%
    pause
)
"@ | Out-File -FilePath $bat -Encoding ASCII

Write-Host ""
Write-Host "================================================"
Write-Host "          安装完成！"
Write-Host "================================================"
Write-Host ""
Write-Host "  双击桌面上的「逐字稿提取.bat」即可使用"
Write-Host ""
Write-Host "  验证 N 卡是否启用，可在 cmd 里运行："
Write-Host "  python -c `"import torch; print('CUDA:', torch.cuda.is_available())`""
Write-Host ""
pause
