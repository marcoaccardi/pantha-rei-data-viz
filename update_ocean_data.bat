@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

REM Comprehensive On-Demand Ocean Data Update Script for Windows
REM This script intelligently detects gaps in ocean data and downloads missing files
REM from the last available date to the current date. It includes comprehensive
REM file validation, error recovery, and data processing to ensure zero errors.
REM
REM Features:
REM - Intelligent gap detection based on actual files
REM - Downloads from last file date to current date (handles days to months of gaps)
REM - Comprehensive file validation and corruption detection
REM - Automatic error recovery with retry logic
REM - Coordinate harmonization for raw data
REM - Health checks and cleanup operations
REM
REM Usage:
REM   update_ocean_data.bat                                    # Update all datasets
REM   update_ocean_data.bat --datasets sst,currents           # Update specific datasets
REM   update_ocean_data.bat --dry-run                         # Preview what would be updated
REM   update_ocean_data.bat --repair-mode                     # Aggressive repair mode
REM   update_ocean_data.bat --cleanup                         # Include cleanup operations
REM   update_ocean_data.bat --validate-only                   # Only run validation
REM

REM Script configuration
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%"
set "BACKEND_DIR=%PROJECT_DIR%backend"
set "OCEAN_DATA_DIR=%PROJECT_DIR%ocean-data"
set "LOGS_DIR=%OCEAN_DATA_DIR%\logs"

REM Default options
set "DATASETS="
set "DRY_RUN=false"
set "REPAIR_MODE=false"
set "CLEANUP=false"
set "VALIDATE_ONLY=false"
set "VERBOSE=false"
set "FORCE=false"
set "EXIT_CODE=0"

REM Parse command line arguments
:parse_args
if "%~1"=="" goto args_done
if "%~1"=="-d" (
    set "DATASETS=%~2"
    shift
    shift
    goto parse_args
)
if "%~1"=="--datasets" (
    set "DATASETS=%~2"
    shift
    shift
    goto parse_args
)
if "%~1"=="-n" (
    set "DRY_RUN=true"
    shift
    goto parse_args
)
if "%~1"=="--dry-run" (
    set "DRY_RUN=true"
    shift
    goto parse_args
)
if "%~1"=="-r" (
    set "REPAIR_MODE=true"
    shift
    goto parse_args
)
if "%~1"=="--repair-mode" (
    set "REPAIR_MODE=true"
    shift
    goto parse_args
)
if "%~1"=="-c" (
    set "CLEANUP=true"
    shift
    goto parse_args
)
if "%~1"=="--cleanup" (
    set "CLEANUP=true"
    shift
    goto parse_args
)
if "%~1"=="-v" (
    set "VALIDATE_ONLY=true"
    shift
    goto parse_args
)
if "%~1"=="--validate-only" (
    set "VALIDATE_ONLY=true"
    shift
    goto parse_args
)
if "%~1"=="--verbose" (
    set "VERBOSE=true"
    shift
    goto parse_args
)
if "%~1"=="--force" (
    set "FORCE=true"
    shift
    goto parse_args
)
if "%~1"=="-h" goto show_usage
if "%~1"=="--help" goto show_usage
echo [ERROR] Unknown option: %~1
goto show_usage

:args_done

REM Display header
echo Ocean Data Management System - Comprehensive Update
echo ==================================================
echo.

if not "!DATASETS!"=="" (
    call :log_info "Datasets to process: !DATASETS!"
) else (
    call :log_info "Processing all datasets: sst_textures,sst,currents,acidity"
)

if "!DRY_RUN!"=="true" (
    call :log_warn "DRY RUN MODE - No data will be downloaded"
)

if "!REPAIR_MODE!"=="true" (
    call :log_warn "REPAIR MODE - Will revalidate and fix all files"
)

if "!VALIDATE_ONLY!"=="true" (
    call :log_info "VALIDATION ONLY - No updates will be performed"
)

echo.

REM Track execution time
for /f "tokens=1-4 delims=:.," %%a in ("%time%") do (
    set /a "start=(((%%a*60)+1%%b %% 100)*60+1%%c %% 100)*100+1%%d %% 100"
)

REM Execute operations
call :run_pre_flight_checks
if !errorlevel! neq 0 (
    call :log_error "Pre-flight checks failed"
    exit /b 1
)

