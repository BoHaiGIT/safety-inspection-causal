@echo off
chcp 65001 >nul
REM OSHA real-data downloader launcher (no Python needed)
REM Step 1: register a FREE DOL API key at https://dataportal.dol.gov/registration
REM Step 2: put the key (one line) into api_key.txt in this folder, OR set env var DOL_API_KEY
REM Step 3: double-click this file
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0download_osha_v2.ps1" %*
pause
