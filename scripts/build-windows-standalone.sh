#!/usr/bin/env bash
# Builds a self-contained standalone bundle of the Python/Flask absence dashboard using
# PyInstaller --onedir: a folder containing the interpreter, all dependencies, and a
# launcher, zipped for transfer to a Windows Server 2016 / Citrix session with no Python
# install. Modeled directly on testautomation_monitoring's scripts/build-python-standalone.sh.
#
# Bundle layout: a bundle dir with the app executable, a .bat launcher, and
# launch_config.json/state/ left external and editable next to the launcher (not baked
# into the bundle).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUNDLE_DIR="$REPO_ROOT/dist/absence-dashboard-windows"
ZIP_PATH="$REPO_ROOT/dist/absence-dashboard-windows.zip"

if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "ERROR: pyinstaller not found on PATH — install it first with:" >&2
  echo "  pip install pyinstaller" >&2
  exit 1
fi

# PyInstaller's --add-data separator is OS-specific (';' on Windows, ':' elsewhere).
case "${OS:-}${OSTYPE:-}" in
  Windows_NT*|msys*|cygwin*) DATA_SEP=";" ;;
  *) DATA_SEP=":" ;;
esac

echo "Building PyInstaller onedir bundle..."
rm -rf "$REPO_ROOT/build" "$REPO_ROOT/dist/run" "$REPO_ROOT"/*.spec
pyinstaller \
  --name dashboard \
  --onedir \
  --noconfirm \
  --distpath "$REPO_ROOT/dist" \
  --add-data "absence_dashboard/static${DATA_SEP}absence_dashboard/static" \
  "$REPO_ROOT/run.py"

echo "Assembling bundle in $BUNDLE_DIR ..."
rm -rf "$BUNDLE_DIR"
mkdir -p "$BUNDLE_DIR"
cp -R "$REPO_ROOT/dist/dashboard/." "$BUNDLE_DIR/"

cp "$REPO_ROOT/launch_config.example.json" "$BUNDLE_DIR/launch_config.example.json"
# Ship a real, working launch_config.json too — not just the .example — so a fresh
# extraction has a usable excel_source/port from the first launch instead of failing
# with no config file at all.
cp "$REPO_ROOT/launch_config.example.json" "$BUNDLE_DIR/launch_config.json"

# save_state() creates its own parent directory on first write, but ship an empty
# state/ directory anyway so the bundle's intended layout is visible on extraction.
mkdir -p "$BUNDLE_DIR/state"

cat > "$BUNDLE_DIR/run-dashboard.bat" <<'BAT'
@echo off
rem "cd /d %~dp0" cannot target a UNC path (e.g. a network home drive like
rem \\server\share\...) and silently falls back to C:\Windows instead, which
rem breaks the app's cwd-relative launch_config.json/state lookup. "pushd" handles
rem UNC paths by mapping a temporary drive letter, so use that instead.
pushd "%~dp0"
echo Starting dashboard server...
dashboard.exe
echo.
echo Server stopped or failed to start. See any error above.
popd
pause
BAT

echo "Verifying bundle structure..."
for f in "dashboard.exe" "run-dashboard.bat" "launch_config.example.json"; do
  if [ ! -f "$BUNDLE_DIR/$f" ]; then
    echo "ERROR: expected file missing from bundle: $f" >&2
    exit 1
  fi
done
echo "OK: bundle structure verified (dashboard.exe, run-dashboard.bat, launch_config.example.json)."

echo "Zipping bundle to $ZIP_PATH ..."
rm -f "$ZIP_PATH"
if command -v zip >/dev/null 2>&1; then
  (cd "$REPO_ROOT/dist" && zip -qr "$(basename "$ZIP_PATH")" "$(basename "$BUNDLE_DIR")")
else
  # git-bash on GitHub's windows-latest runners has no `zip` on PATH; fall back
  # to PowerShell's Compress-Archive, which is always present on Windows.
  powershell -NoProfile -Command \
    "Compress-Archive -Path '$(cygpath -w "$BUNDLE_DIR" 2>/dev/null || echo "$BUNDLE_DIR")' -DestinationPath '$(cygpath -w "$ZIP_PATH" 2>/dev/null || echo "$ZIP_PATH")' -Force"
fi

echo "OK: $ZIP_PATH ($(du -h "$ZIP_PATH" | cut -f1))"
echo "Copy this zip to the target Windows Server 2016/Citrix session, extract anywhere writable, edit launch_config.json, and double-click run-dashboard.bat."
echo "NOTE: dashboard.exe only runs on the OS it was built on. Build on a Windows runner for a Windows target."
