# RecallScope core implementation GitHub checkpoint

**Date:** 30 October 2026, Asia/Kuala_Lumpur.\
**Branch:** `milestone/recallscope-core-complete-2026-10-30`\
**Commit title:** `feat: complete RecallScope workflows and prepare project delivery`

This checkpoint collects the current agreed core implementation, browser assets,
SQL migrations, ETL/admin helper, verification tools, tests, dated evidence and
delivery documentation. The project remains in Stage 9: teammate fresh installation,
report/slides/video, human rehearsal and final submission checks are pending.

## Why a separate branch

The local work started from `10adb9e5ec642bbe943227a8553bb666a6d3289e`.
A read of GitHub on 30 October found `main` already at
`afcaaafe115b58e78fb0aeda404fe124d27e0a28`, with six newer commits containing
another implementation of cases, fleets, a browser workspace and case-sync
migrations. Several paths overlap this checkout and their contents differ.

The named milestone branch preserves the verified local version and the existing
remote history as separate lines of development. It does not merge the two
implementations or replace GitHub `main`. Future integration needs deliberate
review of routes, schema/migrations, permissions, UI and tests, followed by fresh
verification; the saved local acceptance results do not establish that a combined
version works. Teammates reviewing this implementation should select this branch.

## Verification supporting this checkpoint

- [210 automated tests](packaging/20261030T043036Z-manual-package/automated_tests.json)
  passed on 30 October, including eight package-tool tests.
- The earlier [integrated technical rehearsal](TECHNICAL_REHEARSAL.md) passed
  202 automated tests, 238 browser checks and the selected native case/fleet/
  account/import checks on 30 October. Its original reports retain their dates.
- The [source/data package check](packaging/20261030T043036Z-manual-package/artifact_checks.json)
  verified 452 included files, four approved raw sources and 286 archived local
  links. All 135 earlier tested implementation files remained identical; package
  tooling/tests were additional files.

Publishing this checkpoint does not rerun those application checks. Earlier reports
record their then-current Git HEAD and working-tree manifests; they remain
historical evidence rather than being relabelled with this new commit.

## What goes to GitHub

Source, tests, manual, three dataset dictionaries, source profiles and saved
documentation/evidence are included. `.env`, installed libraries, the raw dataset
ZIPs, generated source/data package ZIPs, staging/browser/log directories and live
database storage remain excluded. Configuration templates have empty password/key
fields. Upload checks compare candidate files with configured private values of
at least 12 characters; this is an exact-match safeguard, not a general secret audit.

The four raw archives are still required for fresh setup. Use the separately
checked source/data/manual ZIP, or obtain the exact approved snapshot described in
the [manual](../USER_MANUAL.md); a branch checkout alone omits `data/raw/`.
The source/data ZIP is a dated review snapshot created before this GitHub note,
and retains its own manifest/hash. Creating this checkpoint does not replace that
archive, publish a website, or complete the outer submission package.

After pushing, verify the branch's remote commit ID matches local HEAD. The GitHub
branch/commit URL reported in chat identifies the uploaded checkpoint; this document
does not invent a self-referential commit hash before the commit exists.
