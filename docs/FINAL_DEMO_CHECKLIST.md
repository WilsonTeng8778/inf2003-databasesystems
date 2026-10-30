# Final demonstration and rehearsal checklist

**Updated:** 30 October 2026. **Status:** Automated technical rehearsal passed;
timed five-member presentation and fresh-package installation remain pending.

The [integrated technical rehearsal](TECHNICAL_REHEARSAL.md) passed **202 automated
tests, 238 browser checks and all selected native case/fleet/account/import checks**
on 30 October. Its [dated evidence index](rehearsals/20261030T040558-cfe0d503/report.json)
records the tested working files, archive fingerprints and cleanup. The checklist
below distinguishes those software results from the team's remaining presentation
and delivery checks. The existing-machine run does not prove the final package
works on another computer.

## Technical preparation and remaining delivery checks

- [x] Include [account deletion](ACCOUNT_DELETION.md) and
  [admin local imports](ADMIN_IMPORT.md) in the integrated technical run.
- [x] Record the tested working-tree manifest and source archive fingerprints.
  Git HEAD alone does not identify the modified/untracked implementation.
- [x] Use owned temporary accounts/fixtures; keep credentials out of evidence;
  remove the fixtures and confirm original record counts/import history.
- [x] Exercise both existing native databases through owned Flask servers.
  No full source import was needed for this rehearsal.
- [x] Record dated technical outcomes and the environment; review representative
  desktop/mobile screenshots. See the linked evidence index.
- [x] Prepare the [user manual](../USER_MANUAL.md) and [locally checked source/data review candidate](SUBMISSION_PACKAGE.md).
- [ ] Freeze the final candidate after reproduction and all relevant content changes.
- [ ] Have a teammate follow the completed manual on a fresh setup using the
  [installation checklist](FRESH_SETUP_CHECKLIST.md) and the chosen ZIP hash.
- [ ] Assign actual speakers and record a timed five-member presentation rehearsal.
  Prepare only owned demo accounts/records and keep credentials out of the video.

## Complete journeys to check

| Journey | Actions | Expected database/result evidence | Technical result / remaining check |
| --- | --- | --- | --- |
| Public research | Search 2022 HONDA CIVIC; open profile, recall/investigation relationships and a complaint's full details/provenance. | Canonical SQL identity, separate official records and MongoDB complaints. The inspected snapshot has four recalls, two investigations and 885 complaints for this vehicle; qualify dates/coverage. | Passed, automated technical run |
| Complaint exploration/analytics | Filter STEERING, an incident attribute and receipt dates; try narrative search. Open the component/monthly charts and drill through to matching reports. | Array/nested/text queries; stable pagination; aggregation counts agree with the same filter scope. Explain allegations, overlapping components and partial/unknown dates. | Passed, automated technical run |
| Personal SQL CRUD | As NORMAL_USER create/read/rename/remove a saved vehicle; reload and sign out/in to check persistence. Try a second user's record through the permitted test harness. | Owner-scoped SQL CRUD; duplicates and cross-owner changes rejected. Public reference data remains unchanged. | Passed, automated technical run |
| Fleet/order SQL CRUD | Create an owned fleet and labelled Civic entry; match a recall, create an order, change status/notes and complete it. Delete rehearsal-owned records. | Applicable recall FK, timestamps, transaction/cascade behaviour and owner boundary. Model-level matches do not prove a VIN's repair status. | Passed, automated technical run |
| Analyst SQL + MongoDB CRUD | As ANALYST create a case, link/unlink a complaint, add/edit/remove a finding and note, set tags/components, change status/close and inspect history; delete the fixture case. | SQL metadata/history and MongoDB content use the same case identity; note authorship is server-owned; deletion removes MongoDB content once its projection is applied, or remains visibly pending for recovery. Do not edit official complaints to demonstrate CRUD. | Passed, automated technical run |
| Role and owner boundaries | Confirm normal-user denial of case/admin screens, analyst ownership limits, admin case oversight and strict personal save/fleet boundaries. | Denials occur in the API as well as the interface; admin does not inherit another user's personal fleet/save ownership. | Passed, automated technical run |
| Admin monitoring/role management | Read dataset/import history and change a rehearsal account's role. Check the next request reflects the role change. | Narrow read projections, role checks, no raw credentials/diagnostics; retain at least one administrator. Native checks cover the last-admin guard. | Passed, automated technical run |
| G1 account deletion | Use the verified deletion flow on an eligible rehearsal-owned account; check denied/protected/conflicting cases under the documented policy. | Fresh 29-check native, 23-check HTTP and cumulative browser evidence in the integrated report. G1 remains closed. | Passed, automated technical run |
| G2 import initiation | Demonstrate the verified local ADMIN helper and source/IMPORT confirmation; show dated success/failure audit evidence. Cancel the confirmation if a real-data refresh is not intended. | Fresh 32-check native auth/CLI/ETL run on isolated fixtures; browser instructions inspected. G2 remains closed; no full real-source refresh was performed. | Passed, automated technical run |
| Failure recovery | Run the established owned verifier's controlled case pending/retry/lost-response journeys and inspect receipts/results. | Fresh case evidence confirms no duplicate note/case from retry and recovery after an owned API server/app instance was recreated. Shared DB services remained running. | Passed, automated technical run |
| Performance explanation | Open saved SQL plans and MongoDB plans/figures; explain the same-query before/after comparison and the new pagination index. | Twenty saved plans validated and four current result fingerprints matched. Timings remain dated 29 October; no cross-DB speed ranking from different queries. | Evidence revalidated; human explanation pending |
| Fixture cleanup | Remove only owned demo fixtures, recheck saved baseline counts and confirm both databases remain usable. | Original counts/import history retained; prior evidence preserved in the dated technical run. | Passed, automated technical run |
| Fresh-package reproduction | Follow the final manual from the chosen source/data package on a teammate's clean setup. | Record the actual machine, inputs, steps and outcome separately. | Pending |

