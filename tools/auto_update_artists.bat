@echo off
echo DJVIBE Spotify MCP - Automated Artist Update
echo ==========================================
echo.
echo This script automatically:
echo 1. Identifies artists needing updates based on tier
echo 2. Processes them in batches
echo 3. Generates detailed reports
echo.
echo Press Ctrl+C to cancel or any key to continue...
pause > nul

python %~dp0\auto_update_artists.py %*

echo.
echo Update process complete. Check logs for details.
pause
