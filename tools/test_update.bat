@echo off
echo DJVIBE Spotify MCP - Test Update
echo Running update for 5 artists...
echo.

python %~dp0\update_all_artists.py --batch-size 5 --limit 5 --config D:\DJVIBE\MCP\spotify-mcp\config.json

echo.
echo Test update complete. Check logs for details.
pause
