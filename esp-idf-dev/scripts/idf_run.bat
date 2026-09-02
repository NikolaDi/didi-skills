@echo off
rem Wrapper so idf.py runs from non-interactive shells (Git Bash / agents).
rem ESP-IDF's export.bat refuses to run when MSYSTEM is defined, and DOSKEY
rem macros created by idf_cmd_init.bat do not work inside batch scripts,
rem so idf.py is invoked through the venv Python explicitly.
rem
rem === EDIT THESE TWO LINES FOR THIS MACHINE ==============================
set "IDF_CMD_INIT=C:\Espressif\idf_cmd_init.bat"
set "IDF_ID="
rem IDF_CMD_INIT: full path to idf_cmd_init.bat (Espressif tools install root)
rem IDF_ID: optional idf-id parameter (esp-idf-<hash>); leave empty if the
rem         init script should resolve IDF by cwd / IDF_PATH instead.
rem ========================================================================
rem
rem Runs idf.py in the current directory if it is an IDF project (has
rem CMakeLists.txt); otherwise it errors out - cd into the project first.
rem Keep this file OUTSIDE any git repository: an untracked file in the repo
rem can pollute version metadata of builds.
setlocal
set "MSYSTEM="
if defined IDF_ID (
    call "%IDF_CMD_INIT%" %IDF_ID%
) else (
    call "%IDF_CMD_INIT%"
)
if not exist "%CD%\CMakeLists.txt" (
    echo [idf_run] current directory is not an IDF project - cd into the project dir first 1>&2
    exit /b 1
)
"%IDF_PYTHON%" "%IDF_PATH%\tools\idf.py" %*
