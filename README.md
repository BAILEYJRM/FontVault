# FontVault — Gestor de Tipografías para Windows

Aplicación de escritorio en Python (`PySide6` + `fonttools` + `Pillow` + `httpx`) para gestionar, respaldar, previsualizar e instalar tipografías en Windows.

## Características
- **Biblioteca unificada por origen**:
  - **Instaladas en Windows**: Sistema (`C:\Windows\Fonts`) y Usuario (`%LOCALAPPDATA%\Microsoft\Windows\Fonts`).
  - **Personalizadas (Bóveda)**: Importa `.ttf`, `.otf`, `.ttc` o paquetes `.zip` y añade carpetas personalizadas.
  - **De Aplicación**: Descubre fuentes incluidas dentro de aplicaciones instaladas (`Program Files`, `%LOCALAPPDATA%\Programs` o carpetas añadidas).
- **Salvar / Copias de seguridad**: Exporta cualquier categoría o fuente individual a `.zip` o carpeta con `manifest.json` y hashes SHA-256.
- **Descarga gratuita e instalación directa**: Catálogo integrado (Fontsource / Google Fonts con caché local), accesos directos a portales comunes (Google Fonts, Font Squirrel, DaFont, 1001 Fonts, Velvetyne) e importación directa desde URL `.zip`/`.ttf`/`.otf`. Instalación por usuario sin requerir UAC.
- **Miniaturas y vista previa de escritura en vivo**: Tarjetas renderizadas en su propia tipografía (carga perezosa) y estudio de escritura en tiempo real con escala de tamaños (*waterfall*) y sincronización opcional con todas las miniaturas.
- **Edición Portable e Instalador de Windows firmado**: Ambos ejecutables incluyen icono multi-resolución (`assets/icon.ico`) y firma digital Authenticode SHA-256.

## Desarrollo rápido
```powershell
.venv\Scripts\python.exe -m fontvault
.venv\Scripts\python.exe -m fontvault --portable
.venv\Scripts\pytest.exe -q
```

## Compilar y firmar (Portable + Instalador)
```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_all.ps1
```
Artefactos generados en `dist/`:
- `dist/FontVault-Setup-win64.exe` — Instalador gráfico de Windows firmado con icono y desinstalador en `HKCU`.
- `dist/FontVault-Portable-win64.exe` y `dist/FontVault-Portable-win64.zip` — Versión portable firmada (guarda datos en `./data/`).

Para firma de producción con tu certificado comercial `.pfx`:
```powershell
$env:CERT_PFX_PATH = "C:\ruta\certificado.pfx"
$env:CERT_PASSWORD = "tu_password"
powershell -ExecutionPolicy Bypass -File scripts/build_all.ps1
```
