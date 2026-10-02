# Exercise the real Windows Installer COM API without installing a package.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$fixtureDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ('mozc-date-msi-metadata-test-' + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $fixtureDirectory
$fixtureMsi = Join-Path $fixtureDirectory 'fixture.msi'
$properties = [ordered]@{
  ProductVersion = '100.2.1'
  UpgradeCode = '{DD94B570-B5E2-4100-9D42-61930C611D8A}'
  ProductName = 'mozc-date'
  Manufacturer = 'mozc-date Project'
}

function Invoke-MsiQuery($Database, [string]$Query) {
  $view = $Database.OpenView($Query)
  try { $null = $view.Execute() }
  finally {
    $null = $view.Close()
    $null = [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($view)
  }
}

try {
  $installer = New-Object -ComObject WindowsInstaller.Installer
  $database = $installer.OpenDatabase($fixtureMsi, 3)
  try {
    Invoke-MsiQuery $database 'CREATE TABLE `Property` (`Property` CHAR(72) NOT NULL, `Value` CHAR(0) LOCALIZABLE PRIMARY KEY `Property`)'
    foreach ($key in $properties.Keys) {
      Invoke-MsiQuery $database "INSERT INTO ``Property`` (``Property``, ``Value``) VALUES ('$key', '$($properties[$key])')"
    }
    Invoke-MsiQuery $database 'CREATE TABLE `File` (`File` CHAR(72) NOT NULL, `Component_` CHAR(72) NOT NULL, `FileName` CHAR(255) NOT NULL LOCALIZABLE, `FileSize` LONG NOT NULL, `Version` CHAR(72), `Language` CHAR(20), `Attributes` SHORT, `Sequence` LONG NOT NULL PRIMARY KEY `File`)'
    Invoke-MsiQuery $database 'INSERT INTO `File` (`File`, `Component_`, `FileName`, `FileSize`, `Version`, `Sequence`) VALUES (''Tool'', ''ToolComponent'', ''tool.exe|mozc_tool.exe'', 1, ''100.2.1.0'', 1)'
    $summary = $database.SummaryInformation(20)
    try {
      $summary.Property(4) = $properties.Manufacturer
      $null = $summary.Persist()
    }
    finally { $null = [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($summary) }
    $null = $database.Commit()
  }
  finally {
    $null = [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($database)
    $null = [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($installer)
  }

  $pathsFile = Join-Path $fixtureDirectory 'paths.txt'
  Set-Content -LiteralPath $pathsFile -Value '' -Encoding utf8
  $metadataFile = Join-Path $fixtureDirectory 'metadata.json'
  & "$PSScriptRoot/read-msi-metadata.ps1" -Path $fixtureMsi -BinaryPathsFile $pathsFile -BinaryBaseDirectory $fixtureDirectory -OutputPath $metadataFile
  $metadata = Get-Content -LiteralPath $metadataFile -Raw | ConvertFrom-Json
  $expected = [ordered]@{
    product_version = $properties.ProductVersion
    upgrade_code = $properties.UpgradeCode
    product_name = $properties.ProductName
    manufacturer = $properties.Manufacturer
    publisher = $properties.Manufacturer
  }
  foreach ($key in $expected.Keys) {
    $actual = $metadata.$key
    if ($actual -isnot [string] -or $actual -cne $expected[$key]) {
      throw "MSI $key must be the scalar string '$($expected[$key])', got '$actual'."
    }
  }
  if ($metadata.files.Count -ne 1 -or $metadata.files[0].name -cne 'mozc_tool.exe' -or $metadata.files[0].version -cne '100.2.1.0') {
    throw 'MSI File table must preserve the installed name and numeric file version.'
  }
  if ($metadata.pe_files.Count -ne 0) { throw 'Empty PE paths must produce an empty array.' }
  Write-Output 'Windows Installer COM metadata regression test passed.'
}
finally {
  # Release script-local COM references before removing this test's own fixture.
  [GC]::Collect()
  [GC]::WaitForPendingFinalizers()
  $resolvedFixture = [System.IO.Path]::GetFullPath($fixtureDirectory)
  $tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
  if (-not $resolvedFixture.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase) -or
      [System.IO.Path]::GetFileName($resolvedFixture) -notmatch '^mozc-date-msi-metadata-test-[0-9a-f]{32}$') {
    throw 'Unexpected metadata fixture cleanup path.'
  }
  Remove-Item -LiteralPath $resolvedFixture -Recurse -Force
}
