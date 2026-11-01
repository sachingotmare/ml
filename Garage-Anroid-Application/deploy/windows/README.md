# Windows Server / IIS deployment

Deployment target: `https://android.sgsoftech.in`, using the server's existing local PostgreSQL instance. This guide does **not** replace PostgreSQL, create a second instance, or modify existing IIS sites.

Architecture:

```text
Android app -> HTTPS android.sgsoftech.in:443 -> IIS / ARR
             -> http://127.0.0.1:3000 -> Node Windows service
             -> PostgreSQL 127.0.0.1:5432 / garage_manager
```

IIS hosts the **API reverse proxy**, not the React Native UI or an APK. Android UI is packaged into the installed app. A browser request to the domain root currently returns the API's 404; use `/health` for readiness.

## 0. Automated, approval-based deployment (recommended)

### Cloudflare-proxied IIS with an Origin certificate

Use **`-CloudflareProxy` on Check, preview and Deploy** when orange-cloud DNS sends traffic through Cloudflare and IIS uses a Cloudflare Origin certificate. Normal/direct IIS mode still requires public trust. Cloudflare mode accepts only certificates chained to the bundled, SHA-256-pinned official Origin CA roots, with matching hostname, current validity and private key. It does not add a CA to Windows trust stores or disable TLS validation.

Configure DNS for `android.sgsoftech.in` as **Proxied**, SSL/TLS as **Full (strict)** (never Flexible), a valid public edge certificate and cache bypass for this entire API hostname. IIS still receives HTTPS. Restrict origin access to Cloudflare's published IP ranges using your firewall administration process, preserving the loopback deployment check and any existing sites. Do not expose PostgreSQL or the backend port.

For the confirmed server certificate and free backend port:

```powershell
$Project = "E:\Project's\Garage-Manager-Server-2026-11-01"
$deploy = Join-Path $Project 'deploy\windows\Deploy-GarageManager.ps1'
$cert = 'A7BBED4B6B64D913A92C6F545BA2FDBA42B6787E'
& $deploy -Mode Check -CloudflareProxy -ApiPort 3100 -CertificateThumbprint $cert
& $deploy -Mode Deploy -CloudflareProxy -ApiPort 3100 -CertificateThumbprint $cert -DownloadWinSW -WhatIf
& $deploy -Mode Deploy -CloudflareProxy -ApiPort 3100 -CertificateThumbprint $cert -DownloadWinSW
```

Add `-LicensePublicKeyPath 'C:\Transfer\issuer-public.pem'` when ready. Without it, trials work but key activation remains unavailable. Review every installer/WinSW/system-change approval.

Local SNI verification uses curl `--cacert` with the pinned Origin CA bundle; public verification uses ordinary public trust and requires a Cloudflare `CF-Ray` header. A curl build without `--cacert` support fails explicitly: update Windows curl through your approved process, do not use `-k`. These checks do not inspect your Cloudflare account settings; confirm Full (strict) and cache bypass in the dashboard. Certificate hostname or expiry failure still stops deployment.

[Deploy-GarageManager.ps1](Deploy-GarageManager.ps1) automates sections 1-8 below and the local Android build in section 9. It is **approval-based**: every installer, database change, service/IIS/Task Scheduler change and Android SDK license prompt requires your explicit interactive answer. `-WhatIf` lists the changes and never prompts, downloads or installs. Run Deploy from an elevated **Windows PowerShell 5.1** console on the server.

```powershell
Set-Location '<project>\deploy\windows'
.\Deploy-GarageManager.ps1 -Mode Check                 # read-only report, exit code 2 if something is missing
.\Deploy-GarageManager.ps1 -Mode Deploy -WhatIf        # ordered plan of every change, no prompts
.\Deploy-GarageManager.ps1 -Mode Deploy `
  -WinSWPath 'C:\Tools\WinSW-x64.exe' -WinSWSha256 '<SHA-256 you verified>' `
  -PfxPath 'D:\certs\android.sgsoftech.in.pfx'         # or -CertificateThumbprint '<existing cert>'
.\Deploy-GarageManager.ps1 -Mode BuildAndroid -KeystorePath 'D:\keys\upload.jks' -KeyAlias upload
.\Deploy-GarageManager.ps1 -Mode All -WhatIf           # Check + Deploy + BuildAndroid plan
.\Test-DeployScripts.ps1                               # parser/static/focused tests; changes nothing
```

