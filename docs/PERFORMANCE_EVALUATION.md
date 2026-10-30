# Performance evaluation: indexes and query plans

**Verified:** 29 October 2026, Asia/Kuala_Lumpur. **Stage:** 8 of 9, in progress.

We now have measured evidence for selected PostgreSQL and MongoDB queries. The
existing SQL vehicle indexes helped both recall queries. A MongoDB index that
matches complaint pagination's full ordering reduced unnecessary sorting and was
then added to the real application database. Broader final evaluation remains.

## Start here: what this experiment means

An index is a lookup structure, similar to the index at the back of a book. The
database can use it to find selected records without checking every record. The
order of its fields matters: our complaint page filters by vehicle, sorts by
receipt date and uses the complaint ID to break ties between equal dates.

A **query plan** describes how the database answered a query. Timings tell us
how long a run took; plans help explain why it took that long. We measured
identical queries before and after indexing **within each database**. These are
different SQL and MongoDB workloads, so their times do not rank the two DBMSs.

The experiments ran on disposable, full-sized copies. The original records and
indexes stayed in place throughout those comparisons. After the copies were
removed and this was checked, we separately added the measured MongoDB index.

## Evidence you can inspect or use in the report

| Artifact | What it contains |
| --- | --- |
| [Controlled benchmark report](benchmarks/20261029T235059_28426da4/report.json) | Every measured/warmup time, two plans per phase, query definitions, result hashes, scale/environment and cleanup/source-count/index checks. |
| [Summary CSV](benchmarks/20261029T235059_28426da4/summary.csv) | Medians, quartiles, extrema and representative plan counters. |
| [PostgreSQL PNG](benchmarks/20261029T235059_28426da4/postgres_timings.png) / [SVG](benchmarks/20261029T235059_28426da4/postgres_timings.svg) | Standalone figures suitable for report/slides. |
| [MongoDB PNG](benchmarks/20261029T235059_28426da4/mongodb_timings.png) / [SVG](benchmarks/20261029T235059_28426da4/mongodb_timings.svg) | Separate figure showing all three MongoDB phases. |
| [Live index improvement report](index_improvements/20261029T235322_731cbce8/report.json) | Before/after plans/timings on the actual complaint collection and five native checks. |
| [Automated test summary](benchmarks/20261029T235059_28426da4/automated_tests.json) / [test log](benchmarks/20261029T235059_28426da4/automated_tests.txt) | 177 tests passed on 29 October, including seven measurement-integrity tests. |

Each raw plan is a separate JSON file named in the relevant report's `plan_file`
field. SQL plans retain the entire `EXPLAIN` response. MongoDB files retain the
complete planner/execution trees; server host/port diagnostics are excluded.
Complaint narratives are hashed in memory for result checks and are not copied
into the evidence. Previous milestone reports/screenshots were preserved. The
219 browser checks belong to the earlier [frontend step 6 run](frontend_step_6_verification_report.json);
they were not rerun for this index-only application change.

## Workloads and dataset scale

The predefined demonstration vehicle is **2022 HONDA CIVIC**, catalogue identity
**17527**. Its full-window scope has 885 complaints, four official recalls and
nine STEERING recall source rows. The narrower 2026 complaint window has 31
matches. Both complaint queries fetch the first 20 reports in the same stable
order. Parameters were fixed before measuring.

| Full source copied | Records |
| --- | ---: |
| PostgreSQL `recall` | 13,600 |
| PostgreSQL `recall_vehicle` | 93,743 |
| PostgreSQL `recall_record` | 219,728 |
| MongoDB `complaints` | 428,837 |

SQL copies retain the primary-key columns/indexes, with `VACUUM ANALYZE` run before
measurement. They omit unrelated foreign keys, triggers and secondary indexes;
only the stated vehicle indexes are added for the indexed phase. They are query
fixtures, not replacements for the full application schema. MongoDB copies retain
all complaint fields, including narratives, and initially have only the default
`_id_` index. Row/document counts are checked against their sources.

SQL query 1 joins `recall_vehicle` to `recall` by `recall_id`, filters on
`model_year_id=17527`, and returns campaign number/date/summary ordered by report
date descending with campaign number as tie-breaker. Its indexed phase adds
`recall_vehicle(model_year_id, recall_id)`, matching the application's existing
`idx_recall_vehicle_model_year` definition.

SQL query 2 joins `recall_record` to `recall`, filters on vehicle identity and
`component='STEERING'`, and returns source ID/campaign/component/production dates
ordered by source ID, limited to 20. Its indexed phase uses
`recall_record(model_year_id, recall_id)`, matching `idx_recall_record_vehicle`.
These isolate representative relational lookup patterns; they do not time the
complete official-record HTTP endpoint or safety-summary view.

