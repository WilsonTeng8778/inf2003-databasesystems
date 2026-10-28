# INF2003 Group 19 — Implementation Greenlight

**Project:** Vehicle Safety Recall & Defect Investigation System  
**Status:** APPROVED TO BEGIN IMPLEMENTATION  
**Date:** 24 October 2026

## 1. Purpose

This document resolves the outstanding alignment questions in `PROJECT_UNDERSTANDING_AND_PLAN.md` and authorizes Codex to begin implementation.

Use the project materials in this order of authority:

1. Official INF2003 project description and FAQ.
2. Submitted Group 19 proposal.
3. This final scope/greenlight document.
4. Vehicle Safety blueprint and Codex implementation plan for lower-level implementation guidance.

Do not silently expand the project beyond this approved scope.

## 2. Final Product

The application is a desktop-first responsive web application integrating official NHTSA:

- vehicle recalls;
- consumer complaints;
- official defect investigations.

It has three functional areas:

```text
Vehicle Safety Recall & Defect Investigation System
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
   Vehicle Safety    Analyst Defect   Fleet Recall
      Research       Investigation      Tracking
       (CORE)           (CORE)        (SECONDARY)
```

The project is not a general fleet-management or workshop-management system.

## 3. Final Fleet / Work-Order Decision

**KEEP the fleet/work-order functionality, but keep it deliberately small.**

The submitted proposal included fleet/workshop users, fleets, fleet vehicles, and work orders. The later blueprint removed them to prevent scope creep. The final decision is to retain only the minimum fleet functionality needed to honour the submitted proposal and demonstrate useful relational CRUD/workflow.

Implement only:

```text
FLEET
  |
  +-- FLEET_VEHICLE
           |
           +-- RECALL MATCH
                    |
                    +-- WORK_ORDER
```

A fleet user can:

1. Create a fleet.
2. Add/remove fleet vehicles.
3. See whether a vehicle's normalized make/model/year matches recall records.
4. Create a recall work order.
5. Update the work-order status.

Recommended work-order statuses:

```text
OPEN
IN_PROGRESS
COMPLETED
CANCELLED
```

Do not implement mechanics, workshop bookings, parts inventory, invoices, repair costs, customer management, general maintenance scheduling, telematics, route planning, or unrelated fleet features.

## 4. Core Workflow: Vehicle Safety Research

A normal user searches by:

```text
Model Year
Make
Model
```

PostgreSQL returns:

- normalized vehicle identity;
- official recall campaigns;
- official NHTSA defect investigations;
- saved-vehicle information.

MongoDB returns:

- consumer complaints;
- complaint narratives;
- component breakdowns;
- crash/fire/injury attributes;
- complaint aggregations.

The combined safety profile must clearly distinguish:

```text
Consumer Complaint != Confirmed Defect != Official Recall
```

Do not infer that a vehicle is unsafe solely from complaint counts.

## 5. Core Workflow: Analyst Defect Investigation

Analysts investigate patterns in imported complaint data:

```text
Explore complaints
    ->
Filter/search
    ->
Identify relevant complaints
    ->
Create Internal Analysis Case
    ->
Link complaints
    ->
Add findings / notes / tags
    ->
Update case status
    ->
Close case
```

Internal application cases must be clearly separated from **Official NHTSA Investigations**.

The analyst is an application role and does not represent NHTSA.

## 6. User Roles

### NORMAL_USER

Can:

- search vehicles;
- view recalls;
- explore complaints;
- view official investigations;
- save/remove personal vehicles;
- manage their own small fleet/recall work orders if the ownership model allows it.

### ANALYST

Can:

- perform research functions;
- create internal analysis cases;
- link/unlink complaints;
- add/edit/delete findings and notes;
- manage tags;
- change case priority/status;
- close cases.

### ADMIN

Can:

- manage users/roles;
- inspect dataset/import status;
- perform or initiate imports;
- inspect import logs.

Keep authorization simple and testable.

## 7. Final Database Responsibility Split

### PostgreSQL

Expected logical entities:

```text
MANUFACTURER
VEHICLE_MAKE
VEHICLE_MODEL
MODEL_YEAR

RECALL
RECALL_VEHICLE

OFFICIAL_INVESTIGATION
INVESTIGATION_VEHICLE

APP_USER
SAVED_VEHICLE

ANALYSIS_CASE
CASE_STATUS_HISTORY

FLEET
FLEET_VEHICLE
WORK_ORDER

DATA_IMPORT_LOG
```

