---
name: build-and-sign
description: >-
  Use this skill when generating Windows icons, building the FontVault portable
  executable or Windows GUI setup installer, or signing binaries with
  Authenticode (dev certificate or production PFX).
---

# Build & Authenticode Signing Workflow

## 1. Regenerate Icon Assets
```powershell
.venv\Scripts\python.exe scripts/generate_assets.py
```
Outputs `assets/icon.png` (256x256) and multi-size `assets/icon.ico` (16–256 px).

## 2. Full Build + Sign Pipeline (Portable + Installer)
```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_all.ps1
```
This runs:
1. `scripts/generate_assets.py`
2. PyInstaller build of `build/payload/FontVault.exe` (installed-mode payload)
3. PyInstaller build of `dist/FontVault-Portable-win64.exe` (embedded `bundled_portable.flag`)
4. `scripts/sign_binaries.ps1` on `FontVault.exe` and `FontVault-Portable-win64.exe`
5. PyInstaller build of `dist/FontVault-Setup-win64.exe` (bundles signed `FontVault.exe`)
6. `scripts/sign_binaries.ps1` on `dist/FontVault-Setup-win64.exe` and verifies `Get-AuthenticodeSignature`.

## 3. Production Signing (Trusted PFX)
Set environment variables before running `scripts/build_all.ps1` or `scripts/sign_binaries.ps1`:
```powershell
$env:CERT_PFX_PATH = "C:\ruta\a\tu_certificado.pfx"
$env:CERT_PASSWORD = "tu_password"
powershell -ExecutionPolicy Bypass -File scripts/sign_binaries.ps1 -Targets @("dist\FontVault-Portable-win64.exe", "dist\FontVault-Setup-win64.exe")
```
Without `CERT_PFX_PATH`, `sign_binaries.ps1` creates/reuses a local dev `CodeSigningCert` in `Cert:\CurrentUser\My` (`CN=FontVault Developer Code Signing`) and exports `.certs/FontVault-DevCert.cer`.
