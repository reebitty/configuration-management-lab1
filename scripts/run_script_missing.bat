@echo off
rem Test: both parameters, script file does not exist
python "%~dp0..\src\emulator.py" --vfs "%~dp0..\vfs\nested.csv" --script "%~dp0missing_script.txt"