The exact physical schema must be finalized after inspecting the real source files.

### MongoDB

Collections:

```text
complaints
case_details
```

`complaints` contains imported NHTSA consumer complaint documents.

`case_details` contains flexible application-owned analyst content such as:

```text
linkedComplaints[]
suspectedComponents[]
findings[]
notes[]
tags[]
```

PostgreSQL owns structured case workflow. MongoDB owns flexible case content.

## 8. Vehicle Identity Decision

Do not assume manufacturer and vehicle make are identical.

Use a logical hierarchy similar to:

```text
MANUFACTURER
     |
     v
VEHICLE_MAKE
     |
     v
VEHICLE_MODEL
     |
     v
MODEL_YEAR
```

The final design must be based on the actual NHTSA source layouts.

Document normalization/mapping rules.

## 9. Canonical Vehicle Catalogue

Do not create the SQL vehicle catalogue only from recall records.

Build normalized vehicle identities using relevant identities from:

```text
Recall data
    +
Investigation data
    +
Complaint data
    |
    v
Normalize / deduplicate
    |
    v
Canonical Make / Model / Model-Year
```

Complaint-only vehicles must not disappear merely because they have no recall.

## 10. Approved Datasets

Official source directory:

https://www.nhtsa.gov/nhtsa-datasets-and-apis

### Recalls — PostgreSQL

`FLAT_RCL_POST_2010.zip`

https://static.nhtsa.gov/odi/ffdd/rcl/FLAT_RCL_POST_2010.zip

### Consumer Complaints — MongoDB

`COMPLAINTS_RECEIVED_2020-2024.zip`

https://static.nhtsa.gov/odi/ffdd/cmpl/COMPLAINTS_RECEIVED_2020-2024.zip

`COMPLAINTS_RECEIVED_2025-2026.zip`

https://static.nhtsa.gov/odi/ffdd/cmpl/COMPLAINTS_RECEIVED_2025-2026.zip

### Official Defect Investigations — PostgreSQL

`FLAT_INV.zip`

https://static.nhtsa.gov/odi/ffdd/inv/FLAT_INV.zip

## 11. Mandatory First Technical Step

Before finalizing DDL, MongoDB validation, ETL mappings, or API assumptions:

1. Download the selected source files.
2. Inspect actual filenames and extracted formats.
3. Record headers, delimiter, encoding, row grain, null conventions, date formats, identifiers, duplicate behavior, and representative samples.
4. Determine whether one complaint/campaign/investigation spans multiple rows.
5. Inspect actual manufacturer/make/model representations.
6. Define normalization rules.
7. Define stable import/upsert keys.
8. Choose a manageable but sufficient import scope.

Blueprint schemas are logical guidance, not verified raw-file layouts.

## 12. ETL Requirements

Create reproducible scripts such as:

```text
etl/
  import_recalls.py
  import_investigations.py
  import_complaints.py
  common.py
```

ETL should:

```text
Extract
 -> Parse
 -> Clean
 -> Normalize
 -> Validate
 -> Deduplicate/Upsert
 -> Load
 -> Log
```

Track records read, inserted, updated, skipped/rejected, errors, timing, and source dataset.

Repeated imports should be safe.

Do not import unnecessary personal/contact information.

## 13. CRUD Requirements

Both databases must demonstrate meaningful CRUD.

### PostgreSQL

Demonstrate CRUD through:

- saved vehicles;
- structured analysis cases;
- fleets;
- fleet vehicles;
- recall work orders.

Official NHTSA reference records should normally remain read-only.

### MongoDB

Use `case_details` for application-owned CRUD:

- create case detail document;
- read case details;
- link/unlink complaints;
- add/edit/delete findings;
- add/edit/delete notes;
- add/remove tags;
- delete test/erroneous case detail when appropriate.

Imported complaints are reference data and should not be modified merely to demonstrate CRUD.

## 14. Cross-Database Case Consistency

Use:

```text
PostgreSQL ANALYSIS_CASE.case_id
          |
          v
MongoDB case_details.caseId
```

Uniquely index `caseId` in MongoDB.

