#!/bin/bash
# Wrapper script for kopia B2 snapshot — adds timestamps to log output.
# The plist's StandardOutPath/StandardErrorPath capture all output here.

KOPIA_BIN="/opt/homebrew/bin/kopia"
CONFIG="/Users/dang/Library/Application Support/kopia/repository-1680706950621.config"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') Starting kopia B2 snapshot ==="

"$KOPIA_BIN" snapshot create --all \
    --config-file "$CONFIG" \
    --log-level=info

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') Snapshot completed successfully ==="
else
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') Snapshot FAILED (exit code: $EXIT_CODE) ==="
fi

exit $EXIT_CODE
