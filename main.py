#!/usr/bin/env python3
"""
Entrypoint script for Color Filters Tray App.
Can be run directly via `python main.py` or bundled into a standalone executable via PyInstaller.
"""
import sys

from color_filter_tray.app import main

if __name__ == "__main__":
    sys.exit(main())