What Deploy does, in order (stopping explicitly on the first failure):

1. Detects Node 24.13+ x64, PostgreSQL `psql` 15+, IIS role, URL Rewrite, ARR, WinSW and the certificate. After a **specific** approval it can install Node (nodejs.org MSI: published SHA-256 + OpenJS signature), IIS features, URL Rewrite and ARR (Microsoft-hosted MSI: Microsoft Authenticode signature enforced; Microsoft publishes no checksum). It never installs or replaces PostgreSQL. Enabling the server-wide ARR proxy setting needs its own approval; an existing pool/site/binding is preserved and conflicting bindings or a different bound certificate cause a refusal. An existing `runtime.env` is validated (Node dotenv quoting supported, weak/placeholder `PGPASSWORD` rejected) and never overwritten or restored from defaults.
2. Creates the ACL-restricted secrets/logs/backups/service folders (SYSTEM, Administrators, LocalService only).
3. Prompts securely for the PostgreSQL administrator password (or reads `GARAGE_PG_ADMIN_PASSWORD`) and for the `garage_deploy`/`garage_runtime` passwords (`GARAGE_PG_DEPLOY_PASSWORD`, `GARAGE_PG_RUNTIME_PASSWORD`). Passwords are never script parameters or files in the repository; they reach `psql` only through the child process environment. [provision-idempotent.psql](provision-idempotent.psql) creates only missing roles and database; existing data, role passwords and database ownership are never changed. REVOKE-from-PUBLIC hardening is applied only to a database it just created unless you pass `-HardenExistingDatabase`.
4. If a service already exists, takes a JSON backup (skip with `-SkipPreDeployBackup`), stops only `GarageManager`, additively copies sources with robocopy (no mirror/purge/delete; secrets, `node_modules`, Android folders and build output are excluded) and runs `npm ci` for the shared and server workspaces plus `npm run build`.
5. Runs the existing `server\dist\migrate.js` as `garage_deploy`, then `grant-runtime.sql`. `runtime.env` is created once with `MIGRATIONS_ON_START=false` and `WHATSAPP_STATUS_TEMPLATE=bike_service_status`; an existing file is validated, never overwritten (add missing variables yourself). The owner bootstrap runs only when `users` is empty.
6. Generates the WinSW XML from [GarageManager.xml](GarageManager.xml) with the real Node, env-file, entry-point and log paths and installs/refreshes the `LocalService` service. Supply WinSW with `-WinSWPath` plus `-WinSWSha256` you verified (WinSW publishes no checksum file) unless validly Authenticode-signed, or pass `-DownloadWinSW`: after your approval it downloads the official v2.12.0 release from github.com/winsw to `%LOCALAPPDATA%\GarageManager\downloads`, shows SHA-256 and signature status, and keeps it only if the signature is valid and you approve, or you type a SHA-256 you verified independently; otherwise it deletes the file and stops.
7. Creates the dedicated `GarageApi` pool/site, HTTP and SNI HTTPS bindings, `web.config` and enables the **server-wide** ARR proxy flag. It throws if another site already binds the domain, owns the folder, or an existing non-SNI `0.0.0.0:443` binding would clash; other sites are never modified. Only an existing, valid, CA-issued certificate covering the domain (chain builds, not self-signed, has a private key) is accepted: choose from `LocalMachine\My`, or import a PFX (password via secure prompt or `GARAGE_PFX_PASSWORD`).
8. Registers `GarageManager-Reminders` (every 5 minutes) and `GarageManager-Backup` (daily at `-BackupTime`, default 02:30) as `LocalService`, no overlapping runs, calling the existing `Run-Reminders.ps1`/`Run-Backup.ps1`.
9. Verifies loopback `/health`, then HTTPS through this server's SNI binding, then through public DNS and an unregistered `/customers` 400 for missing installation credentials. With valid active installation headers but no staff session, `/customers` returns 401 instead. Each failure is an explicit error.

