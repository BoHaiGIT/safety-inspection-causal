<#
  download_osha_v2.ps1
  ============================================================
  OSHA 真实数据下载器（美国劳工部 DOL 开放数据 API，无需 Python）
  ------------------------------------------------------------
  数据源（当前官方可用）：
    https://apiprod.dol.gov/v4/get/OSHA/{table}/csv
  可用表：inspection / accident / accident_abstract / violation / ...
  依赖：一个【免费】DOL API Key
        注册：https://dataportal.dol.gov/registration （2 分钟，邮箱验证）
  Key 提供方式（二选一）：
    1) 把 Key 单独一行写入本脚本同目录的 api_key.txt
    2) 设置环境变量 DOL_API_KEY
  运行：双击同目录的 download_osha_v2.bat
  输出：<脚本目录>\data\raw\inspection.csv / accident.csv / accident_abstract.csv
        + schema_probe.txt（字段表头） + download_report.txt（下载报告）
  ============================================================
#>

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = 'SilentlyContinue'
$ErrorActionPreference = "Stop"

# 模拟浏览器 UA，规避部分 .gov 前端的 WAF 拦截
$UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

$ScriptDir = $PSScriptRoot
$OutDir    = Join-Path $ScriptDir "data\raw"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$Host1  = "https://apiprod.dol.gov/v4"
$report = @()
$report += "OSHA 数据下载报告 (DOL Open Data API)"
$report += ("生成时间: " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
$report += ("输出目录: " + $OutDir)
$report += "============================================================"

# ---------- 读取 API Key ----------
$Key = $env:DOL_API_KEY
if (-not $Key) {
    $kf = Join-Path $ScriptDir "api_key.txt"
    if (Test-Path $kf) { $Key = (Get-Content $kf -Raw).Trim() }
}
if (-not $Key) {
    Write-Host "ERROR: 未找到 DOL API Key。" -ForegroundColor Red
    Write-Host "  1) 免费注册 https://dataportal.dol.gov/registration" 
    Write-Host "  2) 把 Key 单独一行写入本脚本同目录的 api_key.txt，或设置环境变量 DOL_API_KEY"
    Write-Host "     例如：echo '你的KEY' > api_key.txt"
    Read-Host "按回车退出"; exit 1
}

# ---------- URL 编码（保留 % 通配符，编码其余特殊字符）----------
function Encode-Filter($s) {
    $out = ""
    foreach ($c in $s.ToCharArray()) {
        if (($c -ge 'A' -and $c -le 'Z') -or ($c -ge 'a' -and $c -le 'z') -or
            ($c -ge '0' -and $c -le '9') -or $c -eq '-' -or $c -eq '_' -or
            $c -eq '.' -or $c -eq '~' -or $c -eq '%') {
            $out += $c
        } else {
            $out += '%' + ([int]$c).ToString('X2')
        }
    }
    return $out
}

# ---------- 单页抓取（含 429 限流退避 / 413 降量 / 超时重试）----------
function Fetch-Page($dataset, $filterJson, $offset, $limit) {
    $fo  = Encode-Filter $filterJson
    $url = "$Host1/get/OSHA/$dataset/csv?limit=$limit&offset=$offset&filter_object=$fo&X-API-KEY=$Key"
    $tmp = Join-Path $env:TEMP ("dol_" + (Get-Random) + ".tmp")
    $attempt = 0
    while ($true) {
        $attempt++
        try {
            Invoke-WebRequest -Uri $url -UserAgent $UA -OutFile $tmp -TimeoutSec 180 -ErrorAction Stop | Out-Null
            $lines = [System.IO.File]::ReadAllLines($tmp, [System.Text.Encoding]::UTF8)
            Remove-Item $tmp -Force -ErrorAction SilentlyContinue
            return $lines
        }
        catch [System.Net.WebException] {
            $resp = $_.Exception.Response
            if ($resp -and $resp.StatusCode -eq 429) {
                Write-Host "    429 限流，等待 65s 后重试..." -ForegroundColor Yellow
                Start-Sleep -Seconds 65
                if ($attempt -ge 8) { Remove-Item $tmp -Force -ErrorAction SilentlyContinue; throw "too many 429" }
                continue
            }
            elseif ($resp -and $resp.StatusCode -eq 413) {
                Remove-Item $tmp -Force -ErrorAction SilentlyContinue
                throw "413"
            }
            else {
                $status = if ($resp) { $resp.StatusCode } else { "none" }
                Remove-Item $tmp -Force -ErrorAction SilentlyContinue
                throw ("HTTP " + $status)
            }
        }
        catch {
            Remove-Item $tmp -Force -ErrorAction SilentlyContinue
            throw $_
        }
    }
}

# ---------- 整表下载（多 filter 变体自动回退；分页；限流自愈）----------
function Download-Table($dataset, $variants, $outFile) {
    $limit   = 10000
    $maxReq  = 20          # 安全上限：最多 20 次请求（约 20 万行），超出则报部分结果
    foreach ($v in $variants) {
        # 探测该变体是否有数据
        try {
            $p = Fetch-Page $dataset $v 0 1
            if ($p.Count -le 1) { Write-Host "  变体无数据，尝试下一个 filter..."; continue }
        }
        catch { Write-Host ("  变体探测出错: " + $_.Exception.Message); continue }

        Write-Host ("  采用 filter: " + $v)
        $offset = 0; $reqCount = 0; $first = $true; $total = 0
        while ($reqCount -lt $maxReq) {
            $reqCount++
            try {
                $lines = Fetch-Page $dataset $v $offset $limit
            }
            catch {
                if ($_.Exception.Message -eq "413") {
                    $limit = [math]::Floor($limit / 2)
                    $reqCount--
                    Write-Host ("    413 过大 -> 单页降至 " + $limit)
                    if ($limit -lt 500) { break }
                    continue
                }
                Write-Host ("    抓取失败 @offset=$offset : " + $_.Exception.Message)
                break
            }
            if ($lines.Count -le 1) { break }   # 无更多数据
            if ($first) {
                [System.IO.File]::WriteAllLines($outFile, $lines, [System.Text.Encoding]::UTF8)
                $first = $false
            }
            else {
                [System.IO.File]::AppendAllLines($outFile, ($lines | Select-Object -Skip 1), [System.Text.Encoding]::UTF8)
            }
            $got = $lines.Count - 1
            $total += $got
            Write-Host ("    offset " + $offset + " -> +" + $got + " (累计 " + $total + ")")
            if ($got -lt $limit) { break }
            $offset += $limit
            Start-Sleep -Seconds 1
        }
        if ($total -gt 0) { return $total }
    }
    return 0
}

# =================== 主流程 ===================
Write-Host "============================================================"
Write-Host "  OSHA 真实数据下载 (DOL Open Data API，无需 Python)"
Write-Host ("  输出目录: " + $OutDir)
Write-Host "============================================================"

# 1) 探测 API 主机可达性
try {
    Invoke-WebRequest -Uri "$Host1/datasets" -UserAgent $UA -TimeoutSec 30 -UseBasicParsing -ErrorAction Stop | Out-Null
    Write-Host "apiprod.dol.gov : REACHABLE (catalog)" -ForegroundColor Green
    $report += "apiprod.dol.gov : REACHABLE"
}
catch {
    Write-Host ("apiprod.dol.gov : UNREACHABLE (" + $_.Exception.Message + ")") -ForegroundColor Red
    $report += ("apiprod.dol.gov : UNREACHABLE (" + $_.Exception.Message + ")")
    Read-Host "无法连通 API 主机，按回车退出"; exit 1
}

# 2) 探测 Key 有效性
try {
    $p = Fetch-Page "inspection" "{}" 0 1
    Write-Host "API Key          : OK" -ForegroundColor Green
    $report += "API Key : OK"
}
catch {
    Write-Host ("API Key          : 无效或出错 (" + $_.Exception.Message + ")") -ForegroundColor Red
    $report += ("API Key : INVALID (" + $_.Exception.Message + ")")
    Read-Host "按回车退出"; exit 1
}

# 3) inspection —— 建筑业(NAICS 23) 2021-2023；多 filter 回退
$inspVariants = @(
    '{"and":[{"field":"naics_code","operator":"like","value":"23%"},{"field":"open_date","operator":"gte","value":"2021-01-01"},{"field":"open_date","operator":"lte","value":"2023-12-31"}]}',
    '{"and":[{"field":"naics_code","operator":"like","value":"23%"}]}',
    '{"and":[{"field":"open_date","operator":"gte","value":"2021-01-01"},{"field":"open_date","operator":"lte","value":"2023-12-31"}]}',
    '{}'
)
Write-Host ""
Write-Host ">> 下载 inspection（建筑业 NAICS 23，2021-2023）..." -ForegroundColor Cyan
$insFile = Join-Path $OutDir "inspection.csv"
$nIns = Download-Table "inspection" $inspVariants $insFile
Write-Host ("   inspection.csv : " + $nIns + " 行")
$report += ("inspection.csv : " + $nIns + " 行  -> " + $insFile)

# 4) accident —— 2021-2023 事故/重伤（fatality/catastrophe）调查
$accVariants = @(
    '{"and":[{"field":"event_date","operator":"gte","value":"2021-01-01"},{"field":"event_date","operator":"lte","value":"2023-12-31"}]}',
    '{}'
)
Write-Host ""
Write-Host ">> 下载 accident（2021-2023 事故/重伤调查）..." -ForegroundColor Cyan
$accFile = Join-Path $OutDir "accident.csv"
$nAcc = Download-Table "accident" $accVariants $accFile
Write-Host ("   accident.csv : " + $nAcc + " 行")
$report += ("accident.csv : " + $nAcc + " 行  -> " + $accFile)

# 5) （可选）accident_abstract —— 事故叙述文本，用于 embedding 高维控制
#    默认关闭；如需启用，在 download_osha_v2.bat 里加 -WithAbstract，
#    或在此把 $WithAbstract 改为 $true
$WithAbstract = $false
if ($args -contains "-WithAbstract") { $WithAbstract = $true }
if ($WithAbstract) {
    Write-Host ""
    Write-Host ">> 下载 accident_abstract（事故叙述文本）..." -ForegroundColor Cyan
    $absFile = Join-Path $OutDir "accident_abstract.csv"
    $absVariants = @('{}')
    $nAbs = Download-Table "accident_abstract" $absVariants $absFile
    Write-Host ("   accident_abstract.csv : " + $nAbs + " 行")
    $report += ("accident_abstract.csv : " + $nAbs + " 行  -> " + $absFile)
}

# 6) 写出字段表头（供助手适配 loader）
$schema = @()
$schema += "=== schema_probe : 各表字段表头（首行）==="
foreach ($f in @($insFile, $accFile)) {
    if (Test-Path $f) {
        $h = (Get-Content $f -Encoding utf8 -TotalCount 1)
        $schema += ("--- " + (Split-Path $f -Leaf) + " ---")
        $schema += $h
    }
}
$schema | Out-File -Encoding utf8 (Join-Path $OutDir "schema_probe.txt")

# 7) 完成报告
$report += "============================================================"
$report += ("完成时间: " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
$report | Out-File -Encoding utf8 (Join-Path $OutDir "download_report.txt")

Write-Host ""
Write-Host "============================================================"
Write-Host "下载完成。文件位于: $OutDir" -ForegroundColor Green
Write-Host "  inspection.csv      : $nIns 行"
Write-Host "  accident.csv        : $nAcc 行"
Write-Host "  schema_probe.txt    : 字段表头（交给助手适配 loader）"
Write-Host "  download_report.txt : 下载日志"
Write-Host "============================================================"
Write-Host "把以上结果（或 data\raw 目录）交给助手，即可清洗并跑真实 PSM/DML。"
Read-Host "按任意键关闭"
