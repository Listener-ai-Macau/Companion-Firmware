param([Parameter(Mandatory=$true)][string]$SessionDirectory,[switch]$ReplayForAgent)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$sessionPath=[System.IO.Path]::GetFullPath($SessionDirectory)
$statePath=Join-Path $sessionPath 'ui-state.json'
$eventPath=Join-Path $sessionPath 'operator-actions.jsonl'
$script:state=$null
$script:closed=$false
$script:imuLayout=$false
$form=[System.Windows.Forms.Form]::new()
$form.Text='Companion 外设检查'
$form.ClientSize=[System.Drawing.Size]::new(780,510)
$form.StartPosition='CenterScreen';$form.TopMost=$true
if($ReplayForAgent){$form.TopMost=$false}
$form.FormBorderStyle='FixedDialog';$form.MaximizeBox=$false;$form.AutoScaleMode='Dpi'
$form.Font=[System.Drawing.Font]::new('Microsoft YaHei UI',11)
function Label([string]$Text,[int]$Y,[int]$Height,[int]$Size) {
    $v=[System.Windows.Forms.Label]::new();$v.Text=$Text
    $v.Location=[System.Drawing.Point]::new(20,$Y);$v.Size=[System.Drawing.Size]::new(740,$Height)
    $v.Font=[System.Drawing.Font]::new('Microsoft YaHei UI',$Size)
    [void]$form.Controls.Add($v);return $v
}
$heading=Label '本次只检查一个外设' 16 38 17
$status=Label '正在准备，请稍候' 65 45 14
$instructions=Label '请按窗口提示操作。' 116 105 12
$live=Label '' 228 60 12
$pose=[System.Windows.Forms.Panel]::new();$pose.Visible=$false
$pose.Location=[System.Drawing.Point]::new(580,224);$pose.Size=[System.Drawing.Size]::new(180,92)
$pose.BackColor=[System.Drawing.Color]::White
$pose.Add_Paint({param($sender,$eventArgs)
    $g=$eventArgs.Graphics;$g.SmoothingMode='AntiAlias'
    $v=if($script:state){$script:state.imuVisual}else{$null}
    $pen=[System.Drawing.Pen]::new([System.Drawing.Color]::LightGray,2)
    $brush=[System.Drawing.SolidBrush]::new([System.Drawing.Color]::RoyalBlue)
    try{
        $g.DrawEllipse($pen,61,27,58,58)
        if($v){
            $x=90+([double]$v.gravityX*27);$y=56+([double]$v.gravityY*27)
            $g.FillEllipse($brush,[single]($x-6),[single]($y-6),12,12)
            if([bool]$v.moving){$pen.Color=[System.Drawing.Color]::RoyalBlue;$g.DrawEllipse($pen,57,23,66,66)}
            $g.DrawString([string]$v.caption,$sender.Font,[System.Drawing.Brushes]::RoyalBlue,25,2)
        }else{$g.DrawString('等待实时姿态',$sender.Font,[System.Drawing.Brushes]::Gray,25,2)}
    }finally{$pen.Dispose();$brush.Dispose()}
})
[void]$form.Controls.Add($pose)
$hold=[System.Windows.Forms.ProgressBar]::new();$hold.Visible=$false
$hold.Location=[System.Drawing.Point]::new(20,300);$hold.Size=[System.Drawing.Size]::new(540,14)
[void]$form.Controls.Add($hold)
$notesLabel=Label '备注（可留空）' 295 22 10
$notes=[System.Windows.Forms.TextBox]::new();$notes.Multiline=$true
$notes.Location=[System.Drawing.Point]::new(20,322);$notes.Size=[System.Drawing.Size]::new(740,52)
[void]$form.Controls.Add($notes)
function Record([string]$Action) {
    $r=[ordered]@{action=$Action;actor=if($ReplayForAgent){'agent-replay'}else{'owner'};atLocal=[DateTimeOffset]::Now.ToString('o');note=$notes.Text
        phaseAtClick=if($script:state){$script:state.phase}else{'preparing'}
        stepAtClick=if($script:state){$script:state.step}else{$null}}
    $w=[System.IO.StreamWriter]::new($eventPath,$true,[System.Text.UTF8Encoding]::new($false))
    try{$w.WriteLine(($r|ConvertTo-Json -Compress));$w.Flush()}finally{$w.Dispose()}
}
function Button([string]$Text,[string]$Action,[int]$X,[int]$Width) {
    $v=[System.Windows.Forms.Button]::new();$v.Text=$Text;$v.Tag=$Action
    $v.Location=[System.Drawing.Point]::new($X,390);$v.Size=[System.Drawing.Size]::new($Width,45)
    $v.Enabled=$false
    $v.Add_Click({param($sender,$eventArgs);$sender.Enabled=$false;Record ([string]$sender.Tag)})
    [void]$form.Controls.Add($v);return $v
}
$start=Button '开始' 'start' 20 140
$pass=Button '通过' 'pass' 170 140
$fail=Button '有异常' 'fail' 320 140
$none=Button '完全无声' 'no_sound' 470 140
$skip=Button '尚未观察' 'skip' 620 140
$stop=[System.Windows.Forms.Button]::new();$stop.Text='停止并关闭'
$stop.Location=[System.Drawing.Point]::new(605,457);$stop.Size=[System.Drawing.Size]::new(155,32)
$stop.Add_Click({$form.Close()});[void]$form.Controls.Add($stop)
$trace=[System.Windows.Forms.Button]::new();$trace.Text='查看追溯资料'
$trace.Location=[System.Drawing.Point]::new(20,457);$trace.Size=[System.Drawing.Size]::new(155,32)
[void]$form.Controls.Add($trace)
$details=[System.Windows.Forms.TextBox]::new();$details.Multiline=$true;$details.ReadOnly=$true
$details.ScrollBars='Vertical';$details.Visible=$false
$details.Location=[System.Drawing.Point]::new(20,510);$details.Size=[System.Drawing.Size]::new(740,140)
[void]$form.Controls.Add($details)
$trace.Add_Click({$details.Visible=-not $details.Visible;$baseHeight=if($script:imuLayout){530}else{510};$form.ClientSize=[System.Drawing.Size]::new(780,($baseHeight+$(if($details.Visible){160}else{0})))})
$timer=[System.Windows.Forms.Timer]::new();$timer.Interval=200
$timer.Add_Tick({
    try {
        $sharing=[System.IO.FileShare]::ReadWrite -bor [System.IO.FileShare]::Delete
        $stream=[System.IO.FileStream]::new($statePath,[System.IO.FileMode]::Open,[System.IO.FileAccess]::Read,$sharing)
        $reader=$null
        try {
            $reader=[System.IO.StreamReader]::new($stream,[System.Text.Encoding]::UTF8,$true)
            $contents=$reader.ReadToEnd()
        } finally {
            if($reader){$reader.Dispose()}else{$stream.Dispose()}
        }
        $script:state=$contents|ConvertFrom-Json
        $s=$script:state;$form.Text=[string]$s.title;$heading.Text=[string]$s.heading
        if([string]$s.uiKind -eq 'imu' -and -not $script:imuLayout){
            $script:imuLayout=$true;$form.ClientSize=[System.Drawing.Size]::new(780,530)
            $live.Size=[System.Drawing.Size]::new(540,68);$pose.Visible=$true;$hold.Visible=$true
            $notesLabel.Top=322;$notes.Top=349;$notes.Height=42
            foreach($button in @($start,$pass,$fail,$none,$skip)){$button.Top=408}
            $stop.Top=477;$trace.Top=477;$details.Top=530
        }
        if($script:imuLayout){
            $hold.Value=if($s.imuVisual){[Math]::Min(100,[Math]::Max(0,[int]$s.imuVisual.holdPercent))}else{0}
            $pose.Invalidate()
        }
        $status.Text=[string]$s.status;$instructions.Text=[string]$s.instructions;$live.Text=[string]$s.live
        $details.Text=[string]$s.details
        $status.ForeColor=switch([string]$s.color){'green'{[System.Drawing.Color]::ForestGreen};'red'{[System.Drawing.Color]::Firebrick};default{[System.Drawing.Color]::DarkOrange}}
        $start.Text=[string]$s.startLabel;$pass.Text=[string]$s.passLabel;$fail.Text=[string]$s.failLabel
        $start.Enabled=[bool]$s.canStart
        $pass.Enabled=if($null -ne $s.canPass){[bool]$s.canPass}else{[bool]$s.canRespond}
        $fail.Enabled=[bool]$s.canRespond;$skip.Enabled=[bool]$s.canRespond
        $none.Visible=[bool]$s.showNoSound;$none.Enabled=[bool]$s.canRespond
        if($ReplayForAgent -and $s.renderReceipt){
            $form.Refresh()
            $r=[ordered]@{mode='HOST_UI_REPLAY_NO_BOARD_ACCESS';atLocal=[DateTimeOffset]::Now.ToString('o')
                replayCase=[string]$s.renderReceipt;status=$status.Text;live=$live.Text;imuLayout=$script:imuLayout
                formSize=$form.ClientSize.ToString();poseVisible=$pose.Visible;holdValue=$hold.Value
                visual=$s.imuVisual}
            $path=Join-Path $sessionPath ('render-'+[string]$s.renderReceipt+'.json')
            if(-not [System.IO.File]::Exists($path)){
                [System.IO.File]::WriteAllText($path,($r|ConvertTo-Json -Depth 6),[System.Text.UTF8Encoding]::new($false))
                $bitmap=[System.Drawing.Bitmap]::new($form.Width,$form.Height)
                try{$form.DrawToBitmap($bitmap,[System.Drawing.Rectangle]::new(0,0,$form.Width,$form.Height));$bitmap.Save((Join-Path $sessionPath ('render-'+[string]$s.renderReceipt+'.png')))}finally{$bitmap.Dispose()}
            }
        }
        if($ReplayForAgent -and [string]$s.phase -eq 'replay_finished'){$form.Close()}
    } catch {if($ReplayForAgent){[System.IO.File]::AppendAllText((Join-Path $sessionPath 'render-errors.log'),($_.ToString()+[Environment]::NewLine))}}
})
$form.Add_Shown({
    $r=[ordered]@{shownAtLocal=[DateTimeOffset]::Now.ToString('o');processId=$PID;bounds=$form.Bounds.ToString()}
    [System.IO.File]::WriteAllText((Join-Path $sessionPath 'popup-ready.json'),($r|ConvertTo-Json),[System.Text.UTF8Encoding]::new($false))
    [Console]::WriteLine('POPUP_SHOWN '+$sessionPath)
    $form.Activate();$form.BringToFront();$timer.Start()
})
$form.Add_FormClosing({if(-not $script:closed){Record 'close';$script:closed=$true}})
try{[void]$form.ShowDialog()}finally{$timer.Stop();$timer.Dispose();$form.Dispose()}