Things that **cannot** be automated and are not claimed: public DNS A/AAAA records, firewall/NAT for 80/443, obtaining a CA-issued certificate and its renewal, verifying the site from another network, WinSW provenance, PostgreSQL installation and `pg_hba.conf` review, and rotating the supplied PostgreSQL administrator password. If the session is not interactive, approval-requiring steps stop instead of proceeding. Hosts without `winget` are supported (the script does not depend on it); where an installer cannot be validated (no signature or published hash) the script stops and tells you what to provide.

Parts/accessories service tracking, status timeline sharing and the WhatsApp queue are application features implemented separately. The reminder worker run by `Run-Reminders.ps1` also sends the shared service status; your custom WhatsApp gateway must accept the additional variables `serviceStatus`, `workNote` and `promisedDelivery`, and approve the `WHATSAPP_STATUS_TEMPLATE` (`bike_service_status`) template. Customers do not log in.

The manual steps below remain the reference for what the script performs.
Default directories: app `C:\Apps\GarageManager`, service `C:\Services\GarageManager`, IIS root `C:\inetpub\garage-api`, data `C:\ProgramData\GarageManager\{secrets,logs,backups}`, downloads `%LOCALAPPDATA%\GarageManager\downloads`, Android output `Documents\GarageManager\android-releases` (override via parameters). `-WhatIf` and `Check` never prompt, install or change anything.

## 1. Prerequisites and paths

### Public-key installation and upgrading existing garages

Follow the [30-day licensing guide](../../licensing/README.md) to initialize issuer keys on a trusted workstation. Supply `-LicensePublicKeyPath 'C:\Transfer\issuer-public.pem'` with `-Mode Deploy`. The script validates an Ed25519 **public** key, obtains approval, installs it in the restricted secrets directory and updates only `LICENSE_PUBLIC_KEY_FILE`; it refuses private keys, duplicate settings and unapproved replacement of another key/path. Without that argument, an existing configured public key is validated and preserved; an unconfigured server allows trials but cannot activate licenses.

The normal migration and runtime-grant steps create/authorize the new `installations` table for existing databases. Do not reset garage data or grant runtime schema-owner rights. Back up the full PostgreSQL database, including installations, for disaster recovery; JSON business backups do not preserve licenses. Private issuer keys and issued license files are excluded from deployment source copying and must never be installed on IIS or embedded in the Android app.

