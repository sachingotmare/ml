"""MLab end-to-end manual test case catalog.

This file is intentionally exhaustive and field-oriented, so each regression
cycle can execute tab-by-tab and field-by-field checks.

Examples:
    python qa/mlab_e2e_test_cases.py --summary
    python qa/mlab_e2e_test_cases.py --module TESTS
    python qa/mlab_e2e_test_cases.py --export-csv qa/mlab_e2e_execution_sheet.csv
    python qa/mlab_e2e_test_cases.py --export-json qa/mlab_e2e_test_cases.json
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Iterable
import argparse
import csv
import json


@dataclass(frozen=True)
class TestCase:
    id: str
    module: str
    tab: str
    field: str
    title: str
    preconditions: str
    steps: List[str]
    expected_result: str
    test_data: str = ""
    priority: str = "High"
    severity: str = "Major"


def _field_cases(
    module: str,
    tab: str,
    prefix: str,
    fields: list[str],
    *,
    preconditions: str,
    priority: str = "High",
    severity: str = "Major",
) -> list[TestCase]:
    """Create one field-level case per UI field."""
    out: list[TestCase] = []
    for i, field_name in enumerate(fields, start=1):
        tc = TestCase(
            id=f"{prefix}-{i:03d}",
            module=module,
            tab=tab,
            field=field_name,
            title=f"Validate {field_name}",
            preconditions=preconditions,
            steps=[
                f"Open tab '{tab}'.",
                f"Locate field '{field_name}'.",
                "Check default value, enabled/disabled state and placeholder/help text.",
                "Enter valid input and save/apply.",
                "Reopen record and verify persisted value.",
            ],
            expected_result=(
                f"Field '{field_name}' is visible and functional; valid value persists and "
                "validation behaves correctly."
            ),
            test_data=_sample_value(field_name),
            priority=priority,
            severity=severity,
        )
        out.append(tc)
    return out


def _sample_value(field_name: str) -> str:
    """Return executable sample data for a given UI field label."""
    f = field_name.lower()
    if "lab code" in f:
        return "DEMO2026"
    if "user id" in f:
        return "demo2026admin"
    if "password" in f:
        return "Admin@1234"
    if "name" in f and "doctor" in f:
        return "Dr QA Automation"
    if "patient name" in f or ("name" in f and "doctor" not in f and "account" not in f):
        return "QA Test Record"
    if "code" in f:
        return "QA26AUTO01"
    if "mobile" in f or "phone" in f:
        return "9876543210"
    if "email" in f:
        return "qa.demo@mlab.local"
    if "address" in f:
        return "QA Block, Test Street, Ranchi"
    if "date" in f:
        return "2026-09-11"
    if "age" in f:
        return "32"
    if "gender" in f:
        return "Male"
    if "department" in f:
        return "Pathology (DEPT001)"
    if "category" in f and "sub" not in f:
        return "Clinical Biochemistry (CTGY002)"
    if "sub category" in f:
        return "BIOCHEMISTRY (BI01)"
    if "test selection" in f or "test" in f:
        return "BLOOD SUGAR"
    if "loinc" in f:
        return "2345-7"
    if "unit" in f:
        return "mg/dL"
    if "method" in f:
        return "Colorimetric"
    if "rate" in f or "amount" in f or "charges" in f:
        return "250"
    if "discount" in f:
        return "10"
    if "tat" in f:
        return "4"
    if "daily limit" in f:
        return "100"
    if "male min" in f:
        return "70"
    if "male max" in f:
        return "110"
    if "female min" in f:
        return "65"
    if "female max" in f:
        return "105"
    if "child min" in f:
        return "60"
    if "child max" in f:
        return "100"
    if "critical low" in f:
        return "40"
    if "critical high" in f:
        return "450"
    if "specimen" in f:
        return "Blood"
    if "tube" in f:
        return "EDTA"
    if "storage" in f:
        return "Room Temperature"
    if "volume" in f:
        return "2"
    if "stability" in f:
        return "24"
    if "inversion" in f:
        return "8"
    if "remark" in f or "narration" in f or "note" in f or "suggestion" in f:
        return "QA auto-entry validation note"
    if "search" in f:
        return "QA"
    if "status" in f:
        return "Active"
    if "mode" in f:
        return "Cash"
    return "QA_SAMPLE"


def build_test_cases() -> list[TestCase]:
    cases: list[TestCase] = []

    # --- Authentication ---
    cases.extend(
        [
            TestCase(
                id="AUTH-001",
                module="AUTH",
                tab="Login",
                field="Credentials",
                title="Valid login",
                preconditions="Active user with valid Lab Code, User ID and Password.",
                steps=[
                    "Open login page.",
                    "Enter valid Organization/Lab Code, User ID, Password.",
                    "Click Sign In.",
                ],
                expected_result="Dashboard opens and authenticated session is created.",
                priority="Critical",
                severity="Critical",
            ),
            TestCase(
                id="AUTH-002",
                module="AUTH",
                tab="Login",
                field="Password",
                title="Invalid password",
                preconditions="Valid Lab Code and User ID exist.",
                steps=["Enter incorrect password and click Sign In."],
                expected_result="Error is shown and login is denied.",
                priority="High",
                severity="Major",
            ),
            TestCase(
                id="AUTH-003",
                module="AUTH",
                tab="Login",
                field="Failed Attempt Lockout",
                title="Lockout after threshold",
                preconditions="Lockout policy configured.",
                steps=["Submit wrong password repeatedly past configured threshold."],
                expected_result="Account is locked as per policy.",
                priority="Critical",
                severity="Critical",
            ),
        ]
    )
    cases.extend(
        _field_cases(
            "AUTH",
            "Login",
            "AUTHF",
            [
                "Organization / Lab Code",
                "User ID",
                "Password",
                "Password Visibility Toggle",
                "Sign In Button",
            ],
            preconditions="Login page is loaded.",
            priority="High",
        )
    )

    # --- Dashboard ---
    cases.extend(
        _field_cases(
            "DASHBOARD",
            "Dashboard",
            "DB",
            [
                "Search patients, tests, entries",
                "Today's Entries Card",
                "Today's Revenue Card",
                "Pending Readings Card",
                "Total Patients Today Card",
                "Account-wise Entries Chart",
                "Top Tests Chart",
                "Revenue Split Chart",
                "Recent Entries Grid",
            ],
            preconditions="User logged in and dashboard opened.",
            priority="Medium",
        )
    )

    # --- Main module tabs ---
    cases.extend(
        _field_cases(
            "PATIENT_ENTRY",
            "Patient Entry",
            "PE",
            [
                "Voucher Number",
                "Entry Date",
                "Patient Search",
                "Patient Name",
                "Age",
                "Age Unit",
                "Gender",
                "Mobile Number",
                "Consulting Doctor",
                "Referring Doctor",
                "Account / Company",
                "Test Selection",
                "Discount",
                "Net Amount",
                "Save Button",
            ],
            preconditions="Patient Entry page opened.",
            priority="Critical",
        )
    )

    cases.extend(
        _field_cases(
            "SAMPLE_COLLECTION",
            "Sample Collections",
            "SC",
            [
                "Entry Search",
                "Sample Barcode",
                "Sample Status",
                "Specimen Type",
                "Tube / Container",
                "Collection Time",
                "Collector",
                "Handoff",
                "Reject Reason",
                "Recollection Link",
            ],
            preconditions="Sample Collections page opened with at least one entry.",
            priority="High",
        )
    )

    cases.extend(
        _field_cases(
            "READINGS",
            "Readings",
            "RD",
            [
                "Voucher Search",
                "Test Grid",
                "Result Value",
                "Unit",
                "Reference Range",
                "Critical Low",
                "Critical High",
                "Suggestion",
                "Save",
                "Approve/Finalize",
            ],
            preconditions="Readings page opened for a pending entry.",
            priority="Critical",
        )
    )

    cases.extend(
        _field_cases(
            "RECEIPT_ENTRY",
            "Receipt Entry",
            "RE",
            [
                "Voucher Search",
                "Payment Amount",
                "Payment Mode",
                "Transaction Reference",
                "Outstanding Balance",
                "Save/Print Receipt",
            ],
            preconditions="Receipt Entry page opened with billable entry.",
            priority="High",
        )
    )

    cases.extend(
        _field_cases(
            "PAYMENT_ENTRY",
            "Payment Entry",
            "PAY",
            [
                "Party Account",
                "Payment Date",
                "Amount",
                "Mode",
                "Remarks",
                "Save",
            ],
            preconditions="Payment Entry page opened.",
            priority="Medium",
        )
    )

    cases.extend(
        _field_cases(
            "JOURNAL_ENTRY",
            "Journal Entry",
            "JE",
            [
                "Journal Date",
                "Debit Account",
                "Credit Account",
                "Amount",
                "Narration",
                "Save",
            ],
            preconditions="Journal Entry page opened.",
            priority="Medium",
        )
    )

    cases.extend(
        _field_cases(
            "INVENTORY",
            "Inventory",
            "INV",
            [
                "Item Search",
                "Item Code",
                "Item Name",
                "Category",
                "Unit",
                "Reorder Level",
                "Purchase Entry",
                "Usage Entry",
                "Stock Ledger",
            ],
            preconditions="Inventory page opened.",
            priority="Medium",
        )
    )

    cases.extend(
        _field_cases(
            "APPOINTMENTS",
            "Appointments",
            "APP",
            [
                "Appointment Date",
                "Patient",
                "Doctor",
                "Time Slot",
                "Status",
                "Linked Lab Entry",
                "Save",
            ],
            preconditions="Appointments page opened.",
            priority="Medium",
        )
    )

    # --- Masters section tabs ---
    cases.extend(
        _field_cases(
            "PATIENT_MASTER",
            "Masters > Patients",
            "MPAT",
            [
                "Patient Code",
                "Title",
                "Name",
                "DOB/Age",
                "Gender",
                "Mobile",
                "Address",
                "Account Link",
                "Save",
            ],
            preconditions="Patients master opened.",
        )
    )

    cases.extend(
        _field_cases(
            "ACCOUNT_MASTER",
            "Masters > Accounts",
            "MACC",
            [
                "Account Code",
                "Account Name",
                "Account Group",
                "Contact Person",
                "Mobile",
                "Email",
                "Address",
                "Active Toggle",
                "Save",
            ],
            preconditions="Accounts master opened.",
        )
    )

    # Tests tab: each visible section and field from screenshot/UI
    cases.extend(
        _field_cases(
            "TESTS",
            "Masters > Tests > Basic Information",
            "TBI",
            [
                "Test Type Selector",
                "Test Name",
                "Short Name / Alias",
                "Department",
                "Category",
                "Sub Category",
                "LOINC Code",
                "Unit",
                "Method / Technique",
            ],
            preconditions="Tests page opened in new/modify mode.",
            priority="Critical",
        )
    )
    cases.extend(
        _field_cases(
            "TESTS",
            "Masters > Tests > Billing & Pricing",
            "TBP",
            ["Default Rate", "CGHS Code"],
            preconditions="Tests page opened.",
            priority="High",
        )
    )
    cases.extend(
        _field_cases(
            "TESTS",
            "Masters > Tests > Reference Ranges",
            "TRR",
            [
                "Male Min",
                "Male Max",
                "Female Min",
                "Female Max",
                "Child Min",
                "Child Max",
                "Critical Low",
                "Critical High",
            ],
            preconditions="Reading test type selected.",
            priority="High",
        )
    )
    cases.extend(
        _field_cases(
            "TESTS",
            "Masters > Tests > Display & Suggestions",
            "TDS",
            ["Reading Detail Template", "Default Suggestion"],
            preconditions="Tests page opened.",
            priority="Medium",
        )
    )
    cases.extend(
        _field_cases(
            "TESTS",
            "Masters > Tests > Limits & Flags",
            "TLF",
            ["Daily Limit", "TAT (Hours)", "Print on New Page", "Add to Quick List"],
            preconditions="Tests page opened.",
            priority="Medium",
        )
    )
    cases.extend(
        _field_cases(
            "TESTS",
            "Masters > Tests > Sample Collection Information",
            "TSC",
            [
                "Specimen Type",
                "Tube / Container",
                "Storage Condition",
                "Min Volume (mL)",
                "Recommended Volume (mL)",
                "Stability (hours)",
                "Inversions Required",
                "Requires Fasting",
                "Protect from Light",
                "Requires Mixing/Inversion",
                "Sample Collection Note",
            ],
            preconditions="Tests page opened.",
            priority="Critical",
        )
    )

    cases.extend(
        _field_cases(
            "GENERAL_MASTER",
            "Masters > General Master",
            "GM",
            [
                "Departments Counter",
                "Categories Counter",
                "Sub-Categories Counter",
                "Inactive Counter",
                "Search by name or code",
                "Department Toggle",
                "Category Toggle",
                "Sub-category Toggle",
                "Refresh",
            ],
            preconditions="General Master page opened.",
            priority="High",
        )
    )

    cases.extend(
        _field_cases(
            "RATES",
            "Masters > Rates",
            "RT",
            ["Account", "Test", "Rate", "Effective Date", "Save"],
            preconditions="Rates page opened.",
            priority="High",
        )
    )

    cases.extend(
        _field_cases(
            "PACKAGES",
            "Masters > Packages",
            "PKG",
            ["Package Code", "Package Name", "Included Tests", "Package Rate", "Save"],
            preconditions="Packages page opened.",
            priority="Medium",
        )
    )

    cases.extend(
        _field_cases(
            "DOCTORS",
            "Masters > Doctors",
            "DOC",
            ["Doctor Code", "Doctor Name", "Department", "Category", "Mobile", "Save"],
            preconditions="Doctors page opened.",
            priority="Medium",
        )
    )

    cases.extend(
        _field_cases(
            "REPORTS",
            "Reports",
            "RP",
            ["Report Category", "Date Filter", "Doctor Filter", "Test Filter", "Preview", "Export PDF", "Export Excel"],
            preconditions="Reports page opened with data.",
            priority="High",
        )
    )

    cases.extend(
        _field_cases(
            "SYSTEM",
            "System",
            "SYS",
            ["User Management", "Role Rights", "Menu Rights", "Audit Logs", "Backup Trigger"],
            preconditions="System section opened with admin permissions.",
            priority="High",
        )
    )

    # --- Migration-focused safeguards requested by team ---
    cases.extend(
        [
            TestCase(
                id="MIG-001",
                module="MIGRATION",
                tab="TstMaster -> TestMasters",
                field="SubCategoryCode",
                title="Create missing sub-category if meaningful and absent",
                preconditions="Migration script configured with GeneralMasters lookup.",
                steps=[
                    "Run migration for tests.",
                    "Pick source rows where target sub-category code does not exist in GeneralMasters.",
                    "Verify missing valid SCTG rows are created.",
                ],
                expected_result="Meaningful missing sub-categories are auto-created and assigned.",
                priority="Critical",
                severity="Critical",
            ),
            TestCase(
                id="MIG-002",
                module="MIGRATION",
                tab="TstMaster -> TestMasters",
                field="SubCategoryCode",
                title="Keep sub-category blank when test name equals sub-category name",
                preconditions="Rule enabled in migration utility.",
                steps=[
                    "Run migration for rows where normalized TestName equals normalized SubCategoryName.",
                    "Inspect destination TestMasters rows.",
                ],
                expected_result="SubCategoryCode remains null/blank for such rows.",
                priority="Critical",
                severity="Major",
            ),
            TestCase(
                id="MIG-003",
                module="MIGRATION",
                tab="TstMaster -> TestMasters",
                field="SubCategoryName quality",
                title="Reject nonsense sub-category names",
                preconditions="Bad-name filter enabled (e.g., '.', '>', 'DR.', 'TEST', 'DUPLICATE').",
                steps=[
                    "Run migration on records with nonsense candidate names.",
                    "Inspect GeneralMasters and TestMasters outputs.",
                ],
                expected_result="Nonsense names are not created and not assigned to tests.",
                priority="Critical",
                severity="Major",
            ),
            TestCase(
                id="MIG-004",
                module="MIGRATION",
                tab="TstMaster -> TestMasters",
                field="Hierarchy mapping",
                title="Reuse existing DEPT/CTGY/SCTG masters before creating new",
                preconditions="GeneralMasters pre-populated.",
                steps=[
                    "Run migration.",
                    "Verify existing codes are reused and duplicates are not created.",
                ],
                expected_result="Mapping prefers existing masters; only valid missing rows are inserted.",
                priority="High",
                severity="Major",
            ),
        ]
    )

    # --- Security and performance ---
    cases.extend(
        [
            TestCase(
                id="SEC-001",
                module="SECURITY",
                tab="Cross-module",
                field="Input sanitization",
                title="SQL injection payload handling",
                preconditions="Text input fields available.",
                steps=["Inject SQL-like payload in key search/login fields and submit."],
                expected_result="No SQL execution or auth bypass occurs.",
                priority="Critical",
                severity="Critical",
            ),
            TestCase(
                id="SEC-002",
                module="SECURITY",
                tab="Cross-module",
                field="Output encoding",
                title="XSS payload handling",
                preconditions="Free text fields available.",
                steps=["Store script payload and reopen screens/reports where value is rendered."],
                expected_result="Payload is escaped/sanitized and never executed.",
                priority="Critical",
                severity="Critical",
            ),
            TestCase(
                id="PERF-001",
                module="PERFORMANCE",
                tab="Masters > Tests",
                field="Search",
                title="Test search responsiveness",
                preconditions="Large test catalog loaded.",
                steps=["Search by partial code/name repeatedly.", "Measure average response time."],
                expected_result="Search remains responsive within SLA.",
                priority="Medium",
                severity="Major",
            ),
        ]
    )

    return cases


TEST_CASES: List[TestCase] = build_test_cases()


def iter_cases(module: str | None = None) -> Iterable[TestCase]:
    if not module:
        return TEST_CASES
    target = module.strip().upper()
    return [tc for tc in TEST_CASES if tc.module.upper() == target]


def print_summary(cases: Iterable[TestCase]) -> None:
    cases = list(cases)
    print(f"Total test cases: {len(cases)}")
    module_counts: dict[str, int] = {}
    for tc in cases:
        module_counts[tc.module] = module_counts.get(tc.module, 0) + 1
    for mod in sorted(module_counts):
        print(f"- {mod}: {module_counts[mod]}")


def export_csv(path: str, cases: Iterable[TestCase]) -> None:
    cases = list(cases)
    columns = [
        "Test Case ID",
        "Module",
        "Tab",
        "Field",
        "Title",
        "Preconditions",
        "Steps",
        "Expected Result",
        "Test Data",
        "Priority",
        "Severity",
        "Actual Result",
        "Status",
        "Defect ID",
        "Remarks",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for tc in cases:
            writer.writerow(
                {
                    "Test Case ID": tc.id,
                    "Module": tc.module,
                    "Tab": tc.tab,
                    "Field": tc.field,
                    "Title": tc.title,
                    "Preconditions": tc.preconditions,
                    "Steps": " | ".join(tc.steps),
                    "Expected Result": tc.expected_result,
                    "Test Data": tc.test_data,
                    "Priority": tc.priority,
                    "Severity": tc.severity,
                    "Actual Result": "",
                    "Status": "Not Run",
                    "Defect ID": "",
                    "Remarks": "",
                }
            )


def export_json(path: str, cases: Iterable[TestCase]) -> None:
    rows = [asdict(tc) for tc in cases]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="MLab E2E test case catalog utility")
    parser.add_argument("--module", help="Filter by module, e.g. AUTH, TEST_MASTER, MIGRATION")
    parser.add_argument("--list-modules", action="store_true", help="List all available module names")
    parser.add_argument("--summary", action="store_true", help="Print test case counts")
    parser.add_argument("--export-csv", help="Export execution-ready CSV sheet")
    parser.add_argument("--export-json", help="Export test cases as JSON")
    args = parser.parse_args()

    selected = list(iter_cases(args.module))

    if args.summary or (not args.export_csv and not args.export_json):
        print_summary(selected)

    if args.list_modules:
        mods = sorted({tc.module for tc in TEST_CASES})
        print("Modules:")
        for m in mods:
            print(f"- {m}")

    if args.export_csv:
        export_csv(args.export_csv, selected)
        print(f"CSV exported: {args.export_csv}")

    if args.export_json:
        export_json(args.export_json, selected)
        print(f"JSON exported: {args.export_json}")


if __name__ == "__main__":
    main()
