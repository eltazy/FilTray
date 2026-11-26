#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/build_deb.sh <app_name> <version> <arch> <binary_path> <output_dir>
APP_NAME="${1:-filtray}"
VERSION="${2:-0.2.0}"
ARCH="${3:-amd64}"
BINARY_PATH="${4:-dist/${APP_NAME}}"
OUTPUT_DIR="${5:-release-assets}"

MAINTAINER="${DEB_MAINTAINER:-eltazy <https://github.com/eltazy>}"
DESCRIPTION="${DEB_DESCRIPTION:-FilTray - Cross-platform system tray app for controlling Color Filters}"
HOMEPAGE="${DEB_HOMEPAGE:-https://github.com/eltazy/FilTray}"

if [ ! -f "$BINARY_PATH" ]; then
  echo "Error: Binary not found at '$BINARY_PATH'" >&2
  exit 1
fi

BUILD_ROOT="$(mktemp -d)"
PKG_DIR="${BUILD_ROOT}/${APP_NAME}_${VERSION}_${ARCH}"

mkdir -p "${PKG_DIR}/DEBIAN"
mkdir -p "${PKG_DIR}/usr/bin"
mkdir -p "${PKG_DIR}/usr/share/doc/${APP_NAME}"

# Copy executable binary
cp "${BINARY_PATH}" "${PKG_DIR}/usr/bin/${APP_NAME}"
chmod 0755 "${PKG_DIR}/usr/bin/${APP_NAME}"

# Copy documentation & license if present
[ -f README.md ] && cp README.md "${PKG_DIR}/usr/share/doc/${APP_NAME}/"
[ -f LICENSE ] && cp LICENSE "${PKG_DIR}/usr/share/doc/${APP_NAME}/copyright"

# Include desktop launcher entry if present
if [ -f "packaging/${APP_NAME}.desktop" ]; then
  mkdir -p "${PKG_DIR}/usr/share/applications"
  cp "packaging/${APP_NAME}.desktop" "${PKG_DIR}/usr/share/applications/${APP_NAME}.desktop"
  chmod 0644 "${PKG_DIR}/usr/share/applications/${APP_NAME}.desktop"
fi

# Calculate installed size in KB
INSTALLED_SIZE="$(du -sk "${PKG_DIR}" | cut -f1)"

# Create DEBIAN/control metadata
cat > "${PKG_DIR}/DEBIAN/control" <<EOF
Package: ${APP_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Installed-Size: ${INSTALLED_SIZE}
Maintainer: ${MAINTAINER}
Homepage: ${HOMEPAGE}
Description: ${DESCRIPTION}
 Packaged as a self-contained PySide6 system tray executable with no external Python runtime required.
EOF

chmod 0755 "${PKG_DIR}/DEBIAN"
chmod 0644 "${PKG_DIR}/DEBIAN/control"

mkdir -p "${OUTPUT_DIR}"
DEB_FILE="${OUTPUT_DIR}/${APP_NAME}_${VERSION}_${ARCH}.deb"

dpkg-deb --build --root-owner-group "${PKG_DIR}" "${DEB_FILE}"
rm -rf "${BUILD_ROOT}"

echo "Built Debian package: ${DEB_FILE}"
