# Draft
S-01: Export downloads CSV with name,status columns.
S-02: That same action must return JSON instead of CSV.
S-03: Send daily export emails to the administrator.
S-04: Existing export_projects is a streaming generator. Source: src/export.py, export_projects.
S-05: Existing export_projects returns a list. Source: src/export.py, export_projects.
CUJ: UI sends GET /export; controller queries DB; serializer writes data; HTTP 200 is returned.
