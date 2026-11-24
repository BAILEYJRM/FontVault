# Reglas del Proyecto — FontVault

## Idioma y Estilo
- Responde al usuario siempre en **español**.
- Identificadores de código, nombres de clases/funciones y docstrings en **inglés**; textos visibles en la UI, mensajes de estado y README en **español**.

## Entorno Python (Estricto)
- **NUNCA** ejecutes `pip install` global. Usa siempre `.venv\Scripts\python.exe` y `.venv\Scripts\pip.exe`.
- Ejecuta pruebas con `.venv\Scripts\pytest.exe -q`.

## Economía de Tokens y Memoria
- Antes de explorar o buscar archivos, lee `docs/CONTEXT.md` (mapa compacto del proyecto) y `docs/MEMORY.md` (decisiones y estado).
- **NUNCA** hagas grep/búsquedas ni leas archivos dentro de `.venv/`, `dist/`, `build/`, `data/`, `.certs/` ni binarios (`.exe`, `.ttf`, `.otf`, `.ico`).
- Lee únicamente los rangos de líneas necesarios (`StartLine`/`EndLine`); agrupa llamadas independientes en paralelo.
- Para empaquetar/firmar consulta `.agents/skills/build-and-sign/SKILL.md`; para actualizar memoria al cerrar un hito usa `.agents/skills/context-hygiene/SKILL.md`.

## Seguridad en Windows
- La instalación de fuentes por defecto es **por usuario** (`%LOCALAPPDATA%\Microsoft\Windows\Fonts` + `HKCU`) para no requerir elevación UAC.
- **NUNCA** elimines fuentes del sistema (`C:\Windows\Fonts`) sin confirmación explícita del usuario.
- **NUNCA** instales certificados autofirmados en almacenes raíz (`Root`) de Windows silenciosamente; firma usando `Cert:\CurrentUser\My` o el `.pfx` configurado por el usuario.

## Git, Versionado y Changelog
- Trabaja siempre sobre la rama `master` vinculada a `origin`.
- Después de cada cambio o funcionalidad completada:
  1. Actualiza la versión SemVer en `src/fontvault/__init__.py`, `pyproject.toml`, `packaging/version_info.txt`, `packaging/setup_wizard.py` y `packaging/installer.iss`.
  2. Añade una entrada en `CHANGELOG.md` bajo la nueva versión y fecha.
  3. Ejecuta `.venv\Scripts\pytest.exe -q` para confirmar que todas las pruebas pasan.
  4. Realiza `git commit` descriptivo y `git push origin master`.