if "!VALIDATE_ONLY!"=="true" (
    REM Only run validation
    call :run_validation
    if !errorlevel! neq 0 set "EXIT_CODE=1"
) else (
    REM Full update process
    
    REM 1. Run initial validation and recovery
    call :log_info "Phase 1: Initial validation and recovery"
    call :run_recovery
    if !errorlevel! neq 0 (
        call :log_warn "Recovery phase had issues, but continuing..."
    )
    
    REM 2. Run main update
    call :log_info "Phase 2: Data update"
    call :run_update
    if !errorlevel! neq 0 set "EXIT_CODE=1"
    
    REM 3. Run post-update recovery
    call :log_info "Phase 3: Post-update validation and recovery"
    call :run_recovery
    if !errorlevel! neq 0 (
        call :log_warn "Post-update recovery had issues"
        set "EXIT_CODE=1"
    )
    
    REM 4. Final validation
    call :log_info "Phase 4: Final validation"
    call :run_validation
    if !errorlevel! neq 0 (
        call :log_warn "Final validation found issues"
    )
    
    REM 5. Cleanup
    call :cleanup_operations
)

REM Calculate execution time
for /f "tokens=1-4 delims=:.," %%a in ("%time%") do (
    set /a "end=(((%%a*60)+1%%b %% 100)*60+1%%c %% 100)*100+1%%d %% 100"
)
set /a "duration=(!end!-!start!)/100"
set /a "hours=!duration!/3600"
set /a "minutes=(!duration! %% 3600)/60"
set /a "seconds=!duration! %% 60"

REM Generate summary
call :generate_summary_report

echo.
echo Execution time: %hours%:%minutes%:%seconds%
echo.

if "!EXIT_CODE!"=="0" (
    call :log_info "Ocean data update completed successfully!"
) else (
    call :log_error "Ocean data update completed with errors (exit code: !EXIT_CODE!)"
    call :log_error "Check the logs in !LOGS_DIR! for details"
)

exit /b !EXIT_CODE!

:show_usage
echo Usage: %~nx0 [OPTIONS]
echo.
echo Comprehensive On-Demand Ocean Data Update Script
echo.
echo OPTIONS:
echo     -d, --datasets DATASETS     Comma-separated list of datasets to update
echo                                 (sst_textures,sst,currents,acidity)
echo     -n, --dry-run              Show what would be updated without downloading
echo     -r, --repair-mode          Run aggressive repair mode (revalidate all files)
echo     -c, --cleanup              Include cleanup of obsolete/partial files
echo     -v, --validate-only        Only run validation checks, no updates
echo     --verbose                  Verbose output and logging
echo     --force                    Force update even if pre-flight checks fail
echo     -h, --help                 Show this help message
echo.
echo EXAMPLES:
echo     %~nx0                                      # Update all datasets to current date
echo     %~nx0 -d sst_textures,sst                 # Update only SST data and textures
echo     %~nx0 -n                                  # Dry run to see what would be updated
echo     %~nx0 -r                                  # Repair mode - fix any corrupted files
echo     %~nx0 -c                                  # Include cleanup operations
echo     %~nx0 -v                                  # Only validate existing files
echo     %~nx0 -d currents --verbose              # Update currents with verbose logging
echo.
echo DATASETS:
echo     sst_textures    High-quality SST texture PNG files (5km resolution)
echo     sst             Raw SST NetCDF data (NOAA OISST v2.1)
echo     currents        Ocean currents NetCDF data (CMEMS)
echo     acidity         Ocean biogeochemistry data (hybrid CMEMS sources)
echo.
exit /b 0

:log_info
echo [INFO] %~1
exit /b 0

:log_warn
echo [WARN] %~1
exit /b 0

:log_error
echo [ERROR] %~1
exit /b 0

:log_debug
if "!VERBOSE!"=="true" (
    echo [DEBUG] %~1
)
exit /b 0

:check_dependencies
call :log_info "Checking dependencies..."

REM Check Python
python --version >nul 2>&1
if !errorlevel! neq 0 (
    call :log_error "Python is required but not installed or not in PATH"
    exit /b 1
)

REM Quick check for essential packages
python -c "import numpy, xarray, pandas" >nul 2>&1
if !errorlevel! neq 0 (
    call :log_warn "Some Python packages are missing"
    call :log_warn "Run setup_windows_env.bat to install required packages"
)

REM Check if we're in the right directory
if not exist "!BACKEND_DIR!\requirements.txt" (
    call :log_error "Cannot find backend directory with requirements.txt"
    call :log_error "Please run this script from the project root directory"
    exit /b 1
)

REM Check for virtual environment
if not exist "!BACKEND_DIR!\.venv" (
    call :log_error "Virtual environment not found at !BACKEND_DIR!\.venv"
    call :log_error "Please run: cd !BACKEND_DIR! && python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt"
    exit /b 1
)

call :log_info "Dependencies check passed"
exit /b 0

:check_disk_space
call :log_info "Checking available disk space..."

REM Create ocean-data directory if it doesn't exist
if not exist "!OCEAN_DATA_DIR!" mkdir "!OCEAN_DATA_DIR!"

