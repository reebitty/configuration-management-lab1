@echo off
rem Test: both parameters, script with errors
python "%~dp0..\src\emulator.py" --vfs "%~dp0..\vfs.csv" --script "%~dp0start_errors.txt"
