# Specification conformance — full report

Build **v1.0.0** against the **1.ID API Specification Document** (42 pages,
sections 1–7), and against the payload collection in [`payloads/`](payloads/).

Compiled 2026-08-05 by reading all seven specification sections against every
route handler. Line references point at the source in this repository.

---

## Verdict

**The payloads in this collection are not copies of the specification's samples,
and they should not be.** They follow the specification's *field contract* — same
field names, same types, same required/optional split — but carry values this
build accepts, because **the specification's own sample payloads are rejected by
this build.**

| Measure | Result |
|---|---|
| Spec endpoints implemented | **12 of 12** |
| Spec endpoints with a ready payload here | **12 of 12** |
| Spec error codes implemented | **49 of 71** |
| Spec error codes missing | **22** |
| Codes this build raises that the spec does not define | **1** (`40050`) |
| Codes carrying more than one meaning | **6** |
| Validation rules that differ in substance | **3** |
| Spec sample payloads that would be accepted as printed | **7 of 12** |

The endpoint surface is faithful. The **error contract is not** — that is where
an integration will break.

---

## How to read this report

Parts 1–7 follow the specification's own numbering. Each endpoint gets the same
five blocks:

| Block | What it tells you |
|---|---|
| **Contract** | spec § and URL, build URL, method, payload file |
| **Validation order** | every check this build runs, in source order, with line refs. The **first** failure returns; later checks never run |
| **Error codes** | spec's list for that endpoint vs what the build raises |
| **Payload** | how our payload differs from the spec's sample, and why |
| **Verdict** | one line |

Part 8 covers routes with no spec counterpart. The appendices carry the
cross-endpoint views: the code index, the guest object, and the deviation
register.

---

## Contents

