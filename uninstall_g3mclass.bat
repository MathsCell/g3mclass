rem Uninstall g3mclass via pip in userspace and
rem remove a launching script on user's Desktop

rem author: Serguei Sokol
@echo on

for /F "tokens=*" %%g in ('where python') do set pexe=%%g
if "%pexe%"=="" (@echo Python3 was not found on this system. && pause && exit)

%pexe% -m pip uninstall g3mclass

rem remove .vbs on desktop
rem del  %userprofile%\desktop\g3mclass.vbs
rem remove .lnk on desktop
del  %userprofile%\desktop\g3mclass.lnk
