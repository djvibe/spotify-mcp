@echo off
echo DJVIBE Spotify MCP - Update All Artists
echo.
echo This will update all artists that need updates based on their tier schedule.
echo The process may take some time depending on how many artists need updates.
echo.
echo Options:
echo - Default batch size: 10 artists
echo - Default concurrency: 3 simultaneous updates
echo - Both Standard and Partner API will be used as needed
echo.
echo Press Ctrl+C to cancel or any key to continue...
pause > nul

python %~dp0\update_all_artists.py --batch-size 10 --config D:\DJVIBE\MCP\spotify-mcp\config.json

echo.
echo Update complete. Check logs and report file for details.
pause
