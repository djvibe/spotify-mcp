@echo off
REM Script to fetch enhanced artist data and update the database

REM Default values
set ARTIST_ID=76M2Ekj8bG8W7X2nbx2CpF
set DB_PATH=..\spotify.db
set OUTPUT_DIR=..\tests\output
REM Check if output directory exists and create it if not
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"


REM Parse command line arguments
:parse_args
if "%~1"=="" goto :end_parse_args
if "%~1"=="-a" (
    set ARTIST_ID=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--artist-id" (
    set ARTIST_ID=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="-d" (
    set DB_PATH=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--db-path" (
    set DB_PATH=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="-o" (
    set OUTPUT_DIR=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--output-dir" (
    set OUTPUT_DIR=%~2
    shift
    shift
    goto :parse_args
)
echo Unknown option: %~1
exit /b 1

:end_parse_args

echo Fetching enhanced data for artist: %ARTIST_ID%

REM Step 1: Fetch the enhanced data using our test script
python ..\tests\test_spotify_api.py --artist-id "%ARTIST_ID%" --output-dir "%OUTPUT_DIR%"

REM Check if the fetch was successful
if %ERRORLEVEL% neq 0 (
    echo Failed to fetch enhanced data for artist: %ARTIST_ID%
    exit /b 1
)

set METRICS_FILE=%OUTPUT_DIR%\%ARTIST_ID%_metrics.json
set RESPONSE_FILE=%OUTPUT_DIR%\%ARTIST_ID%_spotify_response.json

REM Check if the metrics file exists
if not exist "%METRICS_FILE%" (
    echo Metrics file not found: %METRICS_FILE%
    exit /b 1
)

REM Check if the response file exists
if not exist "%RESPONSE_FILE%" (
    echo Response file not found: %RESPONSE_FILE%
    exit /b 1
)

echo Successfully fetched enhanced data
echo Metrics file: %METRICS_FILE%
echo Response file: %RESPONSE_FILE%

REM Step 2: Update the database with the enhanced data
echo Updating database with enhanced data...
python update_artist_from_enhanced_data.py --artist-id "%ARTIST_ID%" --db-path "%DB_PATH%" --metrics-file "%METRICS_FILE%" --response-file "%RESPONSE_FILE%"

REM Check if the update was successful
if %ERRORLEVEL% neq 0 (
    echo Failed to update database with enhanced data
    exit /b 1
)

echo Successfully updated database with enhanced data for artist: %ARTIST_ID%
echo Done!
