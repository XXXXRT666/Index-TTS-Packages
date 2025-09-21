$ErrorActionPreference = "Stop"

Write-Host "Current location: $(Get-Location)"

$cuda = $env:TORCH_CUDA
if (-not $cuda) {
    Write-Error "Missing TORCH_CUDA env (cu124 or cu128)"
    exit 1
}

$date = $env:DATE
if ([string]::IsNullOrWhiteSpace($date)) {
    $date = Get-Date -Format "MMdd"
}

$pkgName = "Index-TTS-Packages-$date"
$tmpDir = "tmp"
$srcDir = $PWD

$pkgName = "$pkgName-$cuda-windows-amd64"

$baseHF = "https://huggingface.co/XXXXRT/GPT-SoVITS-Pretrained/resolve/main"
$UVR5_URL = "$baseHF/uvr5_weights.zip"
$NLTK_URL = "$baseHF/nltk_data.zip"

$PYTHON_VERSION = "3.10.17"
$PY_RELEASE_VERSION = "20250521"

Write-Host "[INFO] Cleaning .git..."
Remove-Item "$srcDir\.git" -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "[INFO] Creating tmp dir..."
New-Item -ItemType Directory -Force -Path $tmpDir

Write-Host "[INFO] System Python version:"
python --version
python -m site

Write-Host "[INFO] Downloading Python $PYTHON_VERSION..."
$zst = "$tmpDir\python.tar.zst"
Invoke-WebRequest "https://github.com/astral-sh/python-build-standalone/releases/download/$PY_RELEASE_VERSION/cpython-$PYTHON_VERSION+$PY_RELEASE_VERSION-x86_64-pc-windows-msvc-pgo-full.tar.zst" -OutFile $zst
& "C:\Program Files\7-Zip\7z.exe" e $zst -o"$tmpDir" -aoa
$tar = Get-ChildItem "$tmpDir" -Filter "*.tar" | Select-Object -First 1
& "C:\Program Files\7-Zip\7z.exe" x $tar.FullName -o"$tmpDir\extracted" -aoa
Move-Item "$tmpDir\extracted\python\install" "$srcDir\venv"

Write-Host "[INFO] Copying Redistributing Visual C++ Runtime..."
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$vsPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
$redistRoot = Join-Path $vsPath "VC\Redist\MSVC"
$targetVer = Get-ChildItem -Path $redistRoot -Directory |
    Where-Object { $_.Name -match "^14\." } |
    Sort-Object Name -Descending |
    Select-Object -First 1
$x64Path = Join-Path $targetVer.FullName "x64"
Get-ChildItem -Path $x64Path -Directory | Where-Object {
    $_.Name -match '^Microsoft\..*\.(CRT|OpenMP)$'
} | ForEach-Object {
    Get-ChildItem -Path $_.FullName -Filter "*.dll" | ForEach-Object {
        Copy-Item -Path $_.FullName -Destination "$srcDir\venv" -Force
    }
}

function DownloadAndUnzip($url, $targetRelPath) {
    $filename = Split-Path $url -Leaf
    $tmpZip = "$tmpDir\$filename"
    Invoke-WebRequest $url -OutFile $tmpZip
    Expand-Archive -Path $tmpZip -DestinationPath $tmpDir -Force
    $subdirName = $filename -replace '\.zip$', ''
    $sourcePath = Join-Path $tmpDir $subdirName
    $destRoot = Join-Path $srcDir $targetRelPath
    $destPath = Join-Path $destRoot $subdirName
    if (Test-Path $destPath) {
        Remove-Item $destPath -Recurse -Force
    }
    Move-Item $sourcePath $destRoot
    Remove-Item $tmpZip
}

Write-Host "[INFO] Download UVR5 model..."
DownloadAndUnzip $UVR5_URL "tools\uvr5"

# Write-Host "[INFO] Downloading funasr..."
# $funasrUrl = "https://huggingface.co/XXXXRT/GPT-SoVITS-Pretrained/resolve/main/funasr.zip"
# $funasrZip = "$tmpDir\funasr.zip"
# Invoke-WebRequest -Uri $funasrUrl -OutFile $funasrZip
# Expand-Archive -Path $funasrZip -DestinationPath "$srcDir\tools\asr\models" -Force
# Remove-Item $funasrZip

