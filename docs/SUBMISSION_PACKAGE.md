# Source/data/manual package preparation

**Updated:** 30 October 2026. **Stage:** 9, document and deliver, in progress.

The package builder is [package_project.py](../scripts/package_project.py).
The [user manual](../USER_MANUAL.md) brings first installation, daily startup,
research, normal/analyst/admin tasks and troubleshooting into one document.
The [fresh-setup checklist](FRESH_SETUP_CHECKLIST.md) is ready for a teammate;
its installation and human checks remain pending.

## Build and verify

From the repository root:

```powershell
.\.venv\Scripts\python.exe scripts/package_project.py
```

This reads current working files and the approved local archives. It neither
connects to a database nor imports/resets data. It writes a new UTC-stamped folder
under `data/processed/packages/`, containing:

- `INF2003_Group19_Source_Data.zip` — the review candidate.
- `package_report.json` — verified member count, ZIP hash/size, approved-archive
  result and comparison to the earlier technical rehearsal.

The completed ZIP has one `INF2003_Group19/` project folder and an internal
`PACKAGE_MANIFEST.json`. It includes code/templates/local assets, SQL migrations,
ETL, requirements, tests, configuration template, manual, project documentation/
saved evidence, three dictionaries and the four exact raw source archives.
Installed libraries, `.env`, Git internals, staging/log/browser profiles and live
database dumps/storage are excluded. Uncommitted source is included: the export
does not assume GitHub already contains all working files.

The builder selects the newest successful rehearsal whose recorded implementation
files match the current source, including legitimate file moves/refactors. It
checks file hashes, rather than trusting the newest date. An explicit matching
report can be selected with `--rehearsal`. New source files are listed separately.
If no evidence matches, it refuses the export until the changed version has a
successful rehearsal. Earlier [technical results](TECHNICAL_REHEARSAL.md) retain
their original counts/dates; documentation may evolve after those milestones.

Reopen/read verification checks every member hash, exact membership, required
files, blank credential fields in `.env.example`, approved raw archive hashes
and the archived rehearsal comparison. A filename collision or content mismatch
is rejected. Source changes during assembly are detected by archive hash checks;
keep the workspace idle while exporting. Failed/interrupted `.partial` outputs
are not completed packages. Existing exports/reports are retained.

To check an existing completed ZIP without databases or installed app packages:

```powershell
python scripts/package_project.py --verify 'C:\path\to\INF2003_Group19_Source_Data.zip'
```

Verification streams the ZIP without extracting it. The internal hashes detect
accidental corruption against its manifest; they are not a digital signature or
proof of an untrusted publisher's identity. Building from a configured checkout
also scans included bytes for its private password/key values of at least 12
characters. Ordinary short words are excluded from that substring scan. No secret
values are written into the manifest/report.

Raw ZIPs total **137,707,247 bytes (131.3 MiB)** before adding code/evidence.
The exact output size/hash is in that run's report. Raw archives remain stored
without another compression pass; saved documentation/assets are compressed.
The output directory is already Git-ignored through `data/processed/`. These
archives are not pushed or uploaded by building them.

## What verification establishes

| Check | Scope |
| --- | --- |
| Package-tool automated tests | Missing data/dictionaries, private-file exclusion, changed source/snapshot, accidental secret, corrupt/extra members and existing-output protection. |
| Actual local ZIP verification | Exact exported bytes/membership/hash consistency, approved four sources and retained technical implementation files. |
| Fresh installation | **Pending.** A teammate must extract/install/import/run the chosen ZIP using the manual and record actual results. |
| Team presentation | **Pending.** Agree speakers, rehearse at normal speed and check the ten-minute limit/order/names. |
| Final outer submission | **Pending.** Report, slides, MP4 and source ZIP must be assembled/checked after current XSite rules are confirmed. |

The source/data/manual ZIP is a review candidate. It does not contain a final
report PDF, slides or video unless those are separately prepared later; the builder
does not create the outer submission ZIP. Preserve dated test evidence and the
chosen candidate's report, and rebuild after relevant source/manual/data changes.
Before final submission, complete the [readiness review](FINAL_READINESS_REVIEW.md)
and [demo checklist](FINAL_DEMO_CHECKLIST.md). Do not treat packaging as publication
or successful fresh-machine reproduction.
