import csv
from pathlib import Path
from collections import Counter

p = Path(r"C:\GitRepo\ml\qa\mlab_e2e_execution_sheet.csv")
rows = list(csv.DictReader(p.open(encoding="utf-8")))
fields = rows[0].keys()

updates = {
    "APP-001": ("Pass", "EV-20260911-APP-CTRL", "Appointment date control loaded and editable.", "Date input visible on New Appointment form."),
    "APP-002": ("Pass", "EV-20260911-APP-CTRL", "Patient lookup dropdown loaded with selectable records (e.g., DEMO).", "Listbox rendered with patient rows."),
    "APP-003": ("Pass", "EV-20260911-APP-CTRL", "Doctor lookup dropdown loaded with selectable records (e.g., A . KUSHWAHA).", "Doctor listbox rendered."),
    "APP-004": ("Pass", "EV-20260911-APP-CTRL", "Time slot input accepted value 11:30.", "Time input editable."),
    "APP-005": ("Blocked", "BLK-APP-STATUS-001", "Status control not independently exposed in current New Appointment UI.", "Could not validate status transition from form."),
    "APP-006": ("Blocked", "BLK-APP-LINK-001", "Linked lab entry field/control not independently exposed in current form.", "Mapping appears backend-driven."),
    "APP-007": ("Fail", "BUG-APP-SAVE-001", "Appointment save did not persist row after selecting patient/doctor/company and clicking Save.", "Grid remained 'No appointments found'."),

    "MACC-001": ("Pass", "EV-20260911-ACC-001", "New account code generated and visible in search result as QAC001.", "Company account created successfully."),
    "MACC-002": ("Pass", "EV-20260911-ACC-001", "Account name saved: QA COMPANY 0911.", "Search returns created account."),
    "MACC-003": ("Pass", "EV-20260911-ACC-001", "Account group selected as Current Assets and saved.", "Persisted with created account."),
    "MACC-004": ("Pass", "EV-20260911-ACC-001", "Contact/phone information accepted in entry form.", "Phone saved and searchable."),
    "MACC-005": ("Pass", "EV-20260911-ACC-001", "Mobile number saved (9876510911).", "Value persisted."),
    "MACC-006": ("Pass", "EV-20260911-ACC-001", "Email saved (qa.company0911@mlab.local).", "Value accepted without validation error."),
    "MACC-007": ("Pass", "EV-20260911-ACC-001", "Address and city saved (Ranchi).", "Record searchable with location."),
    "MACC-008": ("Blocked", "BLK-ACC-ACTIVE-001", "Active toggle not distinctly exposed during this account workflow.", "No explicit active toggle control found in form."),
    "MACC-009": ("Pass", "EV-20260911-ACC-001", "Account save action completed and customers count incremented (9 -> 10).", "Creation confirmed by list/search."),

    "RT-001": ("Pass", "EV-20260911-RATE-001", "Company account QA COMPANY 0911 selected for rate override.", "Company chip displayed in Add New Rate form."),
    "RT-002": ("Pass", "EV-20260911-RATE-001", "Test QAAU001 selected for rate mapping.", "Test chip displayed in Add New Rate form."),
    "RT-003": ("Pass", "EV-20260911-RATE-001", "Rate 275 entered and saved.", "Grid shows ₹275.00 for QAAU001 corporate rate."),
    "RT-004": ("Blocked", "BLK-RATE-DATE-001", "Effective date controls were not set explicitly in this quick create flow.", "Needs dedicated date-effective scenario."),
    "RT-005": ("Pass", "EV-20260911-RATE-001", "Create Rate action succeeded.", "Coverage moved to 1788/1788 and active/client counters incremented."),

    "RP-001": ("Blocked", "BLK-RPT-META-001", "Report category selector opened but no selectable metadata options were exposed.", "Cannot execute category scenario without report definitions."),
    "RP-002": ("Blocked", "BLK-RPT-META-001", "Date filter controls not rendered before report selection.", "Dependent on report metadata."),
    "RP-003": ("Blocked", "BLK-RPT-META-001", "Doctor filter controls not rendered before report selection.", "Dependent on report metadata."),
    "RP-004": ("Blocked", "BLK-RPT-META-001", "Test filter controls not rendered before report selection.", "Dependent on report metadata."),
    "RP-005": ("Blocked", "BLK-RPT-META-001", "Preview action unavailable without selected report.", "No report instance loaded."),
    "RP-006": ("Blocked", "BLK-RPT-META-001", "Export PDF unavailable without selected report.", "No report instance loaded."),
    "RP-007": ("Blocked", "BLK-RPT-META-001", "Export Excel unavailable without selected report.", "No report instance loaded."),

    "SYS-001": ("Fail", "BUG-ADMIN-USER-001", "User creation modal accepted input but Create User did not persist/close during attempt.", "No new user row observed after submit."),
    "SYS-002": ("Pass", "EV-20260911-PERM-001", "Role permissions view validated; role cards and privilege matrix loaded.", "Role-level configuration controls active."),
    "SYS-003": ("Pass", "EV-20260911-PERM-001", "Menu rights matrix editable; permission level buttons and Save action triggered.", "No frontend error on save action."),
    "SYS-004": ("Blocked", "BLK-SYS-AUDIT-001", "Audit logs screen/control not directly available in current navigation path.", "Requires dedicated route or feature flag."),
    "SYS-005": ("Blocked", "BLK-SYS-BACKUP-001", "Backup trigger action not exposed in visible admin/settings UI.", "Requires backend/admin feature toggle."),
}

updated = 0
for r in rows:
    tc = r["Test Case ID"].strip()
    if tc in updates:
        status, evid, actual, remarks = updates[tc]
        r["Status"] = status
        r["Defect ID"] = evid
        r["Actual Result"] = actual
        r["Remarks"] = remarks
        updated += 1

with p.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

print("updated", updated)
print("counts", dict(Counter(r["Status"] for r in rows)))
