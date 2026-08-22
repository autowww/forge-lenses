#!/usr/bin/env bash
# Register Forge Lenses and Forge Studio in the Ubuntu/GNOME app grid and search.
# Usage: ./install-ubuntu-launchers.sh          # install
#        ./install-ubuntu-launchers.sh --remove
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
REMOVE=false
if [[ "${1:-}" == "--remove" || "${1:-}" == "-r" ]]; then
  REMOVE=true
fi

install_one() {
  local id="$1"
  local name="$2"
  local comment="$3"
  local exec_script="$4"
  local icon_file="$5"
  local path="${APPS_DIR}/${id}.desktop"
  mkdir -p "$APPS_DIR"
  cat >"$path" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=${name}
Comment=${comment}
Exec=${SCRIPT_DIR}/${exec_script}
Icon=${SCRIPT_DIR}/icons/${icon_file}
Terminal=false
Categories=Development;
Keywords=forge;lenses;workspace;studio;
StartupWMClass=forge-lenses-desktop
EOF
  chmod 644 "$path"
  echo "Installed: $path"
}

if [[ "$REMOVE" == true ]]; then
  rm -f "${APPS_DIR}/forge-lenses.desktop" "${APPS_DIR}/forge-studio.desktop" "${APPS_DIR}/virtual-camera-studio.desktop"
  echo "Removed forge-lenses.desktop, forge-studio.desktop, and virtual-camera-studio.desktop from $APPS_DIR"
  if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPS_DIR" 2>/dev/null || true
  fi
  exit 0
fi

chmod +x "${SCRIPT_DIR}/launch-forge-lenses.sh" "${SCRIPT_DIR}/launch-forge-studio.sh" "${SCRIPT_DIR}/launch-virtual-camera-studio.sh" 2>/dev/null || true

install_one "forge-lenses" "Forge Lenses" \
  "Workspace visualization (Electron shell for forge-lenses)" \
  "launch-forge-lenses.sh" "forge-lenses.png"

install_one "forge-studio" "Forge Studio" \
  "Lenses Studio UI (Electron opens /studio/)" \
  "launch-forge-studio.sh" "forge-studio.png"

install_one "virtual-camera-studio" "Virtual Camera Studio" \
  "Dedicated virtual webcam profiles for VDI and Teams (minimal Electron shell)" \
  "launch-virtual-camera-studio.sh" "forge-studio.png"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APPS_DIR" 2>/dev/null || true
fi

echo ""
echo "Done. Open the app grid (Super+A) or search for \"Forge Lenses\", \"Forge Studio\", or \"Virtual Camera Studio\"."
echo "First run: cd \"$SCRIPT_DIR\" && npm install   (if you have not already)."
