# ===================================================================
# Browser Connectivity Diagnostic Script (Non-Admin)
# ===================================================================
# This script diagnoses connectivity issues without requiring admin rights.
# Run: powershell -ExecutionPolicy Bypass -File scripts/diagnose_browser.ps1
# ===================================================================

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " BROWSER CONNECTIVITY DIAGNOSTIC" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Function to test port connectivity
function Test-PortConnectivity {
    param($Port, $Description)
    
    Write-Host "Testing $Description (port $Port)..." -ForegroundColor Yellow
    
    # Test with netstat
    $listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    
    if ($listening) {
        Write-Host "  [OK] Port $Port is LISTENING" -ForegroundColor Green
        $listening | ForEach-Object {
            Write-Host "      - $($_.LocalAddress):$($_.LocalPort)" -ForegroundColor Gray
        }
        return $true
    } else {
        Write-Host "  [FAIL] Port $Port is NOT listening" -ForegroundColor Red
        return $false
    }
}

# Function to test HTTP connection
function Test-HttpConnection {
    param($Url, $Description)
    
    Write-Host "Testing $Description..." -ForegroundColor Yellow
    
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec 5 -UseBasicParsing
        Write-Host "  [OK] $Url - Status: $($response.StatusCode)" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "  [FAIL] $Url - Error: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to check proxy settings
function Test-ProxySettings {
    Write-Host "`nChecking system proxy settings..." -ForegroundColor Yellow
    
    $proxySettings = Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" -ErrorAction SilentlyContinue
    
    if ($proxySettings.ProxyEnable -eq 1) {
        Write-Host "  [WARN] System proxy is ENABLED" -ForegroundColor Yellow
        Write-Host "      Proxy Server: $($proxySettings.ProxyServer)" -ForegroundColor Gray
        
        # Check localhost bypass
        if ($proxySettings.ProxyOverride) {
            Write-Host "      Proxy Override: $($proxySettings.ProxyOverride)" -ForegroundColor Gray
            if ($proxySettings.ProxyOverride -match "localhost") {
                Write-Host "  [OK] Localhost is in proxy bypass list" -ForegroundColor Green
            } else {
                Write-Host "  [WARN] Localhost may NOT be in proxy bypass list" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "  [OK] System proxy is DISABLED" -ForegroundColor Green
    }
}

# Function to check DNS resolution
function Test-DnsResolution {
    Write-Host "`nTesting DNS resolution..." -ForegroundColor Yellow
    
    try {
        $ip = [System.Net.Dns]::GetHostAddresses("localhost")
        Write-Host "  [OK] Localhost resolves to: $($ip[0].IPAddressToString)" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Cannot resolve localhost: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Function to check for VPN
function Test-NetworkAdapters {
    Write-Host "`nChecking network adapters..." -ForegroundColor Yellow
    
    # Check for common VPN adapters
    $vpnAdapters = Get-NetAdapter | Where-Object { 
        $_.Status -eq "Up" -and 
        ($_.InterfaceDescription -match "VPN" -or $_.InterfaceDescription -match "Tunnel" -or $_.InterfaceDescription -match "Virtual")
    }
    
    if ($vpnAdapters) {
        Write-Host "  [WARN] Found active VPN/Tunnel adapters:" -ForegroundColor Yellow
        $vpnAdapters | ForEach-Object { Write-Host "      - $($_.Name) ($($_.InterfaceDescription))" -ForegroundColor Gray }
        Write-Host "  [INFO] VPN may be blocking localhost connections" -ForegroundColor Cyan
    } else {
        Write-Host "  [OK] No active VPN adapters found" -ForegroundColor Green
    }
}

# ============================================================================
# RUN DIAGNOSTICS
# ============================================================================

Write-Host "PHASE 1: SERVER STATUS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$backendOk = Test-PortConnectivity -Port 8000 -Description "Backend Server"
$frontendOk = Test-PortConnectivity -Port 5173 -Description "Frontend Server"

Write-Host "`nPHASE 2: HTTP CONNECTION TESTS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

Test-HttpConnection -Url "http://127.0.0.1:8000/health" -Description "Backend Health (127.0.0.1)"
Test-HttpConnection -Url "http://localhost:8000/health" -Description "Backend Health (localhost)"
Test-HttpConnection -Url "http://127.0.0.1:5173/" -Description "Frontend (127.0.0.1)"
Test-HttpConnection -Url "http://localhost:5173/" -Description "Frontend (localhost)"

Write-Host "`nPHASE 3: SYSTEM CONFIGURATION" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

Test-ProxySettings
Test-DnsResolution
Test-NetworkAdapters

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host " DIAGNOSTIC COMPLETE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "SUMMARY:" -ForegroundColor Yellow
Write-Host "  Backend Server:  $(if ($backendOk) { 'RUNNING' } else { 'NOT RUNNING' })" -ForegroundColor $(if ($backendOk) { 'Green' } else { 'Red' })
Write-Host "  Frontend Server: $(if ($frontendOk) { 'RUNNING' } else { 'NOT RUNNING' })" -ForegroundColor $(if ($frontendOk) { 'Green' } else { 'Red' })
Write-Host ""
Write-Host "If servers are running but browser shows ERR_CONNECTION_RESET:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Try incognito mode (Ctrl+Shift+N in Chrome)" -ForegroundColor White
Write-Host "2. Clear browser cache for localhost" -ForegroundColor White
Write-Host "3. Disable browser extensions temporarily" -ForegroundColor White
Write-Host "4. Check browser proxy settings" -ForegroundColor White
Write-Host "5. Disconnect any VPN" -ForegroundColor White
Write-Host "6. Try a different browser" -ForegroundColor White
Write-Host ""
Write-Host "To apply automatic fixes, run as Administrator:" -ForegroundColor Yellow
Write-Host "  Right-click PowerShell > Run as Administrator" -ForegroundColor Gray
Write-Host "  .\scripts\fix_browser_connectivity.ps1" -ForegroundColor Gray
Write-Host ""
