Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Android App Java Version Checker" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Checking Java version..." -ForegroundColor Yellow
$javaOk = $false

try {
    $javaOutput = java -version 2>&1
    Write-Host $javaOutput -ForegroundColor Green
    
    if ($javaOutput -match "1\.8\.") {
        Write-Host "✗ Java 8 detected - Android requires Java 11+" -ForegroundColor Red
        $javaOk = $false
    } elseif ($javaOutput -match "11\.|17\.|21\.") {
        Write-Host "✓ Compatible Java version detected" -ForegroundColor Green
        $javaOk = $true
    } else {
        Write-Host "⚠ Unknown Java version" -ForegroundColor Yellow
        $javaOk = $false
    }
} catch {
    Write-Host "✗ Java not found in PATH" -ForegroundColor Red
    $javaOk = $false
}

Write-Host ""
Write-Host "JAVA_HOME: $env:JAVA_HOME" -ForegroundColor Yellow

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SOLUTIONS:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (-not $javaOk) {
    Write-Host ""
    Write-Host "🔧 Option 1: Install Java 17 (Recommended)" -ForegroundColor Green
    Write-Host "   1. Go to https://adoptium.net/" -ForegroundColor White
    Write-Host "   2. Download 'Eclipse Temurin 17' for Windows" -ForegroundColor White
    Write-Host "   3. Install and restart your terminal" -ForegroundColor White
    Write-Host ""
    Write-Host "🔧 Option 2: Use Android Studio (Easiest)" -ForegroundColor Green
    Write-Host "   1. Install Android Studio from https://developer.android.com/studio" -ForegroundColor White
    Write-Host "   2. Open the 'android' folder as a project" -ForegroundColor White
    Write-Host "   3. Android Studio handles Java compatibility automatically" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "🎉 Your Java setup looks good!" -ForegroundColor Green
    Write-Host "Try building: .\gradlew.bat clean assembleDebug" -ForegroundColor White
}

Write-Host ""