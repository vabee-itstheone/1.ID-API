# API Reference

Base URL: `http://<host>:5030`

All requests and responses are JSON.

```
Content-Type: application/json
```

There is no authentication - see the security note in [../README.md](../README.md).

> **Path note.** The 1.ID specification document writes the paths as
> `api/checkin/`. This implementation serves them **without** the `api/` prefix -
> `POST /checkin`. `GET /routes` on a running instance always returns the
> authoritative list.

---

## Contents

- [Common envelope](#common-envelope)
- [Check-in](#check-in)
- [Check-out](#check-out)
- [Check-in cancellation](#check-in-cancellation)
- [Guest](#guest)
- [Guest check-out](#guest-check-out)
- [Guest attachment](#guest-attachment)
- [Room change](#room-change)
- [Reference lookups](#reference-lookups)
- [Staying up to date](#staying-up-to-date)
- [Monitoring](#monitoring)
- [Error codes](#error-codes)

---

## Common envelope

Every business request carries these fields alongside its own payload:

| Field | Type | Notes |
|---|---|---|
| `MessageType` | string | e.g. `CheckinRequest`, `CheckoutRequest` |
| `ClientUID` | string | The hotel's DTCM registration ID |
| `MessageUID` | string | Send `null`; the API generates and returns one |
| `CorrelationUID` | string | Your ID; echoed back unchanged so you can pair request and response |
| `Timestamp` | DateTime | ISO 8601 |

Every business response carries:

```json
{
  "hasErrors": false,
  "errorMessages": {},
  "messageType": "CheckinResponse",
  "clientUID": "Establishment101",
  "messageUID": "7230ad75-8a9f-45c0-a000-ddb587c66345",
  "correlationUID": "f50a8b4d",
  "timestamp": "2025-02-17T11:40:01.125047+05:30"
}
```

On a validation failure the status is **400**, `hasErrors` is `true`, and
`errorMessages.general` holds a numbered code such as
`40002 Checkin room does not exist`.

Unhandled server faults return **500** with the same shape:

```json
{
  "hasErrors": true,
  "errorMessages": { "general": "Internal server error" },
  "detail": "…",
  "status": 500,
  "path": "/checkin",
  "method": "POST"
}
```

Unknown URLs return **404** in the same JSON shape rather than an HTML page.

---

## Check-in

### `GET /checkin`

Fetch one check-in. The identifier is sent in the **request body**, not the query
string.

```json
{
  "CheckinUID": "5",
  "MessageType": "CheckinStatusRequest",
  "ClientUID": "450653bb",
  "MessageUID": null,
  "CorrelationUID": "15ca1074",
  "Timestamp": "2025-02-17T06:07:20.110012"
}
```

**200** - envelope plus `data`:

```json
{
  "data": {
    "Id": 6,
    "CheckinUID": null,
    "RoomNumber": "004",
    "CheckinDate": "2025-01-28T11:37:08",
    "IsActive": false,
    "ChargeExtra": false,
    "IsFeeUpdated": false,
    "TDFee": null,
    "AddedAt": "2025-01-28T11:38:03",
    "AddedFrom": "DESKTOP-SCN1CG5",
    "CheckinTypeId": 1,
    "PaymentId": 6,
    "ChildEscortCount": null,
    "AdultEscortCount": null
  }
}
```

**404** - check-in not found.

### `POST /checkin`

Create a check-in with all its guests and their documents.

```json
{
  "RoomNumber": "112",
  "IsEarlyCheckin": false,
  "CheckinDateTime": "2025-02-01T07:00:05",
  "PaymentMethodCode": "cash",
  "CreditCardNumber": null,
  "CreditCardTypeCode": null,
  "Comment": "NEEWQR88B5",
  "IsWaitingForRoom": false,
  "IsHouseUse": false,
  "MessageType": "CheckinRequest",
  "ClientUID": "Establishment101",
  "MessageUID": null,
  "CorrelationUID": "f50a8b4d",
  "Timestamp": "2025-02-01T07:00:05",
  "Guests": [
    {
      "UID": null,
      "GuestCode": "00001",
      "FirstName": "John",
      "LastName": "Smith",
      "ArabicName": "جون سميث",
      "GenderCode": "male",
      "Email": "john@example.com",
      "Mobile": "4440259578",
      "BirthDate": "1960-08-24T00:00:00",
      "BirthPlace": "TK",
      "NationalityCode": "TF",
      "ResidenceCountryCode": "SH",
      "ResidenceCountryPhone": "0479924628",
      "RelationshipCode": "",
      "VisitPurposeCode": "medical",
      "CheckinDateTime": "2025-02-01T07:00:05",
      "CheckoutDateTime": null,
      "IsMainGuest": true,
      "AttachmentTypeCode": "passport",
      "DocumentNumber": "2429315804",
      "IssueCountryCode": "SO",
      "IssueDate": "2018-10-22T00:00:00",
      "ExpiryDate": "2028-10-22T00:00:00",
      "EmirateCode": "dubai",
      "RequiresAccessibility": true,
      "AccessibilityTypes": [{ "Code": "other" }, { "Code": "visual" }],
      "OtherAccessibilityType": "other types",
      "Attachments": [
        {
          "Id": 0,
          "UID": null,
          "AttachmentCode": "1234",
          "Name": "Image_1.jpg",
          "Size": 5447,
          "ContentBase64Encoded": "/9j/4AAQSkZJRgABAQAAAQABAAD/…"
        }
      ]
    }
  ]
}
```

**Top-level fields**

| Property | Type | Required | Notes |
|---|---|---|---|
| `RoomNumber` | string | Yes | Must exist and be free |
| `IsEarlyCheckin` | bool | Yes | Adds one extra night of tourism dirham fee |
| `CheckinDateTime` | DateTime | Yes | Must not be in the future |
| `Guests` | list | Yes | At least one, exactly one with `IsMainGuest: true` |
| `PaymentMethodCode` | string | Yes | `cash` or `creditcard` |
| `CreditCardNumber` | string | Yes | 14-16 digits when `creditcard`, otherwise `null` |
| `CreditCardTypeCode` | string | Yes | Required when `creditcard`, otherwise `null` |
| `IsWaitingForRoom` | bool | Yes | Always `false` |
| `IsHouseUse` | bool | Yes | House-use stays incur no TD fee |
| `Comment` | string | No | Free text |

**Guest fields**

| Property | Type | Required | Notes |
|---|---|---|---|
| `UID` | string | Yes | `null` on create |
| `GuestCode` | string | Yes | Generated client-side, must be unique |
| `FirstName` / `LastName` | string | Yes | |
| `ArabicName` | string | Yes | |
| `GenderCode` | string | Yes | `male` or `female` |
| `Email` | string | No | |
| `Mobile` | string | Yes | |
| `BirthDate` | DateTime | Yes | |
| `BirthPlace` | string | Yes | |
| `NationalityCode` | string | Yes | CountryCode table |
| `ResidenceCountryCode` | string | Yes | CountryCode table |
| `RelationshipCode` | string | Yes | RelationshipCode table |
| `VisitPurposeCode` | string | Yes | VisitPurposeCode table |
| `CheckinDateTime` | DateTime | Yes | Not before the transaction check-in time |
| `IsMainGuest` | bool | Yes | |
| `AttachmentTypeCode` | string | Yes | AttachmentTypeCode table |
| `DocumentNumber` | string | Yes | |
| `IssueCountryCode` | string | Yes | CountryCode table |
| `IssueDate` / `ExpiryDate` | DateTime | Yes | Issue must precede expiry, and not be in the future |
| `EmirateCode` | string | Conditional | Required when the document is an Emirates ID |
| `Attachments` | list | Yes | See below |
| `RequiresAccessibility` | bool | No | |
| `AccessibilityTypes` | list | No | AccessibilityTypes table |
| `OtherAccessibilityType` | string | Conditional | Required when `AccessibilityTypes` contains `other` |

**Attachment fields**

| Property | Type | Required | Notes |
|---|---|---|---|
| `UID` | string | Yes | `null` on create |
| `AttachmentCode` | string | Yes | |
| `Name` | string | Yes | |
| `Size` | int | Yes | Must not exceed 200 KB |
| `ContentBase64Encoded` | string | Yes | Base64 image data |

**200**

```json
{
  "CheckinUID": 298,
  "clientUID": "Establishment102",
  "correlationUID": "f50a8b4d",
  "errorMessages": {},
  "hasErrors": false,
  "messageType": "CheckinResponse",
  "messageUID": "7230ad75-8a9f-45c0-a000-ddb587c66345",
  "requestMessageID": 260,
  "timestamp": "2025-02-17T11:40:01.125047+05:30",
  "guests": [
    {
      "uid": 166,
      "guestCode": "86868",
      "attachments": [
        { "uid": "edae49a4-0e1b-4277-97d0-528007154210", "attachmenttCode": "V1258434" }
      ]
    }
  ]
}
```

### `PUT /checkin`

Amend an existing check-in.

```json
{
  "UID": "271f23c0",
  "IsEarlyCheckin": false,
  "CheckinDateTime": "2016-12-27T15:03:19",
  "IsLateCheckout": null,
  "CheckoutDateTime": null,
  "Guests": [],
  "PaymentMethodCode": "cash",
  "CreditCardNumber": null,
  "CreditCardTypeCode": null,
  "Comment": "ZD38I5XHHJ",
  "IsWaitingForRoom": null,
  "RoomNumber": null,
  "MessageType": "CheckinUpdateRequest",
  "ClientUID": "b1c4761b",
  "MessageUID": null,
  "CorrelationUID": "e502d8da",
  "Timestamp": "2016-12-27T15:03:19.5370293+04:00"
}
```

### `POST /checkin/AddBackdatedCheckin`

Same payload as `POST /checkin`, for entering a stay that already began. Used
during data migration and back-office correction.

### `GET /checkintable`

Returns all check-in rows. Diagnostic helper, not part of the 1.ID
specification.

---

## Check-out

### `POST /checkout`

```json
{
  "CheckinUID": "284",
  "IsLateCheckout": false,
  "CheckoutDateTime": "2025-02-02T03:15:00",
  "Comment": "ZK074TX1BW",
  "MessageType": "CheckoutRequest",
  "ClientUID": "b1c4761b",
  "MessageUID": null,
  "CorrelationUID": "f4f4e950",
  "Timestamp": "2025-02-02T03:15:00"
}
```

**200** → `{ "CheckinUID": "78" }`

Errors: `40009`, `40010`, `40011`, `40014`, `40016`, `40021`, `40022`, `40034`, `40039`.

### `PUT /checkout`

Same body without `Comment`; adjusts an existing check-out.

Errors: `40009`, `40010`, `40012`, `40014`, `40016`, `40021`, `40022`, `40031`, `40032`.

### `GET /checkout`

Returns all check-out rows.

---

## Check-in cancellation

### `POST /checkincancellation`

```json
{
  "CheckinUID": "298",
  "CancellationDateTime": "2025-02-16T15:07:39",
  "CancellationReasonCode": "Unhappy",
  "Comment": "BKFG53T1VJ",
  "MessageType": "CheckinCancellationRequest",
  "ClientUID": "b1c4761b",
  "MessageUID": null,
  "CorrelationUID": "380b9f…",
  "Timestamp": "2025-02-16T15:07:39"
}
```

`CancellationReasonCode` comes from the CancellationReasonCode table
(`GET /cancellationreason`).

### `GET /checkincancellation`

Returns all cancellation rows.

---

## Guest

### `GET /guest`

Returns the guests of a check-in, each with their document metadata.

```json
{
  "clientUID": "25",
  "correlationUID": "15ca1074",
  "errorMessages": {},
  "hasErrors": false,
  "guests": [
    {
      "uid": 62,
      "guestCode": "hEz8rWLAYk6CUv1jhH7jYQ",
      "isMainGuest": true,
      "attachmentType": "UAE ID Card",
      "documentNumber": "132090627",
      "attachments": "[{\"Id\": 0, \"UID\": null, \"AttachmentCode\": \"_0x-y1FySkKBWTDHsV1Zcg\", \"Name\": \"Image_1.jpg\", \"Size\": 131171, \"ContentBase64Encoded\": null}]"
    }
  ]
}
```

Note that `attachments` arrives as a **JSON string**, not a nested array.

### `POST /guest`

Add a guest to an existing check-in.

| Parameter | Type |
|---|---|
| `CheckinUID` | string |
| `GuestInfo` | GuestInfo (same shape as a `Guests[]` entry in `POST /checkin`) |
| `Comment` | string |

### `PUT /guest`

Update a guest on an existing check-in. Same parameters as `POST /guest`.

Errors: `50001`, `50002`, `50005`-`50016`, `50022`, `40014`, `60001`, `60004`, `60006`-`60010`.

### `GET /guesttable`

Returns all guest rows. Diagnostic helper.

---

## Guest check-out

### `POST /guestcheckout`

Check one guest out of a room while the check-in stays open.

```json
{
  "CheckinUID": "284",
  "GuestUID": "61",
  "CheckoutDateTime": "2025-02-02T03:00:16",
  "NewMainGuestUID": null,
  "MessageType": "GuestCheckoutRequest",
  "ClientUID": "b1c4761b",
  "MessageUID": null,
  "CorrelationUID": "6012d808",
  "Timestamp": "2016-12-27T15:21:16.4326285+04:00"
}
```

`NewMainGuestUID` is required when the departing guest is the main guest - it
names the guest who takes over that role.

Errors: `40009`, `40010`, `40011`, `50016`, `50017`, `50018`, `50019`, `50020`.

---

## Guest attachment

### `POST /guestattachment`

Upload extra documents for a guest who is already checked in.

```json
{
  "CheckinUID": "27",
  "GuestUID": "96",
  "Attachments": [
    {
      "Id": 0,
      "UID": null,
      "AttachmentCode": "Doc001",
      "Name": "Image_1.jpg",
      "Size": 5447,
      "ContentBase64Encoded": "/9j/4AAQSkZJRgABAQAAAQABAAD/…"
    }
  ],
  "MessageType": "GuestAttachmentRequest",
  "ClientUID": "b1c4761b",
  "MessageUID": null,
  "CorrelationUID": "715b52d6",
  "Timestamp": "2016-12-27T15:22:25.6935099+04:00"
}
```

**200** - envelope plus the guest and the codes assigned to each attachment.

Errors: `40009`, `40010`, `40011`, `50016`, `50021`, `60001`, `60004`.

Images are resized server-side by `app/utilities/image_manipulator.py` and written
under `BaseDirectoryPath`.

---

## Room change

### `POST /roomchange`

```json
{
  "CheckinUID": "284",
  "NewRoomNumber": "023",
  "EffectiveDate": "2025-02-02T03:30:00",
  "Comment": "M6QX59LFR1",
  "MessageType": "RoomChangeRequest",
  "ClientUID": "b1c4761b",
  "MessageUID": null,
  "CorrelationUID": "1aa3e27b",
  "Timestamp": "2016-12-27T15:25:12.7357783+04:00"
}
```

**200** → `{ "CheckinUID": "296" }`

Errors: `40009`, `40010`, `40011`, `80001`, `80003`, `80004`.

---

## Reference lookups

Each is a plain `GET` returning the whole table as an array. The WPF client uses
them to fill dropdowns.

| Endpoint | Fields returned |
|---|---|
| `GET /country` | `Id`, `Name`, `ThreeCode`, `TwoCode`, `MobileCode`, `CidCode`, `CidCodeTwo` |
| `GET /emirate` | `Id`, `Name`, `DtcmCode` |
| `GET /room` | `Id`, `RoomNumber`, `BedCount`, `IsChecked`, `CheckinId`, `IsWaitingRoom`, `IsActive` |
| `GET /documenttype` | `Id`, `Type`, `DtcmCode` |
| `GET /visitpurpose` | `Id`, `Purpose`, `CidCode`, `DtcmCode`, `DctCode`, `PurposeType` |
| `GET /relationship` | `Id`, `Relation`, `DtcmCode` |
| `GET /paymenttype` | `Id`, `Type`, `DtcmCode` |
| `GET /cardtype` | `Id`, `Type`, `MinLength`, `MaxLength`, `DtcmCode` |
| `GET /checkintype` | `Id`, `Type` |
| `GET /checkouttype` | `Id`, `Type` |
| `GET /escorttype` | `Id`, `Type` |
| `GET /accessibilitytype` | `Id`, `EnglishName`, `ArabicName`, `DtcmCode` |
| `GET /cancellationreason` | `Id`, `Reason`, `DtcmCode` |
| `GET /dtcmaction` | `Id`, `Name` |
| `GET /payment` | `Id`, `CardNumber`, `PaidAmount`, `AddedAt`, `AddedFrom`, `PaymentTypeId`, `CardTypeId` |
| `GET /checkinguest` | Check-in ↔ guest links with dates and roles |
| `GET /guestversion` | Full historical snapshot of each guest record |
| `GET /guestdocumentimage` | `DocumentId`, `GuestId`, `DocumentUID`, `AttachmentCode`, `FileName`, `FileSizeKB`, `ImageData`, `UploadedAt` |
| `GET /mainguestchange` | Main-guest handover history |
| `GET /log` | `Id`, `AddedAt`, `RoomNumber`, `RequestType`, `DtcmStatus`, `CidStatus`, `CheckinUID`, `PayloadIdentifier`, `Error`, `CheckinGuestId`, `CheckinId` |

> **Important.** These endpoints swallow their own database errors and return
> **HTTP 200** with `{"error": "..."}` in the body. Always inspect the body, not
> just the status code. The `/status` dashboard flags these as failed responses -
> see [MONITORING.md](MONITORING.md).

---

## Staying up to date

**Read this before writing a refresh loop.** Getting it wrong is what made a
141 ms check-out take 77 seconds to appear on screen.

Every `GET` in the previous section returns a **whole table**. On a hotel a year
into service that is 99,722 rows and 27 MB for `GET /log` alone, and about
**109 MB** if a client refreshes by re-reading all of them. There is nothing
wrong with any single one of those calls - the mistake is using them as a
change-detection mechanism.

### The fast path

Poll `/changes`, then read only what it says moved.

```
GET /changes?since=<revision>&wait=25
```

| Field | Meaning |
|---|---|
| `revision` | Opaque token for the current state. Send it back as `?since=` next time |
| `changed` | `true`/`false`, or `null` when your `since` was missing or unrecognised - read in full once and start again from the returned `revision` |
| `changedTables` | Which of `checkin` `checkout` `checkinguest` `roomchange` `mainguestchange` `guest` `log` `room` moved |
| `maxIds` | Highest `Id` now in each table - hand these straight to `?since_id=` |
| `occupiedRooms` | Rooms currently checked in |

`wait=<seconds>` (max 55) holds the request open and answers the moment
something changes, so a check-out reaches the client in **about a quarter of a
second** instead of on the next poll tick. Without `wait` it answers
immediately, in about 2 ms - cheap enough to poll every second.

The revision is computed from the database, not from this process, so a
check-out written by another client - or straight to SQL Server by the desktop
application - moves it just the same, and restarting the API does not reset it.
It also covers updates, not just inserts: `room.IsChecked` flipping to 0 on
check-out is an `UPDATE`, and it is detected in about 15 ms.

### Incremental reads

Every table endpoint accepts these, and ignoring them is what costs 109 MB:

| Parameter | Effect |
|---|---|
| `since_id=<int>` | Rows whose `Id` is greater than this. On `/guestversion` the sequence column is `LogId` |
| `since=<iso8601>` | Rows with `AddedAt` at or after this. Only on tables that have `AddedAt`; a 400 says so |
| `limit=<int>` / `offset=<int>` | A page. An order is applied automatically |
| `order=asc\|desc` | By the sequence column |

Plus per-table filters: `checkin_id` on `/checkout`, `/checkinguest`,
`/guestcheckout`, `/roomchange`, `/mainguestchange`, `/log` and
`/guestversion`; `guest_id` on `/guestattachment`, `/checkinguest` and
`/guestversion`; `active` and `room_number` on `/checkintable`; `occupied`,
`active` and `room_number` on `/room`; `room_number` and `request_type` on
`/log`; `document_number` on `/guesttable`.

An unparsable value is a **400**, never a silently ignored parameter - a client
that believes it is reading incrementally and is really reading the whole table
has no way to notice on its own.

### What a check-out refresh should look like

```
GET /changes?since=<last revision>&wait=25     ->  wakes ~250 ms after the commit
GET /room                                      ->  59 rows, 6 KB, 3 ms
GET /checkout?since_id=<maxIds.checkout>       ->  the one new row
GET /checkintable?since_id=<maxIds.checkin>
GET /checkinguest?since_id=<maxIds.checkinguest>
```

Measured against a live 40,000-guest database: **27 ms and ~2 KB**, versus
8.3 seconds and 102 MB for the full sweep it replaces.

### If you cannot change the client yet

Two savings apply on their own, with no code change at all:

- **gzip.** Send `Accept-Encoding: gzip` - most HTTP stacks already do - and
  responses shrink 5-9x. The full sweep drops from 103 MB to 17 MB.
- **`ETag` / `If-None-Match`.** Every response over 4 KB carries an `ETag`.
  Send it back and an unchanged table answers **304** with an empty body, which
  saves the client its JSON parse as well as the transfer. After a check-out,
  `guest`, `guestattachment`, `payment` and `roomchange` have not changed. The
  server still reads the table to answer, so `/changes` is better where you can
  use it.

---

## Monitoring

| Endpoint | Purpose |
|---|---|
| `GET /status` | Live HTML dashboard |
| `GET /health` | Readiness check; 200 healthy, 503 unhealthy. `?deep=false` skips I/O probes |
| `GET /ping` | Liveness; returns `pong` |
| `GET /version` | Version, PID, start time |
| `GET /metrics` | Counters and recent traffic |
| `POST /metrics/reset` | Zero the counters |
| `GET /routes` | Every URL this build serves |
| `GET /` | Summary with links |

Full detail in [MONITORING.md](MONITORING.md).

---

## Error codes

Returned in `errorMessages.general` with HTTP 400.

### Check-in (4xxxx)

| Code | Message |
|---|---|
| 40001 | Checkin wrong Establishment UID |
| 40002 | Checkin room does not exist |
| 40003 | Checkin room is not available |
| 40004 | Checkin date must not be in future |
| 40005 | Checkin no guests specified |
| 40006 | Checkin no main guest specified |
| 40007 | Checkin invalid payment method |
| 40008 | Checkin invalid credit card number |
| 40009 | Checkin is not specified |
| 40010 | Checkin is already cancelled |
| 40011 | Checkin is already checked out |
| 40012 | Check-out can't be modified, a payment order exists against it |
| 40014 | Checkout Date Time is invalid |
| 40015 | Checkin Date Time overlaps with another checkin on the same room |
| 40016 | Checkout Date Time overlaps with another check-in on the same room |
| 40021 | Checkout Date Time overlaps with a Room Change Action on the same check-in |
| 40022 | Checkout Date Time overlaps with a Main Guest Change Action on the same check-in |
| 40024 | Checkin not allowed, payment order already generated for that month and year |
| 40026 | Checkin date should be after actual establishment opening date |
| 40027 | Waiting-for-room check-in reached the upper limit allowed |
| 40028 | You must have only one main guest |
| 40030 | Check-in can't be added when actual opening date and first receive guest date are empty in the establishment profile |
| 40031 | Check-in is already active |
| 40032 | Check-out date and time should be equal to or after any guest check-out |
| 40033 | Check-in must have at least one guest whose check-in date and time equals the transaction's |
| 40034 | Check-out date and time should be equal to or after any guest check-in |
| 40035 | House-use check-in does not require a payment method |
| 40036 | House-use check-in does not require a credit card number |
| 40037 | House-use check-in does not require early check-in |
| 40038 | House-use check-in not allowed with waiting for room |
| 40039 | House-use check-out does not require late check-out |
| 40050 | Checkin room is occupied |

### Guest (5xxxx)

| Code | Message |
|---|---|
| 50001 | Guest invalid first name |
| 50002 | Guest invalid last name |
| 50005 | Guest invalid nationality |
| 50006 | Guest invalid residence country |
| 50007 | Guest invalid birth date |
| 50008 | Guest invalid visit purpose |
| 50009 | Guest invalid relationship |
| 50010 | Guest is not specified |
| 50011 | Guest mobile number is invalid |
| 50012 | Arabic Name is required |
| 50013 | Birth Place is not specified |
| 50014 | Guest check-in date is before check-in date |
| 50015 | Guest check-in date time should not be in the future |
| 50016 | Guest already exists |
| 50017 | Guest is not in the room, already checked out |
| 50018 | Guest is a main guest |
| 50019 | Guest is a visitor |
| 50020 | Change Main Guest action must be after check-in and before check-out |
| 50021 | Guest does not exist |
| 50022 | Guest Code already exists |

### Attachment (6xxxx)

| Code | Message |
|---|---|
| 60001 | Attachment is not specified |
| 60004 | Attachment should not exceed 200 KB in size |
| 60006 | Attachment document number is invalid |
| 60007 | Attachment Type is not specified |
| 60008 | Attachment issue date can't be in the future |
| 60009 | Attachment issue date should be before expiry date |
| 60010 | Attachment issue country is not specified |
| 60011 | Attachment expiry date is not specified |
| 60012 | Attachment issue emirate is not specified |
| 60013 | Attachment issue date is not specified |

### Room change (8xxxx)

| Code | Message |
|---|---|
| 80001 | The new room doesn't exist |
| 80003 | The new room is occupied |
| 80004 | Change room action must be after check-in and before check-out |

---

## Reference tables

The code values (`PaymentMethodCode`, `CountryCode`, `VisitPurposeCode`, …) are
maintained in the shared reference sheet named in the 1.ID API Specification
Document, and are also served live by the [reference lookup
endpoints](#reference-lookups) above.
