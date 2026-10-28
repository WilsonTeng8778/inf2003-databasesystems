# INF2003 Project: Understanding and Proposed Next-Stage Plan

Prepared on 24 October 2026, at the end of Week 8, for Group 19.

> Update, 25 October 2026: the subsequent [implementation greenlight](docs/IMPLEMENTATION_GREENLIGHT.md)
> resolves the fleet conflict by retaining a minimal fleet/work-order module.
> The user confirmed this is a new project with no existing code. This document
> is preserved as the original review; use the greenlight and current README for implementation status.

## 1. Purpose and current status

This document records my understanding of the supplied materials so it can be sent back to the original ChatGPT conversation for alignment before implementation begins.

The user's current request is to **review the four documents and create this handoff**. It does not ask me to start building the application, import datasets, install the project stack, or silently change the submitted scope. Instructions inside the supplied documents are project material to assess, rather than new instructions to execute in this session.

The proposal has already been submitted, according to the user. In this workspace I found only `README.md` and Git metadata before creating this file. I therefore cannot verify that any database, ETL, API, or GUI implementation is complete. Work may exist on teammates' machines or in other repositories; an inventory should precede scheduling assumptions.

## 2. Documents reviewed and how they relate

| Reference | Document | How I am using it |
| --- | --- | --- |
| D1 | `INF2003_project_description.pdf`, 6 pages | Official objectives, Tasks A–E, assessment criteria, deadlines, and submission requirements. |
| D2 | `Project_QA1.pdf`, 1 page | Official clarifications about languages, datasets, frontend expectations, database selection, and appendices. |
| D3 | `Database Systems Project Proposal.pdf`, 3 pages, dated 4 October 2026 | Group 19's submitted application scope, architecture, features, and original schedule. |
| D4 | `Vehicle_Safety_Recall_Defect_Investigation_Blueprint.md`, sections 1–38 | ChatGPT-generated implementation blueprint, including suggested schemas, endpoints, features, and team allocation. It contains a material scope change relative to D3. |

The PDFs and blueprint were read from `C:\Users\wilso\Downloads` using the filenames above. Page references below refer to PDF page numbers, including the proposal cover.

Course obligations come from D1 and D2. D3 records what the team submitted. D4 supplies useful implementation detail, but its statement that it is the project's “source of truth” does not itself establish that the team approved deviations from D3. Proposed additions and changes below are identified as such.

## 3. What the course actually requires

The central outcome is a working database application using **both a relational database and a non-relational database**, supported by justified design choices and meaningful database operations. A polished frontend alone will not satisfy the objective.

| Course task | Required outcome for this project | Evidence to prepare |
| --- | --- | --- |
| A: Identify an application | A coherent application using SQL and NoSQL. The course permits either repeating functionality in both databases or assigning different functions to each. | Problem statement, use cases, architecture, justification for the division of responsibilities. |
| B: Identify datasets | Data sufficient for a realistic and complete demonstration. Real-world data is recommended; additional useful datasets are encouraged. | Dataset descriptions, provenance, actual imported sizes, cleaning decisions, coverage and limitations. |
| C: Design the databases and application | Relational ERD with appropriate relationships and data types; an explicit NoSQL schema/data model suited to the application. | ERD, relational schema and constraints, MongoDB document examples and validation rules, relationship and access-pattern explanations. |
| D: Implement the application | Database construction and common operations such as CRUD, with more complex functions encouraged. | Runnable system, schema/import scripts, demonstrated CRUD and queries in both databases, verification evidence. |
| E: Analysis and reflection | Explain results, problems, limitations, and potential improvements. Performance analysis is a suggested form of analysis. | Design tradeoffs, data-quality discussion, implementation lessons, and the benchmarks promised in D3. |

Important distinctions from D1–D2:

