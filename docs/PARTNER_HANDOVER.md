# ITSthe1.ID API — integration handover report

**For:** partner development team
**From:** ITSthe1 API team
**Build:** v1.0.0 · **Report date:** 2026-08-04

This is the package you need to integrate against the ITSthe1.ID API: the API
itself, a request collection covering every endpoint, two runner scripts, and an
honest account of what works, what does not, and what we have and have not been
able to test.

Read this file first, then [PAYLOADS.md](PAYLOADS.md) when you need the
field-by-field detail.

---

## Contents

- [In one page](#in-one-page)
- [What is in this package](#what-is-in-this-package)
- [Standing up the test environment](#standing-up-the-test-environment)
- [Verification status — what we actually ran](#verification-status--what-we-actually-ran)
- [Known issues](#known-issues)
- [The integration contract](#the-integration-contract)
- [Escorts and additional guests](#escorts-and-additional-guests)
- [Error codes](#error-codes)
- [Reference database contents](#reference-database-contents)
- [Security](#security)
- [What we need from you](#what-we-need-from-you)

---

## In one page

The ITSthe1.ID API records hotel guest movements — check-in, additional guests,
document images, room changes, guest departures, check-out and cancellation —
into SQL Server, following the **1.ID API Specification Document**. It normally
runs on the hotel's front-desk machine, serving the ITSthe1.ID WPF desktop
client over the local network.

| | |
|---|---|
| Stack | Python 3 · Flask 3.1 · SQLAlchemy 2.0 · pyodbc · Waitress |
| Packaging | single Windows executable, `dist/run.exe` (PyInstaller) |
| Database | SQL Server, schema `[<database>].[itsthe1.id]` |
| Transport | HTTP, JSON, **no authentication**, default port `5030` |
| Surface | 50 routes: 7 business transactions, 14 reference lookups, 13 table dumps, 9 monitoring |
| Health check | `GET /health` — 200 healthy, 503 with the failing check named |

Every business request and response carries the 1.ID envelope:

```json
{
  "MessageType": "CheckinRequest",
  "ClientUID": "Establishment101",
  "MessageUID": null,
  "CorrelationUID": "your-id-here",
  "Timestamp": "2026-08-04T08:00:00"
}
```

```json
{
  "hasErrors": false,
  "errorMessages": {},
  "messageType": "CheckinResponse",
  "clientUID": "Establishment101",
  "messageUID": "7230ad75-8a9f-45c0-a000-ddb587c66345",
  "correlationUID": "your-id-here",
  "timestamp": "2026-08-04T11:40:01.125047+05:30"
}
```

Validation failures come back as **HTTP 400** with `hasErrors: true` and a
numbered code in `errorMessages.general`, e.g. `40002 Checkin room does not
exist`.

---

## What is in this package

| Path | What it is |
|---|---|
| [`docs/PARTNER_HANDOVER.md`](PARTNER_HANDOVER.md) | **This report.** Start here. |
| [`docs/SPEC_CONFORMANCE.md`](SPEC_CONFORMANCE.md) | **This build vs the 1.ID API Specification Document** — endpoint coverage, the 22 spec error codes not implemented, and why the spec's own sample payloads are rejected here |
| [`docs/PAYLOADS.md`](PAYLOADS.md) | Field-by-field payload reference — every endpoint, every rule, every code value, with the live reference-table contents |
| [`docs/API.md`](API.md) | Endpoint contract and the full error-code list |
| [`docs/MONITORING.md`](MONITORING.md) | Health checks, the `/status` dashboard, logs, troubleshooting |
| [`docs/BUILD.md`](BUILD.md) | Building `run.exe` and deploying it |
| [`README.md`](../README.md) | How the API works, configuration reference |
| [`docs/payloads/*.json`](payloads/) | **17 ready-to-send payloads**, one per scenario |
| [`docs/payloads/ITSthe1.ID.postman_collection.json`](payloads/ITSthe1.ID.postman_collection.json) | **Postman collection: 61 requests in 8 folders**, every endpoint, with assertions and automatic id capture |
| [`docs/payloads/ITSthe1.ID.postman_environment.json`](payloads/ITSthe1.ID.postman_environment.json) | Matching environment (`baseUrl` and the id variables) |
| [`docs/payloads/check_all_reads.ps1`](payloads/check_all_reads.ps1) | Smoke test — hits every read-only endpoint, prints OK/FAIL. **Writes nothing.** |
| [`docs/payloads/run_write_flow.ps1`](payloads/run_write_flow.ps1) | Drives the full lifecycle end to end. **Writes to the database.** |
| [`config.example.json`](../config.example.json) | Configuration template — fill in your own connection string |

### The 17 payload files

| File | Endpoint | Scenario |
|---|---|---|
| `01_checkin_get.json` | `GET /checkin` | read one stay (body on GET) |
| `02_checkin_post_cash.json` | `POST /checkin` | one main guest, cash |
| `03_checkin_post_with_escorts.json` | `POST /checkin` | **main guest + two escorts** |
| `04_checkin_post_creditcard.json` | `POST /checkin` | card, early check-in, accessibility `other` |
| `05_checkin_post_houseuse.json` | `POST /checkin` | house use, no payment |
| `06_checkin_put.json` | `PUT /checkin` | amend an open stay |
| `07_checkin_post_backdated.json` | `POST /checkin/AddBackdatedCheckin` | stay already started and ended |
| `08_guest_get.json` | `GET /guest` | list guests on a stay (body on GET) |
| `09_guest_post_add_escort.json` | `POST /guest` | **add an escort to an open stay** |
| `10_guest_put_edit_escort.json` | `PUT /guest` | edit that escort |
| `11_guestattachment_post.json` | `POST /guestattachment` | extra document |
| `12_guestcheckout_post_escort.json` | `POST /guestcheckout` | escort leaves |
| `13_guestcheckout_post_mainguest_handover.json` | `POST /guestcheckout` | **main guest leaves, escort takes over** |
| `14_roomchange_post.json` | `POST /roomchange` | move the stay |
| `15_checkout_post.json` | `POST /checkout` | close the stay |
| `16_checkout_put.json` | `PUT /checkout` | amend a closed stay |
| `17_checkincancellation_post.json` | `POST /checkincancellation` | cancel instead of check out |

Every payload carries the same valid 1×1 JPEG as its attachment, so nothing
depends on a local image file. Tokens reading `REPLACE_WITH_…` need an id from
an earlier response — the Postman collection fills these in automatically.

---

## Standing up the test environment

### Prerequisites

| | |
|---|---|
| Windows | 10 / 11 / Server 2019+ |
| SQL Server | 2019 or later, with the `itsthe1.id` database restored |
| **ODBC Driver 17 for SQL Server** | required by `pyodbc`; the connection string names it explicitly |
| Python 3.11+ | only if running from source; `dist/run.exe` needs nothing installed |
| Storage folder | writable, for guest document images |

### 1. Configure

Copy `config.example.json` to `config.json` next to `run.py` (source) or next to
`run.exe` (deployed), and fill in your connection string.

```json
{
  "SQLALCHEMY_DATABASE_URI": "mssql+pyodbc://USER:PASSWORD@HOST\\INSTANCE/itsthe1.id?driver=ODBC+Driver+17+for+SQL+Server",
  "SCHEMA_NAME": "[itsthe1.id].[itsthe1.id]",
  "BaseDirectoryPath": "C:/ITSthe1/WPF/DOTS_Storage",
  "HOST": "127.0.0.1",
  "PORT": 5030
}
```

Two traps, both of which have cost us time:

- **`SCHEMA_NAME` is a `[database].[schema]` prefix**, applied to every table.
  Get it wrong and *every* endpoint fails with `42S02 Invalid object name`.
- **Use forward slashes in paths.** JSON treats `\` as an escape. `C:\build\files`
  parses without complaint into `C:\x08uild\x0ciles`, and the only symptom is a
  storage directory that "does not exist". The API detects and repairs this in
  memory since v1.0.0 and reports it as a warning on `/health` — fix the file
  anyway.

The file is read **once at startup**. Restart after editing.

### 2. Start it

```bash
dist\run.exe
```

…or from source:

```bash
pip install -r requirements.txt
```

```bash
python run.py
```

`run.exe` is windowless but puts a tray icon in the notification area: green when
every health check passes, red when one fails. Right-click for the status page,
the log folder, and a clean **Quit**. Pass `--no-tray` when running as a service.

### 3. Confirm it is alive

```bash
curl http://localhost:5030/health
```

Open <http://localhost:5030/status> for the live dashboard. Then run the
read-only smoke test — it touches nothing:

```bash
powershell -File docs\payloads\check_all_reads.ps1
```

Expect `OK` on all 5 monitoring endpoints, all 14 reference lookups, 12 of 13
table dumps, and both body-on-GET endpoints. See
[Known issues](#known-issues) for the thirteenth.

### 4. Import the Postman collection

Import both files from `docs/payloads/`, select the **ITSthe1.ID — local**
environment, set `baseUrl`, and run **1. Monitoring → GET /health**.

The collection captures ids for you, so you should not have to paste anything by
hand:

| Variable | Set by | Consumed by |
|---|---|---|
| `checkinUID` | any `POST /checkin` | every downstream request |
| `guestUID` | `POST /guest`, `GET /guest` | attachment, guest check-out |
| `mainGuestUID` | `GET /guest` | handover — the departing guest |
| `newMainGuestUID` | `POST /guest`, `GET /guest` | handover — the successor |

### 5. A working call order

1. `GET /ping`, `GET /health`
2. every reference lookup — these also prove `SCHEMA_NAME` is right
3. `GET /checkin`, `GET /guest` on an existing stay
4. `POST /checkin` on a **free** room — capture `CheckinUID`
5. `GET /checkin` on the new id
6. `POST /guest` — add an escort
7. `GET /guest` — collect the real **guest ids**
8. `POST /guestattachment`
9. `POST /roomchange` to another free room
10. `POST /guestcheckout` — the escort leaves
11. `POST /checkout`
12. `POST /checkincancellation` — on a throwaway check-in only
13. `GET /metrics` — every call above should be counted

Steps 1–3 and 13 are `check_all_reads.ps1`. Steps 4–11 are
`run_write_flow.ps1 -Force`, which generates fresh guest codes and document
numbers each run so it can be repeated.

**Timestamp ordering matters.** Room change and check-out are validated against
the most recently added guest, so keep: *check-in < escort check-in < room change
< escort check-out < check-out*. The supplied payloads are already ordered this
way.

---

## Verification status — what we actually ran

Executed on 2026-08-04 against a live instance (SQL Server 2022, database
`itsthe1.id`, API v1.0.0).

| Area | Status | Detail |
|---|---|---|
| 5 monitoring endpoints | ✅ **passed** | `/ping` `/version` `/health` `/metrics` `/routes`. `/health` reported healthy; `/routes` returned 50 URLs |
| 14 reference lookups | ✅ **passed** | all returned rows; every code value in the payloads was checked against them |
| 13 table dumps | ⚠️ **12 of 13** | `GET /guestdocumentimage` fails — see [D1](#d1--blocker--the-guestdocumentimages-table-does-not-exist) |
| `GET /checkin`, `GET /guest` | ✅ **passed** | real records returned, body sent on a GET via `curl.exe` |
| `check_all_reads.ps1` | ✅ **passed** | ran end to end |
| All 17 payload files | ✅ **valid** | parse as JSON; every country, document-type, visit-purpose, relationship and emirate code resolves against the live tables |
| Postman collection | ✅ **valid** | 61 requests, imports cleanly, no unresolved placeholders |
| **Every POST / PUT** | ❌ **not executed** | **blocked by [D1](#d1--blocker--the-guestdocumentimages-table-does-not-exist).** Payload shapes were derived by reading the route handlers line by line, not by observing a successful response |

**Be clear about what that last row means.** The write payloads are correct
against the source code, and every constant in them was validated against the
live reference tables — but no `POST` or `PUT` in this collection has yet
returned a success from a running instance, because none can until D1 is fixed.
Treat them as a well-founded starting point, not as regression-tested fixtures.

We deliberately ran no writes while producing this package: nothing in the
reference database was changed.

---

## Known issues

Fifteen findings, from a read of every route handler. Severity is our
assessment of the impact on **your** integration.

Deviations from the **1.ID API Specification Document** — 22 unimplemented spec
error codes, the `EmirateCode` rule, the missing `api/` URL prefix — are
catalogued separately in [SPEC_CONFORMANCE.md](SPEC_CONFORMANCE.md).

### D1 · **Blocker** · The `guestdocumentimages` table does not exist

Every endpoint that stores a document image — `POST /checkin`,
`POST /checkin/AddBackdatedCheckin`, `POST /guest`, `PUT /guest`,
`POST /guestattachment` — writes to the `GuestDocumentImage` model, and the
table it maps to is not in the database:

```
42S02 Invalid object name 'itsthe1.id.itsthe1.id.guestdocumentimages'
```

**Impact:** the entire write half of the API is unusable. `POST /checkin`
returns **HTTP 500**, and because the handler commits in stages it leaves an
orphan `checkin` row, an orphan `payment` row and a `guest` row behind, with no
`checkinguest`, no `guestversion` and the room left unflagged. Three such
failures are visible in `logs/api.log`:

```
2026-08-03 15:25:24 WARNING POST /checkin -> 500 (1595 ms) from 127.0.0.1
2026-08-03 15:26:58 WARNING POST /checkin -> 500 (1269 ms) from 127.0.0.1
2026-08-03 15:29:20 WARNING POST /checkin -> 500 (1317 ms) from 127.0.0.1
```

**Fix** — create the table:

```sql
USE [itsthe1.id];
CREATE TABLE [itsthe1.id].[guestdocumentimages] (
    DocumentId     INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    GuestId        INT NOT NULL REFERENCES [itsthe1.id].[guest](Id),
    DocumentUID    NVARCHAR(255) NULL,
    AttachmentCode NVARCHAR(255) NULL,
    [FileName]     NVARCHAR(255) NULL,
    FileSizeKB     INT NULL,
    ImageData      VARBINARY(MAX) NULL,
    UploadedAt     DATETIME2 NOT NULL
                   CONSTRAINT DF_guestdocumentimages_UploadedAt DEFAULT SYSDATETIME()
);
```

— or repoint the model if the table exists under another name in your schema.
Then clear the orphans:

```sql
DELETE c FROM [itsthe1.id].[checkin] c
 WHERE NOT EXISTS (SELECT 1 FROM [itsthe1.id].[checkinguest] g WHERE g.CheckinId = c.Id);
DELETE p FROM [itsthe1.id].[payment] p
 WHERE NOT EXISTS (SELECT 1 FROM [itsthe1.id].[checkin] c WHERE c.PaymentId = p.Id);
```

> Review the `SELECT` form of both statements before running the `DELETE` on any
> database you care about.

### D2 · High · `POST /checkin` is not transactional

Payment, check-in, guest, attachment, `checkinguest`, log and `guestversion` are
committed in **separate** steps. A failure part-way leaves a half-written stay
that no endpoint can clean up — the orphans in D1 are exactly this.

**Impact on you:** a 500 from `POST /checkin` does not mean "nothing happened".
Do not retry blindly; check `GET /checkintable` first, and clean up in SQL.

### D3 · High · `PUT /checkin` can edit the wrong stay

The handler locates the row to update with the guest's **newest `checkinguest`
row across every check-in**, not the row belonging to the check-in being
amended. If the same person is also on a more recent stay, that stay's row is
modified instead.

**Impact:** silent cross-contamination for repeat visitors. Keep test guests
unique per stay until this is fixed.

### D4 · Medium · `ChildEscort` cannot be recorded

`EscortTypeId` is hard-coded to `2` (AdultEscort) in all three write paths. No
payload field selects it, so `1 ChildEscort` is never written, and
`checkin.AdultEscortCount` / `ChildEscortCount` are `null` on every row —
although `GET /escorttype` still serves both values for the client's dropdown.

**Impact:** if your integration needs to distinguish adults from children on a
stay, the API cannot currently express it. Flag this to us.

### D5 · Medium · Missing guest keys surface as HTTP 500, not 400

`GenderCode`, `Email`, `ResidenceCountryPhone`, `DocumentNumber`,
`ResidenceCountryCode`, `CheckinDateTime` and `IsMainGuest` are read with `[]`
rather than `.get()`, so an absent key raises `KeyError` and escapes as a 500
with no error code.

**Impact:** a 500 from `POST /checkin` most often means *you omitted a key*, not
that the server is broken. Send all seven, even when the value is `null`.

### D6 · Medium · Reference lookups return HTTP 200 on failure

The lookup and dump handlers catch their own database errors and answer **200**
with `{"error": "…"}`. A 200 is therefore not proof of success.

**Impact:** your client must inspect the body, not the status code. The Postman
tests and `check_all_reads.ps1` both assert on the body for this reason.

### D7 · Medium · The main guest can leave without a successor

If the main guest is checked out through `POST /guestcheckout` with
`NewMainGuestUID: null`, this build does **not** reject the request. It checks
them out and leaves the stay with no main guest, which breaks later
`guestversion` writes.

**Impact:** always send a successor when the departing guest is the main guest.
Guard this in your client.

### D8 · Medium · `ArabicName` is mandatory, then discarded

The shared validator rejects a missing or empty `ArabicName` on `POST` and
`PUT /checkin` (the Arabic-only check returns false for an empty string), and it
must contain Arabic characters and spaces only. The value is then **never
stored** — the API transliterates `FirstName`/`LastName` through
`GOOGLE_TRANSLATOR_URL` instead. The validator does not run on `GuestInfo`, so
`POST /guest` accepts a payload without it.

**Impact:** you must supply a valid Arabic string on the `Guests[]` endpoints
even though it has no effect on what is saved.

### D9 · Medium · `uid` means two different things

`POST /checkin` returns **`checkinguest`** ids in `guests[].uid`. `POST /guest`
and `GET /guest` return **`guest`** ids. `POST /guestattachment`,
`POST /guestcheckout` and `NewMainGuestUID` all want the *guest* id.

**Impact:** using the id from `POST /checkin` will address the wrong record with
no error. **Always take ids from `GET /guest`.**

### D10 · Low · `IsHouseUse` defaults to `true` when omitted

The guard reads `data.get('IsHouseUse', True)`, so omitting the key makes a
normal cash check-in fail with `40035 Check-in with house use flag does not
require payment method`. Always send the key explicitly.

### D11 · Low · The response `timestamp` is computed at import time

It is the same on every response until the process restarts. Do not use it to
order events; use your own `CorrelationUID` and the row timestamps.

### D12 · Low · Bad data in `cardtype`

Visa Electron's `DtcmCode` is the string `"0"`. Almost certainly a data bug —
avoid it in tests.

### D13 · Low · Unreachable code and codes

`ClientUID` is never validated, so error `40001` cannot be raised despite being
in the code table. `AddEscortAction` exists in the overlap helpers but no
endpoint ever passes it, and there is no `CheckinActionName` field to send.

### D14 · Low · Paths differ from the specification document

The 1.ID specification writes paths as `api/checkin/`. This build serves them
**without** the `api/` prefix. `GET /routes` is authoritative.

### D15 · High · The guest field validator never runs on `POST` / `PUT /guest`

Both handlers call the shared validator over the wrong key — they iterate
`data.get("Guests", [])`, but the payload carries `GuestInfo`, an object under a
different key. The loop body never executes.

**Impact:** a guest added *after* check-in skips **every** field-format check —
name characters, Arabic name, email shape, mobile digits, document-number
characters, birth place. The identical guest sent inside `Guests[]` on
`POST /checkin` is validated normally.

Validate these fields in your client. Do not read "the API accepted it" as "the
data is well-formed" on the add-escort path — it is written as sent.

---

## The integration contract

### Endpoint catalogue

| Group | Routes |
|---|---|
| Check-in | `GET POST PUT /checkin`, `POST /checkin/AddBackdatedCheckin`, `GET /checkintable` |
| Guest | `GET POST PUT /guest`, `GET /guesttable` |
| Documents | `GET POST /guestattachment`, `GET /guestdocumentimage` |
| Departure | `GET POST PUT /checkout`, `GET POST /guestcheckout`, `GET POST /checkincancellation` |
| Movement | `GET POST /roomchange`, `GET /mainguestchange` |
| Lookups | `/country /emirate /room /documenttype /visitpurpose /relationship /paymenttype /cardtype /checkintype /checkouttype /escorttype /accessibilitytype /cancellationreason /dtcmaction` |
| Audit | `/checkinguest /guestversion /payment /log` |
| Monitoring | `/ /ping /version /health /metrics`, `POST /metrics/reset`, `/routes /status /favicon.ico` |

### Five things that will surprise you

1. **`GET /checkin` and `GET /guest` take a JSON body.** Postman and `curl.exe`
   handle it; PowerShell 5.1's `Invoke-RestMethod` refuses outright.
2. **`PUT /checkin` uses `UID`**; every other endpoint uses `CheckinUID`. And
   `POST /roomchange` uses `EffectiveDate`, not `EffectiveDateTime`.
3. **`POST /checkout`, `POST /roomchange` and `POST /checkincancellation` return
   a bare `{"CheckinUID": n}`** on success — not the envelope. Only their errors
   use the envelope.
4. **Guest identity is `DocumentNumber`.** Posting a guest whose document number
   already exists **updates** that guest rather than creating one. Reuse it on
   the *same* stay and you get 50016.
5. **Overlap failures carry no error code** — `errorMessages` is a free-text
   sentence naming the conflicting check-in id and times.

### The guest object

The same shape appears in `Guests[]` (check-in endpoints) and `GuestInfo`
(guest endpoints). Full field table with rules in
[PAYLOADS.md](PAYLOADS.md#the-guest-object). The rules that are easy to trip
over:

| Field | Rule |
|---|---|
| `FirstName`, `LastName` | English letters and spaces only, no double spaces |
| `ArabicName` | Arabic characters and spaces only; required on `Guests[]`, see [D8](#d8--medium--arabicname-is-mandatory-then-discarded) |
| `BirthPlace` | letters only, **no spaces** — `Abu Dhabi` fails, `AbuDhabi` passes |
| `Mobile` | digits only, no `+`, no spaces |
| `DocumentNumber` | alphanumeric, no spaces — this is the guest's identity |
| `EmirateCode` | required when `IssueCountryCode` is `AE` |
| `RelationshipCode` | required for non-main guests, `null` for the main guest |
| `IssueDate` / `ExpiryDate` | issue not in the future and strictly before expiry; expiry not in the past |
| `OtherAccessibilityType` | required when `AccessibilityTypes` contains `other` |
| `Attachments` | at least one, each under **200 KB** decoded |

Attachments are base64 JPEG. `Name` becomes the filename on disk; `POST /checkin`
and `POST /guest` do **not** rename collisions, so a guest's second document
needs a distinct name. `POST /guestattachment` does auto-suffix
(`Image_2_1.jpg`). Images are resized to 1080×720 at quality 85.

---

## Escorts and additional guests

"Escort" is this API's word for anyone on a stay who is not the main guest —
family, friends, business associates. They live in `checkinguest` alongside the
main guest, distinguished by `IsMainGuest = false`, a `RelationshipName`, and an
`EscortTypeId`.

### Two ways to add one

**1 — At check-in, as extra entries in `Guests[]`.**
[`03_checkin_post_with_escorts.json`](payloads/03_checkin_post_with_escorts.json)
sends a main guest and two escorts in one `POST /checkin`. Each escort is an
ordinary guest object with `IsMainGuest: false` and a `RelationshipCode`.

**2 — Afterwards, through `POST /guest`.**
[`09_guest_post_add_escort.json`](payloads/09_guest_post_add_escort.json). This
is the *add escort* button in the desktop client. One guest per request —
`GuestInfo` is an object, not an array.

### Rules

| Rule | Code |
|---|---|
| `RelationshipCode` required and must exist in `relationship.DtcmCode` | 50009 |
| Exactly one `IsMainGuest: true` per `POST /checkin` | 40006 / 40028 |
| At least one guest whose `CheckinDateTime` equals the transaction's | 40033 |
| An escort may check in later than the transaction, never earlier | 50014 |
| …and never in the future | 50015 |
| That document number is not already on this stay (`POST /guest`) | 50016 |
| At least one attachment, each under 200 KB | 60001 / 60004 |

Valid `RelationshipCode` values: `businessAssociate`, `familyHelper`,
`familyMember`, `friend`, `visitor`.

### Editing and removing

`PUT /guest` edits an escort, matching on `DocumentNumber`. Its 50016 check is
commented out in the source, which is what makes it an edit rather than an add;
it additionally rejects a cancelled stay (40010).

`POST /guestcheckout` removes one guest from the stay while the stay continues.

### Main-guest handover

When the main guest leaves but the stay continues, set `NewMainGuestUID` to the
**guest id** of an escort who is staying —
[`13_guestcheckout_post_mainguest_handover.json`](payloads/13_guestcheckout_post_mainguest_handover.json).

The API then, in order: writes a `MainGuestChange` row and a log entry; clears
`IsMainGuest` on the outgoing guest and copies the incoming guest's relationship
onto them; sets `IsMainGuest` on the successor and clears their relationship;
snapshots a new `guestversion`; and only then checks the departing guest out.

This is the **only** way to change the main guest — there is no dedicated
endpoint. `GET /mainguestchange` is a read-only dump. See
[D7](#d7--medium--the-main-guest-can-leave-without-a-successor) for what happens
if you omit the successor.

### Escorts constrain everything downstream

Room change and check-out are both validated against the **most recently added**
`checkinguest` row — the newest escort:

- `POST /roomchange` must be after that escort's check-in *and* check-out
- `POST /checkout` must likewise be after both

So order your timestamps strictly: **check-in < escort check-in < room change <
escort check-out < check-out**. `run_write_flow.ps1` does exactly this, and the
supplied payloads are already ordered.

### What you cannot do

Choose the escort type — see [D4](#d4--medium--childescort-cannot-be-recorded).

---

## Error codes

| Range | Concerns | Codes seen in this build |
|---|---|---|
| **400xx** | the check-in transaction | 40002 room missing · 40003 room inactive · 40004 date in future · 40005 no guests · 40006 no main guest · 40007 bad payment method · 40008 bad card number · 40009 no check-in · 40010 already cancelled · 40011 already checked out · 40014 bad check-out time · 40023 check-out time on a PUT · 40025 bad cancellation time · 40028 more than one main guest · 40031 stay still active · 40032 / 40034 check-out before a guest's dates · 40033 no guest at the transaction time · 40035–40038 house-use conflicts · 40039 house-use late check-out · 40050 room occupied |
| **500xx** | a guest | 50001 first name / guest code · 50002 last name · 50005 nationality · 50006 residence country · 50007 birth date · 50008 visit purpose · 50009 relationship · 50010 guest not specified · 50011 mobile · 50013 birth place · 50014 guest check-in before the stay's · 50015 guest check-in in future · 50016 guest already on this stay · 50017 guest already checked out |
| **600xx** | an attachment | 60001 none supplied · 60004 over 200 KB · 60006 document number · 60007 document type · 60008 issue date in future / missing "other" accessibility text · 60009 issue after expiry · 60010 issue country · 60011 expiry missing or expired · 60012 emirate required for `AE` · 60013 issue date missing |
| **800xx** | a room change | 80001 new room missing · 80003 new room occupied |

Full text in [API.md](API.md#error-codes). Three things your error handling must
allow for:

- **Overlap failures carry no number.** The spec defines eight codes for them
  (40015, 40016, 40019–40022, 50020, 80004); this build reports a free-text
  sentence naming the conflicting check-in id and times instead.
- **`40050 Checkin room is occupied` is not in the spec.** Handle it alongside
  `40003`.
- **22 spec codes are not implemented at all**, including `50018` (main guest
  leaving without a successor) and `50022` (duplicate guest code). The full list
  is in [SPEC_CONFORMANCE.md](SPEC_CONFORMANCE.md#error-codes).

---

## Reference database contents

Read from the live instance on 2026-08-04. **The codes are stable; the row ids
are not** — re-read them after pointing at your own database.

| Set | Values |
|---|---|
| `PaymentMethodCode` | `cash`, `creditcard` |
| `CreditCardTypeCode` | `visa` (13–16 digits), `mastercard` (16), `amex` (15), `diners` (14–16) |
| `GenderCode` | `male`, `female` |
| `RelationshipCode` | `businessAssociate`, `familyHelper`, `familyMember`, `friend`, `visitor` |
| `VisitPurposeCode` | `tourism`, `visitor`, `business`, `medical`, `religious`, `Athlete`, `crewmember`, `hotelstaff`, `medicalstaff`, `otherstaff`, `patients` |
| `EmirateCode` | `dubai`, `abudhabi`, `sharjah`, `fujirah`, `rak`, `ajman`, `ummalquwain`, `alain`, `westernareas` |
| `AccessibilityTypes[].Code` | `hearing`, `visual`, `mobility`, `other` |
| `CancellationReasonCode` | `Unhappy`, `UserError` |
| `AttachmentTypeCode` | 21 values — `passport`, `emiratesid`, `uaedrivinglicence`, … full list from `GET /documenttype` |
| Country codes | ISO **two-letter**, 252 rows — matched on `TwoCode`, not `DtcmCode` |

> `Athlete` is capitalised in the table. Send it exactly as shown.

Everything except countries is matched on `DtcmCode`. Full tables in
[PAYLOADS.md](PAYLOADS.md#valid-code-values).

Refresh the state of a database before a test run:

```sql
SELECT Id, RoomNumber, IsChecked, CheckinId FROM [itsthe1.id].[room] WHERE IsChecked = 1;
SELECT Id, RoomNumber, CheckinDate, IsActive FROM [itsthe1.id].[checkin] ORDER BY Id;
SELECT Id, CheckinId, GuestId, IsMainGuest, EscortTypeId, CheckoutDate FROM [itsthe1.id].[checkinguest] ORDER BY Id;
```

Use a room with `IsChecked = 0` for every test check-in, so real occupied rooms
are never disturbed.

---

## Security

**The API has no authentication.** Anything that can reach the port can create
check-ins and read guest data. It is designed for a closed hotel LAN.

- Keep `HOST` as `127.0.0.1` when the client runs on the same machine.
- If the client is remote, restrict port 5030 with a Windows Firewall rule to
  specific client addresses.
- Never expose this port to the internet.
- The database password is plain text in `config.json` — protect that file with
  NTFS permissions. The API masks it (`sa:***`) everywhere it reports its own
  configuration.

Guest documents are personal data: names, passport and Emirates ID numbers, and
document photographs, stored both under `BaseDirectoryPath` and as blobs in SQL
Server. Treat any database copy or storage folder shared for testing as
regulated data, and use synthetic guests — as every payload in this collection
does.

---

## What we need from you

1. **Confirm your environment**: SQL Server version, whether ODBC Driver 17 is
   installed, and the `[database].[schema]` prefix you will use.
2. **Tell us whether [D4](#d4--medium--childescort-cannot-be-recorded) blocks
   you** — if you need to record child escorts, we need to add the field.
3. **Report any endpoint whose response shape differs** from what this document
   describes. The write payloads are derived from source, not from observed
   responses ([see the verification table](#verification-status--what-we-actually-ran)),
   so this is where errors are most likely.
4. **Send us the `CorrelationUID`** with any failure report. It is echoed back
   unchanged and is the fastest way for us to find the request in `logs/api.log`.

Logs live in `logs/api.log`, rotating at 5 MB with 5 kept. Set `LOG_LEVEL` to
`DEBUG` in `config.json` and restart for full request bodies.
