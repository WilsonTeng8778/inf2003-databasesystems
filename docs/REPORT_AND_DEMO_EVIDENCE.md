# Report and presentation evidence guide

This is a preparation guide, not the final report, slides or five-member video.
Confirm current XSite instructions and have the team review every claim.

## Evidence-backed project story

The application brings three types of vehicle evidence together: official recall
campaigns, official investigations and consumer complaints. A person researches a
make/model/year; an analyst can link complaints to an internal case and record
findings; a fleet owner can track a model-level recall match through a work order.
The interface separates the three evidence types and explains that complaints are
allegations and a model-level match is not a VIN-specific determination.

PostgreSQL stores the catalogue, official records, users, saved vehicles, case
status, fleets and work orders. MongoDB stores nested complaint documents and
flexible case details. Explain the SQL keys, constraints, joins, views and case
status trigger alongside MongoDB validation, arrays, text search, aggregation and
indexes. Explain that the SQL outbox makes case-document creation/deletion
retryable; it does not make the databases share one atomic transaction.

## Suggested report structure

The supplied brief specifies up to 10 main-content pages in Calibri 12, excluding
the cover, references and appendix. A possible allocation is:

1. **Problem and users** (1 page): purpose, three roles, source-data limitations.
2. **Data and preparation** (1–2 pages): sources, snapshot dates, field grain,
   complaint component merging, normalization, record counts and provenance.
3. **Database design** (2 pages): ERD and relationship examples; MongoDB document
   models; justify the split and the shared model-year and case identifiers.
4. **Implementation and demonstration** (2–3 pages): research, analyst case,
   fleet work order, roles/ownership, error handling and case synchronization.
5. **Evaluation and reflection** (2 pages): tests, indexed queries, measured
   results, limitations, problems encountered and feasible improvements.

Use the actual ERD in [DATABASE_DESIGN.md](DATABASE_DESIGN.md), the updated
[source profile](data_profile_2026-10-28.json), and the
[implementation/evidence map](IMPLEMENTATION_AND_EVIDENCE.md). Show screenshots
and query outputs captured from the team's own final environment.

## Current measured data and performance

The 28 October isolated import contained 53,560 vehicle identities, 13,607 recall
campaigns, 3,629 investigations and 429,582 complaint documents. For a 2022 Honda
Civic, the research API and independent database queries both returned 4 recalls,
2 investigations and 885 complaints. These counts describe the downloaded
snapshot and are recorded in [real-data verification](real_data_verification_2026-10-28.json).

One local index experiment used PostgreSQL 18.6 and MongoDB 6.0.13 on Windows,
one warm-up and five timed runs per phase. The samples were ordered, not random.

| Query and sample | Median before index | Median after index | Same result count? |
| --- | ---: | ---: | --- |
| PostgreSQL: model-year recall lookup; 93,797 copied rows | 3.249 ms | 0.090 ms | Yes, 42 rows |
| MongoDB: model-year complaint lookup; 100,000 copied documents | 64.869 ms | 1.697 ms | Yes, 500 documents |

The MongoDB plan examined 100,000 documents before the index and zero documents
plus 500 index keys afterward for this covered query. PostgreSQL's plan changed
to an index scan. These short, single-machine timings are illustrative and may
vary on a teammate's machine. The SQL and MongoDB queries use different datasets
and workloads; do not use the table to claim that one DBMS is generally faster.
The [raw benchmark JSON](benchmark_2026-10-28.json) contains plans and timings.

Real source data was used for research verification and the benchmark. In an
isolated test database, a synthetic case was linked to a real public complaint
and a synthetic fleet work order to a real recall; generated workflow records
were removed afterward. Broader CRUD, authorization and simulated outage recovery
were checked with synthetic records. The browser walkthrough also used labelled
synthetic records. Keep those verification boundaries clear in the report.

## Suggested demonstration sequence

The brief asks for the order: background and data, relational implementation,
NoSQL implementation and comparison, with performance analysis optional. Keep
the recording at normal speed under 10 minutes and show each member's name.

| Speaker slot | Suggested part | Example time |
| --- | --- | ---: |
| 1 | Problem, users, datasets and source limitations | 1:30 |
| 2 | PostgreSQL ERD, constraints, views and saved/fleet workflow | 2:00 |
| 3 | MongoDB complaint model, filtering, aggregation and case details | 2:00 |
| 4 | Integrated complaint-to-case journey and synchronization recovery | 2:00 |
| 5 | Database trade-offs, measured index example, limitations and conclusion | 1:30 |

The slots are suggestions, not assignments to named members. Rehearse using the
actual final environment, verify that each speaker can explain their work, and
record the team's own demonstration. Do not substitute synthetic screenshots or
this guide for an actual five-member presentation.
