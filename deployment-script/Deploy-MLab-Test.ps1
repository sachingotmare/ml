
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter()]
    [string]$ArchivePath,

    [Parameter()]
    [string]$BrowseUrl
)

$ErrorActionPreference = 'Stop'

$exePath = "E:\Project's\Demo-Websites-Figma\MLab_Web_Test\Exe"
$livePublishPath = "E:\Project's\Demo-Websites-Figma\MLab_Web_Test\publish"
$backupRootPath = "E:\Project's\Demo-Websites-Figma\MLab_Web_Test\Backup"
$websiteName = 'TEST'
$appPoolName = 'TEST'
$browserFolderNames = @('Chrome', 'ChromeHeadlessShell')

function Test-ProtectedConfigFile {
    param([string]$Name)

    return $Name -match '^(appsettings(\..*)?|web\.config)$'
}

function Invoke-Robocopy {
    param(
        [string[]]$Arguments,
        [string]$Operation
    )

    & robocopy @Arguments
    $result = $LASTEXITCODE
    if ($result -ge 8) {
        throw "Robocopy failed while $Operation (exit code $result)."
    }
}

function Wait-IisState {
    param(
        [ValidateSet('Website', 'AppPool')]
        [string]$ObjectType,
        [string]$Name,
        [ValidateSet('Started', 'Stopped')]
        [string]$ExpectedState,
        [int]$TimeoutSeconds = 60
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        if ($ObjectType -eq 'Website') {
            $currentState = (Get-WebsiteState -Name $Name).Value
        }
        else {
            $currentState = (Get-WebAppPoolState -Name $Name).Value
        }

        if ($currentState -eq $ExpectedState) {
            return
        }
        Start-Sleep -Seconds 1
    } while ((Get-Date) -lt $deadline)

    throw "IIS $ObjectType '$Name' did not reach state '$ExpectedState' within $TimeoutSeconds seconds."
}

function Get-IisWebsiteUrl {
    param([string]$Name)

    $bindings = @(
        Get-WebBinding -Name $Name |
            Where-Object {
                if ($_.protocol -notin @('https', 'http') -or
                    $_.bindingInformation -notmatch '^(?<ip>.*):(?<port>\d+):(?<host>.*)$') {
                    return $false
                }

                $hostName = $Matches.host
                if ([string]::IsNullOrWhiteSpace($hostName) -or
                    $hostName -ieq 'localhost' -or
                    $hostName.EndsWith('.localhost', [StringComparison]::OrdinalIgnoreCase)) {
                    return $false
                }

                $hostAddress = $null
                if ([Net.IPAddress]::TryParse($hostName, [ref]$hostAddress) -and
                    [Net.IPAddress]::IsLoopback($hostAddress)) {
                    return $false
                }

                return $true
            } |
            Sort-Object -Property @{ Expression = { if ($_.protocol -eq 'https') { 0 } else { 1 } } }
    )
    if ($bindings.Count -eq 0) {
        throw "IIS website '$Name' has no non-localhost HTTP or HTTPS binding. Pass -BrowseUrl to specify a non-localhost URL."
    }

    $binding = $bindings[0]
    if ($binding.bindingInformation -notmatch '^(?<ip>.*):(?<port>\d+):(?<host>.*)$') {
        throw "Could not parse IIS binding '$($binding.bindingInformation)' for website '$Name'."
    }

    $hostName = $Matches.host
    $uriBuilder = New-Object System.UriBuilder(
        $binding.protocol,
        $hostName,
        [int]$Matches.port
    )
    return $uriBuilder.Uri.AbsoluteUri
}

if (-not (Test-Path -LiteralPath $exePath -PathType Container)) {
    throw "The deployment source folder does not exist: $exePath"
}
if (-not (Test-Path -LiteralPath $livePublishPath -PathType Container)) {
    throw "The live publish folder does not exist: $livePublishPath"
}

if ([string]::IsNullOrWhiteSpace($ArchivePath)) {
    $today = (Get-Date).Date
    $archives = @(
        Get-ChildItem -LiteralPath $exePath -File -Filter '*.zip' |
            Where-Object { $_.LastWriteTime.Date -eq $today } |
            Sort-Object -Property LastWriteTime -Descending
    )
    if ($archives.Count -eq 0) {
        throw "No ZIP modified today was found in $exePath. Pass -ArchivePath to select a ZIP explicitly."
    }
    $ArchivePath = $archives[0].FullName
    Write-Host "Found today's ZIP: $ArchivePath (modified $($archives[0].LastWriteTime))"
}

