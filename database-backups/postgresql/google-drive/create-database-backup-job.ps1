$TaskName = "Python-PostgreSQL-Database-Backup-To-Google-Drive"
$TaskExists = Get-ScheduledTask | Where-Object {$_.TaskName -eq $TaskName}

$Action = New-ScheduledTaskAction -Execute "C:\ProgramData\anaconda3\python.exe" -Argument "C:\Python\database-backup.py" -WorkingDirectory "C:\Python\"
# Adjust the schedule here
$Trigger = New-ScheduledTaskTrigger -Daily -At 11pm
$Principal = New-ScheduledTaskPrincipal -UserId "NT AUTHORITY\SYSTEM" -LogonType ServiceAccount
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -DontStopOnIdleEnd
$Task = New-ScheduledTask -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings

if ($TaskExists) {
    Write-Output "Task already exists. Updating..."
    Set-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings
} else {
    Write-Output "Creating new task..."
    Register-ScheduledTask -TaskName $TaskName -InputObject $Task
}
