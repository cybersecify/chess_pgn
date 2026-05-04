#!/bin/bash
# MCP server launcher — DB path derived from CHESS_USERNAME or CHESS_DB_PATH.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -n "$CHESS_DB_PATH" ]; then
    DB_PATH="$CHESS_DB_PATH"
elif [ -n "$CHESS_USERNAME" ]; then
    DB_PATH="$SCRIPT_DIR/../data/$CHESS_USERNAME.duckdb"
else
    echo "Error: set CHESS_USERNAME or CHESS_DB_PATH before starting the MCP server." >&2
    echo "  export CHESS_USERNAME=<your-chess.com-username>" >&2
    exit 1
fi

exec uvx mcp-server-duckdb --db-path "$DB_PATH" --readonly
