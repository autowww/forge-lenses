# Azure Virtual Desktop / Windows 365 — Teams + virtual camera diagnostic
# Run inside your Cloud PC (Windows session).
# Output is printed and saved to a text file (paste file contents into Virtual Camera Studio).

param(
    [Parameter(HelpMessage = "Path for the diagnostic report (.txt). Default: Documents\forge-vc-avd-diagnostic-<timestamp>.txt")]
    [string]$OutputPath = ""
)

$ErrorActionPreference = 'SilentlyContinue'

if (-not $OutputPath) {
    $dir = Join-Path $env:USERPROFILE 'Documents'
    if (-not (Test-Path -LiteralPath $dir)) {
        $dir = $env:TEMP
    }
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $OutputPath = Join-Path $dir "forge-vc-avd-diagnostic-$stamp.txt"
}

$parent = Split-Path -Parent $OutputPath
if ($parent -and -not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}

$lines = New-Object System.Collections.Generic.List[string]

function Write-Diag {
    param([string]$Line = "")
    $lines.Add($Line)
    Write-Output $Line
}

Write-Diag "=== Forge Virtual Camera — AVD Teams diagnostic ==="
Write-Diag "Host: $env:COMPUTERNAME"
Write-Diag "User: $env:USERDOMAIN\$env:USERNAME"
Write-Diag "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Diag ""

# Teams install
$teamsPaths = @(
    "${env:ProgramFiles}\Microsoft\Teams\current\Teams.exe",
    "${env:LocalAppData}\Microsoft\Teams\current\Teams.exe"
)
$teamsInstalled = $false
foreach ($p in $teamsPaths) {
    if (Test-Path -LiteralPath $p) {
        Write-Diag "Teams installed: YES ($p)"
        $teamsInstalled = $true
        break
    }
}
if (-not $teamsInstalled) {
    Write-Diag "Teams installed: NO"
}

# WVD environment flag
$wvdKey = 'HKLM:\SOFTWARE\Microsoft\Teams'
$isWvd = Get-ItemProperty -Path $wvdKey -Name IsWVDEnvironment -ErrorAction SilentlyContinue
if ($isWvd -and $isWvd.IsWVDEnvironment -eq 1) {
    Write-Diag "IsWVDEnvironment: 1"
} else {
    Write-Diag "IsWVDEnvironment: missing or not 1 (Teams may not detect AVD)"
}

# WebRTC Redirector service
$redirector = Get-Service -Name 'WebRTC Redirector Service' -ErrorAction SilentlyContinue
if ($redirector) {
    Write-Diag "WebRTC Redirector Service: $($redirector.Status)"
} else {
    Write-Diag "WebRTC Redirector Service: NOT FOUND"
}

# Camera enumeration (friendly names)
Write-Diag ""
Write-Diag "Cameras found:"
try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $asyncOp = [Windows.Devices.Enumeration.DeviceInformation, Windows, ContentType = WindowsRuntime]::FindAllAsync([Windows.Media.Capture.MediaDevice]::GetVideoCaptureSelector())
    $devices = $asyncOp.GetResults()
    $count = 0
    foreach ($d in $devices) {
        $count++
        Write-Diag "  Camera $count : $($d.Name)"
    }
    Write-Diag "Camera count: $count"
} catch {
    Write-Diag "  (Could not enumerate via WinRT — $($_.Exception.Message))"
}

Write-Diag ""
Write-Diag "Teams media optimization: check Teams desktop — banner should mention AVD SlimCore / media optimized."
Write-Diag "If devices show as Remote audio/video only, optimization is likely OFF (RDP redirect path)."
Write-Diag "=== End diagnostic ==="

try {
    $lines | Set-Content -LiteralPath $OutputPath -Encoding UTF8
    Write-Output ""
    Write-Output "Saved diagnostic to: $OutputPath"
} catch {
    Write-Output ""
    Write-Output "Failed to save diagnostic file: $($_.Exception.Message)"
    exit 1
}