PostgreSQL transactions cannot automatically roll back MongoDB writes. Use a documented application-level strategy.

For creation:

```text
1. Validate request.
2. Create SQL analysis case.
3. Obtain case_id.
4. Create MongoDB case_details.
5. If MongoDB fails, roll back/remove/mark the SQL case appropriately.
6. Log the failure.
```

No distributed transaction system is required.

## 15. Advanced PostgreSQL Requirements

Use meaningful:

- joins;
- aggregates;
- subqueries;
- views;
- constraints;
- transactions;
- indexes;
- at least one useful trigger.

CTEs and window functions may be added where useful.

A good trigger candidate is case-status history.

## 16. Advanced MongoDB Requirements

Demonstrate:

- nested queries;
- array queries;
- text search;
- aggregation pipelines;
- justified indexes;
- compound indexes based on measured query patterns.

Useful queries include complaints by vehicle/component/time and narrative search.

## 17. Performance Evaluation

Performance evaluation remains part of the implementation because it was promised in the submitted proposal.

### PostgreSQL

Compare the same representative query before and after indexing.

Use, where appropriate:

```sql
EXPLAIN (ANALYZE, BUFFERS)
```

Record dataset size, query, index definition, query plan, repeated timings, and relevant rows examined/returned.

### MongoDB

Compare the same complaint query before and after indexing.

Use:

```javascript
explain("executionStats")
```

Record collection size, query, index definition, execution time, documents examined, and documents returned.

Do not use unrelated workloads to claim one DBMS is inherently faster.

## 18. GUI Decision

Build a **desktop-first responsive web GUI**.

Recommended:

- HTML/CSS;
- Bootstrap;
- JavaScript;
- Chart.js;
- Python Flask backend.

The GUI exists to demonstrate database functionality. Do not prioritize visual polish over a working database core.

Core pages:

```text
Login / Register
Dashboard
Vehicle Search
Vehicle Safety Profile
Recall Details
Complaint Explorer
Official Investigation Details
My Saved Vehicles
Analysis Cases
Analysis Case Workspace
Analytics
```

Secondary fleet pages:

```text
Fleet Vehicles
Fleet Recall Matches
Work Orders
```

Minimal admin pages:

```text
Users / Roles
Dataset Status
Import Logs
```

## 19. Development Order

### Stage 0 — Inventory Existing Work

Before rebuilding anything:

- inspect repository contents;
- identify teammate work;
- identify branches/files/databases already created;
- integrate usable work.

### Stage 1 — Inspect Raw Data

Download and inspect actual NHTSA files.

### Stage 2 — Freeze Physical Data Models

Finalize ERD, constraints, MongoDB documents, normalization, and shared identifiers.

### Stage 3 — Construct Databases

Create PostgreSQL schema and MongoDB collections/indexes.

### Stage 4 — ETL

Build repeatable imports and logs.

### Stage 5 — Database-Only Verification

Before substantial GUI work, prove:

```text
Search vehicle
 -> SQL recalls
 + SQL official investigations
 + MongoDB complaints
```

Also prove saved-vehicle CRUD, analysis-case CRUD, MongoDB case CRUD, and minimal fleet/work-order CRUD.

### Stage 6 — Backend Integration

Build Flask services/routes/authentication.

### Stage 7 — Minimal GUI

Connect verified functions to the UI.

### Stage 8 — Advanced Database Features

Finish advanced SQL, MongoDB aggregation/text search, triggers, views, and indexes.

### Stage 9 — Analytics and Benchmarks

Produce reproducible evidence.

### Stage 10 — Validation and Documentation

Prepare report evidence, ERD, architecture, benchmark results, screenshots, README, user manual, and demo flow.

## 20. Priority If Time Is Limited

```text
1. Correct real-data import
2. PostgreSQL design
3. MongoDB design
4. CRUD in both DBs
5. Combined vehicle search/profile
6. Analyst-case workflow
7. Minimal fleet recall/work-order workflow
8. Advanced SQL/NoSQL
9. Performance evaluation
10. Functional GUI
11. UI polish
12. Stretch features
```

## 21. Stretch Features

Only after the approved project works:

- Technical Service Bulletins;
- complaint trend detection;
- materialized views;
- saved searches;
- notifications;
- additional analytics.

