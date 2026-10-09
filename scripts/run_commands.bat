@echo off
rem Test: commands ls, cd, uniq, tree, cal on VFS with 3 levels
python "%~dp0..\src\emulator.py" --vfs "%~dp0..\vfs\nested.csv" --script "%~dp0start_commands.txt"
