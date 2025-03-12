@echo off
echo DJVIBE Spotify MCP - Standard API Updates Only
echo.
echo This will update artists using only the standard Spotify API.
echo Use this if you're experiencing issues with the Partner API.
echo.
echo Press Ctrl+C to cancel or any key to continue...
pause > nul

python %~dp0\update_all_artists.py --standard-only --batch-size 10 --config D:\DJVIBE\MCP\spotify-mcp\config.json

echo.
echo Update complete. Check logs and report file for details.
pause
