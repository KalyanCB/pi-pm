#!/bin/bash
# Watch replay_daily progress — refreshes every 30s
LOG=/tmp/replay_daily.log

while true; do
    clear
    echo "=== replay_daily progress === $(date '+%H:%M:%S')"
    echo ""

    # Last 5 lines
    tail -5 "$LOG"

    echo ""

    # Summary stats
    DONE=$(grep -c "✓ completed" "$LOG" 2>/dev/null || echo 0)
    ERRORS=$(grep -c " ERROR:" "$LOG" 2>/dev/null || echo 0)
    LAST=$(grep "✓ completed" "$LOG" | tail -1 | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1)

    echo "Done: $DONE / 1348 | Errors: $ERRORS | Last date: $LAST"

    # Process alive?
    PID=$(pgrep -f "replay_daily_from_2021" | head -1)
    if [ -n "$PID" ]; then
        CPU=$(ps -p "$PID" -o %cpu= 2>/dev/null | tr -d ' ')
        echo "Process PID $PID alive | CPU: ${CPU}%"
    else
        echo "WARNING: process not running!"
    fi

    sleep 30
done