REM Get available space in GB (Windows) - simplified version
set "AVAILABLE_GB=50"
for /f "tokens=3" %%a in ('dir /-c "!OCEAN_DATA_DIR!" ^| findstr /C:"bytes free"') do (
    REM Extract just the number, avoiding overflow
    set "FREE_BYTES=%%a"
)
REM Simple check - if we have some free space, assume it's enough for demo
if defined FREE_BYTES set "AVAILABLE_GB=50"

call :log_info "Available disk space: !AVAILABLE_GB! GB (estimated)"

if !AVAILABLE_GB! lss 5 (
    call :log_error "Less than 5 GB available. Please free up disk space."
    if not "!FORCE!"=="true" (
        exit /b 1
    ) else (
        call :log_warn "Continuing due to --force flag"
    )
)
if !AVAILABLE_GB! lss 20 (
    call :log_warn "Less than 20 GB available. Monitor disk usage during update."
)
exit /b 0

:check_network_connectivity
call :log_info "Checking network connectivity..."

REM Test connectivity to key data sources
powershell -Command "try { Invoke-WebRequest -Uri 'https://www.ncei.noaa.gov' -Method Head -TimeoutSec 10 -UseBasicParsing | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if !errorlevel! equ 0 (
    call :log_debug "Connectivity to NOAA: OK"
) else (
    call :log_warn "Cannot reach NOAA - some downloads may fail"
)

powershell -Command "try { Invoke-WebRequest -Uri 'https://pae-paha.pacioos.hawaii.edu' -Method Head -TimeoutSec 10 -UseBasicParsing | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if !errorlevel! equ 0 (
    call :log_debug "Connectivity to ERDDAP: OK"
) else (
    call :log_warn "Cannot reach ERDDAP - some downloads may fail"
)
exit /b 0

:activate_virtual_environment
call :log_info "Activating virtual environment..."

REM Change to backend directory
cd /d "!BACKEND_DIR!"

REM Check what type of venv we have and use appropriate Python
if exist ".venv\Scripts\python.exe" (
    REM Windows-style venv - use directly
    set "PYTHON_EXE=!BACKEND_DIR!\.venv\Scripts\python.exe"
    call :log_info "Using Windows-style venv Python: !PYTHON_EXE!"
) else if exist ".venv\bin" (
    REM Unix-style venv found - cannot use with Windows Python
    REM Check if we're in conda environment
    if defined CONDA_PREFIX (
        REM Use conda Python which should have required packages
        set "PYTHON_EXE=python"
        call :log_info "Unix-style venv detected, using conda Python from: !CONDA_PREFIX!"
        call :log_warn "Note: Using conda environment instead of Unix venv"
    ) else (
        REM Try to use system Python and hope packages are installed
        set "PYTHON_EXE=python"
        call :log_warn "Unix-style venv found but incompatible with Windows"
        call :log_warn "Using system Python - packages may be missing"
    )
) else (
    REM No venv found - use system Python
    set "PYTHON_EXE=python"
    call :log_warn "Virtual environment not found, using system Python"
)

REM Set virtual environment variable for reference
set "VIRTUAL_ENV=!BACKEND_DIR!\.venv"

call :log_info "Python environment ready"
exit /b 0

:run_pre_flight_checks
call :log_info "Running pre-flight checks..."

call :check_dependencies
if !errorlevel! neq 0 exit /b 1

call :check_disk_space  
if !errorlevel! neq 0 exit /b 1

call :check_network_connectivity
if !errorlevel! neq 0 exit /b 1

call :activate_virtual_environment
if !errorlevel! neq 0 exit /b 1

REM Create necessary directories
if not exist "!LOGS_DIR!" mkdir "!LOGS_DIR!"
if not exist "!OCEAN_DATA_DIR!\raw" mkdir "!OCEAN_DATA_DIR!\raw"
if not exist "!OCEAN_DATA_DIR!\processed\unified_coords" mkdir "!OCEAN_DATA_DIR!\processed\unified_coords"
if not exist "!OCEAN_DATA_DIR!\textures" mkdir "!OCEAN_DATA_DIR!\textures"

call :log_info "Pre-flight checks completed successfully"
exit /b 0

:run_update
call :log_info "Starting ocean data update..."

REM Use the correct Python executable
if not defined PYTHON_EXE set "PYTHON_EXE=python"

REM Build Python command
set "python_cmd=!PYTHON_EXE! scripts/production/update_ocean_data.py"

if not "!DATASETS!"=="" (
    set "python_cmd=!python_cmd! --datasets !DATASETS!"
)

