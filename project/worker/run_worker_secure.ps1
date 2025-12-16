<#
Prompts for the Supabase service role key (secure input), then runs the Python worker
for a given run id. The key is kept only in memory for the session and cleared afterwards.
Usage: .\run_worker_secure.ps1 -RunId <run-uuid>
#>

param(
  [Parameter(Mandatory=$false)]
  [string]$RunId
)

# Prompt for service role key securely
$svcSecure = Read-Host -Prompt 'Enter SUPABASE_SERVICE_ROLE_KEY (input hidden)' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($svcSecure)
try {
  $svcKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
} finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}

# Prompt for run id if not provided
if (-not $RunId) {
  $RunId = Read-Host 'Enter run id to process (or leave blank to poll first pending run)'
}

# Set env vars for this session only
$supabaseUrlInput = Read-Host 'Enter SUPABASE_URL (e.g., https://<project>.supabase.co)'
if (-not $supabaseUrlInput) {
  Write-Host 'SUPABASE_URL is required.' -ForegroundColor Red
  exit 1
}
$env:SUPABASE_URL = $supabaseUrlInput
$env:SUPABASE_SERVICE_ROLE_KEY = $svcKey

# Activate venv if exists
if (Test-Path .venv) {
  . .\.venv\Scripts\Activate.ps1
}

# Run worker
if ($RunId) {
  python process_run.py --run-id $RunId
} else {
  python process_run.py
}

# Clear sensitive env and variables
Remove-Item Env:SUPABASE_SERVICE_ROLE_KEY -ErrorAction SilentlyContinue
$svcKey = $null
[System.GC]::Collect()
[System.GC]::WaitForPendingFinalizers()
Write-Host 'Worker finished. Service role key removed from session.'
