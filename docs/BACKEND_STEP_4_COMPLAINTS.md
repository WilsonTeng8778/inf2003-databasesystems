# Backend step 4 — Complaint browsing and filtering

Implemented and verified on **28 October 2026**. Public read-only APIs now expose
the imported MongoDB complaint records as a filtered list and individual details.
The visual complaint explorer remains part of the later frontend stage.

## Try the feature

Restart Flask if it was already running before these routes were added:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend:create_app run --host 127.0.0.1 --port 5000
```

Open these links in a browser:

- [First five 2022 Honda Civic complaints](http://127.0.0.1:5000/api/complaints?year=2022&make=HONDA&model=CIVIC&pageSize=5)
- [Civic complaints about the steering component](http://127.0.0.1:5000/api/complaints?year=2022&make=HONDA&model=CIVIC&component=STEERING&pageSize=5)
- [Civic narratives matching steering](http://127.0.0.1:5000/api/complaints?year=2022&make=HONDA&model=CIVIC&q=steering&pageSize=5)

These requests return JSON. An `item` is one merged complaint, not one component
row from the original file. Copy an item's `odiNumber` and visit
`http://127.0.0.1:5000/api/complaints/ODI_NUMBER`, replacing `ODI_NUMBER` with that
value, to see its full narrative and source provenance. You do not need to sign in.

`page=2` requests the next page. `pagination.total` counts all matching complaints;
`items` contains only the requested page. The first example has **885** total
complaints in the verified snapshot. Starting Flask and browsing do not import,
reset or change the stored data.

## Endpoints and filters

| Request | Result |
| --- | --- |
| `GET /api/complaints` | Paginated `items`, `pagination` and an interpretation note. |
| `GET /api/complaints/{odiNumber}` | `complaint` with the full narrative, vehicle/incident fields, mileage, occurrences, manufacturer and selected source metadata; 404 if absent. |

The list accepts these optional query parameters. Supplied filters combine with
AND: every filter must match the same complaint.

| Parameter | Meaning |
| --- | --- |
| `modelYearId` | Positive catalogue ID returned by vehicle search/profile; matches the MongoDB reference. |
| `year`, `make`, `model` | Exact vehicle labels; make/model normalize case and whitespace as during import. |
| `component` | Exact normalized member of the complaint's `components` array, such as `STEERING`. |
| `receivedFrom`, `receivedTo` | Valid `YYYY-MM-DD` dates, including both endpoint days in UTC; either bound can be supplied. Filters receipt date, not incident date. |
| `crash`, `fire` | `true` or `false` (case insensitive), matching the reported flag. Unknown/null values match neither. |
| `hasInjuries`, `hasFatalities` | `true` means a reported count greater than zero; `false` means exactly zero. Unknown/null counts match neither. |
| `q` | 1–200 printable characters for narrative text search. |
| `page`, `pageSize` | Defaults 1 and 20. Page size is 1–100; page is 1–10,000. Narrow the filters for deeper browsing. |

Results sort by `receivedDate` descending, then string ODI ID descending as a
stable tie-break. Dates are returned as `YYYY-MM-DD`, or null if unknown. ODI IDs
remain strings. Lists have a preview of up to 240 narrative characters and a
`narrativeTruncated` flag; the detail response supplies the complete narrative.

Text search uses the existing English `narrative_text` index. It searches words
with MongoDB's stemming/stop-word rules, rather than arbitrary substrings. For
example, `q=steering` searches that term; a value of `"steering wheel" -brake`
requests a phrase and excludes a term. Space-separated terms normally use OR
within the text expression; other supplied filters still use AND.
See the [MongoDB text-query reference](https://www.mongodb.com/docs/manual/reference/operator/query/text/).

Duplicate/unknown parameters, invalid booleans/dates/IDs, reversed date bounds,
empty text and excessive pagination return JSON 400 errors. Valid unmatched
filters return 200 with an empty list; an absent detail returns 404. Imported
complaints have no POST/PATCH/DELETE routes; these methods return 405.

## How the databases are used

The earlier safety profile combines SQL official-record counts and MongoDB
complaint summaries. These new endpoints read the complaint collection directly;
they need no SQL connection. The shared `modelYearId` connects a searched vehicle
to the complaint documents. This prepares the complaint selection needed by the
later analyst-case workspace.

MongoDB filters demonstrate nested-field queries (`incident.crash`), array
membership (`components`), date/count conditions and indexed narrative search.
The list count and page use the same validated filter. Query field names and
operators are defined by the server; clients cannot submit arbitrary MongoDB
filter objects. Output fields are selected explicitly. Each count/find has a
five-second server execution limit, and query failures return a sanitized 503.
Driver details are in the official [count](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/crud/query/count/)
and [find](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/crud/query/find/) references.

The existing `vehicle_received`, `vehicle_components` and `narrative_text` indexes
were retained. No schema change, new dependency or reimport was needed. The MongoDB
connection still uses the existing local configuration; API read-only behavior
does not establish database-level MongoDB user permissions.

Consumer complaints remain allegations rather than confirmed defects, and a
make/model/year match does not establish one VIN's recall status. Separate count
and page reads are not a shared snapshot during a concurrent data refresh. Before/
after index benchmarks and the visual explorer are still planned.

## Verification

On **28 October 2026**:

- **71 automated tests passed**, including 18 new complaint API tests covering
  validation, null handling, output fields, query construction and failure paths.
- **42 live HTTP checks passed**, comparing filters/results with direct MongoDB
  reads and the SQL-linked vehicle search/safety profile.
- Live checks exercised array membership, boolean/count filters, inclusive dates,
  combined filters, text/phrase/exclusion search, deterministic pages, detail
  provenance, empty results, invalid inputs and unsupported write methods.
- Checked SQL/MongoDB record counts were unchanged, including existing users,
  sessions, saves and source records. The verifier inserted no fixtures.

Evidence: [complaints_verification_report.json](complaints_verification_report.json).
Historical database/auth/saved-vehicle reports keep their original results.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/verify_complaints.py
```

The live verifier starts/stops its own temporary local server and replaces only
its evidence report. Database outage behavior is tested with simulated failures;
verification does not stop the database services. Remaining official-record
lists/details, analyst-case workflows, fleets, the GUI and evaluation remain.
