# FilTray

An open-source command-line tool and background service with prebuilt standalone executables for **Windows**, **macOS**, and **Debian / Ubuntu** (no Python installation required).

---

## Installation

Download the latest release for your operating system from the [**GitHub Releases**](https://github.com/eltazy/FilTray/releases/latest) page:

### 1. Debian / Ubuntu (`.deb` Package)
Download `filtray_<version>_amd64.deb` from the latest release and install it with `apt`:

```bash
sudo apt install ./filtray_0.1.0_amd64.deb
```

Verify installation:
```bash
filtray --version
```

*(Optional)* Run as a background `systemd` service:
```bash
sudo systemctl enable --now filtray
sudo systemctl status filtray
```

---

### 2. Windows (`.exe` / `.zip`)
1. Download `filtray-windows-amd64.exe` (or `filtray-windows-amd64.zip`) from the [**Releases**](https://github.com/eltazy/FilTray/releases/latest) page.
2. Rename `filtray-windows-amd64.exe` to `filtray.exe` and place it in a folder on your `PATH`, or run it directly in PowerShell / Command Prompt:

```powershell
.\filtray-windows-amd64.exe --version
```

---

### 3. macOS

#### Option A: Native `.pkg` Installer
1. Download `filtray-<version>-macos-arm64.pkg` from the [**Releases**](https://github.com/eltazy/FilTray/releases/latest) page.
2. Right-click the `.pkg` file and click **Open** to install `filtray` into `/usr/local/bin/filtray`.

#### Option B: Portable `.tar.gz` Binary
```bash
curl -LO https://github.com/eltazy/FilTray/releases/latest/download/filtray-macos-arm64.tar.gz
tar -xzf filtray-macos-arm64.tar.gz
sudo mv filtray /usr/local/bin/
```

> **Note for macOS Gatekeeper:** Because the binary is community-built without a paid Apple Developer certificate, if macOS blocks the first launch, clear the quarantine attribute with:
> ```bash
> sudo xattr -d com.apple.quarantine /usr/local/bin/filtray
> ```

---

## How to Publish a New Release (For Maintainers)

This repository uses GitHub Actions ([`.github/workflows/release.yml`](.github/workflows/release.yml)) to automatically compile standalone binaries for Windows, macOS, and Debian whenever you push a version tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Within a few minutes, GitHub Actions will create a new GitHub Release containing:
- `filtray_0.1.0_amd64.deb` (Debian/Ubuntu package)
- `filtray-linux-amd64.tar.gz` (Portable Linux binary)
- `filtray-windows-amd64.exe` & `filtray-windows-amd64.zip` (Windows executable)
- `filtray-0.1.0-macos-arm64.pkg` & `filtray-macos-arm64.tar.gz` (macOS)
- `SHA256SUMS.txt` (Checksums for verification)

---

## License

Released under the [MIT License](LICENSE).
