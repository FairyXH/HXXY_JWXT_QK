@echo off
cd "%~dp0"
for /f "delims=" %%i in ('where pyinstaller') do (copy /Y upx.exe "%%~dpiupx.exe")
python vercode.py
for /r %cd% %%i in (*.py) do (if %%~zi leq 3072000 black "%%i")
pyinstaller --version-file=file_version_info.txt -n main -i icon.ico --onefile main.py
move /Y dist\main.exe main.exe
rd /s /q build
rd /s /q dist
del /f /q *.spec
attrib +h .idea
timeout /t 3
exit