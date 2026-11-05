param([Parameter(Mandatory=$true)][string]$SessionDirectory)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$sessionPath = [System.IO.Path]::GetFullPath($SessionDirectory)
$statePath = Join-Path $sessionPath 'ui-state.json'
$eventPath = Join-Path $sessionPath 'operator-actions.jsonl'
$script:state = $null
$script:closingRecorded = $false
$form = [System.Windows.Forms.Form]::new()
$form.Text = 'Companion 实体按键 — 同步检查'
$form.ClientSize = [System.Drawing.Size]::new(760,520)
$form.StartPosition = 'CenterScreen'
$form.TopMost = $true
$form.MaximizeBox = $false
$form.FormBorderStyle = 'FixedDialog'
$form.AutoScaleMode = 'Dpi'
$form.Font = [System.Drawing.Font]::new('Microsoft YaHei UI',10)
function Add-Label([string]$Text,[int]$Y,[int]$Height,[int]$FontSize=10) {
    $label = [System.Windows.Forms.Label]::new()
    $label.Text=$Text; $label.Location=[System.Drawing.Point]::new(20,$Y)
    $label.Size=[System.Drawing.Size]::new(720,$Height)
    $label.Font=[System.Drawing.Font]::new('Microsoft YaHei UI',$FontSize)
    [void]$form.Controls.Add($label)
    return $label
}
$heading=Add-Label '实体按键检查：你操作，我同步监控' 14 32 16
$statusLabel=Add-Label '正在准备检测窗口，请稍候……' 58 48 15
$statusLabel.ForeColor=[System.Drawing.Color]::DarkOrange
$instructions=Add-Label "等窗口显示绿色【正在采集】后，再短按并松开实体键 3 次。`r`n每次间隔约 1～2 秒，没有倒计时；屏幕可以保持原画面。" 112 68 11
$counts=Add-Label '本轮：按下 0 次    松开 0 次' 190 40 19
$live=Add-Label '当前按键：等待有效数据' 242 30 13
$last=Add-Label '最后变化：尚未收到' 278 25 10
$noteLabel=Add-Label '备注（可留空）' 315 22 10
$notes=[System.Windows.Forms.TextBox]::new()
$notes.Location=[System.Drawing.Point]::new(20,340);$notes.Size=[System.Drawing.Size]::new(720,52)
$notes.Multiline=$true;[void]$form.Controls.Add($notes)
function Add-Button([string]$Text,[int]$X,[int]$Width) {
    $button=[System.Windows.Forms.Button]::new()
    $button.Text=$Text;$button.Location=[System.Drawing.Point]::new($X,410)
    $button.Size=[System.Drawing.Size]::new($Width,40)
    [void]$form.Controls.Add($button);return $button
}
$connect=Add-Button '开始连接' 20 210
$done=Add-Button '我已按完' 245 145
$problem=Add-Button '有异常 / 失败' 405 145
$stop=Add-Button '停止并关闭' 565 175
$connect.Enabled=$false;$done.Enabled=$false;$problem.Enabled=$false
$detailsButton=[System.Windows.Forms.Button]::new()
$detailsButton.Text='查看追溯资料';$detailsButton.Location=[System.Drawing.Point]::new(20,467)
$detailsButton.Size=[System.Drawing.Size]::new(145,30);[void]$form.Controls.Add($detailsButton)
$footer=[System.Windows.Forms.Label]::new()
$footer.Text='仅测按键 · 无操作倒计时 · 自动保存数据和反馈'
$footer.Location=[System.Drawing.Point]::new(185,474);$footer.Size=[System.Drawing.Size]::new(555,24)
[void]$form.Controls.Add($footer)
$details=[System.Windows.Forms.TextBox]::new()
$details.Multiline=$true;$details.ReadOnly=$true;$details.ScrollBars='Vertical'
$details.Location=[System.Drawing.Point]::new(20,512);$details.Size=[System.Drawing.Size]::new(720,155)
$details.Visible=$false;[void]$form.Controls.Add($details)
$detailsButton.Add_Click({
    $details.Visible=-not $details.Visible
    $form.ClientSize=[System.Drawing.Size]::new(760, $(if($details.Visible){685}else{520}))
})
function Write-Action([string]$Action) {
    $record=[ordered]@{
        action=$Action; atLocal=[DateTimeOffset]::Now.ToString('o'); note=$notes.Text
        phaseAtClick=if($script:state){$script:state.phase}else{'preparing'}
        pressesAtClick=if($script:state){$script:state.presses}else{0}
        releasesAtClick=if($script:state){$script:state.releases}else{0}
    }
    $writer=[System.IO.StreamWriter]::new($eventPath,$true,[System.Text.UTF8Encoding]::new($false))
    try {$writer.WriteLine(($record|ConvertTo-Json -Compress));$writer.Flush()}finally{$writer.Dispose()}
}
$connect.Add_Click({$connect.Enabled=$false;Write-Action 'connect'})
$done.Add_Click({$done.Enabled=$false;Write-Action 'done'})
$problem.Add_Click({$problem.Enabled=$false;Write-Action 'problem'})
$stop.Add_Click({$form.Close()})
$timer=[System.Windows.Forms.Timer]::new();$timer.Interval=200
$timer.Add_Tick({
    try {
        if(-not(Test-Path -LiteralPath $statePath)){return}
        $script:state=Get-Content -LiteralPath $statePath -Raw -Encoding UTF8|ConvertFrom-Json
        $s=$script:state
        $statusLabel.Text=[string]$s.status
        $statusLabel.ForeColor=switch([string]$s.color){'green'{[System.Drawing.Color]::ForestGreen};'red'{[System.Drawing.Color]::Firebrick};default{[System.Drawing.Color]::DarkOrange}}
        $instructions.Text=[string]$s.instructions
        $counts.Text=if($s.keyState -eq '等待有效数据'){'本轮计数：尚无有效数据'}else{"本轮：按下 $($s.presses) 次    松开 $($s.releases) 次"}
        $live.Text="当前按键：$($s.keyState)"
        $last.Text="最后变化：$($s.lastEvent)"
        $connect.Enabled=[bool]$s.canConnect
        $connect.Text=if($s.phase -in @('unavailable','interrupted')){'恢复供电/连接后重试'}else{'开始连接'}
        $done.Enabled=[bool]$s.canFinish
        $problem.Enabled=[bool]$s.canReportProblem
        $details.Text=[string]$s.details
    }catch{}
})
$form.Add_Shown({
    $ready=[ordered]@{shownAtLocal=[DateTimeOffset]::Now.ToString('o');processId=$PID;bounds=$form.Bounds.ToString()}
    [System.IO.File]::WriteAllText((Join-Path $sessionPath 'popup-ready.json'),($ready|ConvertTo-Json),[System.Text.UTF8Encoding]::new($false))
    [Console]::WriteLine('POPUP_SHOWN '+$sessionPath)
    $form.Activate();$form.BringToFront();$timer.Start()
})
$form.Add_FormClosing({
    if(-not $script:closingRecorded){Write-Action 'close';$script:closingRecorded=$true}
})
try{[void]$form.ShowDialog()}finally{$timer.Stop();$timer.Dispose();$form.Dispose()}