MongoDB uses the application's `complaint_query` and `LIST_FIELDS` definitions:
vehicle identity, inclusive UTC receipt dates, and the projected complaint list
fields including narrative. The windows are **1 January 2020–22 October 2026** and
**1 January 2026–22 October 2026**. Sort is `{receivedDate:-1, _id:-1}` and limit
is 20. These measurements time the list fetch, not the separate total-count
query, JSON rendering, Flask request or browser rendering.

| MongoDB phase | Indexes on the copy |
| --- | --- |
| Baseline | `_id_` only. |
| Current | `_id_` plus `vehicle_received(modelYearId:1, receivedDate:-1)`. |
| Candidate | Both preceding indexes plus `vehicle_received_ordered(modelYearId:1, receivedDate:-1, _id:-1)`. |

The controlled copy omits component/text indexes to isolate this date-pagination
question. The subsequent live verification uses the real collection with all
existing component, text, ID and date indexes retained.

## Measurement method and environment

Two rounds use reversed phase order: SQL baseline/indexed, then indexed/baseline;
MongoDB baseline/current/candidate, then candidate/current/baseline. Each phase
and workload has **three excluded warmups and 15 measured fetches per round**:
30 measured samples per reported phase. Index creation/copying/cleanup are outside
those query timings. All measured and warmup results must have the same ordered
SHA-256 fingerprint across phases. Hashing happens after the timer stops.

The timer includes the reused local driver's execute, network round trip and full
fetch/decode. Connection establishment is excluded; PostgreSQL automatic prepared
statements are disabled so later samples do not silently switch preparation mode.
No query/index hints force the optimizer. Separate plans are obtained after each
measured batch. Source application table counts and index definitions, including
import/account/workflow tables, are compared before and after cleanup. This checks
counts/definitions; it is not a full before/after content checksum of every source
record. The runner contains no writes targeting source tables/documents.

The run used Windows 11, Intel Core i5-14600KF, 20 logical CPU threads, about
31.7 GiB RAM, Python 3.13.7, PostgreSQL 18.6, MongoDB 9.0.4, psycopg 3.3.6 and
pymongo 4.19.0. PostgreSQL settings included 128 MB shared buffers, 4 MB work
memory, 4 GB effective cache size, random page cost 4 and at most two parallel
workers per gather. Full allowlisted settings are in the report. No server tuning
was changed. Figures were generated with matplotlib 3.11.2.

## Measured PostgreSQL results

Client fetch/decode milliseconds, **median [25th–75th percentile]**, 30 samples per phase:

| Query | Primary keys only | Existing vehicle index added |
| --- | ---: | ---: |
| Recall campaigns for vehicle | 2.562 [2.405–2.810] | 0.267 [0.190–0.303] |
| STEERING recall source rows | 23.959 [22.938–27.237] | 0.188 [0.179–0.215] |

The recall query's plan changed from scanning all 93,743 link rows to an index-only
scan returning four links, followed by four primary-key recall lookups. Root
shared-buffer hits fell from **519 to 16**. Both phases returned the same four
ordered records.

The source-row query changed from a parallel sequential scan of the 219,728-row
table to a bitmap lookup of the selected vehicle's 15 rows, filtering out six
non-STEERING rows and joining nine remaining rows. Root shared-buffer hits fell
from **3,419 to 34**. Both phases returned the same nine ordered source records.
These indexes already existed in the real application; the experiment validates
their benefit rather than adding duplicate live SQL indexes.