Do not add ML defect prediction, AI chatbot, safety scoring, general workshop management, or general fleet management.

## 22. INF2003 Coverage

### Task A

Vehicle Safety Recall & Defect Investigation System using SQL + NoSQL.

### Task B

Real NHTSA recalls, complaints, and investigations. Clearly label synthetic/demo users, cases, fleets, and work orders.

### Task C

Relational ERD, constraints, MongoDB document model, architecture, and design justification.

### Task D

SQL CRUD, MongoDB CRUD, search, joins, aggregations, workflows, indexes, and GUI.

### Task E

Performance evaluation, SQL-vs-NoSQL tradeoffs, ETL/data-quality issues, scalability, reliability, security, limitations, and future improvements.

## 23. Evidence to Preserve

Preserve throughout development:

- source filenames/versions;
- record counts;
- ETL logs;
- rejected-data examples;
- normalization rules;
- ERD revisions;
- MongoDB examples;
- SQL queries;
- MongoDB pipelines;
- index definitions;
- EXPLAIN/executionStats output;
- benchmark results;
- screenshots;
- tests;
- authorization tests;
- setup instructions.

## 24. Main Demo Story

The finished system should support this coherent demo:

```text
1. Login as normal user.
2. Search year/make/model.
3. Show combined SQL + MongoDB safety profile.
4. View recalls.
5. Explore/filter complaints.
6. Show complaint aggregation.
7. View official investigation.
8. Save vehicle.
9. Login as analyst.
10. Create internal analysis case.
11. Link complaints.
12. Add finding/note.
13. Change case status.
14. Briefly show fleet vehicle -> recall match -> work order.
15. Show advanced SQL feature.
16. Show advanced MongoDB feature.
17. Show before/after indexing benchmark.
```

## 25. Final Scope

### CORE

```text
Vehicle Safety Research
+
Consumer Complaint Exploration
+
Analyst Defect Investigation Cases
```

### SECONDARY — retained from submitted proposal

```text
Small Fleet Recall Tracking
+
Recall Work Orders
```

### NOT IN SCOPE

```text
General fleet management
Workshop management
Repair scheduling
Parts/inventory
Invoices
AI chatbot
ML defect prediction
Vehicle safety score
Used-car recommendation
```

## 26. Answers to Codex's Alignment Questions

### Q1 — Fleet/work orders?

**Retain a minimal fleet recall/work-order module. Do not expand it into general fleet/workshop management.**

### Q2 — Existing Week 5–8 implementation?

Unknown from the original ChatGPT conversation. Inventory repository/team work before rebuilding.

### Q3 — Split analyst-case architecture intentional?

**Yes.** PostgreSQL owns structured workflow; MongoDB owns flexible case content. Handle partial failures explicitly.

### Q4 — Raw datasets fully inspected already?

**No confirmed field-by-field inspection has been completed in the original conversation.** Inspect real files before freezing physical schemas.

### Q5 — Database-first plan approved?

**Yes.** Prioritize database correctness, real data, CRUD, integration, advanced DB features, and evaluation before frontend polish.

## 27. Greenlight

**Codex is authorized to begin implementation.**

Immediate actions:

1. Inventory existing repository/team work.
2. Download and inspect the approved NHTSA datasets.
3. Report any source-data facts that materially contradict the logical model.
4. Finalize ERD and MongoDB schemas from actual data.
5. Begin database construction and ETL.
6. Verify core queries before substantial GUI development.
7. Continue through the approved implementation plan.

Codex may make ordinary low-level implementation decisions without asking for approval each time, provided they do not materially change:

- application purpose;
- selected NHTSA datasets;
- PostgreSQL/MongoDB responsibility split;
- three user roles;
- analyst-case workflow;
- minimal fleet recall/work-order module;
- INF2003 assessment coverage.

If actual source data makes an approved design impossible or substantially inappropriate, document the issue and propose the smallest justified adjustment instead of silently changing scope.

## 28. Source of Truth Going Forward

For implementation scope, this document records the final alignment decision:

> **Build a hybrid PostgreSQL + MongoDB vehicle-safety application integrating NHTSA recalls, complaints, and official defect investigations. Vehicle research and analyst investigation cases are the core. Retain a deliberately small fleet recall/work-order module to honour the submitted proposal.**

**Implementation is greenlit.**
