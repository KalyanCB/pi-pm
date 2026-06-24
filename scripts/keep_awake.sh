#!/usr/bin/env bash
# Prevents macOS display sleep by moving the mouse 1px every 60s.
# Run: bash scripts/keep_awake.sh
# Stop: Ctrl+C

trap 'echo "Stopped."; exit 0' INT

echo "Keeping screen awake. Press Ctrl+C to stop."

while true; do
    caffeinate -u -t 1 2>/dev/null || \
        osascript -e 'tell application "System Events" to key code 63' 2>/dev/null
    sleep 60
done
