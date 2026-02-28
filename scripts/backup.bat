@echo off
REM =============================================================================
REM IIT ML Service - Automated Backup Script (Windows)
REM =============================================================================
REM This script performs automated backups of SQLite database and model files
REM Usage: Run via Task Scheduler or manually
REM =============================================================================

setlocal enabledelayedexpansion

REM Configuration
set BACKUP_DIR=backups
set TIMESTAMP=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set LOG_FILE=backup.log

REM Create backup directory
if not exist "%BACKUP_DIR%\database" mkdir "%BACKUP_DIR%\database"
if not exist "%BACKUP_DIR%\models" mkdir "%BACKUP_DIR%\models"

echo [%date% %time%] Starting backup... >> %LOG_FILE%

REM =============================================================================
REM Database Backup
REM =============================================================================
echo [%date% %time%] Starting database backup... >> %LOG_FILE%

copy "backend\ml-service\iit_ml_service.db" "%BACKUP_DIR%\database\iit_ml_service_%TIMESTAMP%.db" >nul

if %ERRORLEVEL% EQU 0 (
    echo [%date% %time%] Database backup completed: iit_ml_service_%TIMESTAMP%.db >> %LOG_FILE%
) else (
    echo [%date% %time%] ERROR: Database backup failed! >> %LOG_FILE%
    goto :error
)

REM =============================================================================
REM Model Files Backup
REM =============================================================================
echo [%date% %time%] Starting model files backup... >> %LOG_FILE%

if exist "backend\ml-service\models" (
    cd backend\ml-service
    tar -czf "../%BACKUP_DIR%/models/models_%TIMESTAMP%.tar.gz" models/
    cd ../..
    
    if %ERRORLEVEL% EQU 0 (
        echo [%date% %time%] Model backup completed: models_%TIMESTAMP%.tar.gz >> %LOG_FILE%
    ) else (
        echo [%date% %time%] ERROR: Model backup failed! >> %LOG_FILE%
        goto :error
    )
) else (
    echo [%date% %time%] WARNING: Model directory not found, skipping model backup >> %LOG_FILE%
)

REM =============================================================================
REM Cleanup Old Backups (30 days)
REM =============================================================================
echo [%date% %time%] Cleaning up backups older than 30 days... >> %LOG_FILE%

forfiles /P "%BACKUP_DIR%\database" /M *.db /D -30 /C "cmd /c del @path" 2>nul
forfiles /P "%BACKUP_DIR%\models" /M *.tar.gz /D -30 /C "cmd /c del @path" 2>nul

echo [%date% %time%] Cleanup completed >> %LOG_FILE%

REM =============================================================================
REM Verification
REM =============================================================================
echo [%date% %time%] Verifying latest backup... >> %LOG_FILE%

dir /B /O-D "%BACKUP_DIR%\database\*.db" 2>nul >nul
if %ERRORLEVEL% EQU 0 (
    echo [%date% %time%] Backup verification passed >> %LOG_FILE%
) else (
    echo [%date% %time%] WARNING: No backup files found >> %LOG_FILE%
)

echo [%date% %time%] ========== Backup completed ========== >> %LOG_FILE%
echo Backup completed successfully!
echo Backup location: %BACKUP_DIR%
goto :end

:error
echo [%date% %time%] ========== Backup failed ========== >> %LOG_FILE%
echo Backup failed! Check %LOG_FILE% for details.
exit /b 1

:end
endlocal
exit /b 0