if (-not (Test-Path -LiteralPath $ArchivePath -PathType Leaf)) {
    throw "The deployment ZIP does not exist: $ArchivePath"
}
if ([IO.Path]::GetExtension($ArchivePath) -ine '.zip') {
    throw "The deployment archive must be a ZIP file: $ArchivePath"
}

$ArchivePath = (Resolve-Path -LiteralPath $ArchivePath).Path
$archiveName = [IO.Path]::GetFileName($ArchivePath)
$deploymentTimestamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$backupPath = Join-Path $backupRootPath "publish_$deploymentTimestamp"
$stagingPath = Join-Path $exePath "Extracted_$deploymentTimestamp"

$principal = New-Object Security.Principal.WindowsPrincipal(
    [Security.Principal.WindowsIdentity]::GetCurrent()
)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this deployment script from an elevated PowerShell session.'
}

if (-not $PSCmdlet.ShouldProcess(
        "$websiteName / $appPoolName at $livePublishPath",
        "Deploy $archiveName"
    )) {
    return
}

Import-Module WebAdministration

if (-not (Get-Website -Name $websiteName -ErrorAction SilentlyContinue)) {
    throw "IIS website '$websiteName' was not found."
}
if (-not (Test-Path -LiteralPath "IIS:\AppPools\$appPoolName")) {
    throw "IIS application pool '$appPoolName' was not found."
}

if ([string]::IsNullOrWhiteSpace($BrowseUrl)) {
    $BrowseUrl = Get-IisWebsiteUrl -Name $websiteName
}
else {
    $parsedBrowseUrl = $null
    if (-not [Uri]::TryCreate($BrowseUrl, [UriKind]::Absolute, [ref]$parsedBrowseUrl) -or
        $parsedBrowseUrl.Scheme -notin @('http', 'https')) {
        throw "BrowseUrl must be an absolute HTTP or HTTPS URL: $BrowseUrl"
    }
    $browseAddress = $null
    if ($parsedBrowseUrl.Host -ieq 'localhost' -or
        $parsedBrowseUrl.Host.EndsWith('.localhost', [StringComparison]::OrdinalIgnoreCase) -or
        ([Net.IPAddress]::TryParse($parsedBrowseUrl.Host, [ref]$browseAddress) -and
            [Net.IPAddress]::IsLoopback($browseAddress))) {
        throw "BrowseUrl must not use a localhost or loopback address: $BrowseUrl"
    }
}

Write-Host "Creating backup at $backupPath"
New-Item -ItemType Directory -Path $backupRootPath -Force | Out-Null
New-Item -ItemType Directory -Path $backupPath | Out-Null
$backupExclusions = @(
    (Join-Path $livePublishPath $browserFolderNames[0]),
    (Join-Path $livePublishPath $browserFolderNames[1])
)
$backupArguments = @(
    $livePublishPath,
    $backupPath,
    '/E',
    '/COPY:DAT',
    '/DCOPY:DAT',
    '/R:2',
    '/W:2',
    '/XJ',
    '/XD'
) + $backupExclusions
Invoke-Robocopy -Arguments $backupArguments -Operation 'backing up the live publish folder'

Write-Host "Extracting $archiveName to $stagingPath"
New-Item -ItemType Directory -Path $stagingPath | Out-Null
Expand-Archive -LiteralPath $ArchivePath -DestinationPath $stagingPath

$publishRoot = $stagingPath
if (-not (Test-Path -LiteralPath (Join-Path $publishRoot 'wwwroot') -PathType Container)) {
    $wwwrootFolders = @(
        Get-ChildItem -LiteralPath $stagingPath -Directory -Recurse -Filter 'wwwroot' |
            Where-Object { $_.Parent -ne $null }
    )
    $publishRoots = @($wwwrootFolders | ForEach-Object { $_.Parent.FullName } | Select-Object -Unique)
    if ($publishRoots.Count -ne 1) {
        throw "Could not identify one published application root containing wwwroot in $stagingPath."
    }
    $publishRoot = $publishRoots[0]
}