- [Summary: endpoint coverage](#summary-endpoint-coverage)
- [Summary: the spec's samples on this build](#summary-the-specs-samples-on-this-build)
- [Part 1 — § 1 Check-in](#part-1--1-check-in)
- [Part 2 — § 2 Check-out](#part-2--2-check-out)
- [Part 3 — § 3 Check-in cancellation](#part-3--3-check-in-cancellation)
- [Part 4 — § 4 Guest](#part-4--4-guest)
- [Part 5 — § 5 Guest check-out](#part-5--5-guest-check-out)
- [Part 6 — § 6 Guest attachment](#part-6--6-guest-attachment)
- [Part 7 — § 7 Room change](#part-7--7-room-change)
- [Part 8 — routes with no spec counterpart](#part-8--routes-with-no-spec-counterpart)
- [Appendix A — error code index](#appendix-a--error-code-index)
- [Appendix B — the guest object](#appendix-b--the-guest-object)
- [Appendix C — deviation register](#appendix-c--deviation-register)

---

## Summary: endpoint coverage

| Spec § | Spec URL | Build URL | Payload | Conformance |
|---|---|---|---|---|
| 1.1 | `GET api/checkin/` | `GET /checkin` | `01` | ✅ full — response matches field for field |
| 1.2 | `POST api/checkin/` | `POST /checkin` | `02` `03` `04` `05` | ⚠️ 10 codes missing, 1 added |
| 1.3 | `PUT api/checkin/` | `PUT /checkin` | `06` | ⚠️ 10 codes missing |
| 2.1 | `POST api/checkout/` | `POST /checkout` | `15` | ⚠️ 3 overlap codes unnumbered |
| 2.2 | `PUT api/checkout/` | `PUT /checkout` | `16` | ⚠️ 4 codes missing |
| 3.1 | `POST api/checkincancellation/` | `POST /checkincancellation` | `17` | ✅ full, plus an extra rule |
| 4.1 | `GET api/guest/` | `GET /guest` | `08` | ✅ full |
| 4.2 | `POST api/guest/` | `POST /guest` | `09` | ❌ **40010 not checked**; validator dead |
| 4.3 | `PUT api/guest/` | `PUT /guest` | `10` | ⚠️ 50016 disabled by design, 50022 missing |
| 5.1 | `POST api/guestcheckout/` | `POST /guestcheckout` | `12` `13` | ❌ **50018/50019/50020 missing** |
| 6.1 | `POST api/guestattachment/` | `POST /guestattachment` | `11` | ⚠️ 5 codes missing incl. 60005 |
| 7.1 | `POST api/roomchange/` | `POST /roomchange` | `14` | ⚠️ 80004 unnumbered |

**Every one of the twelve differs in one shared respect:** the spec writes paths
as `api/checkin/`; this build serves `/checkin`, with no `api/` prefix.
`GET /routes` is authoritative.

---

## Summary: the spec's samples on this build

Paste the specification's printed sample into this API and this is what happens.

| Spec § | Sample | Outcome |
|---|---|---|
| 1.1 | Checkin GET | ✅ accepted |
| 1.2 | Checkin POST | ❌ **rejected — 5 reasons** (see [1.2](#12--post-checkin)) |
| 1.3 | Checkin PUT | ⚠️ `"Guests":'Add Guest Details'` is a placeholder, not JSON |
| 2.1 | Checkout POST | ⚠️ unterminated string — `"Timestamp":"2025-02-02T03:15:00` is missing its closing quote |
| 2.2 | Checkout PUT | ⚠️ same unterminated string |
| 3.1 | Cancellation POST | ✅ accepted |
| 4.1 | Guest GET | ✅ accepted |
| 4.2 | Guest POST | ❌ **rejected — 3 reasons** (see [4.2](#42--post-guest)) |
| 4.3 | Guest PUT | ❌ **rejected — same 3** |
| 5.1 | GuestCheckout POST | ✅ accepted |
| 6.1 | GuestAttachment POST | ✅ accepted |
| 7.1 | RoomChange POST | ✅ accepted |

The five write endpoints that carry a full guest object are exactly the five that
fail. **Use the payloads in [`payloads/`](payloads/) instead.**

---

# Part 1 — § 1 Check-in

## 1.1 — `GET /checkin`

**Contract**

| | |
|---|---|
| Spec | § 1.1, `GET api/checkin/` |
| Build | `GET /checkin` — [checkin/routes.py:47](../app/checkin/routes.py#L47) |
| Payload | [`01_checkin_get.json`](payloads/01_checkin_get.json) |

The identifier travels in a **JSON body on a GET**. The spec specifies this and
the build implements it. Postman and `curl.exe` can send it; PowerShell 5.1's
`Invoke-RestMethod` cannot.

**Validation order** — none. Unknown `CheckinUID` → **404 `Check-in not found`**,
as the spec states.

**Response** — the `data` object carries all **14 fields** the spec prints in
§ 1.1.3, in the same names and types
([checkin/routes.py:70](../app/checkin/routes.py#L70)):

```
Id · CheckinUID · RoomNumber · CheckinDate · IsActive · ChargeExtra ·
IsFeeUpdated · TDFee · AddedAt · AddedFrom · CheckinTypeId · PaymentId ·
ChildEscortCount · AdultEscortCount
```

**Payload** — identical to the spec's sample but for the id and timestamp.

**Verdict:** ✅ **full conformance.** The only difference is the URL prefix.

---

## 1.2 — `POST /checkin`

**Contract**

| | |
|---|---|
| Spec | § 1.2, `POST api/checkin/` |
| Build | `POST /checkin` — [checkin/routes.py:98](../app/checkin/routes.py#L98) |
| Payloads | [`02` cash](payloads/02_checkin_post_cash.json) · [`03` **+ 2 escorts**](payloads/03_checkin_post_with_escorts.json) · [`04` card](payloads/04_checkin_post_creditcard.json) · [`05` house use](payloads/05_checkin_post_houseuse.json) |

**Validation order** — 41 numbered checks plus one unnumbered overlap check.
Transaction level first, then per guest, then per attachment. The first failure
returns 400; later checks never run.

| # | Line | Code | Check |
|---|---|---|---|
| 1 | [125](../app/checkin/routes.py#L125) | 40002 | room exists |
| 2 | [137](../app/checkin/routes.py#L137) | 40003 | room is active |
| 3 | [162](../app/checkin/routes.py#L162) | **40050** | room not already occupied |
| — | | *free text* | check-in does not overlap the room's previous stay |
| 4 | [180](../app/checkin/routes.py#L180) | 40004 | check-in not in the future |
| 5 | [192](../app/checkin/routes.py#L192) | 40005 | at least one guest |
| 6 | [205](../app/checkin/routes.py#L205) | 40006 | a main guest exists |
| 7 | [217](../app/checkin/routes.py#L217) | 40028 | exactly one main guest |
| 8 | [245](../app/checkin/routes.py#L245) | 50014 | no guest checks in before the transaction |
| 9 | [266](../app/checkin/routes.py#L266) | 40007 | payment method is `cash` or `creditcard` |
| 10 | [279](../app/checkin/routes.py#L279) | 40008 | card number present when `creditcard` |
| 11–14 | [291](../app/checkin/routes.py#L291)–[328](../app/checkin/routes.py#L328) | 40035–40038 | house use rejects payment method, card, early check-in, waiting-for-room |
| 15 | [345](../app/checkin/routes.py#L345) | 40033 | at least one guest at the transaction's exact time |
| 16 | [406](../app/checkin/routes.py#L406) | 50010 | guest object present |
| 17 | [419](../app/checkin/routes.py#L419) | **50001** | **guest code valid** — spec assigns this to *first name* |
| 18–19 | [432](../app/checkin/routes.py#L432), [445](../app/checkin/routes.py#L445) | 50001 / 50002 | first, last name |
| 20 | [459](../app/checkin/routes.py#L459) | 50011 | mobile is digits |
| 21–22 | [472](../app/checkin/routes.py#L472), [486](../app/checkin/routes.py#L486) | 50005 / 50006 | nationality, residence country |
| 23 | [501](../app/checkin/routes.py#L501) | 50009 | relationship — **skipped when `IsMainGuest` is true** |
| 24–25 | [517](../app/checkin/routes.py#L517), [527](../app/checkin/routes.py#L527) | 50007 | birth date present, not future |
| 26 | [540](../app/checkin/routes.py#L540) | 50013 | birth place, letters, no spaces |
| 27 | [553](../app/checkin/routes.py#L553) | 50008 | visit purpose |
| 28–29 | [570](../app/checkin/routes.py#L570), [588](../app/checkin/routes.py#L588) | 50014 / 50015 | guest check-in ≥ transaction's, not future |
| 30 | [600](../app/checkin/routes.py#L600) | 60001 | at least one attachment |
| 31 | [616](../app/checkin/routes.py#L616) | 60006 | document number alphanumeric |
| 32 | [630](../app/checkin/routes.py#L630) | 60007 | document type |
| 33–37 | [645](../app/checkin/routes.py#L645)–[697](../app/checkin/routes.py#L697) | 60013 · 60008 · 60011 · 60009 · **60011** | issue date present, not future; expiry present; issue before expiry; **not expired** |
| 38 | [713](../app/checkin/routes.py#L713) | 60010 | issue country |
| 39 | [727](../app/checkin/routes.py#L727) | 60012 | emirate — **gated on `IssueCountryCode == 'AE'`** |
| 40 | [745](../app/checkin/routes.py#L745) | 60004 | attachment under 200 KB |
| 41 | [764](../app/checkin/routes.py#L764) | **60008** | `OtherAccessibilityType` present when `other` selected |

**Error codes**

| Spec code | Status |
|---|---|
| 40002 40003 40004 40005 40006 40007 40008 40028 40033 40035 40036 40037 40038 50001 50002 50005 50006 50007 50008 50009 50010 50011 50013 50014 50015 60001 60004 60006 60007 60008 60009 60010 60011 60012 60013 | ✅ implemented |
| **40001** wrong Establishment UID | ❌ present but commented out ([routes.py:104](../app/checkin/routes.py#L104)); `ClientUID` never validated |
| **40015** check-in overlap | ❌ implemented as behaviour, reported as **free text** |
| **50012** Arabic Name is required | ❌ enforced, but as a field-keyed message, not this code |
| **50022** Guest Code already exists | ❌ not implemented — duplicates accepted |
| **40024 40026 40027 40030** | ❌ not implemented (payment-order and establishment-profile concepts absent) |
| **40009 40014** | n/a on create |
| — | **40050** raised here, not in the spec |

**Payload** — the spec's § 1.2 sample is rejected five times over:

| Spec sample | Rejected | Code |
|---|---|---|
| `"FirstName":"2HELQSXB"` | digits in a name | 50001 |
| `"LastName":"3S8E4T8O"` | digits in a name | 50002 |
| `"ArabicName":"JIA1ULMC"` | not Arabic characters | field error |
| `"IssueDate"` = `"ExpiryDate"` = `2018-10-22` | issue must be strictly before expiry | 60009 |
| the same `ExpiryDate` | expiry in the past | 60011 |

Two spec quirks that turn out harmless: the sample writes `attachmenttCode`
where page 9's field table says `AttachmentCode` — **the build accepts both**
on every write path; and `"RelationshipCode":""` on the main guest is fine,
because check 23 is skipped for main guests.

Our payloads add **`PaidAmount`**, which the spec never documents. The build
reads it — `data.get('PaidAmount', 0)`
([routes.py:783](../app/checkin/routes.py#L783)) — and stores it on the payment
row. Omit it and it defaults to `0`.

**Response** — matches § 1.2.3, with one difference: attachment `uid` is an
**integer**, where the spec prints a GUID string. `guests[].uid` here is the
**`checkinguest`** id, not the guest id.

**Verdict:** ⚠️ **field contract conforms; error contract does not.** Ten spec
codes missing, one added, one reused for a different meaning.

---

## 1.3 — `PUT /checkin`

**Contract**

| | |
|---|---|
| Spec | § 1.3, `PUT api/checkin/` |
| Build | `PUT /checkin` — [checkin/routes.py:1220](../app/checkin/routes.py#L1220) |
| Payload | [`06_checkin_put.json`](payloads/06_checkin_put.json) |

The identifier is **`UID`**, not `CheckinUID`. The spec says so; this is the only
endpoint that differs, and it is the spec's design, not a build quirk.

**Validation order** — 34 checks, the same guest and attachment blocks as § 1.2,
preceded by:

| # | Line | Code | Check |
|---|---|---|---|
| 1 | [1249](../app/checkin/routes.py#L1249) | 40004 | check-in not in the future |
| 2–3 | [1263](../app/checkin/routes.py#L1263), [1275](../app/checkin/routes.py#L1275) | 40002 / 40003 | room exists, is active |
| 4 | [1332](../app/checkin/routes.py#L1332) | 40008 | card number |
| 5 | [1345](../app/checkin/routes.py#L1345) | 40011 | stay not already checked out |
| 6–7 | [1358](../app/checkin/routes.py#L1358), [1370](../app/checkin/routes.py#L1370) | 40006 / 40028 | exactly one main guest |
| 8 | [1399](../app/checkin/routes.py#L1399) | 50014 | guest check-in ≥ the stay's |
| 9 | [1412](../app/checkin/routes.py#L1412) | 40023 | **no `CheckoutDateTime` on an update** |

**Error codes**

| Spec code | Status |
|---|---|
| 40002 40003 40004 40006 40008 40011 40014 40023 40028 50001 50002 50005–50011 50013 50014 50015 60001 60004 60006–60013 | ✅ implemented |
| **40009** checkin not specified | ❌ not checked here |
| **40012** payment order generated | ❌ not implemented |
| **40015 40016 40019 40020 40021 40022** | ❌ all six overlap codes → **free text** |
| **40026** | ❌ not implemented |
| **50012** | ❌ field-keyed message instead |

**Payload** — the spec's sample prints `"Guests":'Add Guest Details'`, a
placeholder in single quotes; it is not valid JSON and cannot be sent. Ours
carries the full guest array the spec's field table requires. The spec's
`"RoomNumber":null` and `"IsWaitingForRoom":null` are legal; ours send real
values.

> **Known defect, not a spec deviation.** This handler finds the row to update
> via the guest's newest `checkinguest` row **across every check-in**
> ([routes.py:2134](../app/checkin/routes.py#L2134)), so a repeat visitor on a
> newer stay has the wrong row edited. Handover report D3.

**Verdict:** ⚠️ **conforms in shape; six overlap codes and 40009/40012 missing.**

---

# Part 2 — § 2 Check-out

## 2.1 — `POST /checkout`

**Contract**

| | |
|---|---|
| Spec | § 2.1, `POST api/checkout/` |
| Build | `POST /checkout` — [checkout/routes.py:34](../app/checkout/routes.py#L34) |
| Payload | [`15_checkout_post.json`](payloads/15_checkout_post.json) |

**Validation order**

| # | Line | Code | Check |
|---|---|---|---|
| 1 | [48](../app/checkout/routes.py#L48) | 40014 | `CheckoutDateTime` present |
| 2–3 | [70](../app/checkout/routes.py#L70), [94](../app/checkout/routes.py#L94) | 40034 | at or after every guest check-in, and every guest check-out |
| — | | *free text* | after the newest escort's check-in and check-out; after any room change; after any main-guest change |
| 4 | [112](../app/checkout/routes.py#L112) | 40009 | check-in exists |
| 5 | [135](../app/checkout/routes.py#L135) | 40010 | not cancelled |
| 6 | [148](../app/checkout/routes.py#L148) | 40011 | not already checked out |
| 7 | [163](../app/checkout/routes.py#L163) | 40014 | date parses |
| 8 | [180](../app/checkout/routes.py#L180) | 40004 | not in the future |
| 9 | [192](../app/checkout/routes.py#L192) | 40039 | house use rejects late check-out |

**Error codes** — 40009 40010 40011 40014 40034 40039 ✅ · **40016 40021 40022**
❌ free text · **40004** raised here, not in the spec's list for this endpoint.

**Payload** — the spec's sample is missing the closing quote on
`"Timestamp":"2025-02-02T03:15:00` and will not parse. Ours is otherwise
identical, field for field.

**Response** — bare `{"CheckinUID": 78}`, as specified. The build returns a
**number**; the spec prints a string.

**Verdict:** ⚠️ **full behavioural conformance; three overlap codes unnumbered.**

## 2.2 — `PUT /checkout`

**Contract** — § 2.2, `PUT /checkout` —
[checkout/routes.py:325](../app/checkout/routes.py#L325) ·
[`16_checkout_put.json`](payloads/16_checkout_put.json)

**Validation order**

| # | Line | Code | Check |
|---|---|---|---|
| 1 | [340](../app/checkout/routes.py#L340) | 40031 | stay must be **inactive** — the mirror of the POST |
| 2 | [352](../app/checkout/routes.py#L352) | 40014 | date present |
| 3 | [398](../app/checkout/routes.py#L398) | 40032 | at or after every guest check-out |
| 4–5 | [416](../app/checkout/routes.py#L416), [439](../app/checkout/routes.py#L439) | 40009 / 40010 | exists, not cancelled |
| 6–8 | [455](../app/checkout/routes.py#L455)–[484](../app/checkout/routes.py#L484) | 40014 · 40004 · 40039 | parses, not future, house-use rule |

**Error codes** — 40009 40010 40014 40031 40032 ✅ · **40012 40016 40021 40022**
❌ · **40004 40039** extra.

**Verdict:** ⚠️ **conforms; four codes missing.**

---

# Part 3 — § 3 Check-in cancellation

## 3.1 — `POST /checkincancellation`

**Contract** — § 3.1, `POST /checkincancellation` —
[checkincancellation/routes.py:35](../app/checkincancellation/routes.py#L35) ·
[`17_checkincancellation_post.json`](payloads/17_checkincancellation_post.json)

**Validation order**

| # | Line | Code | Check |
|---|---|---|---|
| 1 | [55](../app/checkincancellation/routes.py#L55) | 40011 | not already checked out |
| 2 | [69](../app/checkincancellation/routes.py#L69) | 40009 | check-in exists |
| 3 | [92](../app/checkincancellation/routes.py#L92) | 40010 | not already cancelled |
| 4 | [106](../app/checkincancellation/routes.py#L106) | 40025 | cancellation does not predate the check-in |
| 5 | [120](../app/checkincancellation/routes.py#L120) | 40004 | not in the future |
| — | | *free text* | **the cancellation must fall in the check-in's own month** |

**Error codes** — all four the spec lists (40009 40010 40011 40025) ✅ · **40004**
and the same-month rule are additions this build makes.

**Payload** — the spec's sample is accepted as printed. `CancellationReasonCode`
is `Unhappy` or `UserError`; the spec's `"Unhappy"` is valid.

**Verdict:** ✅ **full conformance, plus two extra rules.** The same-month
refusal is undocumented — code for it.

---

# Part 4 — § 4 Guest

## 4.1 — `GET /guest`

**Contract** — § 4.1, `GET /guest` —
[guest/routes.py:44](../app/guest/routes.py#L44) ·
[`08_guest_get.json`](payloads/08_guest_get.json)

Body on a GET, as specified. No validation; unknown id → 404.

**This is the only reliable source of guest ids** — see
[Appendix C, D9](#appendix-c--deviation-register).

**Verdict:** ✅ **full conformance.**

## 4.2 — `POST /guest`

**Contract**

| | |
|---|---|
| Spec | § 4.2, `POST api/guest/` |
| Build | `POST /guest` — [guest/routes.py:105](../app/guest/routes.py#L105) |
| Payload | [`09_guest_post_add_escort.json`](payloads/09_guest_post_add_escort.json) |

This is the **add-escort** path. One guest per request: `GuestInfo` is an object,
not an array.

**Validation order**

| # | Line | Code | Check |
|---|---|---|---|
| 1 | [123](../app/guest/routes.py#L123) | 40009 | check-in exists |
| 2 | [136](../app/guest/routes.py#L136) | 40011 | not already checked out |
| — | | | **no 40010 check — see below** |
| 3 | [172](../app/guest/routes.py#L172) | 50010 | `GuestInfo` present |
| 4–16 | [185](../app/guest/routes.py#L185)–[354](../app/guest/routes.py#L354) | 50001–50015 | the guest block, identical to § 1.2 |
| 17–28 | [366](../app/guest/routes.py#L366)–[530](../app/guest/routes.py#L530) | 60001–60013, 60004, 60008 | the attachment block, identical to § 1.2 |
| 29 | [544](../app/guest/routes.py#L544) | 50016 | that document number is not already on this stay |

29 checks in all.

**Two deviations, both material:**

**❌ `40010 Checkin is already cancelled` is never checked.** The spec lists it
for this endpoint; the handler goes straight from 40009 to 40011. **A guest can
be added to a cancelled stay.** `PUT /guest` does check it
([guest/routes.py:996](../app/guest/routes.py#L996)) — the POST simply omits it.

**❌ The shared field validator never runs here.** Both guest handlers call it
over the wrong key:

```python
guests1 = data.get("Guests", [])      # the payload carries "GuestInfo"
for guest1 in guests1:
    errors = validate_guest(guest1)
```

`GuestInfo` is an object under a different key, so the loop body never executes
([guest/routes.py:144](../app/guest/routes.py#L144)). The numbered checks above
still run, but the *format* validator — the one that enforces Arabic name, email
shape and double-space rules — does not. This is why `50012 Arabic Name is
required` never fires on the guest endpoints.

**Error codes** — 40009 40011 50001 50002 50005–50011 50013–50016 60001 60004
60006–60013 ✅ · **40010** ❌ **not checked** · **50012** ❌ · **50022** ❌.

**Payload** — the spec's § 4.2 sample is rejected three times:

| Spec sample | Rejected | Code |
|---|---|---|
| `"Attachments":null` | at least one attachment required | **60001** |
| `"RelationshipCode":"Son"` | not in the relationship table — valid: `businessAssociate` `familyHelper` `familyMember` `friend` `visitor` | **50009** |
| `"ExpiryDate":"2020-12-27…"` | expiry in the past | 60011 |

`"UID":"null"` is the string, not JSON `null` — ignored on create, but wrong.

**Response** — as specified, with one trap: `guests[].uid` here **is** the guest
id, the opposite of `POST /checkin`.

**Verdict:** ❌ **two real gaps** — the missing cancelled-stay check and the dead
validator.

## 4.3 — `PUT /guest`

**Contract** — § 4.3, `PUT /guest` —
[guest/routes.py:956](../app/guest/routes.py#L956) ·
[`10_guest_put_edit_escort.json`](payloads/10_guest_put_edit_escort.json)

Matching is on **`DocumentNumber`**: a guest whose document already exists is
updated in place rather than duplicated.

**Validation order** — 40009 [972](../app/guest/routes.py#L972) · **40010**
[996](../app/guest/routes.py#L996) · 40011
[1009](../app/guest/routes.py#L1009), then the same guest and attachment blocks.

**50016 is deliberately disabled** ([guest/routes.py:1415](../app/guest/routes.py#L1415)) —
that is exactly what makes this an edit rather than an add.

**Error codes** — as § 4.2 plus 40010 ✅ · **50012 50022** ❌ · 50016 disabled by
design.

**Verdict:** ⚠️ **conforms; 50022 missing, validator dead as in § 4.2.**

---

# Part 5 — § 5 Guest check-out

## 5.1 — `POST /guestcheckout`

**Contract**

| | |
|---|---|
| Spec | § 5.1, `POST api/guestcheckout/` |
| Build | `POST /guestcheckout` — [guestcheckout/routes.py:34](../app/guestcheckout/routes.py#L34) |
| Payloads | [`12` escort leaves](payloads/12_guestcheckout_post_escort.json) · [`13` **main-guest handover**](payloads/13_guestcheckout_post_mainguest_handover.json) |

**Validation order**

| # | Line | Code | Check |
|---|---|---|---|
| 1 | [58](../app/guestcheckout/routes.py#L58) | 40011 | stay not already checked out |
| 2 | [70](../app/guestcheckout/routes.py#L70) | 40014 | `CheckoutDateTime` present |
| 3 | [128](../app/guestcheckout/routes.py#L128) | 40032 | at or after that guest's check-in |
| 4–5 | [144](../app/guestcheckout/routes.py#L144), [167](../app/guestcheckout/routes.py#L167) | 40009 / 40010 | exists, not cancelled |
| 6–7 | [183](../app/guestcheckout/routes.py#L183), [200](../app/guestcheckout/routes.py#L200) | 40014 / 40004 | parses, not future |
| 8 | [216](../app/guestcheckout/routes.py#L216) | 50017 | guest not already checked out |

**This is the weakest endpoint against the spec.** The spec defines four guest
rules here; **three are absent**:

| Spec code | Spec text | Build |
|---|---|---|
| **50018** | Guest is a main guest | ❌ **not implemented** |
| **50019** | Guest is a visitor | ❌ not implemented |
| **50020** | Main Guest Change must fall between check-in and check-out | ❌ free text |
| 50016 | Guest already exists | ❌ not implemented |

The 50018 gap is the consequential one. The spec's design is that checking out
the main guest is *refused* unless handled properly; this build accepts it and,
with `NewMainGuestUID: null`, **leaves the stay with no main guest**, which
breaks later `guestversion` writes. **Always send a successor.**

**Main-guest handover** — driven entirely by `NewMainGuestUID`, exactly as the
spec describes. The build writes a `MainGuestChange` row and a log entry, clears
`IsMainGuest` on the outgoing guest and copies the incoming guest's relationship
onto them, sets `IsMainGuest` on the successor and clears their relationship,
snapshots a new `guestversion`, then checks the departing guest out. There is no
separate main-guest-change endpoint; `GET /mainguestchange` is a read-only dump.

**Payload** — the spec's sample is accepted as printed. Both `GuestUID` and
`NewMainGuestUID` are **guest ids**.

**Verdict:** ❌ **four spec codes missing, including the safety rail 50018.**

---

# Part 6 — § 6 Guest attachment

## 6.1 — `POST /guestattachment`

**Contract** — § 6.1, `POST /guestattachment` —
[guestattachment/routes.py:44](../app/guestattachment/routes.py#L44) ·
[`11_guestattachment_post.json`](payloads/11_guestattachment_post.json)

**Validation order** — 40009 [62](../app/guestattachment/routes.py#L62) · 40010
[86](../app/guestattachment/routes.py#L86) · 40011
[99](../app/guestattachment/routes.py#L99) · 50010
[115](../app/guestattachment/routes.py#L115) (no `GuestUID`) · 60001
[130](../app/guestattachment/routes.py#L130) · 60004
[150](../app/guestattachment/routes.py#L150).

Six checks where the spec lists ten.

**Error codes** — 40009 40010 40011 60001 60004 ✅ · **50016 50021 60002 60003
60005** ❌.

**`60005 Attachment should be an image` is the one to note** — there is no
content-type check anywhere. Any base64 string is accepted and handed to the
image resizer, which will fail with a 500 rather than a clean 400.

**Behaviour beyond the spec** — this endpoint **de-duplicates filenames**: a
second `Image_2.jpg` is stored as `Image_2_1.jpg`. `POST /checkin` and
`POST /guest` do not, so a guest's second document there needs a distinct
`Name`. Files land under `BaseDirectoryPath\Attachments\…\<GuestId>\`.

**Payload** — the spec's sample is accepted. `GuestUID` is the **guest id**.

**Response** — the spec prints a PascalCase envelope here (`ClientUID`,
`MessageType`, `Timestamp`) where every other section uses camelCase; the build
uses camelCase throughout. The spec is internally inconsistent, not the build.

**Verdict:** ⚠️ **conforms; five codes missing, 60005 the significant one.**

---

# Part 7 — § 7 Room change

## 7.1 — `POST /roomchange`

**Contract** — § 7.1, `POST /roomchange` —
[roomchange/routes.py:36](../app/roomchange/routes.py#L36) ·
[`14_roomchange_post.json`](payloads/14_roomchange_post.json)

The date field is **`EffectiveDate`**, not `EffectiveDateTime`. The spec says so.

**Validation order**

| # | Line | Code | Check |
|---|---|---|---|
| 1 | [56](../app/roomchange/routes.py#L56) | 40011 | not already checked out |
| 2 | [70](../app/roomchange/routes.py#L70) | 40009 | check-in exists |
| 3 | [93](../app/roomchange/routes.py#L93) | 40010 | not cancelled |
| 4 | [111](../app/roomchange/routes.py#L111) | 40004 | not in the future |
| 5 | [122](../app/roomchange/routes.py#L122) | **40004** | **after the stay's check-in** — the spec's 80004 case, raised under 40004 |
| 6 | [136](../app/roomchange/routes.py#L136) | 80001 | new room exists |
| 7 | [150](../app/roomchange/routes.py#L150) | 80003 | new room is free |
| — | | *free text* | after any previous room change, any main-guest change, and the newest escort's check-in **and** check-out |

**Error codes** — 40009 40010 40011 80001 80003 ✅ · **80004** ❌ — the rule
exists but is split between code `40004` and free text.

**Payload** — the spec's sample is accepted as printed.

**Verdict:** ⚠️ **conforms; 80004 reported under the wrong code.**

---

# Part 8 — routes with no spec counterpart

The build serves 50 routes. Twelve are the spec's; the other 38 are extensions.

| Group | Count | Routes | Note |
|---|---|---|---|
| Backdated check-in | 1 | `POST /checkin/AddBackdatedCheckin` | Records a stay that has already started **and** ended. 46 validations — the § 1.2 set plus `CheckoutDateTime` at both levels, with the overlap rules relaxed. Payload [`07`](payloads/07_checkin_post_backdated.json) |
| Reference lookups | 14 | `/country` `/emirate` `/room` `/documenttype` `/visitpurpose` `/relationship` `/paymenttype` `/cardtype` `/checkintype` `/checkouttype` `/escorttype` `/accessibilitytype` `/cancellationreason` `/dtcmaction` | The spec distributes these tables as a **Google Sheet**. Serving them live is an improvement — use them instead of hard-coding |
| Table dumps | 13 | `/checkintable` `/guesttable` `/checkinguest` `/guestversion` `/guestattachment` `/guestdocumentimage` `/payment` `/log` `/checkout` `/guestcheckout` `/roomchange` `/checkincancellation` `/mainguestchange` | Diagnostic |
| Monitoring | 9 | `/` `/ping` `/version` `/health` `/metrics` `POST /metrics/reset` `/routes` `/status` `/favicon.ico` | Operational |

**Nothing in the specification is unimplemented.**

> **Caveat on the lookups and dumps:** these handlers catch their own database
> errors and answer **HTTP 200** with `{"error": "…"}`. A 200 is not proof of
> success — inspect the body.

### Escort type: a capability the spec assumes and the build lacks

The spec's reference tables include escort types, and `GET /escorttype` serves
both `1 ChildEscort` and `2 AdultEscort`. But **`EscortTypeId` is hard-coded to
`2`** in all three write paths —
[checkin:1100](../app/checkin/routes.py#L1100),
[checkin:2149](../app/checkin/routes.py#L2149),
[guest:838](../app/guest/routes.py#L838). No payload field selects it, so
`ChildEscort` is never written and `checkin.AdultEscortCount` /
`ChildEscortCount` are `null` on every row — although § 1.1.3 prints both fields
in the response.

---

# Appendix A — error code index

## Implemented as specified (49)

40002 · 40003 · 40004 · 40005 · 40006 · 40007 · 40008 · 40009 · 40010 · 40011 ·
40014 · 40023 · 40025 · 40028 · 40031 · 40032 · 40033 · 40034 · 40035 · 40036 ·
40037 · 40038 · 40039 · 50001 · 50002 · 50005 · 50006 · 50007 · 50008 · 50009 ·
50010 · 50011 · 50013 · 50014 · 50015 · 50016 · 50017 · 60001 · 60004 · 60006 ·
60007 · 60008 · 60009 · 60010 · 60011 · 60012 · 60013 · 80001 · 80003

## Specified, not implemented (22)

| Code | Spec text | Build behaviour |
|---|---|---|
| 40001 | Checkin wrong Establishment UID | commented out; `ClientUID` never validated |
| 40012 | Payment order generated, can't modify | absent — no payment-order concept |
| **40015** | Check-in overlaps another check-in, same room | **free text** |
| **40016** | Check-out overlaps another check-in, same room | **free text** |
| **40019** | Check-in overlaps a Room Change | **free text** |
| **40020** | Check-in overlaps a Main Guest Change | **free text** |
| **40021** | Check-out overlaps a Room Change | **free text** |
| **40022** | Check-out overlaps a Main Guest Change | **free text** |
| 40024 | Payment order for that month/year | absent |
| 40026 | Check-in before establishment opening date | absent — no establishment profile |
| 40027 | Waiting-for-room limit reached | absent |
| 40030 | Establishment profile incomplete | absent |
| 50012 | Arabic Name is required | enforced on check-in, reported as a field-keyed message |
| **50018** | Guest is a main guest | **absent — no safety rail on handover** |
| 50019 | Guest is a visitor | absent |
| **50020** | Main Guest Change outside the stay window | **free text** |
| 50021 | Guest does not exist | absent (50010 covers the missing-id case) |
| 50022 | Guest Code already exists | absent — duplicates accepted |
| 60002 | Attachment is not specified | absent (60001 covers it) |
| 60003 | Attachment is not specified | absent (60001 covers it) |
| **60005** | Attachment should be an image | **absent — no content-type check** |
| **80004** | Room change outside the stay window | **split between 40004 and free text** |

**The pattern:** every *overlap* rule in the spec — 40015, 40016, 40019–40022,
50020, 80004 — is implemented as behaviour but reported as a free-text sentence
naming the conflicting check-in id and times. **Eight rules your error handling
will not see a number for.**

## Raised by the build, not in the spec (1)

| Code | Text | Note |
|---|---|---|
| **40050** | Checkin room is Occupied | The spec folds this into `40003 room is not available`. This build keeps 40003 for an *inactive* room and raises 40050 for an *occupied* one. Handle both |

## Codes carrying more than one meaning (6)

A single code means different things depending on where it fires — switch on the
message text, not the number alone.

| Code | Spec meaning | Also used for | Where |
|---|---|---|---|
| **40004** | date must not be in the future | "Room Change time should be after the Primary Checkin Time" | [roomchange:122](../app/roomchange/routes.py#L122) |
| **40035** | house use does not require payment method | "Guest check-in and check-out must be within main check-in period" | [checkin:2648](../app/checkin/routes.py#L2648) |
| **50001** | Guest invalid first name | "Guest invalid Guest Code" | [checkin:419](../app/checkin/routes.py#L419), [guest:185](../app/guest/routes.py#L185) |
| **50014** | Guest check-in before check-in date | three further orderings on the backdated endpoint | [checkin:2969–3002](../app/checkin/routes.py#L2969) |
| **60008** | issue date can't be in the future | "Other Accessibility Type must be specified" | [checkin:764](../app/checkin/routes.py#L764) |
| **60011** | expiry date is not specified | "Attachment is expired" | [checkin:697](../app/checkin/routes.py#L697) |

---

# Appendix B — the guest object

Used in `Guests[]` (§ 1.2, 1.3) and `GuestInfo` (§ 4.2, 4.3).

| Field | Spec required | Build rule | Agrees? |
|---|---|---|---|
| `UID` | Yes, `null` on create | ignored on create | ✅ |
| `GuestCode` | Yes | ≤ 75 chars; **duplicates accepted** (spec: 50022) | ⚠️ |
| `FirstName` | Yes | English letters and spaces, no double spaces | ✅ |
| `LastName` | Yes | same, ≤ 45 chars on `PUT /checkin` | ✅ |
| `ArabicName` | Yes (50012) | Arabic characters and spaces only; **enforced only on the check-in endpoints**; then discarded — the API transliterates the English names instead | ⚠️ |
| `GenderCode` | Yes, `male`/`female` | same; read with `[]` → **500** if absent | ⚠️ |
| `Email` | **No** | key must be **present**, may be `null`; read with `[]` → **500** if absent | ❌ |
| `Mobile` | Yes | digits only, no `+`, no spaces | ✅ |
| `ResidenceCountryPhone` | Yes | free text; key must be present | ✅ |
| `CheckoutDateTime` | Yes, `null` | `null` except on the backdated endpoint | ✅ |
| `BirthPlace` | Yes, "should not contain spaces" | letters only, no spaces — `Abu Dhabi` fails | ✅ |
| `BirthDate` | Yes | ISO, not in the future | ✅ |
| `NationalityCode` | Yes | ISO two-letter, must exist in `country.TwoCode` | ✅ |
| `ResidenceCountryCode` | Yes | same; also determines the stored `MobileCode` | ✅ |
| `RelationshipCode` | Yes | required for non-main guests only; skipped when `IsMainGuest` | ✅ |
| `VisitPurposeCode` | Yes | must exist in `visitpurpose.DtcmCode` | ✅ |
| `CheckinDateTime` | Yes | ≥ the transaction's, not future | ✅ |
| `IsMainGuest` | Yes | exactly one `true` per check-in | ✅ |
| `AttachmentTypeCode` | Yes | must exist in `documenttype.DtcmCode` | ✅ |
| `DocumentNumber` | Yes | alphanumeric, no spaces — **the guest's identity** | ✅ |
| `IssueCountryCode` | Yes | ISO two-letter | ✅ |
| `IssueDate` | Yes | not future, strictly before expiry | ✅ |
| `ExpiryDate` | Yes | must not be in the past | ✅ |
| `EmirateCode` | **No** — "if Document Type is Emirate ID, Required" | **required when `IssueCountryCode == 'AE'`** | ❌ |
| `Attachments` | Yes | at least one; **spec's guest samples send `null`** | ❌ |
| `RequiresAccessibility` | No | `true` stores the accessibility JSON | ✅ |
| `AccessibilityTypes` | No | `[{"Code": "mobility"}, …]` | ✅ |
| `OtherAccessibilityType` | No — required when list contains `other` | same, code 60008 | ✅ |
| `PaidAmount` *(transaction level)* | **not in the spec** | read, defaults to `0` | — |

**Attachment object** — `Id` `UID` `AttachmentCode` `Name` `Size`
`ContentBase64Encoded`. The spec's samples write `attachmenttCode`; the build
accepts **both** spellings everywhere
([checkin:978](../app/checkin/routes.py#L978),
[guest:717](../app/guest/routes.py#L717),
[guestattachment:220](../app/guestattachment/routes.py#L220)).

`Name` becomes the filename on disk. Images are resized to 1080×720 at quality
85. Limit is **200 KB decoded** (60004).

---

# Appendix C — deviation register

Ordered by what will cost an integration the most.

| # | Severity | Deviation | Where |
|---|---|---|---|
| 1 | **High** | **`POST` / `PUT /guest` never run the field validator** — wrong dict key. Escorts added after check-in skip every format check | [4.2](#42--post-guest) |
| 2 | **High** | **`POST /guest` never checks 40010** — a guest can be added to a cancelled stay | [4.2](#42--post-guest) |
| 3 | **High** | **50018 absent** — the main guest can be checked out with no successor, leaving a headless stay | [5.1](#51--post-guestcheckout) |
| 4 | **High** | **Eight overlap rules carry no error code** — 40015, 40016, 40019–40022, 50020, 80004 report free text | [Appendix A](#specified-not-implemented-22) |
| 5 | Medium | **40050 is not in the spec** — handle alongside 40003 | [1.2](#12--post-checkin) |
| 6 | Medium | **Six codes carry more than one meaning** — switch on text, not number | [Appendix A](#codes-carrying-more-than-one-meaning-6) |
| 7 | Medium | **`EmirateCode` gated on `IssueCountryCode == 'AE'`**, not on document type as the spec says. A UAE-issued passport now needs one; a foreign-issued Emirates ID does not | [Appendix B](#appendix-b--the-guest-object) |
| 8 | Medium | **60005 absent** — non-image attachments are accepted, then fail as a 500 in the resizer | [6.1](#61--post-guestattachment) |
| 9 | Medium | **50022 absent** — duplicate guest codes accepted | [1.2](#12--post-checkin) |
| 10 | Medium | **`ChildEscort` cannot be recorded** — `EscortTypeId` hard-coded to 2 | [Part 8](#escort-type-a-capability-the-spec-assumes-and-the-build-lacks) |
| 11 | Medium | **Seven guest fields read with `[]`** — `GenderCode` `Email` `ResidenceCountryPhone` `DocumentNumber` `ResidenceCountryCode` `CheckinDateTime` `IsMainGuest` raise a **500**, not a 400, when absent | [Appendix B](#appendix-b--the-guest-object) |
| 12 | Low | **Attachment `uid` is an integer**, not the GUID the spec prints | [1.2](#12--post-checkin) |
| 13 | Low | **`50012` enforced but unnumbered** on the check-in endpoints | [Appendix A](#specified-not-implemented-22) |
| 14 | Low | **40001 never raised** — `ClientUID` is not validated | [1.2](#12--post-checkin) |
| 15 | Low | **No `api/` URL prefix** — `GET /routes` is authoritative | all |
| 16 | Low | **Undocumented same-month rule** on cancellation | [3.1](#31--post-checkincancellation) |

## Recommendations

**For the integrating developer**

1. Use [`payloads/`](payloads/), not the spec's samples — five of the twelve are
   rejected as printed.
2. Treat errors as **code-or-sentence**. Eight rules return free text. Never
   assume a number is present.
3. Handle **40050** alongside 40003, and match on message text where a code is
   [reused](#codes-carrying-more-than-one-meaning-6).
4. Do not rely on **50018**, **50022** or **60005** — enforce all three
   client-side.
5. Validate guest fields client-side, especially on the add-escort path
   (deviation 1).
6. Send `EmirateCode` whenever `IssueCountryCode` is `AE`, whatever the document
   type.
7. Send every guest key even when the value is `null` — seven of them 500 on
   absence.

**For the API team**, in order of value per unit of work:

1. **Deviation 1** — change `data.get("Guests", [])` to read `GuestInfo` in both
   guest handlers. One line each; restores every field check on the add-escort
   path.
2. **Deviation 2** — add the 40010 check to `POST /guest`. One block, copied from
   the PUT.
3. **Deviation 3** — implement 50018.
4. **Deviation 4** — attach numbers to the eight overlap messages. The behaviour
   already exists; only the code is missing.
5. **Deviations 8, 9** — 60005 and 50022.
6. **Deviation 7** — decide whether `EmirateCode` follows document type or issue
   country, then fix either the build or the specification. The disagreement
   itself is the problem.

---

## Method and limits

Every claim above was read out of the route handlers; commented-out code was
excluded, which is why 40001 counts as absent. Validation orders were extracted
mechanically from the source and are accurate as of build v1.0.0.

**Not verified by execution.** No `POST` or `PUT` has been run against a live
instance — the `guestdocumentimages` table is missing from the reference
database, so every write endpoint returns 500 before reaching its business logic
(handover report, D1). Read-only endpoints were exercised on 2026-08-04 and are
green. Response-shape claims for the write endpoints come from the source, not
from observed responses.
