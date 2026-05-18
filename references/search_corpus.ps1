param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$SearchArgs
)

$ErrorActionPreference = "Stop"

if (-not $SearchArgs -or $SearchArgs.Count -eq 0) {
    Write-Error "Usage: powershell -File references/search_corpus.ps1 <keyword1> [keyword2 ...] [--collection maozedong|wang_yangming|zeng_guofan] [--hybrid]"
}

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $root
try {
    python scripts/search.py @SearchArgs
}
finally {
    Pop-Location
}
