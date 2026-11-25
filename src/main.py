#!/usr/bin/env python3
"""Entry point for FilTray CLI tool / background service."""

import argparse
import platform
import sys
import time

__version__ = "0.1.0"


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="filtray",
        description="FilTray - Cross-platform CLI and background service.",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__} ({platform.system()} {platform.machine()})",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run continuously as a background service.",
    )
    args = parser.parse_args()

    if args.daemon:
        print(f"Starting FilTray v{__version__} background service on {platform.system()}...")
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("Stopping FilTray service.")
            return 0

    print(f"FilTray v{__version__} is running on {platform.system()} ({platform.machine()})!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
