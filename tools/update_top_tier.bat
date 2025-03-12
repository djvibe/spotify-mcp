@echo off
echo DJVIBE Spotify MCP - Update Top Tier Artists Only
echo.
echo This will update only top tier artists (popularity >= 75) that need updates.
echo.
echo Press Ctrl+C to cancel or any key to continue...
pause > nul

python %~dp0\update_all_artists.py --top-tier-only --batch-size 5 --config D:\DJVIBE\MCP\spotify-mcp\config.json

echo.
echo Update complete. Check logs and report file for details.
pause
