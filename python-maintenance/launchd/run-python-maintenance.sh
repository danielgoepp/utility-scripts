#!/bin/bash

SCRIPT="/Users/YOUR_USERNAME/Development/utility-scripts/python-maintenance/update-python-libraries.py"
PYTHON_BIN="/Users/YOUR_USERNAME/Development/utility-scripts/.venv/bin/python3"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') Starting Python library maintenance ==="

"$PYTHON_BIN" "$SCRIPT" --email

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') Python library maintenance completed successfully ==="
else
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') Python library maintenance FAILED (exit code: $EXIT_CODE) ==="
fi

exit $EXIT_CODE