- Windows Server with IIS, supported Node.js 24.13+ x64, existing PostgreSQL and its command-line tools.
- IIS URL Rewrite 2 and Application Request Routing (ARR) 3, installed from Microsoft's approved distribution.
- A valid TLS certificate for `android.sgsoftech.in`, with monitored renewal.
- A reviewed stable [WinSW release](https://github.com/winsw/winsw/releases). [GarageManager.xml](GarageManager.xml) uses the documented WinSW 2.x configuration; use the matching x64 binary and verify its provenance/checksum before installation.
- Administrator rights for IIS/service/task installation, **not** for the application's runtime identity.

Paths used below:

| Path | Contents |
|---|---|
| `C:\Apps\GarageManager` | Application source, installed dependencies and compiled server |
| `C:\Services\GarageManager` | WinSW executable and service XML |
| `C:\inetpub\garage-api` | Only IIS proxy `web.config` |
| `C:\ProgramData\GarageManager\secrets` | Private runtime environment |
| `C:\ProgramData\GarageManager\logs` | Rotated service logs |
| `C:\ProgramData\GarageManager\backups` | Sensitive business backups |

Use an approved release-copy process to copy this project's contents into `C:\Apps\GarageManager`. Do not copy development environment files, Android build artifacts, or another project's files. On the server:

```powershell
Set-Location 'C:\Apps\GarageManager'
npm ci --workspace @garage/shared --workspace @garage/server --ignore-scripts
npm run build
```

These workspace selectors avoid installing Android tooling on the production server. A complete tested build can also be prepared on your build machine and deployed with its server dependencies.

## 2. Create isolated database accounts

The PostgreSQL administrator account is used **only** for initial provisioning. Do not use `postgres` as the application account. Rotate the supplied weak administrator password through your normal DBA process after checking any existing services that use it.

Locate your installed `psql.exe`; adjust the version path below. Provision once:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' `
  -X -h 127.0.0.1 -p 5432 -U postgres -W -d postgres `
  -f 'C:\Apps\GarageManager\deploy\windows\provision.psql'
if ($LASTEXITCODE -ne 0) { throw 'Database provisioning failed; inspect the error before proceeding.' }
```

Enter the administrator password at the prompt. The script then asks you to set **different strong passwords** for:

- `garage_deploy`: owns `garage_manager`, used only for schema migrations.
- `garage_runtime`: limited to required database/table operations; no superuser, role creation, database creation or schema creation.

Passwords are entered interactively and are not embedded in SQL. The script stops on the first error; it is deliberately **not** a destructive reset or a rerunnable overwrite. If any role/database already exists, ask your DBA to inspect and reconcile it before continuing. The database is dedicated to this garage, not shared with unrelated applications.

Keep PostgreSQL listening only on loopback unless your existing applications require otherwise. Do not expose 5432 through the firewall. Review `pg_hba.conf` for loopback `scram-sha-256` authentication; do not introduce `trust` rules or alter unrelated rules.

## 3. Store the runtime environment securely

Create these named directories if absent. Run the ACL commands only against these application-specific locations, not a parent/root directory:

```powershell
New-Item -ItemType Directory -Force -Path `
  'C:\Services\GarageManager', `
  'C:\inetpub\garage-api', `
  'C:\ProgramData\GarageManager\secrets', `
  'C:\ProgramData\GarageManager\logs', `
  'C:\ProgramData\GarageManager\backups'

icacls 'C:\ProgramData\GarageManager\secrets' /inheritance:r /grant:r `
  '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-18:(OI)(CI)F' '*S-1-5-19:(OI)(CI)RX'
icacls 'C:\ProgramData\GarageManager\logs' /inheritance:r /grant:r `
  '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-18:(OI)(CI)F' '*S-1-5-19:(OI)(CI)M'
icacls 'C:\ProgramData\GarageManager\backups' /inheritance:r /grant:r `
  '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-18:(OI)(CI)F' '*S-1-5-19:(OI)(CI)M'
icacls 'C:\Services\GarageManager' /inheritance:r /grant:r `
  '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-18:(OI)(CI)F' '*S-1-5-19:(OI)(CI)RX'
```

SIDs represent Administrators, SYSTEM and LocalService, avoiding localized account-name ambiguity. Verify each command's success and inspect effective ACLs. These commands remove inheritance; review any pre-existing explicit access entries and remove unauthorized entries using your security administration process.

Copy the environment example **only on first setup**, then edit the private copy using a trusted editor:

```powershell
$runtime = 'C:\ProgramData\GarageManager\secrets\runtime.env'
if (Test-Path -LiteralPath $runtime) { throw 'Runtime environment exists; do not overwrite it.' }
Copy-Item 'C:\Apps\GarageManager\deploy\windows\runtime.env.example' $runtime
```

Set `PGPASSWORD` to the strong `garage_runtime` password you selected. Keep `PGHOST=127.0.0.1`, `PGDATABASE=garage_manager`, `PGUSER=garage_runtime`, `MIGRATIONS_ON_START=false` and `HOST=127.0.0.1`. If your PostgreSQL uses a different port, update `PGPORT`.

Do not set `DATABASE_URL` as well: a URL takes precedence over the individual PG fields. Do not set `NODE_TLS_REJECT_UNAUTHORIZED=0`. Local loopback database traffic need not leave the host; use certificate-verified TLS if moving the database remotely.

Environment files are plaintext secrets protected by ACLs, not encryption. Use encrypted server disks and an approved secret manager where available. LocalService is a shared built-in identity; other services running as LocalService can potentially read its authorized files. Use a dedicated low-privilege service identity instead where stronger service isolation is required, and adjust all ACLs/task identities accordingly.

## 4. Apply schema and grants

Run migration with the deployment role. Supply its password through an interactive secure prompt, not command history or a committed file:

```powershell
$secret = Read-Host 'garage_deploy password' -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try {
  $env:PGUSER = 'garage_deploy'
  $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
  & 'C:\Program Files\nodejs\node.exe' `
    '--env-file=C:\ProgramData\GarageManager\secrets\runtime.env' `
    'C:\Apps\GarageManager\server\dist\migrate.js'
  if ($LASTEXITCODE -ne 0) { throw 'Schema migration failed.' }
} finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
  Remove-Item Env:PGUSER, Env:PGPASSWORD -ErrorAction SilentlyContinue
}

& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' `
  -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U garage_deploy -W -d garage_manager `
  -f 'C:\Apps\GarageManager\deploy\windows\grant-runtime.sql'
if ($LASTEXITCODE -ne 0) { throw 'Runtime grants failed.' }
```

Use a fresh deployment PowerShell session with no unrelated `PG*` or `DATABASE_URL` overrides. Node's process environment overrides env-file values; the deploy credentials are intentionally temporary. Migration errors stop the procedure. Repeat grants after future migrations; do not give the runtime role ownership simply to silence permissions errors.

## 5. Bootstrap the garage owner

Use the runtime environment, which now has access to the migrated tables. Set the garage-owner password only in the temporary process environment:

```powershell
$env:BOOTSTRAP_EMAIL = Read-Host 'Garage owner email'
$secret = Read-Host 'New garage owner password (12+ characters)' -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try {
  $env:BOOTSTRAP_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
  & 'C:\Program Files\nodejs\node.exe' `
    '--env-file=C:\ProgramData\GarageManager\secrets\runtime.env' `
    'C:\Apps\GarageManager\server\dist\bootstrap.js'
  if ($LASTEXITCODE -ne 0) { throw 'Owner bootstrap failed.' }
} finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
  Remove-Item Env:BOOTSTRAP_EMAIL, Env:BOOTSTRAP_PASSWORD -ErrorAction SilentlyContinue
}
```

This works only when there are no accounts. Database passwords and the garage owner's app password are different credentials. Never provide real administrator credentials to a Play reviewer.

## 6. Install the Node Windows service

Place the verified WinSW x64 binary at `C:\Services\GarageManager\GarageManager.exe`. Copy [GarageManager.xml](GarageManager.xml) beside it; the executable and XML must have the same base name.

```powershell
Copy-Item 'C:\Apps\GarageManager\deploy\windows\GarageManager.xml' `
  'C:\Services\GarageManager\GarageManager.xml'
icacls 'C:\Apps\GarageManager' /grant '*S-1-5-19:(OI)(CI)RX'
& 'C:\Services\GarageManager\GarageManager.exe' install
if ($LASTEXITCODE -ne 0) { throw 'Service installation failed.' }
& 'C:\Services\GarageManager\GarageManager.exe' start
if ($LASTEXITCODE -ne 0) { throw 'Service start failed.' }
Get-Service -Name GarageManager
Invoke-RestMethod 'http://127.0.0.1:3000/health'
```

Verify LocalService has read/execute access to the application and Node executable, and **no write access** to application code, WinSW binary or configuration. Review inherited ACLs on `C:\Apps\GarageManager`; the additive grant above does not remove pre-existing write permissions. Keep code updates administrator-controlled.

The API should listen only on `127.0.0.1:3000`:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 3000 |
  Select-Object LocalAddress, LocalPort, OwningProcess
```

Do not add an inbound firewall rule for port 3000. Investigate any listener bound to `0.0.0.0` or `::`. Service logs are bounded to five 10 MB files; inspect errors without publishing secrets.

For a verified release update: back up, stop **this service**, copy the release, migrate with `garage_deploy`, apply grants, restart and verify readiness. Do not reset the database or replace existing private runtime settings.

## 7. Configure IIS and HTTPS

1. Point the domain's DNS A record to the Windows Server's public address. If publishing an AAAA record, confirm IPv6 routing reaches this same server.
2. Install IIS, URL Rewrite and ARR; arrange firewall/NAT access for 443 (and 80 for redirect/certificate validation when used). Do not alter unrelated site's bindings.
3. In IIS Manager, select the **server** → Application Request Routing Cache → Server Proxy Settings → **Enable proxy**. Apply it. ARR proxy enablement is server-wide; review effects on existing sites.
4. Set a proxy timeout of at least 30 seconds. Configure trusted proxy logging/request limits and certificate renewal monitoring.
5. Copy **only** [iis/web.config](iis/web.config) to `C:\inetpub\garage-api\web.config`. Never use the application/secrets directory as the site's physical root.
6. Create a dedicated application pool (`GarageApi`, No Managed Code, Integrated) and website (`GarageApi`) with that physical path. Keep Anonymous Authentication enabled and disable Windows Authentication; app authentication uses Bearer tokens.
7. Add HTTP binding `*:80:android.sgsoftech.in` for redirect. Add HTTPS binding `*:443:android.sgsoftech.in`, enable SNI and select the valid certificate.
8. Grant the app-pool identity read access to the IIS directory only. It does not require access to Node code, PostgreSQL or the environment file.
9. Keep IIS configuration sections for rewrite/request filtering available to this site; a locked section causes 500.19 and must be resolved by an IIS administrator.

