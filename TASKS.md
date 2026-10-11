# Task split

Three branches, three owners. Finish your own list, open a pull request into `main`, and be ready to explain your part in the demonstration.

Sam and Jackson go first. JP's visit and gate records point at their models, so those two models need to be on `main` before the foreign keys are added.

## Sam — `accounts`

Branch: `Sam`

| # | Task | Done when |
| --- | --- | --- |
| 1 | `CampusMember` model | Fields: `campus_id` (unique), `member_type` (student or staff), `full_name`, `email`, `is_active`, optional `department`. Migration is applied. |
| 2 | Django admin | A superuser can add, search, and deactivate members. |
| 3 | Sample records | A few synthetic students and staff exist. Do not import real personal data. |
| 4 | `/verify/` | A form accepts a campus ID, checks the active record, and shows verified or rejected. Unknown and inactive IDs fail validation. |
| 5 | Roles | Groups for Security officer and Administrator. Only those users can open `/dashboard/`. |
| 6 | Login | `/login/` works for staff. Visitors are not asked to create an account. |

## Jackson — `campus`

Branch: `Jackson`

| # | Task | Done when |
| --- | --- | --- |
| 1 | `Building` and `Office` models | An office belongs to one building. Office stores floor, room number, written directions, and `is_active`. |
| 2 | Django admin | Both models are registered and editable. |
| 3 | Sample directory | Several buildings and offices are loaded. Label them as sample data until the real AUCA directory is confirmed. |
| 4 | Office CRUD | Staff can list, create, update, and delete offices. Delete asks for confirmation. The form rejects a missing name, building, or floor. |
| 5 | Public directory | Active offices can be listed and selected. Inactive offices stay hidden. |
| 6 | Directions | Choosing an office shows its building, floor, room, and directions. |

## JP — `gatepass` and `dashboard`

Branch: `JP`

Start the visitor form now. Add the `Office` and `CampusMember` foreign keys after those models are on `main`.

| # | Task | Done when |
| --- | --- | --- |
| 1 | `VisitorVisit` | Stores the visitor, purpose, destination, host, status, `created_at`, and `valid_until`. Status is pending, approved, rejected, checked in, or completed. |
| 2 | Reference number | Generated on save, unique, and not the database id. |
| 3 | `/visitor/register/` | Required fields are validated. A complete form creates a pending visit and shows the reference number. |
| 4 | Pass and directions | `/visitor/pass/<reference>/` shows status. The directions page shows the office location from Jackson's model. |
| 5 | `GateEvent` | Entry or exit, time, officer, and accepted or rejected. Exactly one of campus member or visit is set. Model validation enforces that. |
| 6 | Approval and gate | An officer can approve or reject. Rejected and expired visits cannot be checked in. Entry and exit each save a gate event. |
| 7 | AdminLTE dashboard | `/dashboard/` shows totals calculated from the database: visitors today, pending, entries today, active offices. |
| 8 | Lists | Searchable visitor list, visit detail, and gate log. |

## Everyone

| Task | Done when |
| --- | --- |
| Pull `main` before you start | Your branch contains the latest shared code. |
| Screenshots | Your pull request shows the page you built. |
| ER diagram | Building → Office → VisitorVisit, and CampusMember → GateEvent, with the cardinalities labeled. One diagram for the group. |
| Report | Each person writes the section for their app. |
| Demonstration | You can explain your models, views, and validation without reading from the screen. |

## Order

1. Sam: tasks 1–3. Jackson: tasks 1–3. Merge both into `main`.
2. JP: tasks 1–4, then link the office and the campus member.
3. Sam: tasks 4–6. Jackson: tasks 4–6. JP: tasks 5–8.
4. Together: ER diagram, report, and a full walkthrough of student, staff, and visitor entry.
