#!/bin/sh
# Build the ZIP for OpenAI's plugin submission portal (ChatGPT + Codex directory).
# Only the portable plugin files go in; the Claude-only files (.claude-plugin, .mcp.json,
# commands) stay out. Users install from GitHub or the directory, never from this ZIP.
set -e
cd "$(dirname "$0")/.."
mkdir -p dist && rm -f dist/revexos-invoice-parser-chatgpt.zip
zip -rq dist/revexos-invoice-parser-chatgpt.zip plugin.json mcp.json skills assets LICENSE README.md -x '*.DS_Store' '*__pycache__*'
echo "built dist/revexos-invoice-parser-chatgpt.zip"
