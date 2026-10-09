@echo off
rem Test: VFS with 3 and more levels of files and directories
python "%~dp0..\src\emulator.py" --vfs "%~dp0..\vfs\nested.csv" --script "%~dp0start_vfs.txt"
