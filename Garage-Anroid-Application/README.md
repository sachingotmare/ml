# Garage Manager

Android garage management application with a shared Node.js API and PostgreSQL database. Each installation serves **one garage**, with multiple authenticated staff and devices. Business data lives on your server; internet access is required. There are no mock screens, default passwords, or seeded customer records.

## Included workflows

- Customers, international phone numbers, consent capture and withdrawal.
- Bikes linked to customers, registration uniqueness, odometers and service history.
- Inventory, unique SKU, purchase/selling prices, suppliers, opening stock, stock receipts/corrections, movement history and low-stock indicators.
- Service job cards, complaints, mechanic assignment, parts/labour estimates, optional GST, progress, completion and cancellation.
- Atomic service completion: validate available stock, deduct parts, update odometer, create a numbered immutable invoice and schedule the next-service reminder.
- Partial/full cash, UPI, card and bank payments; outstanding balances and idempotent payment retries.
- PDF invoice sharing, expenses, date-filtered financial reports and dashboard.
- Owner/mechanic permissions, staff activation/deactivation, password changes and session revocation.
- Consent-based automatic WhatsApp reminders through your custom HTTPS service, bounded retries and visible failures.
- Owner-managed service timeline: inspection, approval, waiting for parts, repair, quality check, readiness and delivery; promised delivery times and customer-visible work notes.
- Explicitly classified replacement parts/accessories, quantities, SKU and fitment notes in service history and PDF invoices. Open services can be revised; completed fitted-item records are immutable.
- Share the latest service-status event to customer WhatsApp using the same consent/idempotency-aware worker; no customer login.
- Business JSON export/import; restore refuses to overwrite any live records.
- Per-installation 30-day server-timed trial, phone-generated license request code and issuer-signed expiring activation/renewal keys. Expiry blocks access without deleting business data.

**Accounting boundary:** GST is an optional combined tax rate, not a tax-compliance engine. CGST/SGST/IGST splitting, e-invoicing, credit notes, refunds, payment processing, purchase orders and payroll are not implemented. Confirm tax treatment with your accountant before production invoicing. Closed services/invoices cannot be edited or deleted; cancel an incorrect open job and recreate it.

### Service tracking comparison

