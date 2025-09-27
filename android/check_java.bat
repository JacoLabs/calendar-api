@echo off
echo ========================================
echo Android App Java Version Checker
echo ========================================
echo.

echo Checking Java version...
java -version 2>&1 | findstr "version"
if %errorlevel% neq 0 (
    echo ERROR: Java is not installed or not in PATH
    echo.
    echo Please install Java 11 or newer:
    echo 1. Go to https://adoptium.net/
    echo 2. Download Java 17 for Windows
    echo 3. Install and restart your terminal
    echo.
    pause
    exit /b 1
)

echo.
echo Checking JAVA_HOME...
if "%JAVA_HOME%"=="" (
    echo WARNING: JAVA_HOME is not set
    echo This might cause build issues
) else (
    echo JAVA_HOME: %JAVA_HOME%
)

echo.
echo Checking Gradle...
if exist "gradlew.bat" (
    echo Found Gradle wrapper
    echo Attempting to check Gradle version...
    call gradlew.bat --version 2>nul
    if %errorlevel% neq 0 (
        echo ERROR: Gradle failed to run
        echo This is likely due to Java version incompatibility
        echo.
        echo SOLUTION: Upgrade to Java 11 or newer
        echo Current requirement: Java 11+ for Android development
    ) else (
        echo Gradle is working correctly!
        echo.
        echo You can now build the Android app:
        echo   gradlew.bat clean assembleDebug
    )
) else (
    echo ERROR: Gradle wrapper not found
    echo Make sure you're in the android directory
)

echo.
echo ========================================
echo Summary:
echo ========================================
echo - Java 8 is installed but Android requires Java 11+
echo - Recommended: Install Java 17 from https://adoptium.net/
echo - Alternative: Use Android Studio (includes compatible JDK)
echo ========================================
echo.
pause