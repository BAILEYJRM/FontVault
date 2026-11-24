# FontVault — Persistent Memory

## Architecture Decisions
- **Stack**: Python 3.13 + PySide6 + fonttools + Pillow + httpx + PyInstaller (no Node/SDK .NET/NSIS/Inno installed in local environment).
- **UI/Core Separation**: `core/` has zero Qt imports; UI uses `QThread` workers for scanning, downloads, backups, and Windows font installation.
- **Lazy Font Loading**: System/User installed fonts use `QFont(item.family)` directly; `QFontDatabase.addApplicationFont` is called lazily only for visible/selected `CUSTOM` and `APPLICATION` cards.
- **Token & Context Hygiene**: `.geminiignore` / `.agentignore` exclude `.venv/`, `build/`, `dist/`, `data/`, `.certs/`, and binaries; `AGENTS.md` delegates to `GEMINI.md` without duplicating text.

## Verified External Endpoints
- `https://api.fontsource.org/v1/fonts?subsets=latin` — Requires non-empty `User-Agent` header (`FontVault/1.0 (Windows NT 10.0; Win64; x64)`), otherwise returns HTTP 403. Do NOT pass `?limit=` (returns HTTP 400).
- `https://api.fontsource.org/v1/fonts/{id}` & `https://cdn.jsdelivr.net/fontsource/fonts/{id}@latest/latin-{weight}-normal.ttf` — Returns valid TrueType binaries (`\x00\x01\x00\x00`).

## Packaging & Signing Notes
- Portable build embeds `bundled_portable.flag` inside PyInstaller `_MEIPASS` so `FontVault-Portable-win64.exe` defaults to `<exe_dir>/data/` anywhere.
- Windows Setup Installer (`FontVault-Setup-win64.exe`) uses a GUI wizard (`setup_wizard.py`) wrapping signed `FontVault.exe`, creating `.lnk` shortcuts + `HKCU` Uninstall entry without requiring Admin UAC.
- Signing uses `Set-AuthenticodeSignature -HashAlgorithm SHA256` with `$env:CERT_PFX_PATH` if provided, or `Cert:\CurrentUser\My` dev cert (`CN=FontVault Developer Code Signing`).

## Current Status
- **Version & Repo**: `v1.2.0` on `https://github.com/BAILEYJRM/FontVault.git` (`master`).
- **Tests**: `.venv\Scripts\pytest.exe -q` -> `14 passed` (`test_metadata_and_scanner.py`, `test_backup_and_portable.py`, `test_catalog_and_installer.py`).
- **Icons**: `assets/icon.png` (9,871 bytes) and `assets/icon.ico` (37,871 bytes, 16–256 px).
- **Signed Artifacts (Authenticode SHA-256, Thumbprint `BBE4F1186A767D4849187F86340BB3C9E9EE6F46`, dev cert in `Cert:\CurrentUser\My`, public `.certs/FontVault-DevCert.cer`)**:
  - `build/payload/FontVault.exe` (58,840,512 bytes)
  - `dist/FontVault-Portable-win64.exe` (58,839,896 bytes / 56.11 MB)
  - `dist/FontVault-Portable-win64.zip` (58,476,889 bytes / 55.77 MB)
  - `dist/FontVault-Setup-win64.exe` (69,054,280 bytes / 65.86 MB)
- Note: Self-signed dev signature reports `Status=UnknownError` in `Get-AuthenticodeSignature` unless user manually trusts `.certs/FontVault-DevCert.cer` or signs with `$env:CERT_PFX_PATH`.