$stagedWwwroot = Join-Path $publishRoot 'wwwroot'
$liveWwwroot = Join-Path $livePublishPath 'wwwroot'
if (-not (Test-Path -LiteralPath $liveWwwroot -PathType Container)) {
    throw "The live wwwroot folder does not exist: $liveWwwroot"
}
if (-not (Test-Path -LiteralPath $stagedWwwroot -PathType Container)) {
    throw "The extracted wwwroot folder does not exist: $stagedWwwroot"
}

Get-ChildItem -LiteralPath $publishRoot -File |
    Where-Object { Test-ProtectedConfigFile -Name $_.Name } |
    Remove-Item -Force
$stagedToolsPath = Join-Path $publishRoot 'tools'
if (Test-Path -LiteralPath $stagedToolsPath) {
    Remove-Item -LiteralPath $stagedToolsPath -Recurse -Force
}

Write-Host 'Preserving the current live wwwroot in the extracted publish folder'
Remove-Item -LiteralPath $stagedWwwroot -Recurse -Force
Copy-Item -LiteralPath $liveWwwroot -Destination $publishRoot -Recurse -Force

$iisTouched = $false
$deploymentError = $null
$restartErrors = @()

try {
    $iisTouched = $true
    Write-Host "Stopping IIS website '$websiteName' and application pool '$appPoolName'"
    if ((Get-WebsiteState -Name $websiteName).Value -ne 'Stopped') {
        Stop-Website -Name $websiteName
        Wait-IisState -ObjectType Website -Name $websiteName -ExpectedState Stopped
    }
    if ((Get-WebAppPoolState -Name $appPoolName).Value -ne 'Stopped') {
        Stop-WebAppPool -Name $appPoolName
        Wait-IisState -ObjectType AppPool -Name $appPoolName -ExpectedState Stopped
    }

    Write-Host 'Waiting 5 seconds for IIS worker processes to release publish files'
    Start-Sleep -Seconds 5

    Write-Host 'Removing replaceable content from the live publish folder'
    foreach ($item in Get-ChildItem -LiteralPath $livePublishPath -Force) {
        $keepItem = $false
        if ($item.PSIsContainer) {
            $keepItem = $browserFolderNames -contains $item.Name
        }
        else {
            $keepItem = Test-ProtectedConfigFile -Name $item.Name
        }

        if (-not $keepItem) {
            Remove-Item -LiteralPath $item.FullName -Recurse -Force
        }
    }

    Write-Host 'Copying the extracted publish content to the live folder'
    foreach ($item in Get-ChildItem -LiteralPath $publishRoot -Force) {
        if ($item.PSIsContainer -and $browserFolderNames -contains $item.Name) {
            continue
        }
        if (-not $item.PSIsContainer -and (Test-ProtectedConfigFile -Name $item.Name)) {
            continue
        }
        Copy-Item -LiteralPath $item.FullName -Destination $livePublishPath -Recurse -Force
    }
}
catch {
    $deploymentError = $_
}
finally {
    if ($iisTouched) {
        Write-Host "Starting IIS application pool '$appPoolName' and website '$websiteName'"
        try {
            if ((Get-WebAppPoolState -Name $appPoolName).Value -ne 'Started') {
                Start-WebAppPool -Name $appPoolName
                Wait-IisState -ObjectType AppPool -Name $appPoolName -ExpectedState Started
            }
        }
        catch {
            $restartErrors += "Application pool '$appPoolName': $($_.Exception.Message)"
        }

        try {
            if ((Get-WebsiteState -Name $websiteName).Value -ne 'Started') {
                Start-Website -Name $websiteName
                Wait-IisState -ObjectType Website -Name $websiteName -ExpectedState Started
            }
        }
        catch {
            $restartErrors += "Website '$websiteName': $($_.Exception.Message)"
        }
    }
}

if ($deploymentError) {
    $message = "Deployment failed: $($deploymentError.Exception.Message)"
    if ($restartErrors.Count -gt 0) {
        $message += " IIS restart also failed: $($restartErrors -join '; ')"
    }
    throw $message
}
if ($restartErrors.Count -gt 0) {
    throw "Deployment completed, but IIS could not be fully restarted: $($restartErrors -join '; ')"
}

Write-Host "Deployment completed successfully. Backup: $backupPath"
Write-Host "Opening website in the default browser: $BrowseUrl"
try {
    Start-Process -FilePath $BrowseUrl
}
catch {
    throw "Deployment completed, but the website could not be opened in a browser: $($_.Exception.Message)"
}
