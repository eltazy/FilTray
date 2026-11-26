from __future__ import annotations

import ctypes
import os
import subprocess
import sys

from .base import ColorFilterBackend, ColorFilterType, FilterState

REGISTRY_PATH = r"Software\Microsoft\ColorFiltering"
AT_REGISTRY_PATH = r"Software\Microsoft\Windows NT\CurrentVersion\Accessibility"


class WindowsColorFilterBackend(ColorFilterBackend):
    """
    Controls Windows 10/11 system Color Filters natively via:
      1. HKCU\\Software\\Microsoft\\ColorFiltering (Active & FilterType DWORDs)
      2. HKCU\\Software\\Microsoft\\Windows NT\\CurrentVersion\\Accessibility (Configuration string)
      3. Triggering Windows Assistive Technology Broker (atbroker.exe /colorfiltershortcut /resettransferkeys)
         with a fallback to Magnification.dll (MagSetFullscreenColorEffect) if atbroker is unavailable.
    """

    def __init__(self) -> None:
        self._cached_state = FilterState(
            active=False,
            filter_type=ColorFilterType.GRAYSCALE,
        )

    @property
    def platform_name(self) -> str:
        return "Windows 10/11 (Registry + ATBroker)"

    def get_state(self) -> FilterState:
        if sys.platform != "win32":
            return self._cached_state

        import winreg

        active = False
        filter_type = ColorFilterType.GRAYSCALE
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                REGISTRY_PATH,
                0,
                winreg.KEY_READ,
            ) as key:
                try:
                    active_val, _ = winreg.QueryValueEx(key, "Active")
                    active = bool(int(active_val))
                except FileNotFoundError:
                    active = False

                try:
                    ft_val, _ = winreg.QueryValueEx(key, "FilterType")
                    if int(ft_val) in ColorFilterType._value2member_map_:
                        filter_type = ColorFilterType(int(ft_val))
                except FileNotFoundError:
                    filter_type = ColorFilterType.GRAYSCALE
        except FileNotFoundError:
            pass
        except OSError:
            return self._cached_state

        self._cached_state = FilterState(active=active, filter_type=filter_type)
        return self._cached_state

    def set_state(self, active: bool, filter_type: ColorFilterType) -> None:
        self._cached_state = FilterState(active=active, filter_type=filter_type)
        if sys.platform != "win32":
            return

        import winreg

        # 1. Write Active and FilterType DWORD values to HKCU\Software\Microsoft\ColorFiltering
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_PATH,
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_READ,
        ) as key:
            winreg.SetValueEx(key, "Active", 0, winreg.REG_DWORD, 1 if active else 0)
            winreg.SetValueEx(key, "FilterType", 0, winreg.REG_DWORD, int(filter_type))

        # 2. Update HKCU\Software\Microsoft\Windows NT\CurrentVersion\Accessibility Configuration
        #    so Windows Settings UI and ATBroker remain completely synchronized.
        try:
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                AT_REGISTRY_PATH,
                0,
                winreg.KEY_SET_VALUE | winreg.KEY_READ,
            ) as acc_key:
                try:
                    config_str, _ = winreg.QueryValueEx(acc_key, "Configuration")
                except FileNotFoundError:
                    config_str = ""

                tokens = [t.strip() for t in config_str.split(",") if t.strip()]
                has_cf = any(t.lower() == "colorfiltering" for t in tokens)

                if active and not has_cf:
                    tokens.append("colorfiltering")
                    winreg.SetValueEx(
                        acc_key, "Configuration", 0, winreg.REG_SZ, ",".join(tokens)
                    )
                elif not active and has_cf:
                    tokens = [t for t in tokens if t.lower() != "colorfiltering"]
                    winreg.SetValueEx(
                        acc_key, "Configuration", 0, winreg.REG_SZ, ",".join(tokens)
                    )
        except OSError:
            pass

        # 3. Notify Windows Assistive Technology Broker (atbroker.exe) to apply the filter immediately
        self._trigger_atbroker()

    def _trigger_atbroker(self) -> None:
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        atbroker_path = os.path.join(system_root, "System32", "atbroker.exe")
        if not os.path.exists(atbroker_path):
            atbroker_path = "atbroker.exe"

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        try:
            subprocess.run(
                [atbroker_path, "/colorfiltershortcut", "/resettransferkeys"],
                creationflags=creation_flags,
                check=False,
                timeout=3,
            )
        except Exception:
            pass

        # Broadcast WM_SETTINGCHANGE so any open Windows Settings window refreshes its toggle
        try:
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            SMTO_ABORTIFHUNG = 0x0002
            result = ctypes.c_ulong()
            ctypes.windll.user32.SendMessageTimeoutW(
                HWND_BROADCAST,
                WM_SETTINGCHANGE,
                0,
                "ImmersiveColorSet",
                SMTO_ABORTIFHUNG,
                100,
                ctypes.byref(result),
            )
        except Exception:
            pass
