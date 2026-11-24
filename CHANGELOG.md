# Changelog

Todos los cambios notables en **FontVault** se documentan en este archivo siguiendo [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y [Versionado Semántico](https://semver.org/lang/es/).

## [1.0.0] - 2026-11-24
### Añadido
- Escáner multi-origen de tipografías en Windows: fuentes instaladas (`C:\Windows\Fonts` y usuario `%LOCALAPPDATA%\Microsoft\Windows\Fonts`), bóveda personalizada y fuentes incluidas en aplicaciones (`Program Files`, `%LOCALAPPDATA%\Programs`), con caché incremental.
- Copias de seguridad y exportación a `.zip` o carpeta por categoría (`Instaladas`, `Personalizadas`, `De Aplicación`, `Todas`) con `manifest.json` y hashes SHA-256.
- Importador de `.ttf`, `.otf`, `.ttc` y `.zip` con protección frente a *zip-slip*.
- Catálogo gratuito integrado (Fontsource / Google Fonts) con caché de 24h, respaldo offline, accesos a portales comunes e importación directa desde URL.
- Instalador de fuentes por usuario en Windows (`HKCU` + `AddFontResourceW` + `WM_FONTCHANGE`) sin requerir elevación UAC.
- Tarjetas con miniaturas tipográficas (carga perezosa) y estudio de vista previa de escritura en vivo con escala de tamaños (*waterfall*).
- Empaquetado como versión portable (`FontVault-Portable-win64.exe` / `.zip`) e instalador gráfico de Windows (`FontVault-Setup-win64.exe`) con icono multi-resolución y firma Authenticode SHA-256.
- Reglas de proyecto, archivos ignore para economía de tokens, memoria persistente y suite de pruebas `pytest`.
