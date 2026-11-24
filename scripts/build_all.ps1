$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

$PythonExe = Join-Path $RootDir ".venv\Scripts\python.exe"
$PyInstallerExe = Join-Path $RootDir ".venv\Scripts\pyinstaller.exe"

if (-not (Test-Path $PythonExe)) {
    throw "Virtual environment not found at $PythonExe"
}

Write-Host "=== 1. Generating icon assets ==="
& $PythonExe (Join-Path $RootDir "scripts\generate_assets.py")
if ($LASTEXITCODE -ne 0) { throw "generate_assets.py failed" }

$PayloadDir = Join-Path $RootDir "build\payload"
$WorkDir = Join-Path $RootDir "build\pyinstaller"
$DistDir = Join-Path $RootDir "dist"
New-Item -ItemType Directory -Force -Path $PayloadDir, $WorkDir, $DistDir | Out-Null

Write-Host "=== 2. Building installed payload FontVault.exe ==="
& $PyInstallerExe --noconfirm --clean `
    --distpath $PayloadDir `
    --workpath (Join-Path $WorkDir "app") `
    (Join-Path $RootDir "packaging\app.spec")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller app.spec failed" }

Write-Host "=== 3. Signing payload FontVault.exe ==="
& (Join-Path $RootDir "scripts\sign_binaries.ps1") -Targets @("build\payload\FontVault.exe")

Write-Host "=== 4. Building Portable FontVault-Portable-win64.exe ==="
& $PyInstallerExe --noconfirm --clean `
    --distpath $DistDir `
    --workpath (Join-Path $WorkDir "portable") `
    (Join-Path $RootDir "packaging\portable.spec")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller portable.spec failed" }

Write-Host "=== 5. Building Windows GUI Installer FontVault-Setup-win64.exe ==="
& $PyInstallerExe --noconfirm --clean `
    --distpath $DistDir `
    --workpath (Join-Path $WorkDir "installer") `
    (Join-Path $RootDir "packaging\installer.spec")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller installer.spec failed" }

Write-Host "=== 6. Signing Portable & Setup EXEs ==="
& (Join-Path $RootDir "scripts\sign_binaries.ps1") -Targets @("dist\FontVault-Portable-win64.exe", "dist\FontVault-Setup-win64.exe")

Write-Host "=== 7. Packaging Portable ZIP bundle ==="
$PortableStage = Join-Path $RootDir "build\portable_zip_stage"
if (Test-Path $PortableStage) { Remove-Item -Recurse -Force $PortableStage }
New-Item -ItemType Directory -Force -Path $PortableStage | Out-Null
Copy-Item (Join-Path $DistDir "FontVault-Portable-win64.exe") (Join-Path $PortableStage "FontVault-Portable-win64.exe")
"portable=1" | Out-File -FilePath (Join-Path $PortableStage "portable.flag") -Encoding ascii
$PortableZip = Join-Path $DistDir "FontVault-Portable-win64.zip"
if (Test-Path $PortableZip) { Remove-Item -Force $PortableZip }
Compress-Archive -Path (Join-Path $PortableStage "*") -DestinationPath $PortableZip -CompressionLevel Optimal

Write-Host "=== BUILD SUMMARY ==="
foreach ($Artifact in @("assets\icon.ico", "dist\FontVault-Portable-win64.exe", "dist\FontVault-Portable-win64.zip", "dist\FontVault-Setup-win64.exe")) {
    $Item = Get-Item (Join-Path $RootDir $Artifact)
    Write-Host ("{0} -> {1:N2} MB" -f $Artifact, ($Item.Length / 1MB))
}