All technical passes above refer to the linked 30 October integrated run. They
do not mark any speaker's live demonstration or the team recording complete.

## Arrange the video in the required order

D1 p. 3 specifies **background/datasets → relational implementation/demo → NoSQL
implementation/demo → optional performance**. The normal application can mix DBs;
the presentation should still make each DBMS's contribution easy to identify.

One possible budget is below. These are anonymous speaker slots, not assignments
or claims of contribution. The team must add the actual names and agree coverage.

| Time | Speaker slot | Content |
| --- | --- | --- |
| 0:00–1:10 | Member 1 | Problem, three data types, scope and architecture. |
| 1:10–3:10 | Member 2 | SQL ERD/relationships, vehicle/official-record query and personal CRUD. |
| 3:10–5:00 | Member 3 | SQL fleet/work-order integrity, transactions and case-status trigger/history. |
| 5:00–7:10 | Member 4 | MongoDB document model, complaint queries/text search and case-content CRUD. |
| 7:10–9:20 | Member 5 | MongoDB aggregation/index reasoning, SQL/NoSQL tradeoffs and controlled performance results. |
| 9:20–9:45 | Any agreed speaker | Limits and improvements, with a small buffer below 10 minutes. |

Every member must speak and show their name on screen/slides. Rehearse at normal
speed; this budget is not proof of the recorded MP4's duration. Keep necessary
database design and manipulation visible rather than spending most time navigating
menus. Presenters should explain the actual code/queries they show.

## Evidence saved and still required

The [technical report](rehearsals/20261030T040558-cfe0d503/report.json) records fresh
journey outcomes, cleanup, environment and source/data fingerprints. Representative
screenshots and their review are linked in [TECHNICAL_REHEARSAL.md](TECHNICAL_REHEARSAL.md).
Older milestone JSON remains intact.

Still save the timed human rehearsal, teammate's manual-driven installation and
final artifact checks: report page count/template, slide format, MP4 duration/
speakers/order, ZIP contents and marker access. None of those human/delivery checks
was completed by the automated technical run or by updating this checklist.
