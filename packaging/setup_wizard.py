"""Lightweight Windows GUI Installer Wizard for FontVault."""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import tkinter as tk
import winreg
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


APP_NAME = "FontVault"
APP_VERSION = "1.1.0"
PUBLISHER = "FontVault Project"
UNINSTALL_REG_PATH = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_NAME}"


def _resource_path(rel_path: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / rel_path


def _default_install_dir() -> Path:
    local_appdata = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return local_appdata / "Programs" / APP_NAME


def _create_shortcut(lnk_path: Path, target_exe: Path, icon_path: Path, description: str) -> None:
    lnk_path.parent.mkdir(parents=True, exist_ok=True)
    ps_script = (
        "$ws = New-Object -ComObject WScript.Shell; "
        f"$s = $ws.CreateShortcut('{str(lnk_path).replace(chr(39), chr(39)*2)}'); "
        f"$s.TargetPath = '{str(target_exe).replace(chr(39), chr(39)*2)}'; "
        f"$s.WorkingDirectory = '{str(target_exe.parent).replace(chr(39), chr(39)*2)}'; "
        f"$s.IconLocation = '{str(icon_path).replace(chr(39), chr(39)*2)}'; "
        f"$s.Description = '{description}'; "
        "$s.Save()"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
        check=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def _write_uninstall_script(install_dir: Path, desktop_lnk: Path, startmenu_dir: Path) -> Path:
    uninstall_ps1 = install_dir / "Uninstall-FontVault.ps1"
    script = f"""$ErrorActionPreference = 'SilentlyContinue'
Add-Type -AssemblyName System.Windows.Forms
$res = [System.Windows.Forms.MessageBox]::Show(
    '¿Deseas desinstalar FontVault de este equipo? (Tus copias de seguridad en AppData se conservarán salvo que las borres manualmente)',
    'Desinstalar FontVault',
    [System.Windows.Forms.MessageBoxButtons]::YesNo,
    [System.Windows.Forms.MessageBoxIcon]::Question
)
if ($res -ne [System.Windows.Forms.DialogResult]::Yes) {{ exit 0 }}
Stop-Process -Name 'FontVault' -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath '{desktop_lnk}' -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath '{startmenu_dir}' -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path 'HKCU:\\{UNINSTALL_REG_PATH}' -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 400
Start-Process cmd.exe -ArgumentList '/c timeout /t 2 >nul & rmdir /s /q "{install_dir}"' -WindowStyle Hidden
"""
    uninstall_ps1.write_text(script, encoding="utf-8")
    return uninstall_ps1


def _register_uninstaller(install_dir: Path, exe_path: Path, uninstall_ps1: Path) -> None:
    uninstall_cmd = (
        f'powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{uninstall_ps1}"'
    )
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, UNINSTALL_REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, f"{APP_NAME} — Gestor de Tipografías")
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, PUBLISHER)
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(exe_path))
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(install_dir))
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, uninstall_cmd)
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)


