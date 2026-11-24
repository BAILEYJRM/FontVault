# Changelog

Todos los cambios notables en **FontVault** se documentan en este archivo siguiendo [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y [Versionado Semántico](https://semver.org/lang/es/).

## [1.4.0] - 2026-11-24
### Añadido
- Casillas de verificación en todas las tarjetas de biblioteca y catálogo online con barra de acciones en lote (`Seleccionar visibles`, `Limpiar` y contador de selección).
- Operaciones en masa en biblioteca (`BatchLibraryWorker`): **Instalar seleccionadas**, **Salvar seleccionadas (.zip)** y **Eliminar seleccionadas** (con liberación previa de `QFontDatabase`, confirmación explícita y protección automática frente al borrado de fuentes del sistema y de aplicaciones).
- Operaciones en masa en el catálogo gratuito (`BatchCatalogDownloadWorker`): **Descargar seleccionadas** y **Descargar e Instalar seleccionadas**.

## [1.3.0] - 2026-11-24
### Corregido
- Solucionado cierre repentino de la aplicación provocado por la destrucción prematura de hilos `QThread` en curso (`_active_workers` + eliminación segura mediante `deleteLater()`), secuencia monotónica para descartar vistas previas obsoletas y *debounce* en búsquedas y guardado de ajustes.

### Añadido
- Sistema completo de logs rotativos en `logs/fontvault.log` (2 MB x 3 archivos), trazas nativas de fallos (`faulthandler` en `logs/crash_faulthandler.log`), captura de excepciones no controladas (`sys.excepthook`, `threading.excepthook`) y mensajes internos de Qt (`qInstallMessageHandler`).
- Botón `Abrir carpeta de logs` en la barra lateral para inspeccionar diagnósticos fácilmente en modo Portable e Instalado.

## [1.2.0] - 2026-11-24
### Añadido
- Botón de cambio **Modo oscuro / Modo claro** en la barra lateral (`MainWindow.toggle_theme`) con persistencia automática en `settings.json`.
- Hoja de estilos `LIGHT_STYLESHEET` y selector `get_stylesheet(theme)` en `src/fontvault/ui/theme.py` unificando todos los componentes mediante `objectName` (tarjetas, muestras tipográficas, catálogo online, panel de vista previa y barras de desplazamiento).

## [1.1.0] - 2026-11-24
### Añadido
- Vista previa de tipografías descargables antes de instalarlas: botón `Vista previa` y clic directo sobre tarjetas del catálogo online para probarlas en el estudio de escritura en vivo (`LivePreviewPanel`) con escala *waterfall*.
- Miniaturas tipográficas precargadas en segundo plano (`ThumbnailPrefetchWorker`) y caché local de muestras en `cache/previews/` con sincronización opcional de texto en vivo.
- Instalación directa desde una vista previa online copiando automáticamente la fuente a la bóveda personalizada.

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