The public [Maruti Suzuki app listing](https://play.google.com/store/apps/details?id=com.maruti.icp&hl=en-IN), reviewed November 1, 2026, describes live pickup-to-drop-off service updates, estimates, remote approvals and accessories. Relevant workshop workflows have been implemented independently here: owner-recorded service stages, an actor/time/work-note timeline, promised delivery, editable open estimates, and classified fitted parts/accessories.

Open a service job → Edit work / add parts and accessories to record item, SKU, quantity and fitting/replacement details. Complete the job only after checking that those work lines reflect the actual parts used. Completed history and PDF invoices preserve those details; inventory is deducted exactly at completion.

The owner can select a tracking stage, save a customer-visible note and tap **Share latest status to customer WhatsApp**. Your existing gateway must support the `bike_service_status` template in addition to `bike_service_due`; see the [API contract](server/API.md#service-tracking-and-fitted-accessories). Messages are queued for the scheduled worker, recheck consent and skip stale events. Track pending/accepted/failed states in Reminders. No customer login, GPS/vehicle telemetry, customer remote-approval link, parking marketplace or vehicle-sales feature is included. An “approved” stage is a staff record of approval obtained separately, not proof of online customer approval. No Maruti branding or proprietary code is copied.

## Project layout

- [mobile](mobile): Expo / React Native Android application.
- [server](server): API, PostgreSQL schema, bootstrap, reminder worker and backup CLI.
- [shared](shared): shared request validation, domain types, integer-paise calculations and India calendar dates.
- [licensing](licensing): standalone encrypted-key issuer tool and activation/setup instructions. Private signing keys must stay outside this project and off the server/phone.
- [compose.yaml](compose.yaml): private database and loopback-bound API deployment.
- [server API and WhatsApp contract](server/API.md).

## Local setup (Windows PowerShell)

### Trial and licensing setup

Every installation starts a 30-day trial on its first successful registration with the garage server. After expiry the app asks for a key and shows its request code. You issue a time-limited signed key for that code; the phone pastes it to activate or renew.

Follow the [licensing guide](licensing/README.md) to create encrypted issuer keys on your trusted computer, install **only the public key** on the server (`LICENSE_PUBLIC_KEY_FILE`), and issue licenses with `License-Issuer.ps1`. The Windows deploy script accepts `-LicensePublicKeyPath`. Without public-key configuration, trials work but activation is unavailable. Existing server installations must run the schema migration and runtime grants before using the new app.

As confirmed, clearing app data/reinstalling creates a new request code and may start a new trial. This is installation-based licensing, not immutable physical-device licensing. Expiry does not delete garage records. Review Play billing/payment policy before monetizing license sales.

Requires Node.js 24.13 or newer and PostgreSQL 17 or newer. Android Studio with Java and the Android SDK is needed for a local APK.

```powershell
Set-Location 'C:\GitRepo\ml\Garage-Anroid-Application'
npm ci
npm run build
Copy-Item '.\server\.env.example' '.\server\.env'
```

Edit [server/.env.example](server/.env.example)'s copied values in your private environment:

1. Create an empty PostgreSQL database and a dedicated database user.
2. Set `DATABASE_URL`. For a remote database, require certificate-verified TLS (`sslmode=verify-full`) and trusted certificates.
3. Set a real `BOOTSTRAP_EMAIL` and a unique `BOOTSTRAP_PASSWORD` of at least 12 characters.
4. Set `GARAGE_NAME`.
5. Keep `REMINDERS_ENABLED=false` until the gateway is configured and tested.

Create the initial owner:

```powershell
npm run bootstrap -w @garage/server
```

Bootstrap only works when there are no accounts. Remove the bootstrap password from your environment immediately afterwards.

Start the API:

```powershell
npm run server
```

Health endpoint: `http://127.0.0.1:3000/health`. The API applies the initial schema idempotently on startup. Schema creation is separated in [server/src/db.ts](server/src/db.ts); future schema changes should use versioned migrations.

Start the Android development app:

```powershell
npm run android
```

Use an emulator or scan the Expo development QR code with a compatible Expo Go installation. Enter the server address and your owner credentials on the sign-in screen. Android emulator access to the host is `http://10.0.2.2:3000` in development. Physical devices need a reachable server or HTTPS tunnel you control. **Release APKs allow HTTPS only.** Do not expose a development API publicly.

After signing in:

1. Manage → edit garage identity/GSTIN and add mechanic accounts.
2. Add customers; enable reminders only with their explicit permission.
3. Register customer bikes.
4. Add inventory and stock.
5. Create a service job with parts, labour and the next-service date.
6. Complete the job, then Billing → receive payment / share PDF.

All amounts are stored as integer paise. Prices are tax-exclusive, GST is rounded once at invoice level, and calendar dates use `Asia/Kolkata`. Messages and connection failures are surfaced rather than represented as empty data.

## Deploy on your server

### PowerShell deployment and Android build automation

Use the [deployment orchestrator](deploy/windows/Deploy-GarageManager.ps1) to check prerequisites, preview changes, deploy the Windows API/IIS setup, or build signed Android packages. Start with read-only checks and a plan:

```powershell
Set-Location 'C:\GitRepo\ml\Garage-Anroid-Application'
.\deploy\windows\Deploy-GarageManager.ps1 -Mode Check
.\deploy\windows\Deploy-GarageManager.ps1 -Mode All -WhatIf
```

The check reports missing tools; it does not install them. Actual deployment/build modes ask for approval before changes or supported downloads and ask for secrets securely. Follow the [automation instructions](deploy/windows/README.md) for certificate, WinSW verification, existing signing-keystore and installation parameters. Existing PostgreSQL is reused; the administrator password is never hard-coded. DNS, trusted certificate issuance and Google Play review/account requirements cannot be satisfied by running a local script alone.

For Cloudflare orange-cloud hosting with an IIS Origin certificate, use `-CloudflareProxy` consistently. See the [Cloudflare setup](deploy/windows/README.md#cloudflare-proxied-iis-with-an-origin-certificate): Full (strict), pinned Origin CA validation and normal public edge HTTPS verification are required. Public CA root certificates bundled with deployment are not private/license keys.

The automation's 102 parser/unit/safety checks pass without changing IIS, services, installed tools or live database data, including API 37.0 detection, SDK quoting/completion checks, Android archive/path fixtures, disposable certificate-chain tests and captured Cloudflare TLS invocations. A separate portable CMake 3.22.1 fixture reproduced the failed 128 limit (363-character object path) and verified hashing at 240 (240-character full object path); this is generation verification, not a native Android compilation test. Actual Windows/Cloudflare deployment and native signed APK/AAB execution still require your server/build workstation and credentials; they have not been executed here.

**Your selected target is Windows Server with existing PostgreSQL and IIS at `android.sgsoftech.in`. Follow the [Windows Server / IIS guide](deploy/windows/README.md)** for database roles, separate migrations, WinSW, HTTPS proxy configuration and Task Scheduler. Docker below is an alternative, not needed for your Windows deployment.

Google Play application ID is now `in.sgsoftech.garagemanager`. See the [publishing guide](mobile/PUBLISHING.md) for signed AAB delivery; a Google developer account does not provide Android build tools or an Expo account.

Install Docker Engine / Compose on your server. Configure a TLS-terminating reverse proxy and a DNS name first.

1. Create a private server environment file from the example; never commit it.
2. Provide `POSTGRES_PASSWORD` to Compose through your server's secret manager or protected environment.
3. In `server/.env`, set `DATABASE_URL=postgresql://garage:<URL-encoded-password>@db:5432/garage`.
4. Set `HOST=0.0.0.0`, `NODE_ENV=production` and owner bootstrap variables for the one-time account creation.
5. Build/start:

```sh
docker compose up --build -d
docker compose run --rm api node server/dist/bootstrap.js
```

Remove the bootstrap password after account creation and recreate the API service with the updated environment. The database is not exposed on a host port; the API is bound to host loopback at port 3000.

Configure your reverse proxy to forward `https://your-garage-domain` to `http://127.0.0.1:3000`. Require TLS 1.2+, valid renewed certificates, a 10 MB maximum request body, sensible timeouts and request limits. The API already supplies no-store, anti-framing, CSP, MIME-sniffing protection and HSTS headers. CORS is not enabled because this is a native Android client. Do not run Expo/Metro on a public production server.

The API runs as an unprivileged container user, with read-only filesystem and dropped capabilities. Use encrypted server/database disks, least-privilege accounts, restricted network access, monitored backups and regular dependency/container updates. Restrict environment files to administrators; avoid logging customer information or messaging tokens.

### Automatic WhatsApp reminders

Set the following **server-only** variables:

```dotenv
WHATSAPP_URL=https://your-whatsapp-service.example/send
WHATSAPP_TOKEN=<secret supplied securely>
WHATSAPP_TEMPLATE=bike_service_due
REMINDERS_ENABLED=true
```

Your service must implement the [documented POST contract](server/API.md#custom-whatsapp-service) and deduplicate the idempotency key. No messaging secret belongs in the Android app.

Configure a five-minute cron on the server:

```cron
*/5 * * * * cd /absolute/path/to/garage && docker compose run --rm api node server/dist/worker.js
```

Run the worker once manually and check its exit status before enabling cron. It processes at most 50 reminders per run. Gateway failures are recorded, use exponential backoff and stop after five attempts. Withdrawn consent and a newer completed service suppress an old pending reminder. Multiple workers claim records under the database lock; stale claims recover after ten minutes using the same provider idempotency key.

`sent` means **accepted by your gateway**, not confirmed delivery. Delivery receipts and inbound WhatsApp replies are not implemented. Consent, approved templates and your provider's messaging regulations are your responsibility. This delivery uses your custom WhatsApp service, not a paid SMS provider.

### Backups

Owner → Manage → Export business backup opens the native share sheet. Save to trusted encrypted storage and verify the saved file. Restore accepts JSON up to 10 MB and only works in an empty business database; existing accounts can remain.

For scheduled backups, invoke the backup CLI with a new destination each time:

```sh
BACKUP_FILE=/secure/backups/garage-2026-11-01.json node server/dist/backup.js
```

The container's default filesystem is read-only; mount an approved backup destination if using the CLI inside Docker. Business JSON deliberately excludes users, password hashes, sessions and audit logs. For full disaster recovery, separately schedule encrypted PostgreSQL `pg_dump` backups with a retention policy and periodically test restoration into a separate database. Restore reassigns unavailable staff references to “Unassigned” and preserves original stock-movement actor IDs for historical attribution.

## Build an APK

The source includes [app.json](mobile/app.json) and [eas.json](mobile/eas.json). The confirmed package ID is `in.sgsoftech.garagemanager`; production/preview EAS builds use `https://android.sgsoftech.in`. The [publishing guide](mobile/PUBLISHING.md) covers local production signing and Google Play's AAB requirement.

### Local debug APK

Install Android Studio, its SDK and the JDK version required by the installed React Native release; configure `JAVA_HOME` and `ANDROID_HOME`. Then:

```powershell
Set-Location 'C:\GitRepo\ml\Garage-Anroid-Application'
npm run build -w @garage/shared
Set-Location '.\mobile'
npx expo prebuild --platform android
npx expo run:android --variant debug
```

Debug output is generated under `mobile\android\app\build\outputs\apk\debug`. A standalone production/installable APK also needs a bundled JS build and an appropriate signing key; keep signing keys outside source control.

### Optional Expo cloud build (you initiate)

If you approve uploading the project to Expo and have an account, install/use EAS CLI, sign in, configure the EAS project and run:

```powershell
Set-Location 'C:\GitRepo\ml\Garage-Anroid-Application\mobile'
npx eas-cli login
npx eas-cli build:configure
npx eas-cli build --platform android --profile preview
```

No cloud deployment or source upload has been performed by this implementation.

## Verification

```powershell
Set-Location 'C:\GitRepo\ml\Garage-Anroid-Application'
npm run check
npm run build
npm test
Set-Location '.\mobile'
npx expo install --check
npx expo export --platform android
```

The default workflow tests use `pg-mem` and cover API permissions, validation, registration, stock, job completion, invoices, payments, GST, expenses/reports, reminders and backup protection. Real PostgreSQL locking/rollback is tested separately when `TEST_DATABASE_URL` points to a **fresh disposable database**:

```powershell
$env:TEST_DATABASE_URL = 'postgresql://test_user:<test-password>@localhost:5432/fresh_test_database'
npm test
Remove-Item Env:TEST_DATABASE_URL
```

The test suite refuses an existing garage schema and never deletes your database. It leaves its test schema in the disposable database for inspection.

### Delivery verification and remaining gates

- Type checks and 30 API/configuration/licensing tests passed (one real PostgreSQL test skipped); native Android project generation and Metro/Hermes bundle export passed. The generated project is available in [mobile/android](mobile/android) and can be regenerated from the Expo configuration.
- Real PostgreSQL tests were attempted against a new isolated cluster, not the installed server's existing data. PostgreSQL refused startup because this tool session runs with administrative permissions. Its safety check was not bypassed. Run the optional database test with a fresh database from an unprivileged environment.
- No APK was produced: Java / Android SDK were not detected, and no Expo account or cloud-upload approval was supplied.
- The current stable Expo 58 stack removed the initially identified high-severity dependency advisories. `npm audit` still reports 12 moderate entries propagated from Expo build tooling's `glob`/`minimatch` dependencies. Do not treat this delivery as an approved production release; resolve or formally assess those advisories before publishing.
- Your PostgreSQL production connection, HTTPS deployment, owner account and WhatsApp endpoint/token must still be configured. No external message was sent.

An Expo Android bundle export is **not an APK** and does not verify native installation. Before release, run Android device/emulator tests for sign-in, screen-reader labels, keyboard focus, larger text, form validation, PDF/file sharing, stock contention across devices and reminder gateway behavior. A real gateway acceptance/delivery test requires your service configuration. Production readiness also requires human review, server deployment, tax review and operational backup testing.