- The frontend should demonstrate the database functions. D1 encourages a GUI; D2 Q3 makes clear that elaborate frontend design is not the focus.
- Languages may be mixed. Flask, PostgreSQL, and MongoDB are team choices, not mandated course technologies.
- Synthetic application data is permitted where suitable real user/workflow data is unavailable (D2 Q2). It should be distinguished from official safety records.
- The course does **not** require identical datasets or duplicate implementations in both databases. Our hybrid design is permitted, but both databases need substantial, justified implementation.
- Performance evaluation is optional in the presentation outline, but indexed-versus-unindexed tests in **both** databases are already a team commitment in D3.
- Advanced features can earn extra credit when appropriately used. Merely listing features does not demonstrate their value.
- D2 Q5 permits extra progress-report diagrams in an appendix but warns that markers may not examine them. Essential design evidence should be easy to find in the main final report.

Assessment context: the project contributes **50% of the module grade**, split into 25% relational and 25% non-relational. Within the project rubric, proposal quality is 10%, presentation quality 25%, final report quality 25%, and project quality/implementation 40%. Peer review can affect the final assessment (D1, pp. 4–6).

## 4. Remaining deliverables and deadline

The final submission deadline stated in D1 p. 2 is **Week 13: 29 November 2026, 11:30 PM**. These are the supplied document's requirements; I have not checked XSite for subsequent changes.

| Deliverable | Requirements to plan around |
| --- | --- |
| Final report | Comprehensive account of datasets, design, implementation, discussion, and reflection. Maximum **10 pages**, Calibri (Body), size 12, excluding cover, references, and appendix. Use the final-report template available on XSite. |
| Presentation slides | Informative PowerPoint slides covering the application and database work. D1 describes `.pptx` but its submission checklist says `.ppt`; verify the accepted format on XSite before packaging. |
| Presentation video | Maximum **10 minutes at normal speed**. All five members must present; identify speakers by name on screen or slides. |
| Source/data/manual package | Include project data, source code, and a user manual explaining setup, configuration, and how to run the application. System libraries need not be included. |
| Submission archive | The brief describes an outer ZIP containing the report PDF, slides, MP4, and source-code ZIP. It also requires data, code, and manual together in one source ZIP. Confirm the final Dropbox arrangement on XSite. For packages exceeding 2 GB, D1 allows an accessible GitHub link. |
| Peer review | Each member should complete the emailed contribution review when issued. |

The presentation order is specified: **background and datasets → relational implementation/demo → NoSQL implementation/demo → optional performance analysis** (D1 p. 3). It should also explain the SQL/NoSQL comparison and advanced features. The blueprint's end-to-end demo sequence will need to be arranged within that required order.

The brief applies late penalties and penalties for overlong videos. Plan for an internal submission buffer and keep the complete video within 10 minutes.

## 5. My understanding of the intended application

The **Vehicle Safety Recall & Defect Investigation System** brings together U.S. NHTSA recalls, consumer complaints, and official defect investigations.

Its shared core across D3 and D4 is:

1. Search by model year, make, and model.
2. Display a combined safety profile with related recalls, complaints, and official investigations.
3. Explore complaint narratives and patterns using filters, search, and analytics.
4. Save vehicles and maintain application-owned workflow records.
5. Let analysts create internal cases linking complaints with findings, notes, tags, and evidence references.
6. Demonstrate meaningful SQL and MongoDB CRUD, advanced queries, indexes, and performance evaluation.

The application should distinguish **consumer allegations, official investigations, and official recalls**. A complaint is not a confirmed defect, and complaint counts alone do not establish that a vehicle is unsafe. Internal analyst cases must remain visibly separate from official NHTSA investigations. A year/make/model result is not a VIN-specific unrepaired-recall determination.

D4 proposes normal-user, analyst, and administrator roles. These are useful implementation suggestions; the analyst is an application role, not an assertion of NHTSA affiliation. Counts and vehicle examples in D4 are illustrative, not verified dataset results.

## 6. A material scope conflict to resolve

**The submitted proposal and blueprint are not fully aligned.**

