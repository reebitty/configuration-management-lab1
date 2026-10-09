@echo off
rem Test: both parameters, script without errors
python "%~dp0..\src\emulator.py" --vfs "%~dp0..\vfs\nested.csv" --script "%~dp0start_ok.txt"