The provided rules reject unexpected hosts, redirect HTTP to the fixed HTTPS domain and proxy HTTPS API routes to loopback. HTTP 301 redirects are intended for browser visits; the Android app uses HTTPS directly. **Never send credentials over HTTP**, even if it redirects.

Verify from the server and a separate external device:

```powershell
Invoke-RestMethod 'https://android.sgsoftech.in/health'
curl.exe --silent --show-error --dump-header - --output NUL `
  'https://android.sgsoftech.in/health'
curl.exe --silent --show-error --dump-header - --output NUL `
  'http://android.sgsoftech.in/health'
```

Expected: HTTPS 200 with `{"status":"ok"}`, HTTP redirect to the fixed HTTPS URL, valid certificate chain, `Cache-Control: no-store`, anti-framing/CSP/MIME headers. Confirm a request to `/customers` without installation headers returns 400 JSON, not an IIS error page; valid active installation headers without staff authentication return 401. Do not use `curl -k` to hide TLS errors.

This configuration assumes IIS terminates TLS directly. If there is another load balancer/CDN in front, review HTTPS forwarding and redirect behavior before deployment.

## 8. Schedule reminders and backups on Windows

Set your custom gateway URL/token and approved templates (`WHATSAPP_TEMPLATE`, `WHATSAPP_STATUS_TEMPLATE`) in the private runtime environment. Keep `REMINDERS_ENABLED=false` until the real gateway supports the [POST/idempotency contract](../../server/API.md#custom-whatsapp-service).

After configuration, manually run:

```powershell
$ErrorActionPreference = 'Stop'
& 'C:\Apps\GarageManager\deploy\windows\Run-Reminders.ps1'
& 'C:\Apps\GarageManager\deploy\windows\Run-Backup.ps1'
```

The scripts throw on worker/backup failure. Test them under the **same identity** used by scheduled tasks, not only as administrator.

In Task Scheduler create:

- `GarageManager-Reminders`: every five minutes, run whether logged in or not, do not start a new instance if already running.
- `GarageManager-Backup`: daily at an appropriate local time, same no-overlap setting.

For both use `NT AUTHORITY\LOCAL SERVICE` (or your dedicated service account), without highest privileges. Program:

```text
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe
```

Reminder arguments:

```text
-NoProfile -NonInteractive -File "C:\Apps\GarageManager\deploy\windows\Run-Reminders.ps1"
```

Backup arguments:

```text
-NoProfile -NonInteractive -File "C:\Apps\GarageManager\deploy\windows\Run-Backup.ps1"
```

Use `C:\Apps\GarageManager` as “Start in”. Follow your organization's script-signing/execution policy; do not disable it globally. Enable task history and alert on nonzero results. In the app, “Reminders setting: Enabled” reflects the environment flag, **not proof that a scheduled task is running**.

The backup script writes a fresh timestamped JSON file, never overwrites existing backups and does not automatically delete files. Define a reviewed retention/archival schedule and encrypted off-server storage. JSON excludes accounts/sessions/audit logs, so also schedule DBA-managed PostgreSQL backups and test restore into a separate database.

## 9. Android / Google Play publishing

Permanent application ID: **`in.sgsoftech.garagemanager`**. Production and preview profiles default to **`https://android.sgsoftech.in`**. Both release packages require HTTPS; no database/messaging credentials are included.

See [Google Play guide](../../mobile/PUBLISHING.md) for local signed AAB builds, optional EAS builds, signing, reviewer access and required policy forms. A Google Play developer account does **not** automatically provide an Expo/EAS account.

Before publishing, verify the full flow on at least two Android devices against this IIS server: sign-in, concurrent services/stock/payments, PDF sharing, backup restore and real WhatsApp gateway acceptance. Remaining native/real-database verification and dependency advisories from the [main guide](../../README.md#delivery-verification-and-remaining-gates) remain release gates.
