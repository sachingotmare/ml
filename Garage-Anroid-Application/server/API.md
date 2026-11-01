# Garage API

Base URL: your garage's HTTPS server. Business routes require staff authentication using `Authorization: Bearer <opaque-token>`. `/health`, `/auth/login` and `/license/*` do not require a staff session.

Licensing routes do not require staff authentication. All other routes except `/health`, including `/auth/login`, require a registered installation with active trial/license and headers `X-Installation-Id: <UUID>` and `X-Installation-Secret: <64 hex characters>`. Staff authentication is still independently enforced.

Sessions expire after 12 hours. Password change revokes all sessions; deactivating a staff account immediately blocks access. No public account registration is available.

Responses are JSON; errors have `{ "error": "actionable description" }`. Validation failures return 400, missing sessions 401, role denial 403, missing records 404 and conflicts 409. Internal errors return 500 with a request ID.

## Routes

| Method | Route | Role | Purpose |
|---|---|---|---|
| GET | `/health` | Public | Database health |
| POST | `/license/register` | Installation | `{requestId,secret}` registers first connection; retries preserve trial expiry |
| GET | `/license/status` | Installation | Server-timed trial/license state and public phone request code |
| POST | `/license/activate` | Installation | `{key}` verifies an issuer-signed installation-bound license |
| POST | `/auth/login` | Public | `{email,password}` → `{token,expiresAt,user}` |
| GET | `/auth/me` | Staff | Current account |
| POST | `/auth/logout` | Staff | Revoke current session |
| POST | `/auth/password` | Staff | `{currentPassword,password}`; revoke all sessions |
| GET | `/staff` | Staff | Assignment directory |
| POST | `/staff` | Owner | `{name,email,password,role}` |
| PATCH | `/staff/:id` | Owner | `{active}` |
| GET / PUT | `/settings` | Staff / Owner | Garage identity, GSTIN and reminder lead days |
| GET | `/dashboard` | Staff | Counts; owner also receives all-time accounting totals |
| GET | `/:kind` | Staff* | `{items,total}`; `limit` 1–100, `offset`, literal `search` |
| GET | `/:kind/:id` | Staff* | One domain record |
| POST | `/customers` | Staff | Customer with explicit `whatsappConsent` |
| PUT | `/customers/:id` | Staff | Edit customer / withdraw consent |
| POST | `/bikes` | Staff | Register bike against `customerId` |
| POST | `/items` | Owner | Inventory item and opening movement |
| PUT | `/items/:id` | Owner | Name, cost/selling prices, reorder level and supplier |
| POST | `/items/:id/stock` | Owner | `{delta,reason}` |
| POST | `/jobs` | Staff | Open job card with priced parts snapshot |
| PATCH | `/jobs/:id` | Staff | `{status:"in_progress"\|"completed"\|"cancelled"}` |
| PUT | `/jobs/:id` | Owner | Revise open job parts/accessories/estimate using the complete job request |
| POST | `/jobs/:id/tracking` | Owner | `{stage,note,promisedDelivery?}` records a customer-visible progress event |
| POST | `/jobs/:id/share-status` | Owner | `{eventId}` queues a consent-based latest-event WhatsApp update |
| GET | `/invoices/:id/ledger` | Owner | `{payments,paidPaise}` |
| POST | `/invoices/:id/payments` | Owner | Record idempotent partial/full payment |
| POST | `/expenses` | Owner | `{description,category,amountPaise,date}` |
| GET | `/report?from=YYYY-MM-DD&to=YYYY-MM-DD` | Owner | Date-range cash/invoice totals; all-time outstanding |
| GET | `/gateway-status` | Owner | `{configured,enabled}`; no secrets |
| GET | `/backup` | Owner | Consistent version-1 business snapshot |
| POST | `/restore` | Owner | Validate and restore snapshot into empty garage |

Kinds: `customers`, `bikes`, `items`, `jobs`, `invoices`, `payments`, `expenses`, `movements`, `reminders`.

*`invoices`, `payments` and `expenses` are owner-only. Read-only inventory data is available to staff for estimates; owners alone can change inventory.

Exact request shapes and limits are defined by the [shared schemas](../shared/index.ts). Fields not explicitly allowed are rejected. IDs are UUIDs; dates are real calendar dates in `YYYY-MM-DD`; money uses integer paise and GST uses basis points (18% = 1800).

## Installation licensing

The Android app automatically generates and securely stores a UUID and a random 32-byte secret, then registers on its first successful API connection. Send installation headers on status/activation and all business requests. Sharing the `GM1-<UUID>` request code does not reveal the possession secret. The public register/status/activation routes require installation credentials rather than staff login so expired devices can activate.

