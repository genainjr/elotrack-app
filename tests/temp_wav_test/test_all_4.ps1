$shell = New-Object -ComObject Shell.Application
$folder = $shell.Namespace("C:\workspace\lookup\elotrack-app\tests\temp_wav_test")
1..4 | ForEach-Object {
    $fname = "test_meta_$_.wav"
    $item = $folder.ParseName($fname)
    $t = $folder.GetDetailsOf($item, 21)
    $a = $folder.GetDetailsOf($item, 13)
    $al = $folder.GetDetailsOf($item, 14)
    Write-Output ("$fname -> Title: '$t', Artist: '$a', Album: '$al'")
}