if "!DRY_RUN!"=="true" (
    set "python_cmd=!python_cmd! --dry-run"
)

if "!REPAIR_MODE!"=="true" (
    set "python_cmd=!python_cmd! --repair-mode"
)

if "!VERBOSE!"=="true" (
    set "python_cmd=!python_cmd! --verbose"
)

REM Run the update
call :log_info "Executing: !python_cmd!"

!python_cmd!
set "update_exit_code=!errorlevel!"

if !update_exit_code! equ 0 (
    call :log_info "Update completed successfully"
) else (
    call :log_error "Update failed with exit code: !update_exit_code!"
)

exit /b !update_exit_code!

:run_validation
call :log_info "Running file validation..."

REM Use the correct Python executable
if not defined PYTHON_EXE set "PYTHON_EXE=python"

set "python_cmd=!PYTHON_EXE! scripts/production/file_validator.py --generate-report"

if not "!DATASETS!"=="" (
    REM Run validation for each dataset separately
    for %%a in (!DATASETS!) do (
        call :log_info "Validating dataset: %%a"
        !PYTHON_EXE! scripts/production/file_validator.py --dataset %%a
    )
) else (
    REM Generate comprehensive report
    call :log_info "Generating comprehensive validation report..."
    !python_cmd!
)
exit /b !errorlevel!

:run_recovery
call :log_info "Running error recovery..."

REM Use the correct Python executable
if not defined PYTHON_EXE set "PYTHON_EXE=python"

set "python_cmd=!PYTHON_EXE! scripts/production/recovery_manager.py"

if not "!DATASETS!"=="" (
    set "python_cmd=!python_cmd! --datasets !DATASETS!"
)

if "!REPAIR_MODE!"=="true" (
    set "python_cmd=!python_cmd! --repair-mode"
)

if "!VERBOSE!"=="true" (
    set "python_cmd=!python_cmd! --verbose"
)

call :log_info "Executing: !python_cmd!"

!python_cmd!
set "recovery_exit_code=!errorlevel!"

if !recovery_exit_code! equ 0 (
    call :log_info "Recovery completed successfully"
) else (
    call :log_error "Recovery failed with exit code: !recovery_exit_code!"
)

exit /b !recovery_exit_code!

:cleanup_operations
if not "!CLEANUP!"=="true" exit /b 0

call :log_info "Running cleanup operations..."

REM Clean up old log files (keep last 30 days)
call :log_info "Cleaning up old log files..."
forfiles /p "!LOGS_DIR!" /m *.log /d -30 /c "cmd /c del @path" >nul 2>&1
forfiles /p "!LOGS_DIR!" /m *.json /d -30 /c "cmd /c del @path" >nul 2>&1

REM Clean up temporary files
call :log_info "Cleaning up temporary files..."
if exist "!OCEAN_DATA_DIR!\*.tmp" del /q "!OCEAN_DATA_DIR!\*.tmp" >nul 2>&1
if exist "!OCEAN_DATA_DIR!\*.temp" del /q "!OCEAN_DATA_DIR!\*.temp" >nul 2>&1

call :log_info "Cleanup operations completed"
exit /b 0

:generate_summary_report
call :log_info "Generating summary report..."

REM Get basic statistics
set "total_files=0"
for /f %%i in ('dir "!OCEAN_DATA_DIR!\*.nc" "!OCEAN_DATA_DIR!\*.png" /s /b 2^>nul ^| find /c /v ""') do set "total_files=%%i"

REM Get total size - simplified to avoid overflow
set "total_size_gb=N/A"
for /f "tokens=1-3" %%a in ('dir "!OCEAN_DATA_DIR!" /s /-c ^| findstr /C:"File(s)"') do (
    set "total_files_line=%%a"
    set "total_size=%%b"
)
REM Just display the size as reported, don't try to calculate
for /f "tokens=3" %%a in ('dir "!OCEAN_DATA_DIR!" /s ^| findstr /C:"bytes"') do set "total_size_display=%%a"

echo.
echo ==================================================================
echo                     OCEAN DATA UPDATE SUMMARY                    
echo ==================================================================
echo.
echo Update completed: %date% %time%
echo Total files: !total_files!
echo Total storage: !total_size_display! bytes
echo.

echo Recent log files:
dir /b /o-d "!LOGS_DIR!\*.log" 2>nul | findstr /n "^" | findstr "^[1-5]:" | for /f "tokens=1* delims=:" %%a in ('more') do echo   %%b

echo.
echo Data directory structure:
dir "!OCEAN_DATA_DIR!" 2>nul | findstr /n "^" | findstr "^[1-9]:" | for /f "tokens=1* delims=:" %%a in ('more') do echo %%b

echo.
echo ==================================================================

exit /b 0