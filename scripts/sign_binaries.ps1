param(
    [Parameter(Mandatory = $true, Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$Targets
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
$CertsDir = Join-Path $RootDir ".certs"
New-Item -ItemType Directory -Force -Path $CertsDir | Out-Null

$Cert = $null
$TimestampServer = $null

if ($env:CERT_PFX_PATH -and (Test-Path $env:CERT_PFX_PATH)) {
    Write-Host "Using production PFX certificate: $($env:CERT_PFX_PATH)"
    $SecurePwd = if ($env:CERT_PASSWORD) {
        ConvertTo-SecureString -String $env:CERT_PASSWORD -AsPlainText -Force
    } else {
        Read-Host -Prompt "Enter PFX password" -AsSecureString
    }
    $Cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2(
        $env:CERT_PFX_PATH,
        $SecurePwd,
        [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::Exportable
    )
    $TimestampServer = "http://timestamp.digicert.com"
} else {
    $Subject = "CN=FontVault Developer Code Signing"
    $Cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
        Where-Object { $_.Subject -eq $Subject } |
        Sort-Object NotAfter -Descending |
        Select-Object -First 1

    if (-not $Cert) {
        Write-Host "Creating self-signed CodeSigningCert in Cert:\CurrentUser\My..."
        $Cert = New-SelfSignedCertificate `
            -Type CodeSigningCert `
            -Subject $Subject `
            -KeyAlgorithm RSA `
            -KeyLength 2048 `
            -HashAlgorithm SHA256 `
            -CertStoreLocation "Cert:\CurrentUser\My" `
            -NotAfter (Get-Date).AddYears(3)
    } else {
        Write-Host "Reusing existing CodeSigningCert: $($Cert.Thumbprint)"
    }

    $CerPath = Join-Path $CertsDir "FontVault-DevCert.cer"
    Export-Certificate -Cert $Cert -FilePath $CerPath -Force | Out-Null
    Write-Host "Exported public certificate to $CerPath"
}

foreach ($Target in $Targets) {
    $FullTarget = if ([System.IO.Path]::IsPathRooted($Target)) { $Target } else { Join-Path $RootDir $Target }
    if (-not (Test-Path $FullTarget)) {
        throw "Target executable not found: $FullTarget"
    }

    if ($TimestampServer) {
        $Result = Set-AuthenticodeSignature -FilePath $FullTarget -Certificate $Cert -HashAlgorithm SHA256 -TimestampServer $TimestampServer
    } else {
        $Result = Set-AuthenticodeSignature -FilePath $FullTarget -Certificate $Cert -HashAlgorithm SHA256
    }

    $Verified = Get-AuthenticodeSignature -FilePath $FullTarget
    if (-not $Verified.SignerCertificate) {
        throw "Authenticode signature verification failed (no SignerCertificate) for $FullTarget"
    }

    Write-Host ("Signed: {0} | Status={1} | Thumbprint={2}" -f $FullTarget, $Verified.Status, $Verified.SignerCertificate.Thumbprint)
}
