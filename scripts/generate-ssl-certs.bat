@echo off
REM Generate self-signed SSL certificates for development (Windows)
REM DO NOT use these certificates in production!

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set SSL_DIR=%SCRIPT_DIR%..\nginx\ssl
set DOMAIN=%1
if "%DOMAIN%"=="" set DOMAIN=localhost

REM Create SSL directory if it doesn't exist
if not exist "%SSL_DIR%" mkdir "%SSL_DIR%"

echo Generating self-signed SSL certificate for %DOMAIN%...

REM Generate private key and self-signed certificate in one step
openssl req -x509 -newkey rsa:2048 -keyout "%SSL_DIR%\key.pem" -out "%SSL_DIR%\cert.pem" -days 365 -nodes ^
  -subj "/C=US/ST=State/L=City/O=Organization/CN=%DOMAIN%"

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to generate SSL certificates
    echo Make sure OpenSSL is installed and available in PATH
    exit /b 1
)

REM Set appropriate permissions
icacls "%SSL_DIR%\key.pem" /inheritance:r
icacls "%SSL_DIR%\key.pem" /grant:r "%USERNAME%:R"

echo.
echo SSL certificates generated successfully!
echo Certificate: %SSL_DIR%\cert.pem
echo Private Key: %SSL_DIR%\key.pem
echo.
echo WARNING: These are self-signed certificates for development only.
echo DO NOT use them in production!
echo.
echo To trust this certificate on Windows:
echo   1. Right-click on cert.pem and select "Install Certificate"
echo   2. Select "Local Machine" and click Next
echo   3. Choose "Place all certificates in the following store"
echo   4. Click Browse and select "Trusted Root Certification Authorities"
echo   5. Click Finish
echo.

endlocal
