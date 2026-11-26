#!/usr/bin/env python3
"""
Cross-platform PyInstaller build helper for ColorFilterTray.
Produces a windowless single-file executable:
  - Windows : dist/ColorFilterTray.exe
  - macOS   : dist/ColorFilterTray.app
  - Linux   : dist/ColorFilterTray
"""
from __future__ import annotations

import subprocess
import sys


def build() -> int:
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onefile",
        "--name",
        "ColorFilterTray",
        "main.py",
    ]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(build())