PostgreSQL buffer totals include child nodes, so we read the root counters without
summing the plan tree. The report also provides a scan-row estimate computed from
rows returned/removed and loop counts. This is an estimate because per-loop values
may be averaged/rounded, especially for parallel scans; it is not a universal exact
"rows examined" counter. SQL explain execution times are server-side instrumented
samples and differ from the repeated client measurements. See the primary
[PostgreSQL 18 EXPLAIN guide](https://www.postgresql.org/docs/18/using-explain.html)
for these plan and counter meanings.

## Measured MongoDB results

Client fetch/decode milliseconds, **median [25th–75th percentile]**, 30 samples per phase:

| Complaint window | `_id_` only | Existing date index | Date + ID ordering index |
| --- | ---: | ---: | ---: |
| 2020–22 October 2026 | 247.744 [218.768–265.951] | 1.552 [1.407–1.828] | 0.452 [0.394–0.615] |
| 2026–22 October 2026 | 246.381 [229.266–262.226] | 0.497 [0.472–0.542] | 0.401 [0.366–0.422] |

| Window/phase | Documents examined | Index keys examined | Blocking `SORT` |
| --- | ---: | ---: | --- |
| Broad, baseline | 428,837 | 0 | Yes |
| Broad, current | 885 | 885 | Yes |
| Broad, candidate | 20 | 20 | No |
| Narrow, baseline | 428,837 | 0 | Yes |
| Narrow, current | 31 | 31 | Yes |
| Narrow, candidate | 20 | 20 | No |

Both captured plans per phase agree on these counters and access paths. The
existing date index finds matching vehicle reports, but cannot supply the full
date-plus-ID order. The candidate index supplies that order, letting the database
stop after the first 20 matching documents. This is especially useful when many
reports match: the broad query's median fetch time fell by about 1.10 ms compared
with the existing index. The narrower query's absolute saving was about 0.10 ms.

MongoDB `executionTimeMillis` is integer milliseconds and some indexed plans report
zero; that does not mean a query takes no time. The client timer resolves the
smaller durations. `explain` also bypasses the normal plan cache, so its execution
time is not the same measurement as an ordinary cached fetch. Counter and cache
interpretation follows the primary
[MongoDB explain-results documentation](https://www.mongodb.com/docs/manual/reference/explain-results/).

## Improvement applied to the real application

After the controlled copies were removed, `vehicle_received_ordered` was added
to the real `complaints` collection. Future full setup creates it through
`mongodb/schema.py`; the focused setup helper can add it to an existing database.
The existing `vehicle_received`, component, narrative-text and `_id_` indexes remain.
Retaining the shorter date index avoids making unmeasured claims about all other
workloads or removing an established index during this milestone.

The separate live follow-up used **15 measured fetches per phase, after three
warmups**. Broad-window medians were **1.551 → 0.382 ms**, and narrower-window
medians **0.489 → 0.363 ms**. This sequential live check confirms the effect with
the real index set; the reversed-round copy experiment is the controlled evidence.
Both live post-change winning plans use the new index, examine 20 documents/keys
and have no blocking sort. Ordered results are identical before/after.

Five native assertions passed: eight service scenarios retained identical page
contents/order/totals; both timed result sets matched; both plans used the new
index without sorting; all prior complaint indexes remained; and all SQL counts/
indexes plus MongoDB counts/other indexes remained unchanged. The eight service
scenarios cover pages 1 and 2 of both date windows, a STEERING filter and an empty
1900 date window. They call the actual complaint service, including its count query.

The new index occupied **9,490,432 bytes (about 9.05 MiB)** at verification. The
local `create_index` call took about **1.46 seconds**. That is one observed build,
not a repeatable build-time benchmark. Maintaining an extra index consumes storage
and write work; import/write-throughput overhead was not measured. No source data,
permissions, application accounts, query responses or SQL schema versions changed.

## Limits and work still required

These are **local, single-client, warm-cache microbenchmarks**. There was no cold
cache flush, DB restart, concurrent-user load or production hardware/network.
Other desktop activity was not controlled. The data/window/vehicle and first page
are fixed; deep pagination, text search, unscoped searches, analytics aggregations,
writes/imports and larger future datasets need separate evaluation. Reversed order
helps expose order effects but does not make cache states identical or establish
statistical significance. The narrower candidate improvement is small in absolute
time. Some baseline SQL samples had large scheduling/parallelism outliers; raw
samples and min/max values are retained rather than discarded.

Do not describe these fetch times as full website response times or guaranteed
speedups for every vehicle. Figures use an explicitly labelled logarithmic axis so
sub-millisecond and hundred-millisecond samples remain visible together. The
PostgreSQL and MongoDB panels should be discussed separately in the final report.

Stage 8 continues with requirements-to-evidence coverage, final complete user
journeys, unresolved limitations/refinements and reproducibility checks. The final
report, slides/video, user manual and submission package are still pending.

## Reproduce on another machine

No repeat is necessary to use the already updated local application. Keep both
native DB services running. These are separate PowerShell commands at repo root:

```powershell
# Uses runtime requirements; full-sized temporary copies are created and removed.
.\.venv\Scripts\python.exe scripts/benchmark_databases.py
```

This creates a new `docs/benchmarks/<run_id>/report.json` and raw plans without
overwriting earlier runs. It changes indexes only on its owned copies. Ordinary
exceptions run cleanup in `finally`. A forced process kill or power loss may leave
a `bench_<uuid>` namespace: inspect it against that run's report before removing
anything; the script never deletes other runs' namespaces. Avoid imports or other
database writes during measurement. A source-count change makes the run fail its
invariance check rather than silently claiming an isolated result.

```powershell
# Optional tools for figures, installed into the project's virtual environment.
.\.venv\Scripts\python.exe -m pip install -r requirements-evaluation.txt
# Replace <run_id> with the new directory printed by the benchmark command.
.\.venv\Scripts\python.exe scripts/plot_benchmarks.py docs/benchmarks/<run_id>/report.json
# Add/check the paging index on an existing installation; no import or reset.
.\.venv\Scripts\python.exe scripts/setup_complaint_order_index.py
```

The last helper writes separate dated `docs/index_improvements/<run_id>/` evidence.
On an installation where the index already exists, before/after naturally both
use it; `index_existed_before` records this. It does not remove the index to recreate
an artificial live baseline. Figure generation refuses to overwrite prior figures.
The benchmark runner needs trusted local setup credentials for its temporary DDL;
the web application's restricted SQL roles are unchanged. Timing values will vary.
