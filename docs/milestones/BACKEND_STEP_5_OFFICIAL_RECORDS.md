# Backend step 5 — Recalls and official investigations

Implemented and verified on **28 October 2026**. Public SQL research now includes
paginated recall and official-investigation lists, full details, affected vehicle
identities and recall source records. These complement the MongoDB complaint API.

## Try it

The new public views and reader grants were already applied on this computer.
Start or restart Flask to load the new routes:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend:create_app run --host 127.0.0.1 --port 5000
```

Open [Civic recalls](http://127.0.0.1:5000/api/recalls?year=2022&make=HONDA&model=CIVIC)
and [Civic official investigations](http://127.0.0.1:5000/api/investigations?year=2022&make=HONDA&model=CIVIC).
Their totals are **4** and **2** in the verified snapshot. Open an item's
`detailUrl` to read the complete record. For example, the verified snapshot has
[recall 26V332000](http://127.0.0.1:5000/api/recalls/26V332000) and
[investigation EA23003](http://127.0.0.1:5000/api/investigations/EA23003).
The response is JSON; browser screens remain planned.

Details contain `links.vehicles`, and recalls also contain `links.records`. Open
those URLs to see related records. Add `?pageSize=5&page=2` for another small batch.
Research does not require login. Reading these endpoints leaves stored data alone.

## Endpoints

| Request | Result |
| --- | --- |
| `GET /api/recalls` | One item per matching campaign with a short summary and detail URL. |
| `GET /api/recalls/{campaignNumber}` | Full summary, consequence, remedy, manufacturer, affected-unit count, flags, component names and relationship counts. |
| `GET /api/recalls/{campaignNumber}/vehicles` | Paginated distinct affected make/model/year identities. |
| `GET /api/recalls/{campaignNumber}/records` | Paginated original component/vehicle source rows with manufacturing dates and archive/line provenance. |
| `GET /api/investigations` | One item per matching official investigation with a summary preview and detail URL. |
| `GET /api/investigations/{investigationNumber}` | Full official summary, subject, dates/status, components, all associated manufacturers and linked recall references. |
| `GET /api/investigations/{investigationNumber}/vehicles` | Paginated distinct affected vehicle identities. |

External record numbers accept 1–20 ASCII letters/digits and normalize case.
Use `campaignNumber` or `investigationNumber` in URLs. Numeric `recallId` and
`investigationId` identify SQL rows and are separate from internal analyst case IDs.

## Filters and pagination

| List parameter | Meaning |
| --- | --- |
| `modelYearId` | Exact positive vehicle catalogue identifier. |
| `year`, `make`, `model` | Exact vehicle identity filters; case/whitespace normalize as during import. |
| `component` | Exact normalized component name. For recalls it matches a source record for the same filtered vehicle; investigation components apply to the whole investigation. |
| `manufacturer` | Exact normalized reporting manufacturer for recalls, or any associated manufacturer for investigations. |
| `reportFrom`, `reportTo` | Recall report dates, valid `YYYY-MM-DD`, inclusive. |
| `doNotDrive`, `parkOutside` | Recall flags: `true` or `false`; unknown/null is neither. |
| `openedFrom`, `openedTo` | Official investigation opening dates, valid `YYYY-MM-DD`, inclusive. |
| `status` | Official investigation `OPEN` or `CLOSED`, case insensitive. |
| `investigationType` | Exact normalized official investigation type, such as `PE` or `EA`. |
| `page`, `pageSize` | All lists, including related records: defaults 1/20, page maximum 10,000, size maximum 100. |

Recall-only filters are rejected on investigations and vice versa. Related-record
URLs accept only `page` and `pageSize`. Other supplied list filters combine with
AND; multiple vehicle attributes must match one vehicle identity. Unknown and
repeated parameters, invalid numbers/dates/flags and reversed date ranges return
400 before opening SQL connections.

Recalls sort by report date descending (unknown dates last), then campaign number.
Investigations sort by opening date descending (unknown last), then investigation
number. Affected vehicles sort by make/model/year/ID; source rows sort by their
string source-record ID. Lists return a maximum 240-character summary preview;
details retain full text. Unknown dates/flags/text remain null.

Valid unmatched filters return an empty 200 list. An absent parent returns 404
for both its detail and its related-record URLs. Imported official records have
no POST/PATCH/DELETE routes; these return 405. SQL failures return the existing
sanitized 503 error, with a five-second statement timeout on the application reader.

## Why the queries work this way

A recall can affect many vehicle identities, and each identity can have several
component/source records. The list must count **campaigns**, not matching source
rows. SQL `EXISTS` tests whether a relationship matches while returning each parent
campaign once. With both vehicle and component filters, one source row must match
both, preventing another vehicle's component from qualifying a campaign.

An affected vehicle count describes make/model/year combinations. A recall's
`potentiallyAffected` describes the source's potentially affected units. Neither
is a count of our users' physical fleet vehicles. Source-record count is different
again: campaign 21V058000 has **18,662 source records** in this snapshot. The
separate paginated endpoint avoids putting all those records in one detail response.

Official investigations retain their many-to-many manufacturer relationships.
Their linked recall campaign numbers can fall outside our selected post-2010
recall snapshot. We keep those numbers, set `inImportedSnapshot=false`, and return
`detailUrl=null` rather than pretending a local detail exists.

These official investigations are separate from our planned internal analyst
cases. OPEN/CLOSED is derived from the stored closing date, not a live NHTSA status
check. A model-year recall match does not establish VIN applicability or repair
completion. Separate count/page queries are not a shared snapshot during an import.

## SQL access and setup

[sql/research_views.sql](../../sql/research_views.sql) defines eight public research
views. They expose official records and their relationships without exposing user,
session, saved-vehicle, case or fleet tables. The existing application reader has
SELECT on these views, with no granted writes or direct access to the checked
private and official base tables. Auth/workflow accounts remain separate.

For a fresh installation, normal construction includes the views. For an existing
installation using an older checkout, apply the additive views/reader grants with:

```powershell
.\.venv\Scripts\python.exe scripts/setup_readonly_user.py
```

This was already done locally on 28 October. It reuses the configured reader's
credentials and retains data. It does not require a full import or schema rebuild.

The design uses PostgreSQL's default view-owner access to underlying relations;
only SELECT is granted to the reader. See the official
[view permissions](https://www.postgresql.org/docs/18/sql-createview.html) and
[EXISTS semantics](https://www.postgresql.org/docs/18/functions-subquery.html)
references. These references explain the mechanism; our actual grants were checked
against the running database.

## Verification

On **28 October 2026**:

- **92 automated tests passed**, including 21 new official-record tests and all
  earlier API/auth/ownership/complaint/ETL tests.
- **79 real HTTP checks passed**, covering lists, details, combined filters,
  pagination, missing records, invalid inputs and unsupported writes.
- Direct SQL agreed with the HTTP responses and the existing Civic safety profile.
- A large campaign's paginated source records preserved archive/line provenance;
  out-of-snapshot recall references remained in investigation details.
- SQL permission checks confirmed SELECT-only research views and no direct
  account/workflow or official source-table access for the application reader.
- Inline SQL `VALUES` tested vehicle/component mismatch cases without inserting
  stored fixtures; the current snapshot did not provide a mixed campaign example.
- Checked SQL/MongoDB record counts, including existing users/sessions/saves and
  source/link records, were unchanged. No persistent verification fixtures were used.

Evidence: [official_records_verification_report.json](../official_records_verification_report.json).
Earlier milestone reports retain their original dates/results.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/verify_official_records.py
```

The live verifier starts/stops its own local server and replaces its evidence
report. Database-outage/null handling also has isolated automated coverage. These
are functional checks; performance benchmarks, analyst-case recovery, fleet
workflows, browser pages and final deliverables remain to build.