Write-Host "[INFO] Download ffmpeg..."
$ffUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
$ffZip = "$tmpDir\ffmpeg.zip"
Invoke-WebRequest -Uri $ffUrl -OutFile $ffZip
Expand-Archive $ffZip -DestinationPath $tmpDir -Force
$ffDir = Get-ChildItem -Directory "$tmpDir" | Where-Object { $_.Name -like "ffmpeg*" } | Select-Object -First 1
Move-Item "$($ffDir.FullName)\bin\ffmpeg.exe" "$srcDir\venv"
Move-Item "$($ffDir.FullName)\bin\ffprobe.exe" "$srcDir\venv"
Remove-Item $ffZip
Remove-Item $ffDir.FullName -Recurse -Force

Write-Host "[INFO] Downloading NLTK dictionary..."
$PYTHON = ".\venv\python.exe"
$prefix = & $PYTHON -c "import sys; print(sys.prefix)"
$nltkZip = "$tmpDir\nltk_data.zip"
Invoke-WebRequest -Uri $NLTK_URL -OutFile $nltkZip
Expand-Archive -Path $nltkZip -DestinationPath $prefix -Force
Remove-Item $nltkZip

Write-Host "[INFO] Installing PyTorch..."
& ".\venv\python.exe" -m ensurepip
& ".\venv\python.exe" -m pip install --upgrade pip --no-warn-script-location
switch ($cuda) {
    "cu124" {
        & ".\venv\python.exe" -m pip install torch==2.6 torchaudio --index-url https://download.pytorch.org/whl/cu124 --no-warn-script-location --no-cache-dir
    }
    "cu128" {
        & ".\venv\python.exe" -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128 --no-warn-script-location --no-cache-dir
    }
    default {
        Write-Error "Unsupported CUDA version: $cuda"
        exit 1
    }
}

Write-Host "[INFO] Installing dependencies..."
$repo = $env:GITHUB_REPOSITORY
$apiUrl = "https://api.github.com/repos/$repo/releases/latest"
$headers = @{
  "User-Agent" = "PowerShell"
  "Authorization" = "Bearer $env:GITHUB_TOKEN"
}
Write-Host "$apiUrl"
$release = Invoke-RestMethod -Uri $apiUrl -Headers $headers
Write-Host "$release"
$asset = $release.assets | Where-Object { $_.name -match "pynini-2\.1\.6-cp310-cp310-win_amd64\.whl" } | Select-Object -First 1
if (-not $asset) {
    Write-Error "No Match Whl"
    exit 1
}
$wheelPath = "$tmpDir\$($asset.name)"
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $wheelPath
& ".\venv\python.exe" -m pip install $wheelPath
& ".\venv\python.exe" -m pip show pynini
& ".\venv\python.exe" -m pip install deepspeed --only-binary=:all:
& ".\venv\python.exe" -m pip install -r requirements.txt --no-warn-script-location
& ".\venv\python.exe" -m pip uninstall onnxruntime
& ".\venv\python.exe" -m pip install onnxruntime-gpu

Write-Host "[INFO] Download Models..."
python -m pip install --upgrade pip
python -m pip install "modelscope" "huggingface_hub" --no-warn-script-location
hf download IndexTeam/IndexTTS-1.5 config.yaml bigvgan_discriminator.pth bigvgan_generator.pth bpe.model dvae.pth gpt.pth unigram_12000.vocab --local-dir checkpoints

Write-Host "[INFO] Preparing final directory $pkgName ..."
$items = @(Get-ChildItem -Filter "*.sh") +
         @(Get-ChildItem -Filter "*.ipynb") +
         @("$tmpDir", ".github", "Docker", "docs", ".gitignore", ".dockerignore")
Remove-Item $items -Force -Recurse -ErrorAction SilentlyContinue
$curr = Get-Location
Set-Location ../
Get-ChildItem .
Copy-Item -Path $curr -Destination $pkgName -Recurse
$zipPath = "$pkgName.zip"
$start = Get-Date
Write-Host "Compress Starting at $start"
& "C:\Program Files\7-Zip\7z.exe" a -tzip -mm=Deflate "$zipPath" "$pkgName" -mx=9 -mmt=on -bsp1
$end = Get-Date
Write-Host "Elapsed time: $($end - $start)"
Get-ChildItem .

Write-Host "[INFO] Uploading to ModelScope..."
$msUser = $env:MODELSCOPE_USERNAME
$msToken = $env:MODELSCOPE_TOKEN
if (-not $msUser -or -not $msToken) {
    Write-Error "Missing MODELSCOPE_USERNAME or MODELSCOPE_TOKEN"
    exit 1
}
modelscope upload "$msUser/Index-TTS-Packages" "$zipPath" "$zipPath" --repo-type model --token $msToken

Write-Host "[SUCCESS] Uploaded: $zipPath to ModelScope"