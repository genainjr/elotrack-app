$shell = New-Object -ComObject Shell.Application
$folder = $shell.Namespace("C:\Users\messi\Music\EloTrack")
$item = $folder.ParseName("O Mar Se Abriu [0TL672ovTpk].wav")
0..40 | ForEach-Object {
    $n = $folder.GetDetailsOf($null, $_)
    $v = $folder.GetDetailsOf($item, $_)
    if ($v) {
        Write-Output ("$_ | $n = $v")
    }
}
