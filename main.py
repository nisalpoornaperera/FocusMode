import os
import sys
import shutil
import ctypes
import subprocess
import threading
import winreg
import webview
from src.api import Api

APP_NAME = "FocusMode"
APP_DISPLAY_NAME = "Focus Mode"
APP_VERSION = "1.0.0"
APP_PUBLISHER = "FocusMode"
INSTALL_DIR = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), APP_NAME)
INSTALLED_EXE = os.path.join(INSTALL_DIR, f"{APP_NAME}.exe")
UNINSTALL_REG_KEY = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{APP_NAME}"
CREATE_NO_WINDOW = 0x08000000


def get_base_path():
    """Return base path - handles both source and PyInstaller frozen exe."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def run_as_admin(args=""):
    if getattr(sys, "frozen", False):
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, args, None, 1
        )
    else:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
    sys.exit(0)


def is_installed():
    """Check if the app is already installed to Program Files."""
    return os.path.isfile(INSTALLED_EXE)


def running_from_install_dir():
    """Check if the current exe is running from the install directory."""
    if not getattr(sys, "frozen", False):
        return False
    return os.path.normcase(os.path.dirname(sys.executable)) == os.path.normcase(INSTALL_DIR)


def install_app():
    """Install the app to Program Files, register in Windows, create shortcuts, set auto-start."""
    if not getattr(sys, "frozen", False):
        return

    current_exe = sys.executable

    # Copy exe to Program Files
    os.makedirs(INSTALL_DIR, exist_ok=True)
    # Copy icon to install dir too
    icon_src = os.path.join(sys._MEIPASS, "assets", "icon.ico")
    icon_dst = os.path.join(INSTALL_DIR, "icon.ico")
    try:
        shutil.copy2(current_exe, INSTALLED_EXE)
        if os.path.isfile(icon_src):
            shutil.copy2(icon_src, icon_dst)
    except shutil.SameFileError:
        pass

    # Register in Programs and Features (Add/Remove Programs)
    register_uninstall()

    # Create desktop and Start Menu shortcuts
    create_shortcuts()

    # Set up auto-start via Task Scheduler
    add_to_startup()


def register_uninstall():
    """Add registry entries so the app appears in Programs and Features."""
    try:
        exe_size_kb = os.path.getsize(INSTALLED_EXE) // 1024
    except OSError:
        exe_size_kb = 0

    from datetime import datetime
    install_date = datetime.now().strftime("%Y%m%d")
    icon_path = os.path.join(INSTALL_DIR, "icon.ico")

    try:
        key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, UNINSTALL_REG_KEY, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_DISPLAY_NAME)
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, APP_PUBLISHER)
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, INSTALL_DIR)
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, icon_path)
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{INSTALLED_EXE}" --uninstall')
        winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, exe_size_kb)
        winreg.SetValueEx(key, "InstallDate", 0, winreg.REG_SZ, install_date)
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
    except Exception:
        pass


def create_shortcuts():
    """Create desktop shortcut and Start Menu entry."""
    try:
        import win32com.client
        icon_path = os.path.join(INSTALL_DIR, "icon.ico")
        shell = win32com.client.Dispatch("WScript.Shell")

        # Desktop shortcut
        desktop = shell.SpecialFolders("Desktop")
        lnk = shell.CreateShortCut(os.path.join(desktop, "FocusMode.lnk"))
        lnk.TargetPath = INSTALLED_EXE
        lnk.WorkingDirectory = INSTALL_DIR
        lnk.IconLocation = icon_path
        lnk.Description = "Focus Mode - Screen Time Manager"
        lnk.Save()

        # Start Menu shortcut (makes it searchable in Windows Search)
        start_menu = os.path.join(
            os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs"
        )
        lnk = shell.CreateShortCut(os.path.join(start_menu, "FocusMode.lnk"))
        lnk.TargetPath = INSTALLED_EXE
        lnk.WorkingDirectory = INSTALL_DIR
        lnk.IconLocation = icon_path
        lnk.Description = "Focus Mode - Screen Time Manager"
        lnk.Save()
    except Exception:
        pass


def add_to_startup():
    """Add app to Windows startup via Task Scheduler (runs elevated, no UAC prompt)."""
    try:
        subprocess.run(
            ["schtasks", "/delete", "/tn", APP_NAME, "/f"],
            capture_output=True, creationflags=CREATE_NO_WINDOW,
        )
        subprocess.run(
            [
                "schtasks", "/create",
                "/tn", APP_NAME,
                "/tr", f'"{INSTALLED_EXE}"',
                "/sc", "onlogon",
                "/rl", "highest",
                "/f",
            ],
            capture_output=True, creationflags=CREATE_NO_WINDOW,
        )
    except Exception:
        pass


def uninstall_app():
    """Remove shortcuts, registry entries, scheduled task, and install directory."""
    import win32com.client

    # Remove desktop shortcut
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        desktop = shell.SpecialFolders("Desktop")
        lnk_path = os.path.join(desktop, "FocusMode.lnk")
        if os.path.isfile(lnk_path):
            os.remove(lnk_path)
    except Exception:
        pass

    # Remove Start Menu shortcut
    try:
        start_menu = os.path.join(
            os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs"
        )
        lnk_path = os.path.join(start_menu, "FocusMode.lnk")
        if os.path.isfile(lnk_path):
            os.remove(lnk_path)
    except Exception:
        pass

    # Remove scheduled task
    try:
        subprocess.run(
            ["schtasks", "/delete", "/tn", APP_NAME, "/f"],
            capture_output=True, creationflags=CREATE_NO_WINDOW,
        )
    except Exception:
        pass

    # Remove registry entry
    try:
        winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, UNINSTALL_REG_KEY)
    except Exception:
        pass

    # Schedule self-deletion of install directory after exit
    # Use cmd /c with a small delay so the exe can exit first
    try:
        bat_content = f'@echo off\ntimeout /t 3 /nobreak >nul\nrd /s /q "{INSTALL_DIR}"\ndel "%~f0"\n'
        bat_path = os.path.join(os.environ["TEMP"], "focusmode_uninstall.bat")
        with open(bat_path, "w") as f:
            f.write(bat_content)
        subprocess.Popen(
            ["cmd", "/c", bat_path],
            creationflags=CREATE_NO_WINDOW,
        )
    except Exception:
        pass

    ctypes.windll.user32.MessageBoxW(
        0,
        "Focus Mode has been uninstalled successfully.",
        "Uninstall Complete",
        0x00000040,  # MB_ICONINFORMATION
    )
    sys.exit(0)


def cleanup_stuck_blocks():
    """Remove any stuck YouTube/social media blocks from hosts file at startup."""
    try:
        hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
        with open(hosts_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Remove any FocusMode-SOCIAL entries that shouldn't be there
        lines = content.split("\n")
        filtered = [l for l in lines if "# FocusMode-SOCIAL" not in l]
        new_content = "\n".join(filtered)
        
        if new_content != content:
            with open(hosts_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            os.system("ipconfig /flushdns >nul 2>&1")
    except Exception:
        # Silently fail - hosts cleanup is not critical
        pass


def main():
    if not is_admin():
        args = " ".join(sys.argv[1:]) if getattr(sys, "frozen", False) else ""
        run_as_admin(args)

    # Handle uninstall flag
    if "--uninstall" in sys.argv:
        uninstall_app()
        return

    # If frozen exe and not yet installed, install first
    if getattr(sys, "frozen", False) and not running_from_install_dir():
        install_app()
        # Relaunch from the installed location
        subprocess.Popen([INSTALLED_EXE], creationflags=CREATE_NO_WINDOW)
        sys.exit(0)

    # If running from install dir, refresh registration silently
    if getattr(sys, "frozen", False) and running_from_install_dir():
        register_uninstall()
        add_to_startup()

    # Clean up any stuck hosts file entries from previous crashes
    cleanup_stuck_blocks()

    api = Api()
    api.start()

    # Send task reminder after a short delay so notification doesn't block UI
    def _startup_reminder():
        import time
        time.sleep(3)
        api.send_startup_reminder()

    threading.Thread(target=_startup_reminder, daemon=True).start()

    base = get_base_path()
    ui_path = os.path.join(base, "ui", "index.html")

    window = webview.create_window(
        "Focus Mode",
        url=ui_path,
        js_api=api,
        width=500,
        height=820,
        resizable=True,
        background_color="#000000",
    )

    webview.start(debug=False)
    api.stop()


if __name__ == "__main__":
    main()
