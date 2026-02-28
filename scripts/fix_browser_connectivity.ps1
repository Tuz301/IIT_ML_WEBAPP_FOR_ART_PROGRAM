# ===================================================================
# Browser Connectivity Fix Script for IIT ML Service
# ===================================================================
# This script diagnoses and fixes common Windows connectivity issues
# that prevent browsers from connecting to localhost development servers.
#
# Run this script as Administrator in PowerShell:
#    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
#    .\scripts\fix_browser_connectivity.ps1
# ===================================================================

#Requires -RunAsAdministrator

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " BROWSER CONNECTIVITY DIAGNOSTIC & FIX" -ForegroundColor Cyan
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

# Function to check Windows Firewall rules
function Test-FirewallRules {
    Write-Host "`nChecking Windows Firewall rules..." -ForegroundColor Yellow
    
    $browserPaths = @(
        "C:\Program Files\Google\Chrome\Application\chrome.exe",
        "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "C:\Program Files\Mozilla Firefox\firefox.exe"
    )
    
    foreach ($path in $browserPaths) {
        if (Test-Path $path) {
            $browserName = Split-Path $path -Leaf
            $rules = Get-NetFirewallApplicationFilter -Program $path -ErrorAction SilentlyContinue
            
            if ($rules) {
                Write-Host "  [INFO] Found firewall rules for $browserName" -ForegroundColor Cyan
            } else {
                Write-Host "  [WARN] No firewall rules found for $browserName" -ForegroundColor Yellow
            }
        }
    }
    
    # Check for blocking rules on localhost ports
    $blockingRules = Get-NetFirewallRule | Where-Object {
        $_.Enabled -eq "True" -and 
        $_.Direction -eq "Outbound" -and
        ($_.DisplayName -match "8000" -or $_.DisplayName -match "5173" -or $_.DisplayName -match "localhost")
    }
    
    if ($blockingRules) {
        Write-Host "  [WARN] Found potential blocking rules for localhost ports" -ForegroundColor Yellow
        $blockingRules | ForEach-Object { Write-Host "      - $($_.DisplayName)" -ForegroundColor Gray }
    } else {
        Write-Host "  [OK] No blocking rules found for localhost ports" -ForegroundColor Green
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

# Function to check hosts file
function Test-HostsFile {
    Write-Host "`nChecking hosts file..." -ForegroundColor Yellow
    
    $hostsPath = "$env:SystemRoot\System32\drivers\etc\hosts"
    $hostsContent = Get-Content $hostsPath -ErrorAction SilentlyContinue
    
    $localhostEntries = $hostsContent | Where-Object { $_ -match "^\s*127\.0\.0\.1\s+localhost" }
    
    if ($localhostEntries) {
        Write-Host "  [OK] Localhost entry found in hosts file" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] No localhost entry found in hosts file" -ForegroundColor Yellow
    }
    
    # Check for blocked entries
    $blockedEntries = $hostsContent | Where-Object { $_ -match "localhost" -and $_ -match "#" }
    if ($blockedEntries) {
        Write-Host "  [WARN] Localhost entries may be commented out" -ForegroundColor Yellow
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
    
    try {
        $ip = [System.Net.Dns]::GetHostAddresses("127.0.0.1")
        Write-Host "  [OK] 127.0.0.1 resolves to: $($ip[0].IPAddressToString)" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Cannot resolve 127.0.0.1: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Function to check for VPN/Network filters
function Test-NetworkFilters {
    Write-Host "`nChecking for network filters..." -ForegroundColor Yellow
    
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

# Function to create firewall rules
function Add-FirewallRules {
    Write-Host "`n============================================================" -ForegroundColor Cyan
    Write-Host " CREATING FIREWALL RULES" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    
    $ruleName = "Allow Localhost Development Servers"
    $existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    
    if ($existingRule) {
        Write-Host "Firewall rule already exists. Removing..." -ForegroundColor Yellow
        Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    }
    
    Write-Host "Creating new firewall rule..." -ForegroundColor Yellow
    New-NetFirewallRule -DisplayName $ruleName `
                        -Direction Outbound `
                        -Action Allow `
                        -Enabled True `
                        -Profile Any `
                        -LocalPort 8000,5173,3000,5000,4000,6000 `
                        -Protocol TCP `
                        -EdgeTraversalPolicy Allow `
                        -Description "Allow outbound connections to localhost development servers"
    
    Write-Host "  [OK] Firewall rule created" -ForegroundColor Green
}

# Function to disable proxy for localhost
function Disable-ProxyForLocalhost {
    Write-Host "`n============================================================" -ForegroundColor Cyan
    Write-Host " CONFIGURING PROXY SETTINGS" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    
    $proxySettings = Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" -ErrorAction SilentlyContinue
    
    if ($proxySettings.ProxyEnable -eq 1) {
        Write-Host "Proxy is enabled. Adding localhost to bypass list..." -ForegroundColor Yellow
        
        # Add localhost to proxy bypass if not already there
        $bypassList = $proxySettings.ProxyOverride -split ";"
        
        if ("localhost" -notin $bypassList) {
            $bypassList += "localhost"
            $bypassList += "127.0.0.1"
            
            Set-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" `
                            -Name "ProxyOverride" `
                            -Value ($bypassList -join ";")
            
            Write-Host "  [OK] Added localhost and 127.0.0.1 to proxy bypass" -ForegroundColor Green
        } else {
            Write-Host "  [OK] Localhost already in proxy bypass list" -ForegroundColor Green
        }
    } else {
        Write-Host "Proxy is disabled. No changes needed." -ForegroundColor Green
    }
}

# Function to flush DNS cache
function Clear-DnsCache {
    Write-Host "`nFlushing DNS cache..." -ForegroundColor Yellow
    Clear-DnsClientCache -ErrorAction SilentlyContinue
    Write-Host "  [OK] DNS cache flushed" -ForegroundColor Green
}

# ============================================================================
# MAIN DIAGNOSTIC FLOW
# ============================================================================

Write-Host "PHASE 1: DIAGNOSTIC TESTS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Test ports
Test-PortConnectivity -Port 8000 -Description "Backend Server"
Test-PortConnectivity -Port 5173 -Description "Frontend Server"

# Test HTTP connections
Test-HttpConnection -Url "http://127.0.0.1:8000/health" -Description "Backend Health (127.0.0.1)"
Test-HttpConnection -Url "http://localhost:8000/health" -Description "Backend Health (localhost)"
Test-HttpConnection -Url "http://127.0.0.1:5173/" -Description "Frontend (127.0.0.1)"
Test-HttpConnection -Url "http://localhost:5173/" -Description "Frontend (localhost)"

# Check system configuration
Test-FirewallRules
Test-ProxySettings
Test-HostsFile
Test-DnsResolution
Test-NetworkFilters

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "PHASE 2: AUTOMATIC FIXES" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$applyFixes = Read-Host "`nDo you want to apply automatic fixes? (Y/N)"

if ($applyFixes -eq "Y" -or $applyFixes -eq "y") {
    Add-FirewallRules
    Disable-ProxyForLocalhost
    Clear-DnsCache
    
    Write-Host "`n============================================================" -ForegroundColor Cyan
    Write-Host "FIXES APPLIED" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Please restart your browser and try again:" -ForegroundColor Yellow
    Write-Host "  - Backend:  http://localhost:8000/health" -ForegroundColor White
    Write-Host "  - Frontend: http://localhost:5173/" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "`nFixes skipped. Please manually apply the suggested fixes above." -ForegroundColor Yellow
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "MANUAL TROUBLESHOOTING STEPS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "If the issue persists, try these steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Clear browser cache and cookies for localhost:" -ForegroundColor White
Write-Host "   - Chrome/Edge: Settings > Privacy > Clear browsing data" -ForegroundColor Gray
Write-Host "   - Select 'Cached images and files' and 'Cookies'" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Try incognito/private mode:" -ForegroundColor White
Write-Host "   - Chrome: Ctrl + Shift + N" -ForegroundColor Gray
Write-Host "   - Edge: Ctrl + Shift + P" -ForegroundColor Gray
Write-Host "   - Firefox: Ctrl + Shift + P" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Disable browser extensions:" -ForegroundColor White
Write-Host "   - Ad blockers, VPN extensions, and privacy extensions" -ForegroundColor Gray
Write-Host "   - Can block localhost connections" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Check browser proxy settings:" -ForegroundColor White
Write-Host "   - Settings > System > Open computer's proxy settings" -ForegroundColor Gray
Write-Host "   - Make sure 'Use a proxy server' is OFF" -ForegroundColor Gray
Write-Host ""
Write-Host "5. Disconnect VPN:" -ForegroundColor White
Write-Host "   - VPNs can block localhost connections" -ForegroundColor Gray
Write-Host ""
Write-Host "6. Temporarily disable antivirus:" -ForegroundColor White
Write-Host "   - Some antivirus software blocks localhost" -ForegroundColor Gray
Write-Host ""
Write-Host "7. Try a different browser:" -ForegroundColor White
Write-Host "   - Test with Chrome, Edge, or Firefox" -ForegroundColor Gray
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
