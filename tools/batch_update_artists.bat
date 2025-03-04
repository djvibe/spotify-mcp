@echo off
REM Script to batch update multiple artists with enhanced data

python batch_update_artists.py %*

if %ERRORLEVEL% == 0 (
    echo Batch update completed successfully!
) else (
    echo Batch update finished with errors. Check the log for details.
)
