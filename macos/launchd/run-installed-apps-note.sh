#!/bin/bash

SCRIPT="/Users/YOUR_USERNAME/Development/utility-scripts/macos/update-installed-apps-note.py"
PYTHON_BIN="/Users/YOUR_USERNAME/Development/utility-scripts/.venv/bin/python3"

# launchd's default PATH does not include Homebrew, which the script needs
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') Starting installed applications note update ==="

"$PYTHON_BIN" "$SCRIPT"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') Installed applications note update completed successfully ==="
else
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') Installed applications note update FAILED (exit code: $EXIT_CODE) ==="
fi

exit $EXIT_CODE
