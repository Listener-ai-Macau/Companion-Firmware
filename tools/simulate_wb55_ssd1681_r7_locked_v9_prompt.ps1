param([string]$OutputPath)
$result=[ordered]@{selected='通过';text='offline lifecycle replay selection';status='PASS_OWNER_R7_LOCKED_V9_CHOREOGRAPHY_VISUAL'}
[IO.File]::WriteAllText($OutputPath,(($result|ConvertTo-Json -Compress)+[Environment]::NewLine),[Text.UTF8Encoding]::new($false))
$result|ConvertTo-Json -Compress
