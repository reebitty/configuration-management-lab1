@echo off
rem Test: minimal VFS (only root directory)
python "%~dp0..\src\emulator.py" --vfs "%~dp0..\vfs\minimal.csv" --script "%~dp0start_vfs.txt"
