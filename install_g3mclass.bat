rem Install g3mclass via pip in userspace and
rem create a launching script on user's Desktop

rem author: Serguei Sokol
@echo on
rem v0.17.7
set url="https://drive.google.com/uc?export=download&id=1c29CXniyLcpH5XN05jrebl6gtsFLpBfB"

for /F "tokens=*" %%g in ('where python') do set pexe=%%g
if "%pexe%"=="" (@echo Python3 was not found on this system. && pause && exit)
for /F "tokens=*" %%g in ('%pexe% -m site --user-base') do set pbase=%%g
if not x%pexe:conda=%==x%pexe% (for %%F in ("%pexe%") do set pconda=%%~dpF)

%pexe% -m pip install --user -U %url%

rem create .vbs on desktop
echo Set WshShell = CreateObject^("WScript.Shell"^) > %userprofile%\desktop\g3mclass.vbs
echo | set /p="WshShell.Run " >> %userprofile%\desktop\g3mclass.vbs
if not "%pconda%"=="" (
    echo | set /p=""%pconda%Scripts\conda run -n %CONDA_DEFAULT_ENV% " & " >> %userprofile%\desktop\g3mclass.vbs
)
echo "python -c " ^& Chr^(34^) ^& "import g3mclass.g3mclass; g3mclass.g3mclass.main()" ^& Chr^(34^), 0 >> %userprofile%\desktop\g3mclass.vbs
echo Set WshShell = Nothing  >>  %userprofile%\desktop\g3mclass.vbs