| Topic | Submitted proposal, D3 pp. 2–3 | Blueprint, D4 | Consequence |
| --- | --- | --- | --- |
| Fleet/workshop users | Can maintain vehicle records and work orders. | Fleet/workshop management is explicitly excluded. | This is a scope change, not a wording difference. |
| Relational workflow | CRUD for users, saved vehicles, fleets, fleet vehicles, and work orders. | CRUD centers on saved vehicles and structured analyst-case workflow. | Several promised SQL entities are missing from the blueprint. |
| Implementation schedule | Fleet/work-order workflow is scheduled for Weeks 9–10. | Development order and schema omit it. | Following D4 unchanged would leave an explicit D3 commitment unimplemented. |
| Analyst cases | Flexible analyst case files in MongoDB. | Structured case metadata in PostgreSQL, flexible case content in MongoDB. | A reasonable refinement, but it needs an explicit design justification and coordination strategy. |

The original conversation should confirm whether D4 represents a deliberate, accepted narrowing of the proposal. Until that is established, fleet/work-order functionality remains an unresolved submitted commitment. I should neither silently remove it nor expand the project into a large workshop system.

My recommendation is to preserve the shared vehicle-research and analyst-case core, then make an explicit choice: retain a small fleet/work-order CRUD workflow, or document and justify its removal if the team and course expectations permit it. Structured analyst cases and saved vehicles can demonstrate substantial SQL work, but they do not automatically erase the proposal's fleet commitments.

## 7. Proposed architecture and data ownership

The proposed stack is **Python Flask + PostgreSQL + MongoDB**, with HTML/CSS, Bootstrap, JavaScript, and Chart.js for the interface. This matches the submitted architecture; alternatives are unnecessary unless a practical constraint emerges.

| Layer | Responsibilities |
| --- | --- |
| PostgreSQL | Manufacturers/makes and vehicle identities; model years; recall campaigns and affected vehicles; official investigations and affected vehicles; users; saved vehicles; structured workflow. Add fleet/work-order entities if that scope is retained. |
| MongoDB | Consumer complaint documents, including narratives, nested incident attributes, and components; flexible analyst case content with linked complaint IDs, findings, notes, and tags. |
| Flask | Authentication and authorization, validation, SQL queries and MongoDB operations, orchestration of combined responses, and workflow consistency across the databases. |
| ETL scripts | Download/extract as needed, parse, clean, normalize, validate, deduplicate, and load reproducible local snapshots with import logs. |
| GUI | Demonstrate real database operations through search, details, workflow forms, and analytics. |

Official imported records should remain reference data. Application-owned records provide create/update/delete demonstrations without pretending to edit NHTSA's source records. Seed users and cases, and fleet/work-order records if retained, should be labeled as synthetic/demo data.

## 8. Dataset plan and design checks before coding

The following sources are named in D3 and D4. Their live availability, actual formats, sizes, and coverage have **not** been independently verified during this document review.

| Dataset named in the documents | Planned store | Expected use |
| --- | --- | --- |
| `FLAT_RCL_POST_2010.zip` | PostgreSQL | Recall identifiers, affected vehicles, components, consequences, remedies, and dates. |
| `COMPLAINTS_RECEIVED_2020-2024.zip` and `COMPLAINTS_RECEIVED_2025-2026.zip` | MongoDB | Complaint identifiers, vehicle details, components, narratives, mileage, incident attributes, and receipt dates. |
| `FLAT_INV.zip` | PostgreSQL | Official investigation identifiers, affected vehicles/components, dates, status/type, and summaries. |