class InstallerWizard(tk.Tk):
    """GUI installer window for FontVault."""

    def __init__(self) -> None:
        super().__init__()
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FontVault.Installer.1")
        except Exception:
            pass

        self.title(f"Instalador de {APP_NAME} v{APP_VERSION}")
        self.geometry("560x390")
        self.resizable(False, False)
        self.configure(bg="#0F172A")

        icon_ico = _resource_path("assets/icon.ico")
        if icon_ico.exists():
            try:
                self.iconbitmap(str(icon_ico))
            except Exception:
                pass

        self.install_dir_var = tk.StringVar(value=str(_default_install_dir()))
        self.desktop_var = tk.BooleanVar(value=True)
        self.startmenu_var = tk.BooleanVar(value=True)
        self.launch_var = tk.BooleanVar(value=True)

        self._build_ui()

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#0F172A")
        style.configure("TLabel", background="#0F172A", foreground="#E2E8F0", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), foreground="#F8FAFC")
        style.configure("Sub.TLabel", font=("Segoe UI", 9), foreground="#94A3B8")
        style.configure("TCheckbutton", background="#0F172A", foreground="#E2E8F0", font=("Segoe UI", 10))

        container = ttk.Frame(self, padding=24)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(container, text=f"Instalar {APP_NAME} v{APP_VERSION}", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            container,
            text="Gestor de tipografías para Windows con copia de seguridad, catálogo gratuito y vista previa en vivo.",
            style="Sub.TLabel",
            wraplength=500,
        ).pack(anchor="w", pady=(4, 18))

        ttk.Label(container, text="Carpeta de instalación:").pack(anchor="w")
        path_row = ttk.Frame(container)
        path_row.pack(fill=tk.X, pady=(6, 14))

        entry = tk.Entry(
            path_row,
            textvariable=self.install_dir_var,
            bg="#1E293B",
            fg="#F8FAFC",
            insertbackground="#F8FAFC",
            relief="flat",
            font=("Segoe UI", 10),
        )
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 8))

        browse_btn = tk.Button(
            path_row,
            text="Examinar...",
            command=self._browse_dir,
            bg="#334155",
            fg="#F8FAFC",
            relief="flat",
            padx=12,
            pady=5,
        )
        browse_btn.pack(side=tk.RIGHT)

        ttk.Checkbutton(
            container,
            text="Crear acceso directo en el Escritorio",
            variable=self.desktop_var,
        ).pack(anchor="w", pady=3)

        ttk.Checkbutton(
            container,
            text="Crear acceso directo en el Menú Inicio",
            variable=self.startmenu_var,
        ).pack(anchor="w", pady=3)

        ttk.Checkbutton(
            container,
            text="Abrir FontVault al finalizar la instalación",
            variable=self.launch_var,
        ).pack(anchor="w", pady=(3, 18))

        self.progress = ttk.Progressbar(container, mode="determinate", maximum=100)
        self.progress.pack(fill=tk.X, pady=(0, 8))

        self.status_lbl = ttk.Label(container, text="Listo para instalar.", style="Sub.TLabel")
        self.status_lbl.pack(anchor="w")

        btn_row = ttk.Frame(container)
        btn_row.pack(fill=tk.X, side=tk.BOTTOM, pady=(12, 0))

        cancel_btn = tk.Button(
            btn_row,
            text="Cancelar",
            command=self.destroy,
            bg="#1E293B",
            fg="#CBD5E1",
            relief="flat",
            padx=16,
            pady=7,
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(8, 0))

        self.install_btn = tk.Button(
            btn_row,
            text="Instalar ahora",
            command=self._run_install,
            bg="#4F46E5",
            fg="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=18,
            pady=7,
        )
        self.install_btn.pack(side=tk.RIGHT)

    def _browse_dir(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self.install_dir_var.get())
        if chosen:
            self.install_dir_var.set(str(Path(chosen) / APP_NAME))

    def _run_install(self) -> None:
        self.install_btn.config(state=tk.DISABLED)
        try:
            install_dir = Path(self.install_dir_var.get()).resolve()
            install_dir.mkdir(parents=True, exist_ok=True)
            self.progress["value"] = 20
            self.status_lbl.config(text="Copiando ejecutable y recursos...")
            self.update_idletasks()

            payload_exe = _resource_path("payload/FontVault.exe")
            if not payload_exe.exists():
                raise FileNotFoundError(f"No se encontró el binario empaquetado: {payload_exe}")

            target_exe = install_dir / "FontVault.exe"
            shutil.copy2(payload_exe, target_exe)

            icon_src = _resource_path("assets/icon.ico")
            target_icon = install_dir / "FontVault.ico"
            if icon_src.exists():
                shutil.copy2(icon_src, target_icon)

            self.progress["value"] = 55
            self.status_lbl.config(text="Creando accesos directos...")
            self.update_idletasks()

            desktop_lnk = Path.home() / "Desktop" / f"{APP_NAME}.lnk"
            appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
            startmenu_dir = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / APP_NAME
            startmenu_lnk = startmenu_dir / f"{APP_NAME}.lnk"

            icon_ref = target_icon if target_icon.exists() else target_exe
            if self.desktop_var.get():
                _create_shortcut(desktop_lnk, target_exe, icon_ref, "Gestor de tipografías para Windows")
            if self.startmenu_var.get():
                _create_shortcut(startmenu_lnk, target_exe, icon_ref, "Gestor de tipografías para Windows")

            self.progress["value"] = 85
            self.status_lbl.config(text="Registrando desinstalador en Windows...")
            self.update_idletasks()

            uninstall_ps1 = _write_uninstall_script(install_dir, desktop_lnk, startmenu_dir)
            _register_uninstaller(install_dir, target_exe, uninstall_ps1)

            self.progress["value"] = 100
            self.status_lbl.config(text="Instalación completada con éxito.")
            self.update_idletasks()

            if self.launch_var.get():
                subprocess.Popen([str(target_exe)], cwd=str(install_dir))

            messagebox.showinfo(
                "Instalación completada",
                f"{APP_NAME} se ha instalado correctamente en:\n{install_dir}",
            )
            self.destroy()
        except Exception as exc:
            self.install_btn.config(state=tk.NORMAL)
            messagebox.showerror("Error de instalación", str(exc))


def main() -> int:
    wizard = InstallerWizard()
    wizard.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
