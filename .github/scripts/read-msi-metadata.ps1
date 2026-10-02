[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$Path,
  [Parameter(Mandatory = $true)][string]$BinaryPathsFile,
  [Parameter(Mandatory = $true)][string]$BinaryBaseDirectory,
  [Parameter(Mandatory = $true)][string]$OutputPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$installer = New-Object -ComObject WindowsInstaller.Installer
$database = $installer.OpenDatabase((Resolve-Path -LiteralPath $Path).Path, 0)
function Get-MsiProperty([string]$Name) {
  $view = $database.OpenView("SELECT ``Value`` FROM ``Property`` WHERE ``Property``='$Name'")
  try {
    $null = $view.Execute()
    $row = $view.Fetch()
    if ($null -eq $row) { throw "Built MSI is missing $Name" }
    return $row.StringData(1)
  }
  finally {
    $null = $view.Close()
  }
}

$files = @()
$view = $database.OpenView('SELECT `FileName`, `Version` FROM `File`')
try {
  $null = $view.Execute()
  while ($null -ne ($row = $view.Fetch())) {
    $name = ($row.StringData(1) -split '\|')[-1]
    if ($name -match '^mozc_.*\.(exe|dll)$') {
      $files += [ordered]@{ name = $name; version = $row.StringData(2) }
    }
  }
}
finally {
  $null = $view.Close()
}
$peFiles = @()
$binaryNames = @{
  'mozc_tool_win.exe' = 'mozc_tool.exe'
  'win32_renderer_main.exe' = 'mozc_renderer.exe'
  'mozc_server_win.exe' = 'mozc_server.exe'
  'mozc_broker_main.exe' = 'mozc_broker.exe'
  'mozc_cache_service.exe' = 'mozc_cache_service.exe'
  'mozc_tip32.dll' = 'mozc_tip32.dll'
  'mozc_tip64.dll' = 'mozc_tip64.dll'
  'custom_action.dll' = 'mozc_installer_helper.dll'
}
$seenBinaryNames = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($relativePath in (Get-Content -LiteralPath $BinaryPathsFile)) {
  # The Windows bazelisk wrapper also prints toolchain environment lines.
  # Only cquery artifact paths belong to the version evidence.
  if ($relativePath -notmatch '^bazel-out[/\\].*\.(exe|dll)$') { continue }
  # The architecture-transition wrapper uses the Bazel target's name, while
  # the installer uses the executable_name_map name. Keep the wrapper artifact
  # so TIP32 is checked with the architecture selected by the installer.
  $builtName = [System.IO.Path]::GetFileName($relativePath)
  if (-not $binaryNames.ContainsKey($builtName)) { throw "Unexpected built PE artifact: $builtName" }
  $installedName = $binaryNames[$builtName]
  if (-not $seenBinaryNames.Add($installedName)) { throw "Duplicate built PE artifact for $installedName" }
  $binaryPath = Join-Path $BinaryBaseDirectory $relativePath
  $info = [System.Diagnostics.FileVersionInfo]::GetVersionInfo((Resolve-Path -LiteralPath $binaryPath).Path)
  $peFiles += [ordered]@{
    name = $installedName
    built_name = $builtName
    file_version = "$($info.FileMajorPart).$($info.FileMinorPart).$($info.FileBuildPart).$($info.FilePrivatePart)"
    product_version = "$($info.ProductMajorPart).$($info.ProductMinorPart).$($info.ProductBuildPart).$($info.ProductPrivatePart)"
  }
}
$metadata = [ordered]@{
  product_version = Get-MsiProperty 'ProductVersion'
  upgrade_code = Get-MsiProperty 'UpgradeCode'
  product_name = Get-MsiProperty 'ProductName'
  manufacturer = Get-MsiProperty 'Manufacturer'
  publisher = $database.SummaryInformation(0).Property(4)
  files = @($files | Sort-Object { $_.name })
  pe_files = @($peFiles | Sort-Object { $_.name })
}
$metadata | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutputPath -Encoding utf8
