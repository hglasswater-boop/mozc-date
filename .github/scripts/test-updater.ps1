# Exercise the shipped Windows PowerShell updater with a fake GitHub API and
# installer. No network access or installation is performed by these tests.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$updaterPath = (Resolve-Path (Join-Path $PSScriptRoot '../../src/gui/about_dialog/update-mozc-minimal.ps1')).Path
$testRoot = Join-Path ([IO.Path]::GetTempPath()) ('mozkey-updater-tests-' + [Guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $testRoot
$wrapperPath = Join-Path $testRoot 'run-updater.ps1'
$wrapper = @'
param([string]$FixturePath, [string]$UpdaterPath)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$global:UpdaterFixture = Get-Content -LiteralPath $FixturePath -Raw | ConvertFrom-Json
$env:LOCALAPPDATA = $global:UpdaterFixture.stateDirectory
$global:LASTEXITCODE = 0
function Invoke-RestMethod {
  param($Uri, $Headers)
  return [pscustomobject]@{
    tag_name = $global:UpdaterFixture.tag
    assets = @(
      [pscustomobject]@{ name = 'Mozc64_x64.msi'; browser_download_url = 'fixture:msi' },
      [pscustomobject]@{ name = 'Mozc64_x64.msi.sha256'; browser_download_url = 'fixture:checksum' }
    )
  }
}
function Invoke-WebRequest {
  param([switch]$UseBasicParsing, [string]$Uri, $Headers, [string]$OutFile)
  if ($Uri -eq 'fixture:msi') {
    Copy-Item -LiteralPath $global:UpdaterFixture.payload -Destination $OutFile
  }
  elseif ($Uri -eq 'fixture:checksum') {
    $hash = (Get-FileHash -LiteralPath $global:UpdaterFixture.payload -Algorithm SHA256).Hash.ToLowerInvariant()
    Set-Content -LiteralPath $OutFile -Value "$hash  Mozc64_x64.msi" -Encoding ASCII
  }
  else { throw "Unexpected network request: $Uri" }
}
function Start-Process {
  param([string]$FilePath, [string[]]$ArgumentList, [string]$Verb,
        [switch]$Wait, [switch]$PassThru)
  if ($FilePath -ne 'msiexec.exe' -or $Verb -ne 'RunAs' -or -not $Wait -or -not $PassThru) {
    throw 'Unexpected installer invocation'
  }
  ConvertTo-Json -InputObject @($ArgumentList) -Compress |
      Set-Content -LiteralPath $global:UpdaterFixture.invocation -Encoding ASCII
  return [pscustomobject]@{ ExitCode = 0 }
}
$parameters = @{}
if ($global:UpdaterFixture.check) { $parameters.Check = $true }
if ($global:UpdaterFixture.currentVersion) { $parameters.CurrentVersion = $global:UpdaterFixture.currentVersion }
& $UpdaterPath @parameters
exit $LASTEXITCODE
'@
Set-Content -LiteralPath $wrapperPath -Value $wrapper -Encoding UTF8

function Assert-Equal($Actual, $Expected, [string]$Message) {
  if ($Actual -ne $Expected) { throw "$Message`: expected '$Expected', got '$Actual'" }
}

function Invoke-UpdaterCase([string]$Name, [string]$Tag, [string]$Current = '', [bool]$Check = $false) {
  $caseDirectory = Join-Path $testRoot $Name
  $null = New-Item -ItemType Directory -Path $caseDirectory
  $payload = Join-Path $caseDirectory 'fake.msi'
  Set-Content -LiteralPath $payload -Value 'Test fixture only' -Encoding ASCII
  $fixturePath = Join-Path $caseDirectory 'fixture.json'
  $fixture = @{
    tag = $Tag
    currentVersion = $Current
    check = $Check
    stateDirectory = Join-Path $caseDirectory 'state'
    payload = $payload
    invocation = Join-Path $caseDirectory 'installer-arguments.json'
  }
  $fixture | ConvertTo-Json | Set-Content -LiteralPath $fixturePath -Encoding UTF8
  # About launches stock Windows PowerShell 5.1, so test that runtime even when
  # this test harness itself is run by GitHub Actions' pwsh.
  $output = & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $wrapperPath -FixturePath $fixturePath -UpdaterPath $updaterPath 2>&1
  $code = $LASTEXITCODE
  return [pscustomobject]@{
    Code = $code
    Output = ($output | Out-String).Trim()
    InvokedInstaller = Test-Path -LiteralPath $fixture.invocation
    Fixture = $fixture
  }
}

try {
  foreach ($case in @(
      @{ Name = 'check-product'; Tag = 'v0.2.1'; Display = '0.2.1'; Msi = '100.2.1' },
      @{ Name = 'check-legacy'; Tag = 'v4.0.0.0'; Display = '4.0.0.0'; Msi = '4.0.0' },
      @{ Name = 'check-legacy-mozc'; Tag = 'v3.34.6239.104'; Display = '3.34.6239.104'; Msi = '3.34.6239' },
      @{ Name = 'check-future-major'; Tag = 'v1.0.0'; Display = '1.0.0'; Msi = '101.0.0' }
  )) {
    $result = Invoke-UpdaterCase -Name $case.Name -Tag $case.Tag -Check $true
    Assert-Equal $result.Code 0 $case.Name
    $info = $result.Output | ConvertFrom-Json
    Assert-Equal $info.product_version $case.Display "$($case.Name) display"
    Assert-Equal $info.msi_version $case.Msi "$($case.Name) MSI"
    Assert-Equal $result.InvokedInstaller $false "$($case.Name) read-only"
  }

  foreach ($case in @(
      @{ Name = 'migrate-v4'; Tag = 'v0.2.1'; Current = '4.0.0.0'; Install = $true },
      @{ Name = 'migrate-v3'; Tag = 'v0.2.1'; Current = '3.34.6239.104'; Install = $true },
      @{ Name = 'upgrade'; Tag = 'v0.2.2'; Current = '0.2.1'; Install = $true },
      @{ Name = 'equal'; Tag = 'v0.2.1'; Current = '0.2.1'; Install = $false },
      @{ Name = 'older'; Tag = 'v0.2.0'; Current = '0.2.1'; Install = $false },
      @{ Name = 'prevent-legacy-downgrade'; Tag = 'v4.0.0.0'; Current = '0.2.1'; Install = $false }
  )) {
    $result = Invoke-UpdaterCase -Name $case.Name -Tag $case.Tag -Current $case.Current
    Assert-Equal $result.Code 0 "$($case.Name): $($result.Output)"
    Assert-Equal $result.InvokedInstaller $case.Install "$($case.Name) install decision"
    if ($case.Install) {
      $arguments = Get-Content -LiteralPath $result.Fixture.invocation -Raw | ConvertFrom-Json
      Assert-Equal ($arguments -contains 'REINSTALL=ALL') $false "$($case.Name) major upgrade"
      $statePath = Join-Path $result.Fixture.stateDirectory 'MozcDateEnglish/last-installed-release.txt'
      Assert-Equal (Get-Content -LiteralPath $statePath -Raw).Trim() $case.Tag "$($case.Name) saved tag"
    }
  }

  foreach ($tag in @('0.2.1', 'v0.2', 'v0.2.1-beta', 'v00.2.1', 'v156.0.0', 'v0.256.0', 'v0.0.65536', 'v100.0.0.0', 'V0.2.1', "v0.2.1`n")) {
    $result = Invoke-UpdaterCase -Name ('invalid-' + [Guid]::NewGuid().ToString('N')) -Tag $tag -Check $true
    if ($result.Code -eq 0) { throw "Invalid tag was accepted: $tag" }
    Assert-Equal $result.InvokedInstaller $false "Invalid tag $tag"
  }
  Write-Output 'Updater version checks passed (20 cases, Windows PowerShell).'
}
finally {
  $resolvedRoot = [IO.Path]::GetFullPath($testRoot)
  $tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
  if (-not $resolvedRoot.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to remove test directory outside the temp directory: $resolvedRoot"
  }
  Remove-Item -LiteralPath $resolvedRoot -Recurse -Force
}
