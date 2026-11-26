# FilTray

A cross-platform **Color Filters** system tray application built with Python & PySide6, with prebuilt standalone executables for **Windows**, **macOS**, and **Debian / Ubuntu** (no Python installation required).

---

## Installation

Download the latest release for your operating system from the [**GitHub Releases**](https://github.com/eltazy/FilTray/releases/latest) page:

### 1. Windows (64-bit Intel & AMD)
1. Download **`FilTray-windows-x64.exe`** (or **`FilTray-windows-x64.zip`**) from the [**Releases**](https://github.com/eltazy/FilTray/releases/latest) page.
2. Double-click **`FilTray-windows-x64.exe`** to launch it directly into your Windows **system tray** (look near the clock or inside the `^` overflow tray icon).
   - *If Windows SmartScreen appears on first launch, click **More info → Run anyway**.*

---

### 2. macOS (Intel & Apple Silicon)
#### Option A: Native `.pkg` Installer
1. Download **`FilTray-<version>-macos-x64.pkg`** from the [**Releases**](https://github.com/eltazy/FilTray/releases/latest) page.
2. Right-click the `.pkg` file → **Open** to install **FilTray.app** into `/Applications`.

#### Option B: Portable `.zip` App Bundle
1. Download **`FilTray-macos-x64.zip`**, unzip it, and move **`FilTray.app`** to `/Applications`.

> **Note for macOS Gatekeeper:** Because the app is community-built without a paid Apple Developer certificate, if macOS blocks the first launch, run:
> ```bash
> xattr -dr com.apple.quarantine /Applications/FilTray.app
> ```

---

### 3. Debian / Ubuntu (`.deb` Package)
Download **`filtray_<version>_amd64.deb`** from the latest release and install it with `apt`:

```bash
sudo apt install ./filtray_0.2.0_amd64.deb
```

Then launch **FilTray** from your Applications menu, or from a terminal:
```bash
filtray
```

---

## CLI Options

FilTray also supports command-line flags for scripting or testing:

```bash
filtray --show                # Launch and immediately open the Color Filters flyout card
filtray --toggle              # Toggle Color Filters On/Off and exit
filtray --filter grayscale    # Set active filter (grayscale, inverted, grayscale_inverted, deuteranopia, protanopia, tritanopia)
filtray --status              # Print current Color Filter status and exit
```

---

## Development & Publishing Releases

Run locally from source:
```bash
pip install -r requirements.txt
python main.py
```

Run tests:
```bash
python -m unittest discover -s tests -v
```

Publish a new cross-platform release (triggers [`.github/workflows/release.yml`](.github/workflows/release.yml)):
```bash
git tag v0.2.0
git push origin v0.2.0
```

---

## License

Released under the [MIT License](LICENSE).
