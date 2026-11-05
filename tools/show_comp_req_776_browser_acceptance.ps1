param(
    [string] $Package = ".cache\validation\comp776-component-clip-fix-20260812",
    [int] $TimeoutSeconds = 600
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$packagePath = (Resolve-Path (Join-Path $repo $Package)).Path
$machinePath = Join-Path $packagePath "MACHINE_READY.json"
$ownerResult = Join-Path $packagePath "owner-result.txt"
$selectionPath = Join-Path $packagePath "owner-selection.json"
$serialDir = Join-Path $packagePath "owner-acceptance-final-serial"
$machine = Get-Content -Raw -LiteralPath $machinePath | ConvertFrom-Json
if ($machine.status -ne "MACHINE_READY") {
    throw "COMP-REQ-776 is not machine ready: $machinePath"
}

Start-Process -FilePath (Join-Path $packagePath "bashful-motion-before-after.png")
Start-Process -FilePath (Join-Path $packagePath "expression-risk-and-ten-families.png")

$message = @"
COMP-REQ-776 generation 20 已完成机器闭环并刷到当前板；两张机器图集已经打开。

请在当前实屏依次确认：
1. 日常编舞运行时，双眼、眉毛、嘴、腮红和心形等饰件均完整；尤其 bashful 从 HOLD 到 anticipate/accent/follow 不再缺底行、断线或留下旧像素。
2. 开始录音只认“左下角双击”：日常正中间双击不得开始录音，只执行普通双击表情反应。进入后声波保持最快可用局刷；表情仍按自己的浏览器 life 节奏变化，饰件也保持独立，不随声波每帧同步；无脏屏、卡死、情绪跳错。
3. 录音已经开始后，可在任意位置双击退出；日常脸正常恢复。
4. 产品定义请勿混淆：操作/录音期间不得误入低功耗；连续 3 分钟无触控后才应进入一次静态 sleepy 脸（闭眼 + Z）并冻结。进入后白底和脸应干净、方向正确，触控后可正常唤醒。本轮定向日志已证明操作窗口 low_power_enter=0、sleepy=0；当时出现的是 bashful，不是低功耗。

包：$Package
App HEX SHA-256：$($machine.identity.app_hex_sha256)
App BIN SHA-256：$($machine.identity.app_bin_sha256)
generation/resource：$($machine.identity.generation) / $($machine.identity.resource_id)
页面 SHA-256：$($machine.identity.page_sha256)
外部资源读回 SHA-256：$($machine.identity.external_partition_sha256)
"@
$expected = "手势合同：未录音时仅左下角双击开始，正中双击不开始；录音后任意位置双击退出。低功耗合同：操作期间不得误入；静置 3 分钟后显示一次静态 sleepy 并冻结。通过：动作期间所有脸部组件/饰件完整；声波最快且表情/饰件独立；不脏不卡；低功耗无可见回退。失败：请选择失败并注明截断、同步、脏、卡、情绪错或其它具体部位。"

& pwsh -NoProfile -File (Join-Path $PSScriptRoot "capture_nucleo_serial.ps1") `
    -Execute `
    -PromptOperator `
    -Seconds 10 `
    -PromptTimeoutSeconds $TimeoutSeconds `
    -PromptTitle "COMP-REQ-776 动作组件完整性实机验收" `
    -PromptProgressText "generation 20 已刷入；等待 Owner 实屏验收" `
    -PromptScopeText "当前板：动作组件连续性 + 录音独立 + 低功耗防回退；串口与选择绑定落盘。" `
    -PromptMessage $message `
    -PromptExpectedText $expected `
    -PromptButtons "通过,失败,跳过,中止" `
    -PromptResultPath $ownerResult `
    -OutDir $serialDir
if ($LASTEXITCODE -ne 0) {
    throw "Owner acceptance capture failed with exit code $LASTEXITCODE"
}

$serialSummaryPath = Join-Path $serialDir "nucleo-serial-summary.json"
$serialSummary = Get-Content -Raw -LiteralPath $serialSummaryPath | ConvertFrom-Json
$operatorNote = if (Test-Path -LiteralPath $ownerResult) {
    (Get-Content -Raw -LiteralPath $ownerResult).Trim()
} else { "" }
$ownerLines = @("selection=$([string]$serialSummary.prompt_selection)")
if ($operatorNote) { $ownerLines += "note=$operatorNote" }
$ownerLines | Set-Content -LiteralPath $ownerResult -Encoding UTF8
$receipt = [ordered]@{
    schema = "companion.comp_req_776.component_fix_owner_selection.v1"
    selected = [string]$serialSummary.prompt_selection
    owner_result = $ownerResult
    owner_result_sha256 = if (Test-Path -LiteralPath $ownerResult) {
        (Get-FileHash -LiteralPath $ownerResult -Algorithm SHA256).Hash
    } else { $null }
    serial_summary = $serialSummaryPath
    serial_summary_sha256 = (Get-FileHash -LiteralPath $serialSummaryPath -Algorithm SHA256).Hash
    serial_log = [string]$serialSummary.raw_log
    serial_bytes = [int]$serialSummary.bytes_read
    package = $Package
    app_hex_sha256 = [string]$machine.identity.app_hex_sha256
    app_bin_sha256 = [string]$machine.identity.app_bin_sha256
    page_sha256 = [string]$machine.identity.page_sha256
    generation = [int]$machine.identity.generation
    resource_id = [string]$machine.identity.resource_id
    generated_at = (Get-Date).ToString("o")
}
$receipt | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $selectionPath -Encoding UTF8
$receipt | ConvertTo-Json -Depth 6
if ($receipt.selected -ne "通过") { exit 2 }
