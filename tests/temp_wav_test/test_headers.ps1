$shell = New-Object -ComObject Shell.Application
$folder = $shell.Namespace("C:\workspace\lookup\elotrack-app\tests\temp_wav_test")
0..50 | ForEach-Object {
    $name = $folder.GetDetailsOf($null, $_)
    if ($name) {
        Write-Output ("$_ : $name")
    }
}
