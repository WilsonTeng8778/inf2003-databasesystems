# Repository organization and verification

**Date:** 30 October 2026, Asia/Kuala_Lumpur.\
**Current stage:** 9, documentation and delivery.\
**Branch:** `milestone/recallscope-core-complete-2026-10-30`.

This work improves navigation before writing the report. Core application/database
files retain their contents; no feature, schema, dataset snapshot or main-branch
integration was introduced.

## What changed

- The root README is a short starting point. Detailed commands, API contracts and
  verification instructions are consolidated in [TECHNICAL_REFERENCE.md](../../TECHNICAL_REFERENCE.md).
- [The documentation index](../../README.md) separates current references from
  historical evidence; [CODE_MAP.md](../../CODE_MAP.md) explains the files by feature/task.
- Fourteen foundation/backend/browser narrative reports moved to
  [milestones/](../../milestones/README.md). Their original dates, claims and
  stage descriptions remain historical. Relative links were rebased.
- Five shared Python helpers moved to `scripts/support/`; seven Node/browser
  verification files moved to `scripts/browser/`. Imports, test patches and the
  browser launch path were updated. The 34 runnable top-level Python command
  names remain available.
- Package export now selects the newest successful rehearsal whose recorded
  source matches the current files. Explicit `--rehearsal` still works. New tests
  reject stale explicit evidence and skip unsuccessful/mismatched automatic candidates.

See [moves.json](moves.json) for all 26 moves and before/after hashes.
Machine-readable historical reports, screenshots, plans and logs retain their
original paths and bytes. **22 empty generated browser-run directories were
removed**, using exact-path and empty-directory-only checks. The
[preservation checks](preservation_checks.json) confirm all 71 core files, 278
prior machine-evidence files and the milestone narrative bodies were retained.

## Fresh verification

The [new integrated rehearsal](../../rehearsals/20261030T193432-6d737593/report.json)
passed on **30 October, 19:34–19:36 Kuala Lumpur time**:

| Area | Result |
| --- | --- |
| Automated suite | **212 tests passed**, including two additional package-evidence selection cases. |
| Analyst cases | **98 recorded HTTP checks and 9 assertions**, concurrent flows, terminal client and owned API-server recreation recovery. |
| Fleets/orders | **110 recorded HTTP checks, 6 concurrent requests and 9 assertions**, plus terminal flow. |
| Account database guards | **29 checks passed**. |
| Account SQL-backed HTTP | **23 checks passed**. |
| Admin import helper | **32 checks passed** on owned isolated fixtures; no full real-source import. |
| Browser | **238 checks passed**, zero uncaught browser exceptions; moved driver/modules loaded successfully. |
| Saved performance evidence | **20 saved plans validated; four current result fingerprints matched**. Timings remain the original 29 October measurements. |

The case request count can vary with scheduling: a concurrent note operation may
need one additional recorded retry. This run needed none; the earlier 99-check
run did. Both completed the same concurrency assertions and checked final content.

The rehearsal fingerprints **138 implementation/test/configuration files** and
confirmed tested source, original record counts, private configuration, raw
archives and historical evidence were retained. Child reports supply detailed
fixtures/cleanup/results. The separate [automated log](automated_tests.json)
also passed before the integrated run; it is not added to the run's test count.

## Package and remaining work

The normal package command can export this reorganized version against the new
matching rehearsal. Each completed export has its own manifest and sibling
`package_report.json` under ignored `data/processed/packages/`. Earlier review
ZIPs keep their original layout/hash as dated snapshots; use the refreshed export
for the current file layout.

This is existing-machine technical verification. Teammate installation from the
chosen ZIP/manual, report, slides/video, human rehearsal and final submission
checks remain pending. Branch history and GitHub `main` were not changed by this
organization work. Check the living guide for current progress.
