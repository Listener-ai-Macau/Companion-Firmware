#requires -Version 7.0
param([Parameter(Mandatory=$true)][string]$ConfigJsonPath)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms | Out-Null
Add-Type -AssemblyName System.Drawing | Out-Null
[System.Windows.Forms.Application]::EnableVisualStyles()

$cfg = Get-Content -LiteralPath $ConfigJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
$title = [string]$cfg.title
$progress = [string]$cfg.progress
$scope = [string]$cfg.scope
$message = [string]$cfg.message
$expected = [string]$cfg.expected
$outPath = [string]$cfg.output_path
$logPath = Join-Path (Split-Path $ConfigJsonPath) ("dialog-" + (Get-Date -Format "HHmmss") + ".log")
function L($m){ Add-Content $logPath ((Get-Date).ToString("HH:mm:ss.fff")+" "+$m) -Encoding utf8 }

L "start"
$form = New-Object System.Windows.Forms.Form
$form.Text = if ($progress) { "$title $progress" } else { $title }
$form.StartPosition = "CenterScreen"
$form.TopMost = $true
$form.MinimizeBox = $false
$form.MaximizeBox = $false
$form.FormBorderStyle = "FixedDialog"
$form.ClientSize = New-Object System.Drawing.Size(720, 420)
$form.Font = New-Object System.Drawing.Font("Microsoft YaHei UI", 10)
$form.AutoScaleMode = "Dpi"
$form.ShowInTaskbar = $true

$left=16; $width=688
# Title: "1/7  Companion 真机验收"  (Listener style)
$lblTitle = New-Object System.Windows.Forms.Label
$lblTitle.Font = New-Object System.Drawing.Font("Microsoft YaHei UI", 12, [Drawing.FontStyle]::Bold)
$lblTitle.SetBounds($left, 10, $width, 26)
$lblTitle.Text = if ($progress) { "$progress  $title" } else { $title }
$form.Controls.Add($lblTitle)

# Scope: "你现在做 - ..."
$lblScope = New-Object System.Windows.Forms.Label
$lblScope.SetBounds($left, 42, $width, 20)
$lblScope.Text = if ($scope) { "你现在做 - $scope" } else { "你现在做" }
$form.Controls.Add($lblScope)

# Message box
$msg = New-Object System.Windows.Forms.TextBox
$msg.Multiline=$true; $msg.ReadOnly=$true; $msg.ScrollBars="Vertical"
$msg.SetBounds($left, 64, $width, 72)
$msg.Text = $message
$form.Controls.Add($msg)

# 通过标准
$lblExp = New-Object System.Windows.Forms.Label
$lblExp.SetBounds($left, 144, $width, 20)
$lblExp.Text = "通过标准"
$form.Controls.Add($lblExp)
$exp = New-Object System.Windows.Forms.TextBox
$exp.Multiline=$true; $exp.ReadOnly=$true; $exp.ScrollBars="Vertical"
$exp.SetBounds($left, 166, $width, 62)
$exp.Text = $expected
$form.Controls.Add($exp)

# 备注
$lblNote = New-Object System.Windows.Forms.Label
$lblNote.SetBounds($left, 236, $width, 20)
$lblNote.Text = "备注（可留空；有异常、疑问或小瑕疵就写下来，我会当作需求处理）"
$form.Controls.Add($lblNote)
$note = New-Object System.Windows.Forms.TextBox
$note.Multiline=$true; $note.ScrollBars="Vertical"; $note.AcceptsReturn=$true
$note.SetBounds($left, 258, $width, 90)
$form.Controls.Add($note)

$script:selected = $null
function Save-Result([string]$sel) {
  $script:selected = $sel
  $dir = Split-Path -Parent $outPath
  if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  $obj = [ordered]@{
    selected=$sel; text=$note.Text; progress=$progress; title=$title
    at=(Get-Date).ToUniversalTime().ToString("o"); output_path=$outPath
  }
  [IO.File]::WriteAllText($outPath, ($obj|ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))
  L "saved $sel"
}

# Buttons right-to-left like Listener: 中止 跳过 失败 通过
$panel = New-Object System.Windows.Forms.FlowLayoutPanel
$panel.FlowDirection = "RightToLeft"
$panel.WrapContents = $false
$panel.SetBounds($left, 360, $width, 40)
$form.Controls.Add($panel)
foreach ($name in @("通过","失败","跳过","中止")) {
  $b = New-Object System.Windows.Forms.Button
  $b.Text = $name
  $b.Width = 86; $b.Height = 28
  $b.Margin = New-Object System.Windows.Forms.Padding(4,3,4,3)
  $b.Tag = $name
  $b.Add_Click({ Save-Result ([string]$this.Tag); $form.Close() })
  [void]$panel.Controls.Add($b)
}

$form.AcceptButton = $null
$form.CancelButton = $null
$form.Add_Shown({ L "shown"; $form.Activate(); $form.BringToFront(); $note.Focus() })
$form.Add_FormClosing({ if (-not $script:selected) { Save-Result "关闭" }; L "closing $($script:selected)" })

L "ShowDialog"
[void]$form.ShowDialog()
L "done $($script:selected)"
Write-Output ("selected=" + $script:selected)