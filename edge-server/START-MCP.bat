@echo off
REM Ionity Edge MCP server (stdio) — lets Claude Desktop/Code control the home assistant.
REM Register once:  claude mcp add ionity-edge -- py -3.12 "%~dp0mcp_server.py"
REM (c) Ionity (Pty) Ltd - Policy 986 AED
cd /d "%~dp0"
py -3.12 mcp_server.py
