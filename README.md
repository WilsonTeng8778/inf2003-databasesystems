# RecallScope - INF2003 Group 19

Vehicle Safety Recall & Defect Investigation System using PostgreSQL, MongoDB and
Flask. It combines NHTSA research with analyst cases and small personal fleet/recall
work orders. Development uses native Windows services; Docker is not required.

**Primary working branch:** `milestone/recallscope-core-complete-2026-10-30`.
Continue this version independently of GitHub `main`.

## Start here

| What you need | Document |
| --- | --- |
| Current stage and beginner explanation | [PROJECT_GUIDE.md](PROJECT_GUIDE.md) |
| First installation, daily use and troubleshooting | [USER_MANUAL.md](USER_MANUAL.md) |
| Where a feature/file is implemented | [Code map](docs/CODE_MAP.md) |
| Detailed commands, API contracts and verification | [Technical reference](docs/TECHNICAL_REFERENCE.md) |
| Design, report preparation, milestones and evidence | [Documentation index](docs/README.md) |

## What should I run now?

On the already configured computer, ensure both database services are running,
then start Flask from the repository root:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend:create_app run --host 127.0.0.1 --port 5000
```

Open [RecallScope](http://127.0.0.1:5000/). Keep the terminal running; Ctrl+C stops
Flask while database records persist. Restart your older Flask process after code
updates. Ordinary startup does not require a repeat setup/import.

For a new computer, follow [the complete first-install sequence](USER_MANUAL.md#2-first-installation-on-another-windows-computer).
A GitHub checkout excludes the four raw ZIPs; the source/data/manual package
includes the approved snapshot and dictionaries. Each PowerShell line is a separate
command. Use your application email/password to sign in; database credentials are
configured locally in ignored `.env`.

## What each command does

Use the [command table](docs/TECHNICAL_REFERENCE.md#what-each-command-does) to check
whether a command reads data, performs writes or creates verification fixtures.
The [code map](docs/CODE_MAP.md#runnable-python-commands) groups the commands by task.
Top-level setup, import, demo, verification and packaging command names are retained.
Shared Python helpers now live under `scripts/support/`; browser checks live under
`scripts/browser/` and run through `scripts/verify_frontend.py`.

Common optional read/test commands:

```powershell
.\.venv\Scripts\python.exe scripts/check_environment.py
.\.venv\Scripts\python.exe scripts/safety_profile.py --make HONDA --model CIVIC --year 2022
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The profile reads both databases. The automated suite uses fake/synthetic inputs;
real native/API/browser verification has separate commands and dated evidence.

## Project layout

```text
backend/              Flask routes, services, HTML templates and local assets
etl/                  Source parsing, transformations and import orchestration
sql/                  PostgreSQL definitions and ordered migrations
mongodb/              MongoDB validators/indexes
tests/                Automated feature and integrity checks
scripts/              Runnable local commands
  support/            Shared command clients and verification fixtures
  browser/            Node/Chromium verification modules
docs/                 Current references and original machine evidence
  milestones/         Historical foundation/backend/browser narratives
  organization/       File-move map and reorganization checks
data/dictionaries/    Official column dictionaries
data/raw/             Approved raw ZIPs (local, Git-ignored)
project_config.py     Shared database configuration
```

The [code map](docs/CODE_MAP.md) explains the responsibilities of the individual
files. Related routes/services/templates remain separate because they perform
different jobs; their feature mapping is documented in one place.

## Status and delivery

The agreed core functionality has dated technical acceptance evidence. We remain
in **Stage 9: document and deliver**. See the [living guide](PROJECT_GUIDE.md),
[requirements review](docs/FINAL_READINESS_REVIEW.md),
[technical acceptance](docs/TECHNICAL_REHEARSAL.md),
[performance evaluation](docs/PERFORMANCE_EVALUATION.md) and
[original milestone index](docs/milestones/README.md).

The manual and checked source/data review package are prepared. Teammate fresh
installation, report/slides/video, timed team rehearsal and final submission checks
remain pending. The file-organization checks are recorded separately under
`docs/organization/`; old results keep their original dates.

To build a fresh review package after source changes have passed the technical
rehearsal, run `scripts/package_project.py`. It selects successful evidence whose
recorded implementation matches the current source; `--rehearsal` can select an
explicit matching report. See [package preparation](docs/SUBMISSION_PACKAGE.md).

Keep `.env`, installed environments, raw/package ZIPs and live database storage
out of Git. Complaint counts are allegations, and recall matches are model-level,
not VIN-specific applicability or proof of repair.
