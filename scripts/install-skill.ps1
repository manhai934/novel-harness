param(
  [string]$CodexHome = "$HOME\.codex",
  [string]$SkillName = "novel-core"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$source = Join-Path $repoRoot "skills\$SkillName"
$targetRoot = Join-Path $CodexHome "skills"
$target = Join-Path $targetRoot $SkillName

if (-not (Test-Path -LiteralPath $source)) {
  throw "Skill source not found: $source"
}

New-Item -ItemType Directory -Force -Path $targetRoot | Out-Null

if (Test-Path -LiteralPath $target) {
  Remove-Item -LiteralPath $target -Recurse -Force
}

Copy-Item -LiteralPath $source -Destination $target -Recurse

Write-Host "novel-core skill installed to: $target"
Write-Host "Use it with: /novel-core 帮我写小说"