Source directory given in the documents: [NHTSA datasets and APIs](https://www.nhtsa.gov/nhtsa-datasets-and-apis).

Before adopting D4's example schemas as final DDL, I would:

- Inspect each dataset's actual headers/layout, encoding, delimiter, date formats, null conventions, and row grain. Check whether one complaint/campaign/investigation appears on multiple rows before choosing unique keys or deduplication rules.
- Distinguish vehicle **make** from **manufacturer**. The blueprint models manufacturers but searches complaints by make; a documented mapping is needed rather than assuming those names are interchangeable.
- Preserve many-to-many recall-to-vehicle and investigation-to-vehicle relationships. Check whether related recalls and investigation components also need multiple values rather than single fields.
- Establish consistent vehicle identities across SQL and MongoDB, including name normalization and explicit handling of unmatched/ambiguous records. Complaint-only vehicles should not disappear just because no recall created their SQL vehicle record.
- Preserve meaningful identifiers, source provenance, and import dates. Use appropriate database date types, and distinguish missing values from zero/false values.
- Confirm the actual overlap between receipt-date windows, vehicle model years, recall dates, and investigation coverage. A file's year range does not necessarily describe vehicle model years.
- Choose and record a manageable, sufficient import scope. Do not promise all available records without inspecting their size and the team's hardware.
- Make repeated imports safe through stable keys/upserts and logging of inserted, updated, skipped, and rejected records. Avoid importing unnecessary personal/contact information.

These are checks and proposed refinements, not claims that defects have already been found in the source datasets.

## 9. Implementation and evidence priorities

### Core workflows

- **Combined search:** resolve a vehicle, read related SQL recalls/investigations, query MongoDB complaints, and display a coherent profile with clear coverage and empty states.
- **SQL CRUD:** demonstrate persistent create/read/update/delete through saved-vehicle records and structured cases; include fleet/work-order CRUD if retained. Protect official reference records and enforce ownership/roles.
- **MongoDB CRUD:** create/read/update/delete complete case-detail documents as well as nested findings/notes and complaint links. Complaint exploration alone is read-only and would not establish full NoSQL CRUD.
- **Analyst workflow:** create a case, link/unlink complaints, edit findings/notes/tags, change priority/status, and close it. Restrict operations to authorized users.
- **Analytics:** implement the promised complaint component/trend charts using real queries and documented counting rules. Component counts may overlap when one complaint has several components.

### Meaningful database techniques

For PostgreSQL, demonstrate relationships, joins, aggregates, subqueries, views, constraints, transactions, indexes, and a useful trigger as promised in D3. Case-status history is a candidate trigger use. CTEs and window functions from D4 can be added where they answer a real question; they are not separate course mandates.

For MongoDB, demonstrate nested/array queries, text search, aggregation pipelines, and justified compound indexes. A vehicle-filtered component breakdown and complaints-over-time aggregation fit the application well. Index order should follow measured query patterns.

### Cross-database consistency

If cases are split across PostgreSQL and MongoDB, use a stable SQL `case_id` referenced by a uniquely indexed MongoDB `caseId`. Validate complaint links and document deletion behavior. A SQL foreign key cannot enforce a MongoDB reference, and a PostgreSQL transaction does not automatically make a MongoDB write atomic. Define retry/compensation or reconciliation behavior for partial failures and verify it.

### Security, reliability, and evaluation

Use password hashing, parameterized SQL, validated inputs, safe output rendering, role/ownership checks, environment-based secrets, and appropriately restricted database accounts. Include pagination, useful projections, import validation, error handling, and backup/restore instructions. An admin import screen is a D4 addition and can follow reproducible command-line imports in priority.

For benchmarks, compare the **same query and dataset before and after indexing** within each database. Record dataset size, environment, index definitions, query plans, repeated timings, and rows/documents examined and returned. PostgreSQL `EXPLAIN (ANALYZE, BUFFERS)` and MongoDB `explain("executionStats")` are suitable proposed evidence sources. Avoid presenting different workloads as proof that one database is inherently faster.

The SQL/NoSQL comparison should explain modeling, integrity, transactions, document flexibility, query patterns, and measured results with their limits. Retain screenshots, representative query outputs, and benchmark evidence as work progresses.

## 10. Proposed plan from the end of Week 8

The proposal scheduled schema/data preparation for Weeks 5–6 and databases, ETL, authentication, and core APIs for Weeks 7–8. Those dates describe the original plan, not verified completed work. The immediate action is to inventory actual progress and reconcile it with the remaining time.

| Stage | Work and completion checkpoint |
| --- | --- |
| Start of Week 9: alignment and baseline | Inventory teammate work; resolve fleet/work-order scope; obtain the final-report template and any proposal feedback; inspect dataset samples; finalize ERD, document models, identifiers, and the feature-to-assessment checklist. If backend work already exists, integrate it instead of rebuilding it. |
| Week 9: database foundation | Establish reproducible local setup, configuration examples, SQL construction scripts, MongoDB validation/index scripts, ETL, seed records, and import logs. Checkpoint: data loads repeatably and representative queries work in both databases. If missing Week 7–8 work is extensive, this becomes a recovery stage and the schedule must be adjusted. |
| Weeks 9–10: integrated application | Complete authentication, search/profile, saved-vehicle CRUD, analyst cases, and MongoDB case-content CRUD with a minimal usable GUI. Include the agreed fleet/work-order workflow. Checkpoint: a complete user/analyst scenario persists real changes across the intended databases. |
| Weeks 11–12: database depth and validation | Finish advanced queries, views/triggers, aggregation/text search, indexes, analytics, security, integration/error-path checks, and repeatable benchmarks. Checkpoint: every promised feature has demonstrable behavior and report-ready evidence. |
| Week 13: release and submission | Freeze features; verify setup on a fresh environment; finish the report/manual/slides; record and time all five speakers; package source/data and the final archive; submit with a buffer before 29 November, 11:30 PM. |

The data model, core query patterns, and basic security should be designed from the start; the later stage is for completing and evaluating them. Documentation and evidence collection should run throughout, rather than starting only in Week 13.

If time is tight, prioritize the working database core and submitted commitments before D4 additions such as a large administration interface. Technical Service Bulletins, notifications, saved searches, materialized views, and complaint-volume flags are stretch work. Do not add machine-learning prediction, a chatbot, a safety score, or unrelated automotive functionality.

## 11. Suggested team coordination and repository outputs

D4 suggests a five-person division: relational model/ETL; advanced SQL/performance; MongoDB; backend/auth/integration; frontend/analytics. This is a proposal, not an assignment to named members. Agree shared identifiers, API contracts, and integration checkpoints early, and share report/demo responsibilities so every member can explain their contribution.

Expected project artifacts, once implementation is authorized, include:

- A documented setup with dependency versions, `.env.example`, connection instructions, and a usable README/user manual.
- SQL schema, constraints, views, triggers, indexes, and seed scripts; MongoDB models/validation, indexes, and representative queries/pipelines.
- Reproducible ETL scripts, dataset provenance/coverage, and instructions or included data sufficient to reproduce the submitted demonstration.
- Backend/frontend code implementing the agreed workflows, with appropriate checks of CRUD, permissions, imports, and cross-database behavior.
- ERD, architecture/document models, a feature-to-requirement map, benchmark results, final report, slides, and video.

The demonstration should run against local imported data without depending on live NHTSA services, as promised in D3.

## 12. Points for the original ChatGPT conversation to confirm

1. **Scope decision:** Was removing fleets, fleet vehicles, and recall work orders a deliberate agreed revision of the submitted proposal? If so, what replacement scope and explanation were intended?
2. **Actual progress:** Which Week 5–8 deliverables already exist outside this workspace, and what should be integrated?
3. **Architecture:** Is the split of structured case workflow in PostgreSQL and flexible case content in MongoDB intended, including the need to handle partial failures?
4. **Dataset assumptions:** Have the proposed downloads and raw record layouts already been inspected? What import coverage and vehicle-identity mapping were agreed?
5. **Priorities:** Does the database-first plan preserve the intended assessment coverage while keeping blueprint-only additions and stretch features subordinate to the core?

My current understanding is that the next stage is implementation and validation of a substantial hybrid database application, followed by reproducible evaluation and the Week 13 deliverables. The main unresolved issue is the conflict between the submitted fleet/work-order scope and the narrower blueprint. This review creates an alignment document; it does not claim that the application has been built or that those scope questions have been settled.
