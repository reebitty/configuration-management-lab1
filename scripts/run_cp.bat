@echo off
rem Test: command cp (files, directories, errors) on VFS with 3 levels
python "%~dp0..\src\emulator.py" --vfs "%~dp0..\vfs\nested.csv" --script "%~dp0start_cp.txt"
