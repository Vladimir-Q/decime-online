# Allow Decime API (port 8000) through Windows Firewall on Private networks.
# Run in PowerShell as Administrator.

$ErrorActionPreference = "Stop"

$ruleName = "Decime API 8000"

$existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Rule already exists: $ruleName"
} else {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000 -Profile Private | Out-Null
    Write-Host "Created firewall rule: $ruleName (TCP 8000, Private)"
}

Write-Host ""
Write-Host "Check API on PC: curl http://127.0.0.1:8000/health"
Write-Host "From phone browser: http://YOUR_PC_IP:8000/health"
