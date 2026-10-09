@echo off
rem Test: VFS with several files (text, empty and binary)
python "%~dp0..\src\emulator.py" --vfs "%~dp0..\vfs\files.csv" --script "%~dp0start_vfs.txt"
