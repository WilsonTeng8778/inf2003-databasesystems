# RecallScope — Vehicle Safety Research and Recall Tracking

RecallScope combines NHTSA recalls and investigations in PostgreSQL with consumer
complaints and analyst case content in MongoDB. Flask provides vehicle research,
saved vehicles, analyst cases, fleets and recall work orders.

`main` contains the submission implementation. Start with the user manual below.

## Install and run

Follow [USER_MANUAL.md](USER_MANUAL.md) for first installation, configuration,
database imports, account setup, normal use and troubleshooting. The application
uses native PostgreSQL/MongoDB services, Python and local browser assets; Docker
and a frontend build are not required.

On an existing configured installation, start both database services, then run:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend:create_app run --host 127.0.0.1 --port 5000
```

Open http://127.0.0.1:5000/. Stopping Flask retains database records. Normal startup
does not require another setup or import.

## Source layout

| Location | Purpose |
| --- | --- |
| `backend/` | Flask routes, services, HTML templates and local browser assets. |
| `etl/` | Source reading, cleanup and repeatable imports. |
| `sql/` | Tables, migrations, views, indexes, triggers and guarded operations. |
| `mongodb/` | Document validation and indexes. |
| `scripts/` | Setup, imports, command-line clients, verification and packaging. |
| `tests/` | Automated checks for transformations, permissions and workflows. |
| `data/source_profile.json` | Approved source fingerprints, file layouts and counts; required by imports. |
| `data/dictionaries/` | NHTSA field guides. |
| `project_config.py` | Shared configuration loaded from local `.env`. |

Git excludes the four raw source ZIPs. The source/data/manual distribution includes
them under `data/raw/`; use that package for the approved dataset version.

The former workspace implementation is preserved in branch
`backup/main-before-recallscope-2026-11-02-afcaaaf`. Its case schema and MongoDB
documents differ from this version. Switching Git branches does not migrate
databases; see the manual before reusing an installation from that version.

## Optional verification and package checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/safety_profile.py --make HONDA --model CIVIC --year 2022
```

The automated suite uses synthetic inputs. Native/API/browser verifiers use real
local services and temporary test records; see the manual before running them.
Generated reports and screenshots go under ignored `local/docs/`.

`scripts/package_project.py` builds a source/data/manual ZIP after a matching
technical verification run. Its `--verify` option checks an existing ZIP using
Python's standard library. Package contents exclude `local/`, planning/progress
notes, report drafts, screenshots, credentials and installed libraries.

Complaint counts describe reports rather than confirmed defects. Recall matches
are by make/model/year and do not establish VIN-specific applicability or repair.
