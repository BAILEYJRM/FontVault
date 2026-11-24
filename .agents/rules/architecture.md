# Reglas de Arquitectura

- **Separación estricta `core/` vs `ui/`**:
  - `src/fontvault/core/`, `models.py` y `config.py` NO deben importar `PySide6` ni depender de Qt; deben ser 100% testeables en modo headless.
  - `src/fontvault/ui/` consume `core/` mediante `QThread`/workers para escaneo, descargas HTTP, backups e instalación en Windows sin bloquear el hilo de interfaz.
- **Carga perezosa de fuentes (`QFontDatabase`)**:
  - Las fuentes ya instaladas en Windows (`INSTALLED_SYSTEM`, `INSTALLED_USER`) se renderizan directamente con `QFont(family)`.
  - Solo llama a `QFontDatabase.addApplicationFont` de forma perezosa cuando una tarjeta `CUSTOM` o `APPLICATION` se vuelve visible o es seleccionada.
- **HTTP y seguridad de archivos**:
  - Usa siempre `User-Agent: FontVault/1.0 (Windows NT 10.0; Win64; x64)` al consultar `api.fontsource.org`.
  - Valida cabeceras mágicas de fuente (`\x00\x01\x00\x00`, `OTTO`, `ttcf`) y bloquea *zip-slip* al extraer archivos `.zip`.
