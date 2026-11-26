from __future__ import annotations

import argparse
import sys

from .backends import ColorFilterType, UI_FILTER_OPTIONS, get_backend


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="color-filter-tray",
        description="Cross-platform system tray app for controlling Windows 10/11 Color Filters (with Linux & macOS support).",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Immediately open the Color Filters flyout card on launch.",
    )
    parser.add_argument(
        "--standalone",
        action="store_true",
        help="Keep the popup card open without auto-dismissing on focus loss (useful for testing or desktop widget mode).",
    )
    parser.add_argument(
        "--toggle",
        action="store_true",
        help="Toggle Color Filters On/Off from the command line and exit.",
    )
    parser.add_argument(
        "--enable",
        action="store_true",
        help="Enable Color Filters from the command line and exit.",
    )
    parser.add_argument(
        "--disable",
        action="store_true",
        help="Disable Color Filters from the command line and exit.",
    )
    parser.add_argument(
        "--filter",
        type=str,
        choices=[ft.name.lower() for ft in ColorFilterType],
        help="Set the active color filter type (grayscale, inverted, grayscale_inverted, deuteranopia, protanopia, tritanopia).",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print current Color Filter status and exit.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    backend = get_backend()

    # Handle headless CLI commands if requested
    cli_action = False
    if args.filter:
        ft = ColorFilterType[args.filter.upper()]
        backend.set_filter_type(ft)
        cli_action = True

    if args.toggle:
        current = backend.get_state()
        backend.set_active(not current.active)
        cli_action = True
    elif args.enable:
        backend.set_active(True)
        cli_action = True
    elif args.disable:
        backend.set_active(False)
        cli_action = True

    if args.status or cli_action:
        state = backend.get_state()
        label = next(
            (opt.label for opt in UI_FILTER_OPTIONS if opt.filter_type == state.filter_type),
            state.filter_type.name,
        )
        print(f"Platform Backend : {backend.platform_name}")
        print(f"Color Filters    : {'On' if state.active else 'Off'}")
        print(f"Selected Filter  : {label} (FilterType={int(state.filter_type)})")
        if not args.show and not args.standalone:
            return 0

    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication

    from .ui.tray import ColorFilterTrayController

    app = QApplication(sys.argv)
    app.setApplicationName("Color Filters Tray")
    app.setOrganizationName("ColorFilterTray")
    # Prevent closing the popup from terminating the background tray app
    app.setQuitOnLastWindowClosed(args.standalone)

    if sys.platform == "win32":
        app.setFont(QFont("Segoe UI Variable Text", 10))
    elif sys.platform == "darwin":
        app.setFont(QFont(".AppleSystemUIFont", 12))

    _controller = ColorFilterTrayController(
        app=app,
        backend=backend,
        show_on_start=args.show,
        standalone_mode=args.standalone,
    )
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
