$shell = New-Object -ComObject Shell.Application
$folder = $shell.Namespace("C:\workspace\lookup\elotrack-app\tests\temp_wav_test")
$item = $folder.ParseName("O Mar Se Abriu [0TL672ovTpk].wav")
Write-Output ("Title: " + $folder.GetDetailsOf($item, 21))
Write-Output ("Artists: " + $folder.GetDetailsOf($item, 20))
Write-Output ("Album: " + $folder.GetDetailsOf($item, 14))
