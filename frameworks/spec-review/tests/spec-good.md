# Draft
Export visible active projects as CSV with name,status columns. If no active projects
are visible, download a CSV with headers only. No email or scheduled exports.
The current export_projects returns a list, as shown in
[export_projects, lines 1–2](src/export.py#L1-L2), at the same frozen source snapshot supplied with this draft.

## Key user scenario
A project manager needs a local copy of visible active projects. Starting on Projects
with filters applied, the user selects Export. The browser downloads a CSV. The user
opens it and sees name,status and only visible active projects. With no matching projects,
the same action downloads a file with name,status headers and no rows. Opening the saved
file confirms the result. No additional screen or notification is required.