Trial lasts 30 × 24 hours from registration, based on database time. Re-registering the same UUID and secret never restarts it. An active trial or valid license is required even when the staff session is still valid. Expired business requests return HTTP **402** with `{error,license}`; the entitlement response includes `requestCode`, `state`, `trialExpiresAt`, `licenseExpiresAt`, `serverTime`, `remainingDays` and `activationConfigured`.

The issuer signs `GMK1.<base64url claims>.<Ed25519 signature>` tokens containing version 1, requestId, issuedAt and expiresAt. Only the server's configured public key verifies them. Unknown-phone, expired, future-issued, malformed or tampered tokens fail explicitly. Renewals never shorten stored expiry; neither license activation nor JSON restore resets the original trial.

See the [issuer/setup guide](../licensing/README.md). Credentials and private signing keys are excluded from all business JSON exports; full PostgreSQL disaster-recovery backups must preserve `installations`. Keep your server clock correct. Reinstall/data clearing is intentionally treated as a new installation, not hardware-bound DRM.

## Payment request

```json
{
  "amountPaise": 15000,
  "method": "upi",
  "date": "2026-11-01",
  "reference": "your-payment-reference",
  "idempotencyKey": "3a52ccde-7ab7-4b9e-9a45-1cf455d4059d"
}
```

Generate a fresh UUID per intended payment. Keep it unchanged when retrying that exact payment. Reusing it for changed data returns 409. Invoice balances are checked under the garage database lock.

## Custom WhatsApp service

Configured only through server environment variables. The URL must be HTTPS with no embedded credentials. Redirects are rejected. Requests time out after 15 seconds.

**POST** to `WHATSAPP_URL`, headers:

```http
Content-Type: application/json
Authorization: Bearer <WHATSAPP_TOKEN>
Idempotency-Key: <reminder UUID>
```

Body:

```json
{
  "to": "+919876543210",
  "template": "bike_service_due",
  "variables": {
    "customerName": "Example Customer",
    "garageName": "Garage Manager",
    "registration": "MH12AB1234",
    "serviceDate": "2026-11-15"
  },
  "idempotencyKey": "3a52ccde-7ab7-4b9e-9a45-1cf455d4059d"
}
```

Required success response: an HTTP 2xx JSON object containing:

```json
{"accepted": true}
```

Your gateway must:

1. Authenticate the configured Bearer token.
2. Validate phone number and approved template names.
3. Persist/deduplicate `idempotencyKey` **before** scheduling a message.
4. Return the same accepted result for retries of an already accepted key.
5. Enforce your WhatsApp provider's template, consent, opt-out and rate requirements.

The app sends only when customer consent is currently enabled and the next-service date is within the configured lead window. An old reminder is skipped if a later completed service exists for the same bike. Five failed attempts exhaust automatic retries. Timeouts can occur after your provider accepts the message, so deduplication is mandatory, not optional.

No delivery callback or inbound reply handling is implemented. `sent` means gateway acceptance; it must not be presented as confirmed delivery. Never include tokens or customer details in gateway/API logs.

## Service tracking and fitted accessories

Tracking stages: `received`, `inspection`, `awaiting_approval`, `approved`, `working`, `waiting_parts`, `quality_check`, `ready`, `delivered`, `cancelled`. These are owner-recorded workshop statuses, not GPS telemetry or customer self-service. Actual estimate approval must be obtained separately before recording `approved`.

Job creation/changes accept `promisedDelivery` as an ISO date/time with an explicit timezone, e.g. `2026-11-05T18:00:00+05:30`. Each part request also accepts `category: "part" | "accessory"` and `fitmentNote`. Open work lines are planned items; completion deducts inventory and freezes them into the invoice as fitted/replaced items. Revised estimates use current selling prices and should be reconfirmed with the customer.

Tracking changes and work-line changes append actor/time/note history (maximum 200 events per service). Ready/delivered requires completed invoicing; cancelled/delivered tracking cannot be reopened. Older records without tracking fields remain readable. Backup validation includes timeline/message correspondence.

To share the latest event, POST its UUID to `/jobs/:id/share-status`. The gateway must be configured, reminders enabled, and the customer must have opted in. Repeated requests for the same event reuse its UUID and cannot duplicate a message. The existing scheduled worker processes the queue, rechecks consent and suppresses obsolete events.

Set `WHATSAPP_STATUS_TEMPLATE=bike_service_status` on the server. Status payloads use the same authenticated POST contract above, with additional template variables:

```json
{
  "customerName": "Example Customer",
  "garageName": "Garage Manager",
  "registration": "MH12AB1234",
  "serviceDate": "2026-11-04",
  "serviceStatus": "waiting parts",
  "workNote": "Replacement brake pads ordered",
  "promisedDelivery": "2026-11-05T18:00:00+05:30"
}
```

The message is queued, not sent synchronously. Check its pending/sent/failed/skipped state in Reminders. `sent` only confirms gateway acceptance. The garage owner chooses what to share; no customer login is required.
