# NHTSA source inspection — 25 October 2026

The four downloaded archives were read in full before defining the initial
physical schema. Machine-readable counts, archive SHA-256 hashes, extracted
filenames/sizes, row widths, date ranges and safe sample fields are recorded in
[data_profile.json](data_profile.json). The dictionaries in `data/dictionaries/`
were also inspected. Raw archives are local files excluded from Git.

## Verified file layouts and chosen scope

All four extracted files are **headerless, tab-delimited text**. Quotation marks
are literal narrative characters, so these are not parsed as quoted CSV.
Dictionary dates use `YYYYMMDD`. Model-year `9999` means unknown/not applicable.

| Source | Fields | Raw rows | Eligible vehicle rows | Distinct primary identifiers |
| --- | ---: | ---: | ---: | ---: |
| Recalls after 2010 | 29 | 246,844 | 219,728 | 13,600 campaigns |
| Investigations | 11 | 154,439 | 146,113 | 3,626 action numbers |
| Complaints received 2020–2024 | 51 | 418,884 | 412,866 | 290,634 ODI numbers |
| Complaints received 2025–2026 | 51 | 207,526 | 204,320 | 138,203 ODI numbers |

All observed rows have the dictionary's expected field count. The selected scope
is all supplied **vehicle** records with nonblank make/model and a numeric model
year between 1900 and 2100. Recall/complaint files use product-type `V` to exclude
equipment, tires and child restraints. Investigations have no product-type field:
valid make/model/year is a proxy there and can include trailers/heavy vehicles.
This is a vehicle research catalogue, not a passenger-car-only catalogue.

Unknown-year and out-of-scope product rows are counted as skipped. Malformed
field counts or missing record identifiers are rejected. No arbitrary make,
model-year or record-count sampling limit is imposed on this first import.

The complaint receipt-date windows are confirmed as 2020-01-01–2024-12-31 and
2025-01-01–2026-10-22 in the downloaded snapshot. The recall file is filtered by
report timing, not vehicle model year; it contains older affected vehicles.

## Findings that changed the logical blueprint

1. **One campaign is not one source row.** 10,317 eligible recall campaigns span
   multiple vehicle identities. Campaign metadata belongs in `recall`; vehicle
   applicability belongs in `recall_vehicle`. `recall_record` preserves source
   component/vehicle/manufacturing-date grain and record identifiers.
2. **One ODI complaint is not one component row.** The two complaint files contain
   617,186 eligible rows for 428,837 ODI identifiers (summed across disjoint receipt
   windows). Rows are merged into component arrays; crash/injury/fatality figures
   are not summed across component rows. No ODI in either individual archive is
   associated with multiple eligible vehicle identities. The importer checks this
   again across both files and refuses an ambiguous merge.
3. **Manufacturer and make do not form a strict one-to-many hierarchy.** The recall
   data alone associates 254 makes with multiple source manufacturer names.
   These include historical naming differences and supplier relationships. Store
   source associations in `manufacturer_make`, without claiming corporate ownership.
   Recall field 8 (reporting manufacturer) is distinct from field 15 (vehicle/product
   manufacturer); the importer keeps that distinction.
4. **An investigation can involve several manufacturers and recalls.** 199 eligible
   investigation numbers have multiple manufacturer names. Use separate
   manufacturer, component and recall-reference relations instead of overwriting
   a single manufacturer/campaign column. Related recall identifiers are preserved
   even when the recall is outside this post-2010 snapshot.
5. **The catalogue must use the union of all sources.** There are 53,555 distinct
   normalized make/model/year identities. 3,655 complaint vehicle identities have
   no matching recall identity in this snapshot. Building from recalls alone would
   hide them from search.

## Normalization and interpretation

- Make/model/manufacturer matching trims and collapses whitespace and uppercases
  text. Punctuation is preserved. No fuzzy matching or unverified corporate/name
  alias merging is applied. Known spelling variants can therefore remain separate.
- Source identifiers are strings. Complaint `_id` and `odiNumber` are the ODI
  identifier; CMPLID is preserved as a source row identifier rather than used as a
  complaint identity. Dictionaries say CMPLID can change between exports.
- Empty numeric/flag values become `null`, distinct from zero/false. Original
  explicit zeros are retained; the complaint dictionary warns that an upstream
  change filled some formerly blank fields with zero/`N`, so source-level missingness
  cannot always be recovered.
- Dates become PostgreSQL dates or MongoDB BSON UTC dates, not display strings.
  Invalid dates become null. The inspector counts invalid nonblank primary dates.
- All rows in this snapshot decoded strictly as UTF-8. The reader also supports
  an explicit Windows-1252 fallback and records its use in the profile. Eight
  literal replacement characters are already present in the supplied complaint
  text; no encoding repair is guessed. Source archives remain untouched.
- The investigation layout supplies open/close dates and an action number, but no
  dedicated status/type fields. `OPEN`/`CLOSED` is derived from close-date presence;
  type is the action-number letter prefix. A missing close date is an inferred
  status, not a separately verified NHTSA status feed.
- Manufacturer/make/model are retained for research. VIN, city/state, operator
  name, dealer names, phone numbers and contact columns are excluded from imports
  and temporary complaint staging. Public narratives are retained as supplied and
  may themselves contain personal details; they are not claimed to be redacted.

## Reproducibility and limits

`scripts/inspect_data.py` regenerates the profile without accessing a database.
`scripts/import_all.py` constructs the catalogue first, then recalls,
investigations, and grouped complaint documents. SQLite is disposable disk staging
inside Python's ETL process, not a third application database.

Stable-key upserts make reruns of the same snapshot safe. SQL stages commit
individually. MongoDB batches are independent of SQL: a failed complaint import
can leave valid partial batches, and rerunning completes them. Imports are
serialized with a PostgreSQL advisory lock. Existing references are not deleted
merely because a later source snapshot omits them; full snapshot-deletion
reconciliation is not implemented.

Import logs distinguish raw rows read/skipped/rejected from logical entities
inserted/refreshed. For recalls the entity is a campaign, for investigations an
action number, for complaints an ODI document, and for the catalogue a model-year
identity. Those counts should not be added as if they were all source rows.
“Refreshed” includes matching existing entities even if their values did not change.

Campaign/action-level text is selected deterministically from the first source
record for that identifier. Recall component/source records and investigation
relation sets preserve the repeated relationships. A future snapshot refresh
should review changes to both shared text and relationship sets.

The data findings support the agreed SQL/MongoDB split. The many-to-many
manufacturer associations refine the physical schema while retaining the project
purpose, selected datasets, roles, analyst workflow and small fleet scope.

