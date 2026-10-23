$shell = New-Object -ComObject Shell.Application
$folder = $shell.Namespace("C:\workspace\lookup\elotrack-app\tests\temp_wav_test")
$item = $folder.ParseName("O Mar Se Abriu [0TL672ovTpk].wav")
0..40 | ForEach-Object {
    $n = $folder.GetDetailsOf($null, $_)
    $v = $folder.GetDetailsOf($item, $_)
    if ($v) {
        Write-Output ("$_ | $n = $v")
    }
}
