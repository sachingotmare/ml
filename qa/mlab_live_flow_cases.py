from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class LiveFlowCase:
    id: str
    module: str
    title: str
    steps: List[str]
    expected: str


LIVE_FLOW_CASES: list[LiveFlowCase] = [
    LiveFlowCase(
        id="LF-001",
        module="MASTERS_ACCOUNTS",
        title="Add new customer account",
        steps=[
            "Open Masters > Accounts.",
            "Create a new account/customer.",
            "Save and verify searchable in Accounts list.",
        ],
        expected="New customer account is created and searchable.",
    ),
    LiveFlowCase(
        id="LF-002",
        module="MASTERS_TESTS",
        title="Add tests for all test types",
        steps=[
            "Open Masters > Tests.",
            "Create tests for READING, FORMATTED, GROUP, FORMULA.",
            "Save and verify each is searchable.",
        ],
        expected="All requested test types are created successfully.",
    ),
    LiveFlowCase(
        id="LF-003",
        module="MASTERS_TESTS",
        title="Assign Pathology and Hematology",
        steps=[
            "Edit newly created tests.",
            "Set Department=Pathology (DEPT001).",
            "Set Category=Hematology (CTGY001).",
            "Save and reopen.",
        ],
        expected="Test keeps Department and Category assignments.",
    ),
    LiveFlowCase(
        id="LF-004",
        module="MASTERS_RATES",
        title="Add rates for created tests and customer",
        steps=[
            "Open Masters > Rates.",
            "Add rates for all created tests under created customer.",
            "Save and verify in rates list.",
        ],
        expected="Rate rows are created and visible.",
    ),
    LiveFlowCase(
        id="LF-005",
        module="MASTERS_DOCTORS",
        title="Add doctor with type BOTH",
        steps=[
            "Open Masters > Doctors.",
            "Create doctor Type=BOTH, Department=Referral.",
            "Enable Auto-select in Reading.",
            "Save and verify.",
        ],
        expected="Doctor is created and available in Patient Entry/Readings.",
    ),
    LiveFlowCase(
        id="LF-006",
        module="MAIN_PATIENT_ENTRY",
        title="Create patient entry with account, doctor, tests",
        steps=[
            "Open Main > Patient Entry.",
            "Create one new patient and one entry with existing patient.",
            "Use selected account, doctor, tests.",
            "Save and verify voucher generated.",
        ],
        expected="Patient entry is saved for both new and existing patient.",
    ),
    LiveFlowCase(
        id="LF-007",
        module="MAIN_RECEIPT_ENTRY",
        title="Create receipt for patient entry",
        steps=[
            "Open Main > Receipt Entry.",
            "Search the new voucher/patient entry.",
            "Create receipt and verify saved.",
        ],
        expected="Receipt is saved against the entry.",
    ),
    LiveFlowCase(
        id="LF-008",
        module="MAIN_READINGS",
        title="Enter readings and preview report",
        steps=[
            "Open Main > Readings.",
            "Open saved entry and fill results for assigned tests.",
            "Save and open report preview.",
        ],
        expected="Readings save and report preview loads.",
    ),
    LiveFlowCase(
        id="LF-009",
        module="REPORTS_ALL",
        title="Open and validate all reports",
        steps=[
            "Open Reports section.",
            "Open each report in list with a minimal filter.",
            "Preview/export where available.",
        ],
        expected="Report pages load without blocking errors.",
    ),
]
