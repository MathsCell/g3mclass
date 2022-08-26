# Install g3mclass via pip in userspace and
# create a link on user's Desktop

# author: Serguei Sokol
$url = "g3mclass"
$pexe = (Get-Command python).path
If($pexe -eq "")
{
    Write-Output "Python was not found on this system.";  pause; exit
}
If($pexe -like "*conda*") {
   $pconda = Split-Path -Path "$pexe"
} else {
   $pconda = ""
}

Invoke-Expression "$pexe -mpip install --user -U $url"
$pdiri = Invoke-Expression "$pexe -c 'import g3mclass.g3mclass as g3; import os; print(os.path.dirname(g3.__file__))'"
# create a link on desktop
If($pconda -eq "") {
    $pref = "$pdiri\..\..\Scripts\g3mclass.exe"
    $parg = ""
} else {
    $pref = "$pconda\Scripts\conda"
    $parg = "run -n $env:CONDA_DEFAULT_ENV $pdiri\..\..\Scripts\g3mclass.exe"
}

$ShortcutPath = "$env:userprofile\Desktop\g3mclass.lnk"
$WScriptObj = New-Object -ComObject ("WScript.Shell")
$shortcut = $WscriptObj.CreateShortcut($ShortcutPath)
$shortcut.TargetPath = $pref
$shortcut.Arguments = "$parg"
$shortcut.WindowStyle = 7
$shortcut.IconLocation="$pdiri\g3m.ico"
$shortcut.Save()
