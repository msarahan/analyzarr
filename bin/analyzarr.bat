@echo off
rem First we check for WinPython installs
if exist {%~dp0env.bat} (
 call %~dp0env.bat   
 cd %WINPYDIR%\Scripts
 %WINPYDIR%\python.exe analyzarr %* 
rem Otherwise, we try the traditional way...
) else (
  set path=%~dp0;%~dp0\..\;%PATH%\
  start python.exe %~dp0\analyzarr %*

)
