#!/usr/bin/env bash
# =============================================================================
# kopia-launchd-setup.sh
# Sets up launchd agents for scheduled Kopia backups (SSD + B2 repos).
#
# Usage:
#   chmod +x kopia-launchd-setup.sh
#   ./kopia-launchd-setup.sh
# =============================================================================

set -euo pipefail

LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_SSD="com.kopia.backup.ssd.plist"
PLIST_B2="com.kopia.backup.b2.plist"

# ── 1. Locate kopia binary ──────────────────────────────────────────────────
echo "==> Locating kopia binary..."

KOPIA_BIN=""

# Check common locations in order of preference
for candidate in \
    "$(which kopia 2>/dev/null || true)" \
    "/opt/homebrew/bin/kopia" \
    "/usr/local/bin/kopia" \
    "/Applications/KopiaUI.app/Contents/Resources/kopia" \
    "/Applications/KopiaUI.app/Contents/MacOS/kopia"
do
    if [[ -x "$candidate" ]]; then
        KOPIA_BIN="$candidate"
        break
    fi
done

if [[ -z "$KOPIA_BIN" ]]; then
    # Broader search inside KopiaUI bundle
    KOPIA_BIN=$(find /Applications/KopiaUI.app -name "kopia" -type f -perm +111 2>/dev/null | head -1 || true)
fi

if [[ -z "$KOPIA_BIN" ]]; then
    echo "ERROR: Could not find kopia binary."
    echo "  Install via Homebrew:  brew install kopia"
    echo "  Or locate manually:    find /Applications/KopiaUI.app -name 'kopia' -type f"
    exit 1
fi

echo "    Found: $KOPIA_BIN"
echo "    Version: $("$KOPIA_BIN" --version 2>&1 | head -1)"

# ── 2. Patch KOPIA_PATH_PLACEHOLDER in plists ───────────────────────────────
echo ""
echo "==> Installing plist files to $LAUNCH_AGENTS_DIR ..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for PLIST in "$PLIST_SSD" "$PLIST_B2"; do
    SRC="$SCRIPT_DIR/$PLIST"
    DST="$LAUNCH_AGENTS_DIR/$PLIST"

    if [[ ! -f "$SRC" ]]; then
        echo "ERROR: $SRC not found. Make sure the plist files are in the same directory as this script."
        exit 1
    fi

    # Replace the placeholder with the real binary path
    sed "s|KOPIA_PATH_PLACEHOLDER|$KOPIA_BIN|g" "$SRC" > "$DST"
    echo "    Installed: $DST"
done

# ── 3. Validate plists ───────────────────────────────────────────────────────
echo ""
echo "==> Validating plist XML..."
plutil "$LAUNCH_AGENTS_DIR/$PLIST_SSD" && echo "    $PLIST_SSD OK"
plutil "$LAUNCH_AGENTS_DIR/$PLIST_B2"  && echo "    $PLIST_B2 OK"

# ── 4. Load agents ───────────────────────────────────────────────────────────
echo ""
echo "==> Loading launchd agents..."

for PLIST in "$PLIST_SSD" "$PLIST_B2"; do
    LABEL="${PLIST%.plist}"
    # Unload first (ignore error if not already loaded)
    launchctl unload "$LAUNCH_AGENTS_DIR/$PLIST" 2>/dev/null || true
    launchctl load "$LAUNCH_AGENTS_DIR/$PLIST"
    echo "    Loaded: $LABEL"
done

# ── 5. Verify agents are registered ─────────────────────────────────────────
echo ""
echo "==> Verifying agents..."
launchctl list | grep com.kopia || echo "WARNING: Agents not found in launchctl list"

# ── 6. Optional: run a test backup now ──────────────────────────────────────
echo ""
read -rp "==> Run a test backup NOW against all repos? [y/N] " RUN_TEST
if [[ "$RUN_TEST" =~ ^[Yy]$ ]]; then
    echo ""
    echo "--- Starting test snapshot (SSD) ---"
    "$KOPIA_BIN" snapshot create --all \
        --config-file "$HOME/Library/Application Support/kopia/repository.config" \
        --log-level=info
    echo "--- SSD snapshot complete ---"

    echo ""
    echo "--- Starting test snapshot (B2) ---"
    "$KOPIA_BIN" snapshot create --all \
        --config-file "$HOME/Library/Application Support/kopia/repository-1680706950621.config" \
        --log-level=info
    echo "--- B2 snapshot complete ---"
fi

echo ""
echo "==> Done! Backup schedule:"
echo "    SSD repo:  9:00am, 1:00pm, 5:00pm, 9:00pm"
echo "    B2 repo:   9:15am, 1:15pm, 5:15pm, 9:15pm"
echo ""
echo "    Logs:"
echo "      ~/Library/Logs/kopia-ssd.log"
echo "      ~/Library/Logs/kopia-b2.log"
echo ""
echo "    To check status:     launchctl list | grep com.kopia"
echo "    To trigger manually: launchctl start com.kopia.backup.ssd"
echo "    To unload:           launchctl unload ~/Library/LaunchAgents/com.kopia.backup.ssd.plist"
