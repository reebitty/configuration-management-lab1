@echo off
rem Test: VFS file does not exist
python "%~dp0..\src\emulator.py" --vfs "%~dp0..\vfs\missing.csv" --script "%~dp0start_vfs.txt"
rem Test: VFS file with invalid data (not base64)
python "%~dp0..\src\emulator.py" --vfs "%~dp0..\vfs\bad.csv" --script "%~dp0start_vfs.txt"
