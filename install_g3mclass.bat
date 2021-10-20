rem Install g3mclass via pip in userspace and
rem create a launching script on user's Desktop

rem author: Serguei Sokol

@echo on
for /F "tokens=*" %%g in ('where python') do set pexe=%%g
if "%pexe%"=="" (@echo x=mx=msgbox("Python3 was not found on this system!", vbOKOnly+vbCritical, "g3mclass installer")>%tmp%\tmp.vbs & cscript //nologo %tmp%\tmp.vbs)
rem for /F "tokens=*" %%g in ('%pexe% -m site --user-site') do set psite=%%g

%pexe% -m pip install --user -U "https://drive.google.com/uc?export=download&id=1Zju4J6OcEvmD5E54CmD-V1ZdfSvYPX6l" && echo import g3mclass.g3mclass; g3mclass.g3mclass.main() > %userprofile%\desktop\run_g3mclass.pyw || echo pip did not work


@echo x=msgbox("g3mclass was successfully installed!" ^& vbCrLf ^& "To run it, use a newly created run_g3mclass.pyw on your desktop.",vbOKOnly,"g3mclass installer")> %tmp%\tmp.vbs & cscript //nologo %tmp%\tmp.vbs
del %tmp%\tmp.vbs
