# Documentation index

**Updated:** 30 October 2026. Start with the document for the task you are doing.
The project remains in Stage 9, documentation and delivery, on our milestone branch.

| I want to... | Read this |
| --- | --- |
| Understand the project and current progress | [Project guide](../PROJECT_GUIDE.md) |
| Install, start or use the application | [User manual](../USER_MANUAL.md) |
| Find the file implementing a feature | [Code map](CODE_MAP.md) |
| Find exact commands, API contracts or verification options | [Technical reference](TECHNICAL_REFERENCE.md) |
| Understand tables, relationships, MongoDB models and recovery | [Database design](DATABASE_DESIGN.md) |
| Inspect data directly in pgAdmin/Compass | [Database inspection walkthrough](INSPECTING_DATABASES.md) |
| Understand the datasets and cleaning decisions | [Source inspection](DATA_INSPECTION.md) and [machine-readable profile](data_profile.json) |
| Check the agreed scope | [Implementation alignment](IMPLEMENTATION_GREENLIGHT.md) |
| Prepare the final report or check requirements | [Readiness review](FINAL_READINESS_REVIEW.md) |
| Prepare/rehearse the five-member presentation | [Demo checklist](FINAL_DEMO_CHECKLIST.md) |
| Hand the project to a teammate | [Fresh-setup checklist](FRESH_SETUP_CHECKLIST.md) |
| Export source, data and manual | [Submission package instructions](SUBMISSION_PACKAGE.md) |
| Review the latest full technical acceptance run | [Post-organization verification](organization/20261030T112848Z-e139090e/README.md) |
| Understand the original integrated acceptance method/results | [Technical rehearsal](TECHNICAL_REHEARSAL.md) |
| Explain query performance in the report | [Performance evaluation](PERFORMANCE_EVALUATION.md) |
| Understand guarded account deletion or local imports | [Account deletion](ACCOUNT_DELETION.md) / [Admin import](ADMIN_IMPORT.md) |
| Find the published source checkpoint | [GitHub checkpoint](GITHUB_CHECKPOINT_2026-10-30.md) |

## Historical milestones and evidence

The [milestone index](milestones/README.md) groups the database foundation, seven
backend steps and six browser steps. These describe the project **at their original
dates**. Their stage labels, counts and limitations remain historical; use the
project guide/manual for today's position and commands.

Machine-readable verification reports, dated run folders and screenshots keep
their existing paths and bytes. They support report claims and reproduce a result's
scope; they are not application source or ordinary startup inputs.

| Evidence location | Purpose |
| --- | --- |
| `*_verification_report.json`, `verification_report.json` | Original database/API/browser milestone results. |
| `account_deletion/`, `admin_import/` | Later account/import checks and owned-fixture cleanup evidence. |
| `benchmarks/`, `index_improvements/` | Raw plans, timings, figures and separate live index checks. |
| `rehearsals/` | Dated integrated technical runs and source manifests. |
| `packaging/` | Source/data export and integrity checks. |
| `readiness/` | Original requirements/source review and its checks. |
| `organization/` | File-move map and checks for this organization work. |
| `screenshots/` | Earlier browser milestone captures. |

The evidence is retained for the report rather than deleted as clutter. Folder
grouping and this index separate it from the documents you need for everyday work.
