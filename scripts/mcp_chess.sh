#!/bin/bash
# Portable MCP server launcher — DB path computed relative to this script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_PATH="${CHESS_DB_PATH:-$SCRIPT_DIR/../data/rathnakaragn.duckdb}"
exec uvx mcp-server-duckdb --db-path "$DB_PATH" --readonly
