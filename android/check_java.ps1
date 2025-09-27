Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Android App Java Version Checker" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Checking Java version..." -ForegroundColor Yellow
try {
    $javaVersion = java -version 2>&1 | Select-String "version" | Select-Object -First 1
    Write-Host $javaVersion -ForegroundColor Green
    
    # Extract version number
    $versionMatch = $javaVersion -match '"(\d+)\.(\d+)\.(\d+)_(\d+)"' -or $javaVersion -match '"(\d+)\.(\d+)\.(\d+)"' -or $javaVersion -match '"(\d+)'
    if ($versionMatch) {
        $majorVersion = [int]$matches[1]
        if ($majorVersion -ge 11) {
            Write-Host "✓ Java version is compatible (Java $majorVersion)" -ForegroundColor Green
            $javaOk = $true
        } elseif ($majorVersion -eq 1) {
            # Handle Java 8 format (1.8.x)
            $minorVersion = [int]$matches[2]
            if ($minorVersion -ge 11) {
                Write-Host "✓ Java version is compatible" -ForegroundColor Green
                $javaOk = $true
            } else {
                Write-Host "✗ Java $majorVersion.$minorVersion is too old. Need Java 11+" -ForegroundColor Red
                $javaOk = $false
            }
        } else {
            Write-Host "✗ Java $majorVersion is too old. Need Java 11+" -ForegroundColor Red
            $javaOk = $false
        }
    } else {
        Write-Host "⚠ Could not parse Java version" -ForegroundColor Yellow
        $javaOk = $false
    }
} catch {
    Write-Host "✗ Java is not installed or not in PATH" -ForegroundColor Red
    $javaOk = $false
}

Write-Host ""
Write-Host "Checking JAVA_HOME..." -ForegroundColor Yellow
if ($env:JAVA_HOME) {
    Write-Host "JAVA_HOME: $env:JAVA_HOME" -ForegroundColor Green
} else {
    Write-Host "⚠ JAVA_HOME is not set" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Checking Gradle..." -ForegroundColor Yellow
if (Test-Path "gradlew.bat") {
    Write-Host "✓ Found Gradle wrapper" -ForegroundColor Green
    
    if ($javaOk) {
        Write-Host "Attempting to check Gradle version..." -ForegroundColor Yellow
        try {
            $gradleOutput = & .\gradlew.bat --version 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ Gradle is working correctly!" -ForegroundColor Green
                Write-Host ""
                Write-Host "You can now build the Android app:" -ForegroundColor Cyan
                Write-Host "  .\gradlew.bat clean assembleDebug" -ForegroundColor White
            } else {
                Write-Host "✗ Gradle failed to run" -ForegroundColor Red
                Write-Host "Output: $gradleOutput" -ForegroundColor Gray
            }
        } catch {
            Write-Host "✗ Gradle failed to run: $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        Write-Host "⚠ Skipping Gradle check due to Java version issue" -ForegroundColor Yellow
    }
} else {
    Write-Host "✗ Gradle wrapper not found" -ForegroundColor Red
    Write-Host "Make sure you're in the android directory" -ForegroundColor Gray
}

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
    Write-Host "🔧 Option 2: Use Chocolatey (if installed)" -ForegroundColor Green
    Write-Host "   choco install openjdk17" -ForegroundColor White
    Write-Host ""
    Write-Host "🔧 Option 3: Use Android Studio (Easiest)" -ForegroundColor Green
    Write-Host "   1. Install Android Studio from https://developer.android.com/studio" -ForegroundColor White
    Write-Host "   2. Open the 'android' folder as a project" -ForegroundColor White
    Write-Host "   3. Android Studio will handle Java compatibility automatically" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "🎉 Your Java setup looks good!" -ForegroundColor Green
    Write-Host "You should be able to build the Android app now." -ForegroundColor White
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Read-Host "Press Enter to continue"