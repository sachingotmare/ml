"""
SQL → PostgreSQL DB Migration Tool  v3.0
=========================================
Live GUI: SQL Server 2008 R2  →  PostgreSQL

Tables:
  ACnPMaster    →  AccountMasters
  PatientMaster →  Patients
  DoctorMaster  →  Doctors
  TstMaster     →  TestMasters + TestGroupMappings
  RateMaster    →  RateMasters
  LabEntry      →  LabEntries
  LabTests      →  LabTests

Requirements:  pip install pyodbc psycopg2-binary
"""
from __future__ import annotations

import json
import os
import queue
import re
import threading
import time
import tkinter as tk
import traceback
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import psycopg2
import psycopg2.extras

try:
    import pyodbc
    PYODBC_OK = True
except ImportError:
    PYODBC_OK = False

# ─── Colours ─────────────────────────────────────────────────────────────────
BG       = "#1a1d2e"
BG2      = "#1f2235"
BG3      = "#252a40"
BG4      = "#2d3352"
FG       = "#d8ddf0"
FG_DIM   = "#7880a0"
ACCENT   = "#4a8fff"
GREEN    = "#4caf50"
ORANGE   = "#ff9800"
RED      = "#f44336"
EBORDER  = "#363d5c"

CRED_FILE  = os.path.join(os.path.dirname(__file__), "credentials.json")
CREATED_BY = "Migration"

# ─── Field mappings ──────────────────────────────────────────────────────────
TITLE_MAP = {
    "MR.": "Mr", "MR": "Mr", "SHRI": "Mr", "MD.": "Mr",
    "MRS.": "Mrs", "MRS": "Mrs", "SMT": "Mrs", "SMT.": "Mrs",
    "MISS": "Miss", "KU.": "Miss", "KU": "Miss", "MS.": "Miss", "MS": "Miss",
    "DR.": "Dr", "DR": "Dr",
    "MASTER": "Master", "BABY": "Baby", "B/O": "Baby", "B/O.": "Baby",
}
AGE_UNIT_MAP = {
    "YEARS": "Y", "YEAR": "Y", "Y": "Y",
    "MONTHS": "M", "MONTH": "M", "M": "M",
    "DAYS": "D", "DAY": "D", "D": "D",
}
GENDER_MAP    = {"M": "Male", "F": "Female", "O": "Other", "": "Unknown"}
DOC_TITLE_MAP = {"DR": "Dr", "MR": "Mr", "MRS": "Mrs", "MISS": "Miss"}
DOCTYPE_MAP   = {
    "CONSULTANT": "REFERRAL", "REFERRAL": "REFERRAL",
    "BOTH": "BOTH", "GENERAL": "REFERRAL", "INTERNAL": "INTERNAL",
}
# Maps (TestType, RFormat) → destination TestType
# G|READING         → READING
# G|TEXT            → FORMATTED  (HTML table built from tstMasterDesr)
# G|FORMATED TEXT   → FORMATTED  (raw Desr copied from tstMasterDesr)
# U|*               → GROUP
# F|f|*             → FORMULA
def _map_test_type(src_type: str, rformat: str) -> str:
    st = (src_type or "").strip().upper()
    rf = (rformat  or "").strip().upper()
    if st in ("F",):
        return "FORMULA"
    if st == "U":
        return "GROUP"
    if st == "G":
        if rf == "READING":
            return "READING"
        return "FORMATTED"   # TEXT or FORMATED TEXT
    return "FORMATTED"
RESULT_FORMAT = {"READING": 0, "FORMATTED": 1, "GROUP": 2, "FORMULA": 3}

_TCODE_DEPT_CTGY: dict[str, tuple[str, str]] = {
    "HA04": ("DEPT001", "CTGY001"), "HA05": ("DEPT001", "CTGY001"),
    "HA06": ("DEPT001", "CTGY001"), "HE01": ("DEPT001", "CTGY001"),
    "HE02": ("DEPT001", "CTGY001"), "HE03": ("DEPT001", "CTGY001"),
    "HE04": ("DEPT001", "CTGY001"), "AN03": ("DEPT001", "CTGY001"),
    "AN04": ("DEPT001", "CTGY001"), "BL02": ("DEPT001", "CTGY001"),
    "BL05": ("DEPT001", "CTGY001"), "EP01": ("DEPT001", "CTGY001"),
    "LA01": ("DEPT001", "CTGY001"), "LU01": ("DEPT001", "CTGY001"),
    "BO01": ("DEPT001", "CTGY001"), "AP01": ("DEPT001", "CTGY001"),
    "FR01": ("DEPT001", "CTGY001"), "FR02": ("DEPT001", "CTGY001"),
    "BI01": ("DEPT001", "CTGY002"), "BI03": ("DEPT001", "CTGY002"),
    "BI04": ("DEPT001", "CTGY002"), "BI05": ("DEPT001", "CTGY002"),
    "BI06": ("DEPT001", "CTGY002"), "BI07": ("DEPT001", "CTGY002"),
    "BI08": ("DEPT001", "CTGY002"), "BI09": ("DEPT001", "CTGY002"),
    "BI12": ("DEPT001", "CTGY002"), "BI13": ("DEPT001", "CTGY002"),
    "BI14": ("DEPT001", "CTGY002"), "BI15": ("DEPT001", "CTGY002"),
    "BI16": ("DEPT001", "CTGY002"), "BO02": ("DEPT001", "CTGY002"),
    "CL01": ("DEPT001", "CTGY002"), "CL02": ("DEPT001", "CTGY002"),
    "CS01": ("DEPT001", "CTGY002"), "CS03": ("DEPT001", "CTGY002"),
    "DE01": ("DEPT001", "CTGY002"), "EL01": ("DEPT001", "CTGY002"),
    "FO01": ("DEPT001", "CTGY002"), "GA01": ("DEPT001", "CTGY002"),
    "HO02": ("DEPT001", "CTGY002"), "HO03": ("DEPT001", "CTGY002"),
    "HY01": ("DEPT001", "CTGY002"), "IO01": ("DEPT001", "CTGY002"),
    "KI01": ("DEPT001", "CTGY002"), "KI03": ("DEPT001", "CTGY002"),
    "IN01": ("DEPT001", "CTGY002"), "SE06": ("DEPT001", "CTGY002"),
    "SE07": ("DEPT001", "CTGY002"), "SE10": ("DEPT001", "CTGY002"),
    "SE11": ("DEPT001", "CTGY002"), "TH06": ("DEPT001", "CTGY002"),
    "TS02": ("DEPT001", "CTGY002"), "TS01": ("DEPT001", "CTGY002"),
    "VA01": ("DEPT001", "CTGY002"), "VI03": ("DEPT001", "CTGY002"),
    "ZI01": ("DEPT001", "CTGY002"), "CA01": ("DEPT001", "CTGY002"),
    "IG01": ("DEPT001", "CTGY002"), "IG02": ("DEPT001", "CTGY002"),
    "IG03": ("DEPT001", "CTGY002"), "C301": ("DEPT001", "CTGY002"),
    "HB02": ("DEPT001", "CTGY002"), "SP04": ("DEPT001", "CTGY002"),
    "TO01": ("DEPT001", "CTGY002"), "TO02": ("DEPT001", "CTGY002"),
    "PL03": ("DEPT001", "CTGY002"),
    "SE03": ("DEPT001", "CTGY003"), "SE05": ("DEPT001", "CTGY003"),
    "SE08": ("DEPT001", "CTGY003"), "SE09": ("DEPT001", "CTGY003"),
    "HS01": ("DEPT001", "CTGY003"), "HB01": ("DEPT001", "CTGY003"),
    "MU01": ("DEPT001", "CTGY003"), "RU03": ("DEPT001", "CTGY003"),
    "RU04": ("DEPT001", "CTGY003"), "SS01": ("DEPT001", "CTGY003"),
    "SS02": ("DEPT001", "CTGY003"), "SW01": ("DEPT001", "CTGY003"),
    "VZ01": ("DEPT001", "CTGY003"), "WE01": ("DEPT001", "CTGY003"),
    "AN06": ("DEPT001", "CTGY003"), "AN07": ("DEPT001", "CTGY003"),
    "TB01": ("DEPT001", "CTGY003"), "VI01": ("DEPT001", "CTGY034"),
    "UR01": ("DEPT001", "CTGY004"), "UR04": ("DEPT001", "CTGY004"),
    "UR05": ("DEPT001", "CTGY004"), "UR06": ("DEPT001", "CTGY004"),
    "UR07": ("DEPT001", "CTGY004"), "UR08": ("DEPT001", "CTGY004"),
    "UR09": ("DEPT001", "CTGY004"), "UR10": ("DEPT001", "CTGY004"),
    "FL01": ("DEPT001", "CTGY004"), "FL02": ("DEPT001", "CTGY004"),
    "RO03": ("DEPT001", "CTGY004"), "RU01": ("DEPT001", "CTGY004"),
    "RU02": ("DEPT001", "CTGY004"), "CL03": ("DEPT001", "CTGY004"),
    "BI02": ("DEPT001", "CTGY005"), "BI10": ("DEPT001", "CTGY005"),
    "BI11": ("DEPT001", "CTGY005"), "HI04": ("DEPT001", "CTGY005"),
    "IH01": ("DEPT001", "CTGY005"),
    "CY02": ("DEPT001", "CTGY006"), "CY03": ("DEPT001", "CTGY006"),
    "CY04": ("DEPT001", "CTGY006"), "CY05": ("DEPT001", "CTGY006"),
    "CY06": ("DEPT001", "CTGY006"), "CY07": ("DEPT001", "CTGY006"),
    "FN01": ("DEPT001", "CTGY006"), "FN05": ("DEPT001", "CTGY006"),
    "PA03": ("DEPT001", "CTGY006"),
    "AF02": ("DEPT001", "CTGY007"), "CH01": ("DEPT001", "CTGY007"),
    "NM01": ("DEPT001", "CTGY007"),
    "AN05": ("DEPT001", "CTGY008"), "AN08": ("DEPT001", "CTGY008"),
    "AN09": ("DEPT001", "CTGY008"), "AN10": ("DEPT001", "CTGY008"),
    "AN11": ("DEPT001", "CTGY008"), "AN12": ("DEPT001", "CTGY008"),
    "AL01": ("DEPT001", "CTGY008"), "AR01": ("DEPT001", "CTGY008"),
    "CO05": ("DEPT001", "CTGY008"), "IM01": ("DEPT001", "CTGY008"),
    "IM02": ("DEPT001", "CTGY008"), "IM03": ("DEPT001", "CTGY008"),
    "PL02": ("DEPT001", "CTGY008"),
    "AE01": ("DEPT003", "CTGY032"), "AE02": ("DEPT003", "CTGY032"),
    "AF01": ("DEPT003", "CTGY030"), "BL01": ("DEPT003", "CTGY032"),
    "BL03": ("DEPT003", "CTGY032"), "BL04": ("DEPT003", "CTGY032"),
    "CS02": ("DEPT003", "CTGY032"), "CS04": ("DEPT003", "CTGY030"),
    "CU01": ("DEPT003", "CTGY032"), "EY01": ("DEPT003", "CTGY032"),
    "MI01": ("DEPT003", "CTGY030"), "MI02": ("DEPT003", "CTGY030"),
    "MI03": ("DEPT003", "CTGY030"), "MI04": ("DEPT003", "CTGY030"),
    "MI05": ("DEPT003", "CTGY030"), "OT01": ("DEPT003", "CTGY032"),
    "PL01": ("DEPT003", "CTGY032"), "PU02": ("DEPT003", "CTGY032"),
    "SK02": ("DEPT003", "CTGY030"), "SP03": ("DEPT003", "CTGY030"),
    "ST03": ("DEPT003", "CTGY032"), "TH05": ("DEPT003", "CTGY032"),
    "VI02": ("DEPT003", "CTGY030"),
    "BG01": ("DEPT004", "CTGY040"),
}
_TCODE_FALLBACK: dict[str, tuple[str, str]] = {
    "BI": ("DEPT001", "CTGY002"), "CL": ("DEPT001", "CTGY002"),
    "SE": ("DEPT001", "CTGY003"), "HA": ("DEPT001", "CTGY001"),
    "HE": ("DEPT001", "CTGY001"), "HO": ("DEPT001", "CTGY002"),
    "TH": ("DEPT001", "CTGY002"), "UR": ("DEPT001", "CTGY004"),
    "MI": ("DEPT003", "CTGY030"), "AE": ("DEPT003", "CTGY032"),
    "BL": ("DEPT003", "CTGY032"), "CY": ("DEPT001", "CTGY006"),
    "FN": ("DEPT001", "CTGY006"), "AN": ("DEPT001", "CTGY008"),
    "IM": ("DEPT001", "CTGY008"), "VI": ("DEPT001", "CTGY034"),
}


def _lookup_tcode(t_code: str) -> tuple[str | None, str | None]:
    k4 = t_code[:4] if len(t_code) >= 4 else t_code
    k2 = t_code[:2] if len(t_code) >= 2 else t_code
    return (
        _TCODE_DEPT_CTGY.get(k4)
        or _TCODE_DEPT_CTGY.get(k2)
        or _TCODE_FALLBACK.get(k2.upper(), ("DEPT001", "CTGY002"))
    )


# Maps source TstMaster.DeptCode (GenMain CTG* codes) → (dest DepartmentCode, dest CategoryCode)
# CTG005 = PATHOLOGY is intentionally absent: falls back to TCode-prefix lookup
# so existing pathology mapping logic is preserved.
_SRC_DEPTCODE_MAP: dict[str, tuple[str, str]] = {
    "CTG001": ("DEPT005", "CTGY050"),   # CARDIAC       → Cardiology / ECG
    "CTG002": ("DEPT002", "CTGY020"),   # CT Scan       → Radiology / CT Scan
    "CTG003": ("DEPT007", "CTGY070"),   # EEG           → Neurology / Electrodiagnostics
    "CTG004": ("DEPT006", "CTGY060"),   # CHEST/PFT     → Pulmonology / PFT
    "CTG006": ("DEPT002", "CTGY023"),   # USG           → Radiology / Ultrasound
    "CTG007": ("DEPT002", "CTGY021"),   # X-RAY         → Radiology / X-Ray
    "CTG008": ("DEPT001", "CTGY002"),   # HEALTH CHECK  → Pathology / Clinical Biochemistry
    "CTG009": ("DEPT007", "CTGY070"),   # AUDIOMETRY    → Neurology / Electrodiagnostics
    "CTG010": ("DEPT001", "CTGY008"),   # EYE EXAM      → Pathology / Immunology
    "CTG011": ("DEPT001", "CTGY002"),   # PHYSICIAN OPN → Pathology / Clinical Biochemistry
    "CTG012": ("DEPT001", "CTGY002"),   # DENTAL        → Pathology / Clinical Biochemistry
}
# Source DeptCodes for X-Ray tests that need Left/Right duplication
_XRAY_DEPTCODES: frozenset[str] = frozenset({"CTG007"})


def _dept_ctgy_from_src(dept_code: str, t_code: str) -> tuple[str, str]:
    """Return (DepartmentCode, CategoryCode) for destination.
    Uses source DeptCode if known; falls back to TCode-prefix lookup for
    pathology tests (CTG005) and any unmapped codes."""
    mapped = _SRC_DEPTCODE_MAP.get((dept_code or "").strip().upper())
    if mapped:
        return mapped
    # CTG005 (PATHOLOGY) and unknown codes → use existing TCode-prefix dict
    return _lookup_tcode(t_code)


_BAD_SCTG_EXACT: frozenset[str] = frozenset({
    ".", ">", "<", "-", "DR", "DR.", "TEST", "PROFILE", "DUPLICATE",
})


def _norm_label(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).upper()


def _is_nonsense_subcategory_name(name: str | None) -> bool:
    """True when a sub-category label is clearly placeholder/garbage."""
    n = _norm_label(name)
    if not n:
        return True
    if n in _BAD_SCTG_EXACT:
        return True
    # punctuation-only / symbol-only names like '.', '>', '---'
    if re.fullmatch(r"[\W_]+", n):
        return True
    # very short alnum tokens are usually not meaningful labels
    if len(n) <= 1:
        return True
    return False


def _should_blank_subcategory_for_test(test_name: str | None, subcat_name: str | None) -> bool:
    """Blank SubCategoryCode when sub-category is invalid or same as test name."""
    if _is_nonsense_subcategory_name(subcat_name):
        return True
    tn = _norm_label(test_name)
    sn = _norm_label(subcat_name)
    return bool(tn and sn and tn == sn)


# ─── Migration helpers ────────────────────────────────────────────────────────
def _tbl(schema: str, name: str) -> str:
    return f'{schema}."{name}"'


def _truncate(cur, schema: str, table: str, log):
    log(f"  ✓ Truncated {table}", "OK")
    cur.execute(f'TRUNCATE TABLE {_tbl(schema, table)} RESTART IDENTITY CASCADE')


def _fetch(mssql_conn, table: str, log) -> list[dict]:
    t0 = time.time()
    cur = mssql_conn.cursor()
    cur.execute(f"SELECT * FROM [{table}]")
    cols = [c[0] for c in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    log(f"  ✓ Fetched {len(rows):,} rows  [{table}]  ({time.time()-t0:.1f}s)", "OK")
    return rows


def _reset_seq(cur, schema: str, table: str, col: str, log):
    """Advance the Id sequence to MAX(Id) so future app inserts don't collide.

    Works for both SERIAL and GENERATED AS IDENTITY columns.
    Table names with mixed/upper case (e.g. "Patients") are handled by
    passing a properly double-quoted regclass string to pg_get_serial_sequence.
    Uses a savepoint so a failure never aborts the outer transaction.
    """
    cur.execute("SAVEPOINT _reset_seq_sp")
    try:
        # Step 1: current max id
        cur.execute(f'SELECT COALESCE(MAX("{col}"), 0) FROM {_tbl(schema, table)}')
        maxv: int = cur.fetchone()[0]

        # Step 2: resolve sequence name.
        # IMPORTANT: table names are quoted (case-sensitive), so we must pass
        # '"schema"."Table"' (with embedded double-quotes) to pg_get_serial_sequence.
        tbl_ref = f'"{schema}"."{table}"'
        cur.execute("SELECT pg_get_serial_sequence(%s, %s)", (tbl_ref, col))
        seq: str | None = cur.fetchone()[0]

        # Fallback for GENERATED AS IDENTITY (pg_get_serial_sequence may return
        # NULL in some PG versions for identity columns).
        if not seq:
            cur.execute(
                "SELECT schemaname || '.' || quote_ident(sequencename) "
                "FROM pg_sequences "
                "WHERE schemaname = %s "
                "  AND sequencename ILIKE %s "
                "ORDER BY sequencename DESC LIMIT 1",
                (schema, f'{table}_{col}%'),
            )
            row = cur.fetchone()
            seq = row[0] if row else None

        if seq:
            cur.execute("SELECT setval(%s, %s, true)", (seq, max(maxv, 1)))

        cur.execute("RELEASE SAVEPOINT _reset_seq_sp")
    except Exception:
        cur.execute("ROLLBACK TO SAVEPOINT _reset_seq_sp")
        cur.execute("RELEASE SAVEPOINT _reset_seq_sp")


# ─── Schema bootstrap ────────────────────────────────────────────────────────
def _ensure_schema(cur, schema: str, log):
    """Create missing tables from schema_setup.sql if any of the 5 core tables
    are absent.  Safe to call even when all tables already exist."""
    CORE_TABLES = [
        "AccountMasters", "Patients", "Doctors", "TestMasters", "RateMasters"
    ]
    cur.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = %s AND table_name = ANY(%s)",
        (schema, CORE_TABLES)
    )
    found = {r[0] for r in cur.fetchall()}
    missing = [t for t in CORE_TABLES if t not in found]
    if not missing:
        return  # all tables present — nothing to do

    log(f"  ⚠  Missing tables: {', '.join(missing)} — applying schema_setup.sql …", "WARN")
    sql_path = Path(__file__).parent / "schema_setup.sql"
    if not sql_path.exists():
        raise FileNotFoundError(
            f"schema_setup.sql not found next to migration_tool.py.\n"
            f"Expected: {sql_path}"
        )
    raw = sql_path.read_text(encoding="utf-8")
    # Strip psql meta-commands (\restrict, \connect, etc.) — psycopg2 can't run them
    clean_lines = [ln for ln in raw.splitlines() if not ln.startswith("\\")]
    ddl = "\n".join(clean_lines)
    # Replace the schema name in case the file was generated with a different
    # schema name (e.g. lab_demo2026 but user chose lab_test2).
    ddl = re.sub(r'\blab_demo2026\b', schema, ddl)

    # Step 1: CREATE SCHEMA — safe to ignore if it already exists
    cur.execute("SAVEPOINT _schema_create_sp")
    try:
        cur.execute(f"CREATE SCHEMA {schema}")
        cur.execute("RELEASE SAVEPOINT _schema_create_sp")
    except Exception:
        cur.execute("ROLLBACK TO SAVEPOINT _schema_create_sp")
        cur.execute("RELEASE SAVEPOINT _schema_create_sp")

    # Step 2: Split DDL into statements correctly.
    # pg_dump comments contain ';' (e.g. "-- Name: Foo; Type: TABLE; ...")
    # so naive split(';') embeds CREATE TABLE inside "Owner: -\n--\nCREATE..."
    # fragments.  We extract only the actual SQL by scanning for statement-
    # start keywords after stripping comments line-by-line.
    SQL_KW = (
        'CREATE ', 'ALTER ', 'SET ', 'SELECT ', 'INSERT ', 'UPDATE ',
        'DROP ', 'GRANT ', 'REVOKE ', 'COMMENT ', 'DO ',
    )
    stmts = []
    current = []
    for line in ddl.splitlines():
        stripped = line.strip()
        if stripped.startswith('--'):
            # If we're accumulating a statement, a comment line ends it cleanly
            if current:
                sql = '\n'.join(current).strip().rstrip(';').strip()
                if sql:
                    stmts.append(sql)
                current = []
            continue
        # Start a new statement when we hit a SQL keyword on a fresh line
        if not current and any(stripped.upper().startswith(kw) for kw in SQL_KW):
            current = [line]
        elif current:
            if stripped.endswith(';'):
                current.append(line.rstrip().rstrip(';'))
                sql = '\n'.join(current).strip()
                if sql:
                    stmts.append(sql)
                current = []
            else:
                current.append(line)
    if current:
        sql = '\n'.join(current).strip()
        if sql:
            stmts.append(sql)

    SKIP = {
        '42P07',  # duplicate_table
        '42710',  # duplicate_object (sequences, constraints, indexes)
        '42P06',  # duplicate_schema
        '42701',  # duplicate_column
        '42P16',  # invalid_table_definition (e.g. multiple PKs)
        '42830',  # invalid_foreign_key
        '23503',  # foreign_key_violation (existing rows fail new FK check)
        '23505',  # unique_violation
        '42704',  # undefined_object (DROP of nonexistent)
    }
    for stmt in stmts:
        if not stmt.strip():
            continue
        cur.execute("SAVEPOINT _schema_stmt_sp")
        try:
            cur.execute(stmt)
            cur.execute("RELEASE SAVEPOINT _schema_stmt_sp")
        except Exception as exc:
            pgcode = getattr(exc, "pgcode", None)
            cur.execute("ROLLBACK TO SAVEPOINT _schema_stmt_sp")
            cur.execute("RELEASE SAVEPOINT _schema_stmt_sp")
            if pgcode not in SKIP:
                raise

    # Verify the tables actually exist now
    cur.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = %s AND table_name = ANY(%s)",
        (schema, CORE_TABLES)
    )
    now_found = {r[0] for r in cur.fetchall()}
    still_missing = [t for t in missing if t not in now_found]
    if still_missing:
        raise RuntimeError(
            f"schema_setup.sql executed but tables still missing: "
            f"{', '.join(still_missing)}"
        )
    log(f"  ✓ Schema objects created for: {', '.join(missing)}", "OK")


# ─── AccountMasters ───────────────────────────────────────────────────────────
def migrate_accounts(cur, schema, rows, log, now):
    log("── ACnPMaster  →  AccountMasters", "HEAD")
    # Do NOT truncate — preserve existing default/system entries.
    # Load existing names and codes to avoid duplicates.
    cur.execute(
        f'SELECT "Id", UPPER("Name"), UPPER("Code") FROM {_tbl(schema,"AccountMasters")}'
    )
    existing = cur.fetchall()
    ex_names = {r[1] for r in existing}
    ex_codes = {r[2] for r in existing}
    ex_ids   = {r[0] for r in existing}

    # Next Id = max existing + 1 (never reuse an existing Id)
    next_id = (max(ex_ids) + 1) if ex_ids else 1

    t0 = time.time()
    data = []
    skipped = 0
    for row in rows:
        name = (row.get("Name") or "").strip()
        if not name:
            continue
        code = (row.get("Code") or "")[:20]
        # Skip if name already exists (case-insensitive) — preserve existing entry
        if name.upper() in ex_names:
            skipped += 1
            continue
        # Also skip if code already taken (would violate unique constraint)
        if code and code.upper() in ex_codes:
            skipped += 1
            continue
        ob = 0.0
        try:
            ob = float(row.get("CreditBal") or 0)
        except (ValueError, TypeError):
            pass
        data.append((
            next_id,
            code, name, (row.get("Type") or "C")[:1], None,
            row.get("Address") or None, None,
            row.get("PhNo") or None, row.get("PhNoM") or None,
            row.get("Email") or None, row.get("PAN") or None,
            ob, None, True, now, False, CREATED_BY,
        ))
        ex_names.add(name.upper())
        ex_codes.add(code.upper())
        next_id += 1

    if data:
        psycopg2.extras.execute_values(
            cur,
            f"""INSERT INTO {_tbl(schema,"AccountMasters")}
                ("Id","Code","Name","AccountType","AccountGroupId","Address","City",
                 "Phone","Mobile","Email","GSTNumber","OpeningBalance",
                 "OpeningBalanceType","IsActive","CreatedAt","IsDeleted","CreatedBy")
                VALUES %s""",
            data, page_size=500,
        )
    log(f"  ✓ {len(data)} rows inserted, {skipped} skipped (name already exists)  ({time.time()-t0:.1f}s)", "OK")
    _reset_seq(cur, schema, "AccountMasters", "Id", log)
def migrate_patients(cur, schema, rows, log, now):
    log("── PatientMaster  →  Patients", "HEAD")
    _truncate(cur, schema, "Patients", log)

    cur.execute(
        f'SELECT "Id" FROM {_tbl(schema,"AccountMasters")} WHERE "Code"=%s LIMIT 1',
        ("ZZZZZZ",),
    )
    r = cur.fetchone()
    default_acct = r[0] if r else 1
    log(f"  ✓ Using default AccountId={default_acct}", "OK")

    total = len(rows)
    log(f"  ✓ Fetched {total:,} rows", "OK")

    BATCH = 5_000
    t0 = time.time()
    buf: list[tuple] = []
    inserted = 0
    skipped  = 0
    next_id  = 1

    def _flush(force=False):
        nonlocal inserted
        if not buf:
            return
        if not force and len(buf) < BATCH:
            return
        psycopg2.extras.execute_values(
            cur,
            f"""INSERT INTO {_tbl(schema,"Patients")}
                ("Id","PtCode","PtName","Title","Gender","Age","AgeUnit","DateOfBirth",
                 "Address","City","WhatsApp","Mobile","Email","History",
                 "AccountId","BloodGroup","CreatedAt","IsDeleted","CreatedBy")
                VALUES %s""",
            buf, page_size=BATCH,
        )
        inserted += len(buf)
        buf.clear()
        log(f"  ↳ {inserted:,} / {total:,} rows inserted...", "DIM")

    for row in rows:
        pt_code = (row.get("PtCode") or "").strip()[:20]
        if not pt_code:
            skipped += 1
            continue
        try:
            age = int(float(row.get("Age") or 0))
        except (ValueError, TypeError):
            age = 0
        mobile    = row.get("PhNoM") or None
        blood_grp = (row.get("BloodGrp") or "").strip() or "O+"
        buf.append((
            next_id,
            pt_code,
            (row.get("PtName") or "").strip()[:200] or "Unknown",
            TITLE_MAP.get((row.get("Title") or "").strip().upper(), "Mr"),
            GENDER_MAP.get((row.get("Gender") or "").strip().upper(), "Unknown")[:10],
            age,
            AGE_UNIT_MAP.get((row.get("AgeType") or "").strip().upper(), "Y"),
            None,
            row.get("Address") or None,
            row.get("CtCode") or None,
            mobile, mobile,
            row.get("Email") or None,
            row.get("History") or None,
            default_acct, blood_grp,
            now, False, CREATED_BY,
        ))
        next_id += 1
        if len(buf) >= BATCH:
            _flush()

    _flush(force=True)
    log(f"  ✓ {inserted:,} rows inserted in {time.time()-t0:.1f}s", "OK")
    _reset_seq(cur, schema, "Patients", "Id", log)


# ─── Doctors ──────────────────────────────────────────────────────────────────
def migrate_doctors(cur, schema, rows, log, now):
    log("── DoctorMaster  →  Doctors", "HEAD")
    _truncate(cur, schema, "Doctors", log)
    log(f"  ✓ Fetched {len(rows)} rows", "OK")

    t0 = time.time()
    data = []
    next_id = 1
    for row in rows:
        code = (row.get("Code") or "").strip()[:20]
        if not code:
            continue
        t        = (row.get("Title") or "").strip().upper().rstrip(".")
        doc_type = DOCTYPE_MAP.get((row.get("DocType") or "").strip().upper(), "REFERRAL")[:20]
        vc = 0.0
        try:
            vc = float(row.get("VisitCharges") or 0)
        except (ValueError, TypeError):
            pass
        tin  = row.get("TimeIn")
        tout = row.get("TimeOut")
        # Build full name: Name + MiddleName (if present) + LastName (if present)
        _first  = (row.get("Name")       or "").strip()
        _middle = (row.get("MiddleName") or "").strip()
        _last   = (row.get("LastName")   or "").strip()
        full_name = " ".join(p for p in [_first, _middle, _last] if p)[:200] or "Unknown"
        data.append((
            next_id,
            code,
            full_name,
            DOC_TITLE_MAP.get(t, "Dr"), doc_type,
            row.get("Designation") or None,
            (row.get("Qualification") or "").strip() or "MBBS",
            None,
            row.get("PhoneNo") or None, row.get("MobNo") or None,
            row.get("EmailId") or None, row.get("SignatureFile") or None,
            0, vc, None, None,
            tin.time() if hasattr(tin, "time") else None,
            tout.time() if hasattr(tout, "time") else None,
            now, False, CREATED_BY, False, 0,
        ))
        next_id += 1

    if data:
        psycopg2.extras.execute_values(
            cur,
            f"""INSERT INTO {_tbl(schema,"Doctors")}
                ("Id","Code","Name","Title","DoctorType","Designation","Qualification",
                 "Specialization","Phone","Mobile","Email","SignatureFile",
                 "CommissionPercent","VisitCharges","DepartmentId","CategoryId",
                 "TimeIn","TimeOut","CreatedAt","IsDeleted","CreatedBy","AutoSelectInReading","AutoSelectOrder")
                VALUES %s""",
            data, page_size=500,
        )
    log(f"  ✓ {len(data)} rows inserted in {time.time()-t0:.1f}s", "OK")
    _reset_seq(cur, schema, "Doctors", "Id", log)


# ─── Specimen Type inference for Pathology tests ────────────────────────────
# Rules applied only when DepartmentCode = DEPT001 (Pathology).
# Each entry: (specimen_value, [keyword_fragments_any_match])
# Matching is case-insensitive on the full test name (TName + SubTName).
_SPECIMEN_RULES: list[tuple[str, list[str]]] = [
    # Rules are checked IN ORDER — first match wins.
    # More specific / longer keywords must come before generic ones.

    # ── Bone Marrow ──────────────────────────────────────────────────────────
    ("Bone Marrow", ["bone marrow"]),

    # ── CSF ──────────────────────────────────────────────────────────────────
    ("CSF", ["csf", "cerebrospinal", "spinal fluid"]),

    # ── Pleural Fluid ────────────────────────────────────────────────────────
    ("Pleural Fluid", ["pleural fluid", "pleural"]),

    # ── Peritoneal Fluid (Ascitic) ────────────────────────────────────────────
    ("Peritoneal Fluid", ["ascitic fluid", "ascitis", "peritoneal"]),

    # ── Synovial Fluid ───────────────────────────────────────────────────────
    ("Synovial Fluid", ["synovial", "joint fluid"]),

    # ── Tissue (Histopathology / FNAC / Biopsy) — before Swab/Blood/Urine ───
    ("Tissue", [
        "histopath", "histo path", "fnac", "nipple discharge",
        "cervical tissue", "gallbladder tissue", "rectal tissue",
        "small tissue", "large tissue", "extra large tissue",
    ]),

    # ── Semen ────────────────────────────────────────────────────────────────
    ("Other", ["semen analysis", "semen", "sperm analysis"]),

    # ── Swab / Secretion ─────────────────────────────────────────────────────
    ("Swab", [
        "swab", "high vaginal", "hvs", "nasal swab",
        "saline smear", "vaginal swab",
    ]),

    # ── Sputum ───────────────────────────────────────────────────────────────
    ("Sputum", [
        "sputum", "gram stain", "cbnaat",
        "culture [fl01", "afb [pu",   # sputum AFB
    ]),

    # ── Stool ────────────────────────────────────────────────────────────────
    ("Stool", [
        "stool", "faece", "fecal", "feces",
        "routine & deposit", "r&e", "r & e", "r&d",
        "routine [ge04", "examination [ge",
    ]),

    # ── Urine — SPECIFIC urine keywords (avoid "sugar"/"culture" alone) ──────
    ("Urine", [
        "urine", "urobilinogen", "chyluria", "chyleurea",
        "porphobilinogen", "vma",
        "bile salt", "bile pigment",
        "urine for", "urinary ", "24 hour urine", "24 hrs urine", "24hrs urine",
        "microalbumine",  # urine microalbumin (UR01*)
        "urine culture", "urine routine",
        "urine sugar", "urine protein",
        "urine metanephrine",
        "urine for osmolality",
        "culture & sensitivity [ur",    # urine culture & sensitivity
        "culture [ur",                  # urine culture
    ]),

    # ── Serum ─────────────────────────────────────────────────────────────────
    # Listed BEFORE generic Blood so serum-specific tests win over haematology.
    ("Serum", [
        "serum ", "s. ace", "s.ace", "s.copper",
        "sgot", "sgpt", "ggtp",
        "lipid profile", "lipid profile",
        "liver function", "renal function", "kidney function",
        "bilirubin", "serum albumin", "serum globulin",
        "electrolytes", "serum electrolyte",
        "serum creatinine", "blood urea nitrogen", "blood urea",
        "cholesterol", "triglyceride", "tryglyceride",
        "ldl", "hdl", "vldl", "ldh",
        "alkaline phosphatase", "acid phosphatase", "amylase", "lipase",
        "serum calcium", "serum phosphorus", "serum magnesium",
        "serum sodium", "serum potassium", "serum chloride",
        "serum bicarbonate", "serum iron", "tibc", "ferritin", "feritine",
        "serum cortisol", "serum insulin", "c-peptide", "c peptide",
        "prolactin", "testosterone", "progesterone", "projestrone",
        "estradiol", "fsh", "lh", "dheas", "amh",
        "hba1c", "glucose tolerance",
        "vitamin b12", "vitamin d", "folic acid",
        "protein total", "protein (total)", "serum protein",
        "cardiac enzyme", "ck mb", "ckmb", "cpk", "troponin", "trop",
        "d dimer",
        "psa", "cea", "ca125", "ca19", "ca15",
        "bnp", "pro bnp",
        "ceruloplasmin", "serum copper", "serum zinc", "serum magnesium",
        "a/g ratio", "ag ratio",
        "fibrinogen", "fibranogen",
        "phenytoin", "carbamazepine", "carbomezepin", "lithium",
        "valproate", "valporate", "tacrolimus",
        "electrophoresis", "electrophrosis",
        "blood sugar",  # glucose drawn as serum/plasma
        "blood sugar (f", "blood sugar (pp", "blood sugar (r",
        "glucose tolerance",
        "insulin fasting", "insulin pp",
        "hba1c",
        "blood for osmolality",
        "renal function", "kidney function",
        "lipid", "cholesterol",
        "uric acid",
        "vitamin profile",
        "t3,t4", "t3,tsh", "t4,tsh", "t3 t4", "tsh",    # thyroid panels
        "ft3", "ft4",
    ]),

    # ── AFB (sputum default, but standalone AFB could be blood/CSF; keep Sputum)
    ("Sputum", ["afb", "nasal smear for afb"]),

    # ── Whole Blood (haematology, serology, immunology) ──────────────────────
    ("Blood", [
        "blood group", "blood lead", "blood for",
        "haemoglobin", "hemoglobin",
        "cbc", "complete blood count", "cbp",
        "esr", "erythrocyte sedimentation",
        "platelet", "rbc count", "wbc count", "red blood cell", "white blood",
        "differential count", "dc basophil", "dc eosinophil", "dc lymph",
        "dc monocyte", "dc neutrophil",
        "packed cell volume", "hematocrit",
        "reticulocyte", "peripheral smear", "pbs comment",
        "malarial", "microfilaria",
        "bleeding time", "clotting time", "aptt", "inr",
        "sickling", "hb electro",
        "dengue", "chikungunya", "malaria",
        "hbsag", "hcv", "hiv", "hev", "hav",
        "widal", "aso titre", "ra factor", "ra test", "vdrl", "tpha",
        "torch", "rubella",
        "typhi", "covid", "rat(",
        "ana ", "ds-dna", "anca", "apla",
        "anti ccp", "anti tpo", "anti thyroid", "anti hav", "anti hcv",
        "anti hbeag",
        "hs crp", "crp(", " crp",
        "kahn",
        "cd4", "cd8",
        "hla b27",
        "factor viii", "factor ix",
        "blast cell", "myelocyte", "metamyelocyte", "leukaemia",
        "karyotyp", "chromosome",
        "immature lymph",
        "nlr", "p lcr", "rdw", "pdw", "mpv", "pct",
        "g6pd", "osmotic fragility",
        "coombs", "sickling",
        "bt & ct", "bl gr",
        "flow cytometry",
        "hbcag", "hbeag", "hbveag",
        "ns1", "dengue card",
        "western blot", "elisa for",
        "serology test", "hepatitis b",
        "mantoux",
    ]),
]


def _infer_specimen_type(
    t_name: str,
    sub_t_name: str,
    dept_code: str,
    ctgy_code: str = "",
    sub_cat_code: str = "",
) -> str | None:
    """Return a specimen type string for Pathology (DEPT001) tests only.

    Uses a three-tier strategy:
    1. Category-level shortcut  (CTGY-based override, most reliable)
    2. Sub-category shortcut    (SCTG-based override)
    3. Keyword scan on combined test name

    Only returns values that exist in the app's fixed SpecimenType dropdown.
    Returns None for non-pathology or when no rule matches.
    """
    _VALID_SPECIMEN_TYPES: frozenset[str] = frozenset({
        "Blood", "Urine", "Serum", "Plasma", "Stool", "CSF",
        "Sputum", "Tissue", "Swab", "Synovial Fluid",
        "Peritoneal Fluid", "Pleural Fluid", "Amniotic Fluid",
        "Bone Marrow", "Other",
    })

    if dept_code != "DEPT001":
        return None

    # ── Tier 1: Category-level overrides ─────────────────────────────────────
    # These categories unambiguously determine the specimen type.
    _CTGY_SPECIMEN: dict[str, str] = {
        "CTGY004": "Urine",      # Urine Analysis / Urinalysis
        "CTGY005": "Tissue",     # Histopathology
        "CTGY006": "Tissue",     # Cytology / FNAC
        "CTGY030": "Sputum",     # Microbiology cultures (many sputum)
        "CTGY032": "Swab",       # Swab / Wound cultures
    }
    cat_specimen = _CTGY_SPECIMEN.get((ctgy_code or "").strip())
    if cat_specimen:
        return cat_specimen

    # ── Tier 2: Sub-category-level overrides ─────────────────────────────────
    # Sub-category codes from our SCTG migration (first 2 chars = source TCode prefix)
    _SCTG_SPECIMEN: dict[str, str] = {
        "SCTG040": "Urine",      # Urine sub-category
        "SCTG050": "Tissue",     # Histopathology sub-category
        "SCTG060": "Tissue",     # Cytology sub-category
        "SCTG061": "Tissue",     # FNAC sub-category
    }
    sctg_specimen = _SCTG_SPECIMEN.get((sub_cat_code or "").strip())
    if sctg_specimen:
        return sctg_specimen

    # Also match source TCode prefix used as SCTG code (e.g. "UR01", "BI02")
    sc = (sub_cat_code or "").strip().upper()
    if sc.startswith("UR"):
        return "Urine"
    if sc.startswith(("BI02", "BI03", "HI")):
        return "Tissue"   # Histopathology TCode prefixes

    # ── Tier 3: Keyword scan on combined test name ────────────────────────────
    combined = (t_name + " " + sub_t_name).upper()
    for specimen, keywords in _SPECIMEN_RULES:
        for kw in keywords:
            if kw.upper() in combined:
                return specimen if specimen in _VALID_SPECIMEN_TYPES else None

    # Default fallback for pathology when no keyword matched
    return "Blood"


def _clean_range_value(v):
    """Normalize range value from source.
    - None or blank string -> None
    - Keep other values as-is (including 0-like values)
    """
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        return s if s else None
    return v


def _is_missing_or_zero_range(v) -> bool:
    """True when value is missing, blank, or numeric zero (e.g. 0, '0', '0.0')."""
    val = _clean_range_value(v)
    if val is None:
        return True
    if isinstance(val, (int, float)):
        return float(val) == 0.0
    s = str(val).strip()
    if not s:
        return True
    try:
        return float(s) == 0.0
    except (TypeError, ValueError):
        return False


def _range_with_male_fallback(row: dict, key: str, male_key: str):
    """Return row[key], but fallback to male range when value is missing/blank/zero."""
    val = _clean_range_value(row.get(key))
    if not _is_missing_or_zero_range(val):
        return val
    return _clean_range_value(row.get(male_key))


# ─── TestMasters + TestGroupMappings ─────────────────────────────────────────
# Canonical column definitions: (column_name, lambda row_dict -> value)
# Only columns that actually exist in the target schema will be inserted.
_TM_COL_DEFS: list[tuple[str, object]] = [
    ("Id",                  lambda d: d["_id"]),
    ("TCode",               lambda d: d["sub_code"]),
    ("TName",               lambda d: d["t_name"]),
    ("ShortName",           lambda d: d["t_code"]),
    ("TestType",            lambda d: d["dest_type"]),
    ("DepartmentCode",      lambda d: d["dept_code"]),
    ("CategoryCode",        lambda d: d["ctgy_code"]),
    ("SubCategoryCode",     lambda d: d.get("sub_cat_code")),   # body-part SCTG code for X-Ray
    ("Unit",                lambda d: d["row"].get("Unit") or None),
    ("CalculationExpression", lambda d: d["formula_str"]),
    ("DependsOnTests",      lambda d: d["depends_on"]),
    ("ReadingFormat",       lambda d: d["row"].get("RFormat") or None),
    ("Footer",              lambda d: d["row"].get("Footer") or None),
    ("ReadingDtl",          lambda d: d["row"].get("ReadingDtl") or None),
    ("Remark",              lambda d: d["row"].get("Remark") or None),
    ("Description",         lambda d: d["description"]),    # HTML table / raw text from tstMasterDesr
    ("Gender",              lambda d: d["row"].get("Gender") or None),
    ("MinRange",            lambda d: _clean_range_value(d["row"].get("MinRange"))),
    ("MaxRange",            lambda d: _clean_range_value(d["row"].get("MaxRange"))),
    ("MinRangeF",           lambda d: _range_with_male_fallback(d["row"], "MinRangeF", "MinRange")),
    ("MaxRangeF",           lambda d: _range_with_male_fallback(d["row"], "MaxRangeF", "MaxRange")),
    ("MinRangeCh",          lambda d: _range_with_male_fallback(d["row"], "MinRangeCh", "MinRange")),
    ("MaxRangeCh",          lambda d: _range_with_male_fallback(d["row"], "MaxRangeCh", "MaxRange")),
    # NormalRangeGeneral: build display string "min - max" when both non-zero
    ("NormalRangeGeneral",  lambda d: (
        f'{d["row"].get("MinRange","") or ""} - {d["row"].get("MaxRange","") or ""}'.strip(" -")
        if d["dest_type"] in ("READING", "FORMULA")
           and (d["row"].get("MinRange") or d["row"].get("MaxRange"))
        else None
    )),
    ("CGHSCode",            lambda d: d["row"].get("CGHSCode") or None),
    ("DayLimit",            lambda d: d["row"].get("DayLimit") or None),
    ("PrintOnNewPage",      lambda d: bool(d["row"].get("PrintOnNewPage"))),
    ("QuickList",           lambda d: bool(d["row"].get("QuickList"))),
    ("IsReadingRequired",   lambda d: d["dest_type"] in ("READING", "GROUP")),
    ("HasFormattedContent", lambda d: d["dest_type"] == "FORMATTED"),
    ("ResultFormat",        lambda d: d["result_fmt"]),
    ("AliasName",           lambda d: d["row"].get("AliasName") or None),
    ("DefaultRate",         lambda d: 0),
    ("SortOrder",           lambda d: 0),
    ("IsBold",              lambda d: False),
    ("IsActive",            lambda d: True),
    ("IsDeleted",           lambda d: False),
    ("CreatedAt",           lambda d: d["now"]),
    ("CreatedBy",           lambda d: CREATED_BY),
    ("ResultDataType",      lambda d: "TEXT"),
    ("IsPanel",             lambda d: d["dest_type"] == "GROUP"),
    ("DecimalPrecision",    lambda d: 2),
    ("PanelMembers",        lambda d: None),
]

def _build_desr_lookup(desr_rows: list[dict]) -> dict[str, list[dict]]:
    """Build {sub_code: [{Item, Desr}, ...]} sorted by TCodeSlno."""
    lookup: dict[str, list[dict]] = {}
    for row in desr_rows:
        slno = (row.get("TCodeSlno") or "").strip()
        if len(slno) < 7:
            continue
        code = slno[:7]          # first 7 chars = SubTCode
        lookup.setdefault(code, []).append({
            "slno": slno,
            "item": (row.get("Item") or "").strip(),
            "desr": (row.get("Desr")  or "").strip(),
        })
    for v in lookup.values():
        v.sort(key=lambda x: x["slno"])
    return lookup


def _html_table_description(rows: list[dict]) -> str:
    """Build HTML table from tstMasterDesr rows (G|TEXT format)."""
    td = '<td colspan="1" rowspan="1"><p>{}</p></td>'
    th = '<th colspan="1" rowspan="1"><p>{}</p></th>'
    header = f'<tr>{th.format("Item")}{th.format("Description")}</tr>'
    body_rows = "".join(
        f'<tr>{td.format(r["item"])}{td.format(r["desr"])}</tr>'
        for r in rows if r["item"] or r["desr"]
    )
    if not body_rows:
        return ""
    return (
        '<table style="min-width: 100px;">'
        '<colgroup><col style="min-width: 50px;"><col style="min-width: 50px;"></colgroup>'
        f'<tbody>{header}{body_rows}</tbody></table><p></p>'
    )


def migrate_tests(cur, schema, tst_rows, mmst_rows, desr_rows, log, now):
    log("── TstMaster  →  TestMasters", "HEAD")
    _truncate(cur, schema, "TestMasters", log)
    _truncate(cur, schema, "TestGroupMappings", log)
    log(f"  ✓ Fetched {len(tst_rows)} rows", "OK")
    desr_lookup = _build_desr_lookup(desr_rows)

    # Discover which columns actually exist in this schema version
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema=%s AND table_name='TestMasters'",
        (schema,)
    )
    existing_cols = {r[0] for r in cur.fetchall()}
    active_defs = [(col, fn) for col, fn in _TM_COL_DEFS if col in existing_cols]
    col_sql = ", ".join(f'"{c}"' for c, _ in active_defs)
    skipped_cols = [c for c, _ in _TM_COL_DEFS if c not in existing_cols]
    if skipped_cols:
        log(f"  ℹ Schema missing columns (skipped): {', '.join(skipped_cols)}", "INFO")

    # ── Auto-create SCTG sub-category entries for body-parts ─────────────
    # Key: (TCode, ctgy_code) so the same TCode used in multiple modalities
    # (e.g. AB02 in USG AND CT Scan) gets a separate SCTG under each CTGY.
    # Value: (TName, ctgy_code)
    radiol_sctg: dict[tuple[str,str], str] = {}   # {(TCode, ctgy_code): TName}
    for _r in tst_rows:
        _dc = (_r.get("DeptCode") or "").strip().upper()
        _tc = (_r.get("TCode")  or "").strip().lstrip("(")[:20]
        # Use TName as body-part name; fall back to SubTName when TName is blank
        _tn = (_r.get("TName") or "").strip() or (_r.get("SubTName") or "").strip()
        _tn = _tn[:200]
        if not _tc or not _tn:
            continue
        if _dc in _SRC_DEPTCODE_MAP:
            _ctgy = _SRC_DEPTCODE_MAP[_dc][1]
        else:
            # Pathology (CTG005) and others: use TCode-prefix lookup
            _, _ctgy = _lookup_tcode(_tc)
            if not _ctgy:
                continue
        key = (_tc, _ctgy)
        if key not in radiol_sctg:
            radiol_sctg[key] = _tn

    # tcode_to_sctg: maps (TCode, ctgy_code) → dest GeneralMasters SCTG Code
    tcode_to_sctg: dict[tuple[str,str], str] = {}
    # reverse lookup for final sanitization before writing TestMasters.SubCategoryCode
    sctg_code_to_name: dict[str, str] = {}

    if radiol_sctg:
        # Load ALL existing SCTG entries: Id, Code, normalised Name, ParentCode.
        cur.execute(
            f'SELECT "Id","Code","Name","ParentCode" FROM {_tbl(schema,"GeneralMasters")} WHERE "MasterType"=%s',
            ("SCTG",)
        )
        existing_rows = cur.fetchall()
        existing_codes: set[str] = {r[1] for r in existing_rows}
        sctg_code_to_name = {r[1]: (r[2] or "") for r in existing_rows}

        # Load CTGY Id lookup: ctgy_code → GeneralMasters.Id
        cur.execute(
            f'SELECT "Id","Code" FROM {_tbl(schema,"GeneralMasters")} WHERE "MasterType"=%s',
            ("CTGY",)
        )
        ctgy_id_map: dict[str, int] = {r[1]: r[0] for r in cur.fetchall()}

        # Build: (name_upper, parent_ctgy_id) → dest_code
        # This lets us match by BOTH name AND correct parent category,
        # so "CHEST" under CT Scan (CTGY020) is NOT reused for X-Ray (CTGY021).
        name_ctgy_to_code: dict[tuple[str, int | None], str] = {}
        for _id, _code, _name, _parent in existing_rows:
            name_ctgy_to_code[(_name.strip().upper(), _parent)] = _code

        cur.execute(
            f'SELECT COALESCE(MAX("Id"),0) FROM {_tbl(schema,"GeneralMasters")}'
        )
        gm_next = cur.fetchone()[0] + 1
        sctg_data = []
        for (tc, ctgy_code), tn in sorted(radiol_sctg.items()):
            if _is_nonsense_subcategory_name(tn):
                # Don't create/resolve meaningless SCTG names
                continue
            tn_upper = tn.strip().upper()
            parent_id = ctgy_id_map.get(ctgy_code)

            if (tn_upper, parent_id) in name_ctgy_to_code:
                # Exact name + correct parent category already exists — reuse.
                tcode_to_sctg[(tc, ctgy_code)] = name_ctgy_to_code[(tn_upper, parent_id)]
            elif tc in existing_codes and (tn_upper, parent_id) not in name_ctgy_to_code:
                # TCode exists as code but under different category → fall through to new entry
                # Check if tc is already mapped for this specific ctgy
                matched = next((code for (n, p), code in name_ctgy_to_code.items() if p == parent_id and code == tc), None)
                if matched:
                    tcode_to_sctg[(tc, ctgy_code)] = matched
                else:
                    new_code = f"{tc}_{ctgy_code[-3:]}"[:20]  # e.g. AB02_020
                    if new_code not in existing_codes:
                        sctg_data.append((gm_next, new_code, tn, "SCTG", parent_id, 0, True, False, now))
                        tcode_to_sctg[(tc, ctgy_code)] = new_code
                        existing_codes.add(new_code)
                        sctg_code_to_name[new_code] = tn
                        name_ctgy_to_code[(tn_upper, parent_id)] = new_code
                        gm_next += 1
                    else:
                        tcode_to_sctg[(tc, ctgy_code)] = new_code
            else:
                # Brand-new (name, parent) combination — insert with source TCode as Code.
                sctg_data.append((gm_next, tc, tn, "SCTG", parent_id, 0, True, False, now))
                tcode_to_sctg[(tc, ctgy_code)] = tc
                existing_codes.add(tc)
                sctg_code_to_name[tc] = tn
                name_ctgy_to_code[(tn_upper, parent_id)] = tc
                gm_next += 1
        if sctg_data:
            psycopg2.extras.execute_values(
                cur,
                f'INSERT INTO {_tbl(schema,"GeneralMasters")} '
                f'("Id","Code","Name","MasterType","ParentCode","SortOrder","IsActive","IsDeleted","CreatedAt") VALUES %s '
                f'ON CONFLICT DO NOTHING',
                sctg_data,
            )
            _reset_seq(cur, schema, "GeneralMasters", "Id", log)
            log(f"  ✓ Created {len(sctg_data)} new SCTG body-part entries (with ParentCode); "
                f"{len(radiol_sctg)-len(sctg_data)} reused existing dest codes", "OK")
        else:
            log(f"  ✓ All {len(radiol_sctg)} body-part SCTG entries resolved from existing dest codes", "OK")

    t0 = time.time()
    data = []
    used_tnames: set[str] = set()
    duplicates: list[str] = []
    next_id = 1
    blanked_subcat_same = 0
    blanked_subcat_bad = 0

    for row in tst_rows:
        sub_code = (row.get("SubTCode") or "").strip().lstrip("(")
        t_code   = (row.get("TCode")    or "").strip().lstrip("(")
        t_name   = (row.get("SubTName") or "").strip()[:300]
        if not sub_code or not t_name:
            continue

        if t_name.upper() in used_tnames:
            duplicates.append(f'{sub_code} → "{t_name}"')
            t_name = f"{t_name} [{sub_code}]"[:300]
        used_tnames.add(t_name.upper())

        src_type   = (row.get("TestType") or "").strip()
        rformat    = (row.get("RFormat")   or "").strip().upper()
        dest_type  = _map_test_type(src_type, rformat)
        result_fmt = RESULT_FORMAT.get(dest_type, 1)

        # Use source DeptCode column for dept/category lookup.
        # CTG005 (Pathology) falls back to TCode-prefix dict (_lookup_tcode).
        src_dept_code = (row.get("DeptCode") or "").strip().upper()
        dept_code, ctgy_code = _dept_ctgy_from_src(src_dept_code, t_code)

        # Resolve candidate sub-category code by (TCode, ctgy_code)
        resolved_subcat_code = tcode_to_sctg.get((t_code, ctgy_code))
        resolved_subcat_name = sctg_code_to_name.get(resolved_subcat_code or "")
        if _is_nonsense_subcategory_name(resolved_subcat_name):
            final_subcat_code = None
            if resolved_subcat_code:
                blanked_subcat_bad += 1
        elif _should_blank_subcategory_for_test(t_name, resolved_subcat_name):
            final_subcat_code = None
            if resolved_subcat_code:
                blanked_subcat_same += 1
        else:
            final_subcat_code = resolved_subcat_code

        # Infer specimen type from category, sub-category and test name (Pathology only)
        specimen_type = _infer_specimen_type(
            (row.get("TName") or "").strip(),
            t_name,   # SubTName
            dept_code,
            ctgy_code,
            final_subcat_code or "",
        )

        # Build Description from tstMasterDesr for FORMATTED tests
        description = None
        if dest_type == "FORMATTED" and src_type.upper() == "G":
            desr_entries = desr_lookup.get(sub_code, [])
            if desr_entries:
                if rformat == "TEXT":
                    description = _html_table_description(desr_entries)
                elif rformat == "FORMATED TEXT":
                    # Concatenate raw Desr values
                    description = "".join(e["desr"] for e in desr_entries) or None

        # Extract {CODE} references from Formula for DependsOnTests.
        # Trim everything from "=" onwards, then remove all spaces.
        formula_raw = (row.get("Formula") or "").strip()
        if formula_raw:
            # Keep only the left-hand side (before the first "=")
            formula_lhs = formula_raw.split("=")[0]
            # Remove all whitespace
            formula_str = re.sub(r'\s+', '', formula_lhs)
            dep_codes = list(dict.fromkeys(re.findall(r'\{([^}]+)\}', formula_raw)))
            depends_on = json.dumps(dep_codes) if dep_codes else None
        else:
            formula_str = None
            depends_on = None

        # X-Ray tests (CTG007): expand into two rows — Left and Right.
        # SubTCode gets 'L'/'R' suffix; TName gets ' - Left'/' - Right' suffix.
        if src_dept_code in _XRAY_DEPTCODES:
            for side_suffix, side_label in (("L", " - Left"), ("R", " - Right")):
                sided_sub   = (sub_code + side_suffix)[:20]
                sided_tname = (t_name + side_label)[:300]

                if sided_tname.upper() in used_tnames:
                    duplicates.append(f'{sided_sub} → "{sided_tname}"')
                    sided_tname = f"{sided_tname} [{sided_sub}]"[:300]
                used_tnames.add(sided_tname.upper())

                ctx = {
                    "_id": next_id, "sub_code": sided_sub, "t_name": sided_tname,
                    "t_code": t_code, "dest_type": dest_type, "result_fmt": result_fmt,
                    "dept_code": dept_code, "ctgy_code": ctgy_code,
                    # Resolve to actual dest SCTG Code using (TCode, ctgy) key
                    "sub_cat_code": final_subcat_code,
                    "specimen_type": specimen_type,
                    "row": row, "now": now, "description": description,
                    "depends_on": depends_on, "formula_str": formula_str,
                }
                data.append(tuple(fn(ctx) for _, fn in active_defs))
                next_id += 1
            # Skip the normal single-row path below
            continue

        ctx = {
            "_id": next_id, "sub_code": sub_code, "t_name": t_name,
            "t_code": t_code, "dest_type": dest_type, "result_fmt": result_fmt,
            "dept_code": dept_code, "ctgy_code": ctgy_code,
            # Resolve SCTG by (TCode, ctgy_code) key for correct parent category
            "sub_cat_code": final_subcat_code,
            "specimen_type": specimen_type,
            "row": row, "now": now, "description": description,
            "depends_on": depends_on, "formula_str": formula_str,
        }
        data.append(tuple(fn(ctx) for _, fn in active_defs))
        next_id += 1

    if data:
        psycopg2.extras.execute_values(
            cur,
            f'INSERT INTO {_tbl(schema,"TestMasters")} ({col_sql}) VALUES %s',
            data, page_size=200,
        )

    if duplicates:
        shown = duplicates[:20]
        log(f"  ⚠ {len(duplicates)} duplicate TName rows renamed (first 20):", "WARN")
        for d in shown:
            log(f"      renamed: {d}", "WARN_DIM")

    xray_count = sum(1 for d in data if str(d).endswith(("'L'", "'R'")) )
    # Count X-Ray expanded rows by checking if sub_code ends with L or R
    log(f"  ✓ {len(data)} rows inserted in {time.time()-t0:.1f}s", "OK")
    if blanked_subcat_same or blanked_subcat_bad:
        log(
            f"  ℹ SubCategoryCode blanked for {blanked_subcat_same} same-name tests and "
            f"{blanked_subcat_bad} nonsensical sub-categories",
            "INFO",
        )
    _reset_seq(cur, schema, "TestMasters", "Id", log)

    # GRIV rows for TestGroupMappings
    griv = [r for r in mmst_rows if (r.get("MTYPE") or "").strip() == "GRIV"]

    # TestGroupMappings
    log("── MMST  →  TestGroupMappings", "HEAD")
    cur.execute(
        f'SELECT "TCode" FROM {_tbl(schema,"TestMasters")} WHERE "IsDeleted"=FALSE'
    )
    known = {r[0] for r in cur.fetchall()}

    gm_data: list[tuple] = []
    gm_seen: set[tuple[str, str]] = set()
    gm_skip = 0
    for row in griv:
        g = (row.get("CODE1") or "").strip()
        m = (row.get("CODE2") or "").strip()
        if not g or not m or g not in known or m not in known:
            gm_skip += 1
            continue
        pair = (g, m)
        if pair in gm_seen:
            gm_skip += 1
            continue
        gm_seen.add(pair)
        try:
            so = int(row.get("SlNo") or 0)
        except (ValueError, TypeError):
            so = 0
        gm_data.append((g, m, so, now, False, CREATED_BY))

    if gm_data:
        # Prepend sequential Id to each row
        gm_data = [(i + 1, *row) for i, row in enumerate(gm_data)]
        psycopg2.extras.execute_values(
            cur,
            f"""INSERT INTO {_tbl(schema,"TestGroupMappings")}
                ("Id","GroupTestCode","SubTestCode","SortOrder","CreatedAt","IsDeleted","CreatedBy")
                VALUES %s""",
            gm_data, page_size=500,
        )
    log(f"  ✓ {len(gm_data)} mappings inserted  (skipped={gm_skip})", "OK")
    _reset_seq(cur, schema, "TestGroupMappings", "Id", log)

    # Back-fill PanelMembers JSON array on GROUP tests (only if column exists)
    if "PanelMembers" in existing_cols:
        cur.execute(f"""
            UPDATE {_tbl(schema,"TestMasters")} t
            SET "PanelMembers" = (
                SELECT json_agg(m."SubTestCode" ORDER BY m."SortOrder")::text
                FROM {_tbl(schema,"TestGroupMappings")} m
                WHERE m."GroupTestCode" = t."TCode"
            )
            WHERE t."TestType" = 'GROUP'
        """)
        updated = cur.rowcount
        log(f"  ✓ PanelMembers populated for {updated} GROUP tests", "OK")
    else:
        log("  ℹ PanelMembers column absent — skipping back-fill", "INFO")

# ─── SampleSpecimenRules ───────────────────────────────────────────────────
def migrate_sample_specimen_rules(cur, schema, log, now):
    """Create SampleSpecimenRules rows for every Pathology test.
    Re-derives specimen type from the already-migrated TestMasters rows
    so this function is fully independent and idempotent."""
    log("── TestMasters  →  SampleSpecimenRules", "HEAD")
    cur.execute(f'TRUNCATE {_tbl(schema,"SampleSpecimenRules")} RESTART IDENTITY CASCADE')
    log("  ✓ Truncated SampleSpecimenRules", "OK")

    cur.execute(
        f'SELECT "Id","TCode","TName","ShortName","DepartmentCode","CategoryCode","SubCategoryCode" '
        f'FROM {_tbl(schema,"TestMasters")} '
        f'WHERE "IsDeleted"=false AND "DepartmentCode"=%s',
        ("DEPT001",)
    )
    rows = cur.fetchall()
    log(f"  ✓ Fetched {len(rows)} Pathology tests from TestMasters", "OK")

    data: list[tuple] = []
    skipped = 0
    next_id = 1
    for test_id, tcode, tname, short_name, dept_code, ctgy_code, sub_cat_code in rows:
        specimen = _infer_specimen_type(
            short_name or "",
            tname or "",
            dept_code or "",
            ctgy_code or "",
            sub_cat_code or "",
        )
        if not specimen:
            skipped += 1
            continue
        data.append((
            next_id,    # Id
            test_id,    # TestId FK
            specimen,   # SpecimenType
            "",         # TubeType (not specified - empty string satisfies NOT NULL)
            None,       # TubeColor
            0,          # MinVolumeMl
            None,       # RecommendedVolumeMl
            0,          # StorageCondition  0 = Room Temperature
            24,         # StabilityHours
            False,      # RequiresFasting
            None,       # CollectionInstructions
            False,      # ProtectFromLight
            False,      # RequiresMixing
            None,       # MixInvocations
            None,       # InventoryItemIds
            0,          # SortOrder
            True,       # IsActive
            now,        # CreatedAt
            False,      # IsDeleted
            CREATED_BY, # CreatedBy
        ))
        next_id += 1

    if data:
        psycopg2.extras.execute_values(
            cur,
            f'INSERT INTO {_tbl(schema,"SampleSpecimenRules")} '
            f'("Id","TestId","SpecimenType","TubeType","TubeColor",'
            f'"MinVolumeMl","RecommendedVolumeMl","StorageCondition","StabilityHours",'
            f'"RequiresFasting","CollectionInstructions","ProtectFromLight",'
            f'"RequiresMixing","MixInvocations","InventoryItemIds",'
            f'"SortOrder","IsActive","CreatedAt","IsDeleted","CreatedBy") VALUES %s',
            data, page_size=500,
        )
    _reset_seq(cur, schema, "SampleSpecimenRules", "Id", log)
    log(
        f"  ✓ {len(data)} SampleSpecimenRules inserted  "
        f"(skipped {skipped} non-pathology or unresolved)",
        "OK",
    )


def migrate_rate_masters(cur, schema, rows, log, now):
    log("── RateMaster  →  RateMasters", "HEAD")
    cur.execute(f'TRUNCATE {_tbl(schema,"RateMasters")} RESTART IDENTITY CASCADE')
    log("  ✓ Truncated RateMasters", "OK")

    # Discover columns present in this schema version
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema=%s AND table_name='RateMasters'",
        (schema,)
    )
    rm_cols = {r[0] for r in cur.fetchall()}
    has_labid = "LabId" in rm_cols

    cur.execute(
        f'SELECT "Id","TCode" FROM {_tbl(schema,"TestMasters")} WHERE "IsDeleted"=false'
    )
    tcode_id: dict[str, int] = {r[1]: r[0] for r in cur.fetchall()}
    # Build a set of X-Ray expanded codes (those ending with L or R where the
    # base 7-char code is absent) so we can fan-out rates for Left/Right pairs.
    xray_base_to_sides: dict[str, list[tuple[str, int]]] = {}
    for tc, tid in tcode_id.items():
        if len(tc) == 8 and tc[-1] in ("L", "R") and tc[:7] not in tcode_id:
            xray_base_to_sides.setdefault(tc[:7], []).append((tc, tid))

    cur.execute(f'SELECT "Id","Code" FROM {_tbl(schema,"AccountMasters")}')
    acode_id: dict[str, int] = {r[1]: r[0] for r in cur.fetchall()}

    t0 = time.time()
    data: list[tuple] = []
    seen: set[tuple[int, int]] = set()
    skipped = 0
    xray_expanded = 0
    for row in rows:
        tc_slno = (row.get("TCodeSlno") or "").strip()
        company = (row.get("Company") or "").strip()
        tcode   = tc_slno[:7]
        acct_id = acode_id.get(company)
        if not acct_id:
            skipped += 1
            continue
        try:
            rate = float(row.get("Rate") or 0)
        except (ValueError, TypeError):
            rate = 0.0
        desr = (row.get("Desr") or "").strip() or None

        # Check if this is an X-Ray test that was expanded to Left/Right
        if tcode in xray_base_to_sides:
            for sided_tc, sided_id in xray_base_to_sides[tcode]:
                pair = (sided_id, acct_id)
                if pair in seen:
                    continue
                seen.add(pair)
                if has_labid:
                    data.append((0, acct_id, sided_id, sided_tc, rate, desr, now, False))
                else:
                    data.append((acct_id, sided_id, sided_tc, rate, desr, now, False))
            xray_expanded += 1
            continue

        test_id = tcode_id.get(tcode)
        if not test_id:
            skipped += 1
            continue
        pair = (test_id, acct_id)
        if pair in seen:
            skipped += 1
            continue
        seen.add(pair)
        if has_labid:
            data.append((0, acct_id, test_id, tcode, rate, desr, now, False))
        else:
            data.append((acct_id, test_id, tcode, rate, desr, now, False))

    if has_labid:
        insert_cols = '"Id","LabId","AccountId","TestId","TestCode","Rate","Description","CreatedAt","IsDeleted"'
        default_select = 'ROW_NUMBER() OVER (ORDER BY t."Id") + %s, 0,%s,t."Id",t."TCode",0.00,t."TName"||\'  - Default Rate\',NOW(),false'
    else:
        insert_cols = '"AccountId","TestId","TestCode","Rate","Description","CreatedAt","IsDeleted"'
        default_select = '%s,t."Id",t."TCode",0.00,t."TName"||\'  - Default Rate\',NOW(),false'

    if data:
        # Prepend sequential Id only when LabId absent (Id is first column)
        if not has_labid:
            data = [(i + 1, *row) for i, row in enumerate(data)]
            insert_cols = '"Id",' + insert_cols
        else:
            data = [(i + 1, *row) for i, row in enumerate(data)]
        psycopg2.extras.execute_values(
            cur,
            f'INSERT INTO {_tbl(schema,"RateMasters")} ({insert_cols}) VALUES %s ON CONFLICT DO NOTHING',
            data, page_size=500,
        )

    # Default Rate=0 for tests with no rate entry
    default_acct = acode_id.get("ZZZZZZ") or 1
    cur.execute(f'SELECT COALESCE(MAX("Id"),0) FROM {_tbl(schema,"RateMasters")}')
    base_id = cur.fetchone()[0]
    if has_labid:
        cur.execute(
            f"""INSERT INTO {_tbl(schema,"RateMasters")}
                ("Id","LabId","AccountId","TestId","TestCode","Rate","Description","CreatedAt","IsDeleted")
                SELECT ROW_NUMBER() OVER (ORDER BY t."Id") + %s,
                       0,%s,t."Id",t."TCode",0.00,t."TName"||' - Default Rate',NOW(),false
                FROM   {_tbl(schema,"TestMasters")} t
                WHERE  t."IsDeleted"=false
                  AND  t."Id" NOT IN (
                         SELECT "TestId" FROM {_tbl(schema,"RateMasters")} WHERE "AccountId"=%s
                       )
                ON CONFLICT DO NOTHING""",
            (base_id, default_acct, default_acct),
        )
    else:
        cur.execute(
            f"""INSERT INTO {_tbl(schema,"RateMasters")}
                ("Id","AccountId","TestId","TestCode","Rate","Description","CreatedAt","IsDeleted")
                SELECT ROW_NUMBER() OVER (ORDER BY t."Id") + %s,
                       %s,t."Id",t."TCode",0.00,t."TName"||' - Default Rate',NOW(),false
                FROM   {_tbl(schema,"TestMasters")} t
                WHERE  t."IsDeleted"=false
                  AND  t."Id" NOT IN (
                         SELECT "TestId" FROM {_tbl(schema,"RateMasters")} WHERE "AccountId"=%s
                       )
                ON CONFLICT DO NOTHING""",
            (base_id, default_acct, default_acct),
        )

    cur.execute(f'SELECT COUNT(*) FROM {_tbl(schema,"RateMasters")}')
    total = cur.fetchone()[0]
    log(
        f"  ✓ {len(data):,} rates inserted  skipped={skipped}  "
        f"xray_expanded={xray_expanded}  total={total:,}  ({time.time()-t0:.1f}s)",
        "OK",
    )
    _reset_seq(cur, schema, "RateMasters", "Id", log)


# ─── LabEntries ───────────────────────────────────────────────────────────────
def migrate_lab_entries(cur, schema, le_rows, log, now):
    log("── LabEntry  →  LabEntries", "HEAD")
    _truncate(cur, schema, "LabEntries", log)

    # Build FK lookups
    cur.execute(f'SELECT "Id","PtCode" FROM {_tbl(schema,"Patients")}')
    ptcode_id: dict[str, int] = {r[1]: r[0] for r in cur.fetchall()}

    cur.execute(f'SELECT "Id","Code" FROM {_tbl(schema,"AccountMasters")}')
    acode_id: dict[str, int] = {r[1]: r[0] for r in cur.fetchall()}
    default_acct = acode_id.get("ZZZZZZ") or 1

    cur.execute(f'SELECT "Id","Code" FROM {_tbl(schema,"Doctors")}')
    dcode_id: dict[str, int] = {r[1]: r[0] for r in cur.fetchall()}

    log(f"  ✓ Fetched {len(le_rows):,} rows", "OK")

    def _flt(v):
        try: return float(v or 0)
        except (ValueError, TypeError): return 0.0

    t0 = time.time()
    data: list[tuple] = []
    skipped = 0
    next_id = 1

    for row in le_rows:
        vrno = (row.get("VrNo") or "").strip()
        if not vrno:
            skipped += 1
            continue

        pt_code   = (row.get("PtID")    or "").strip()
        patient_id = ptcode_id.get(pt_code)
        if not patient_id:
            skipped += 1
            continue

        company  = (row.get("Company") or "").strip()
        acct_id  = acode_id.get(company, default_acct)

        reffby     = (row.get("ReffBy") or "").strip()
        ref_doc_id = dcode_id.get(reffby) if reffby else None

        # Entry date/time — keep as-is if already datetime, else parse
        vr_date = row.get("VrDate")
        if vr_date is None:
            entry_dt = now
        elif hasattr(vr_date, "year"):
            entry_dt = vr_date
        else:
            try:
                entry_dt = datetime.strptime(str(vr_date)[:10], "%Y-%m-%d")
            except Exception:
                entry_dt = now

        gross    = _flt(row.get("GrossAmt"))
        disc_per = _flt(row.get("DiscPer"))
        # Discount amount: prefer explicit Discount column, fall back to LessAmt
        disc_amt = _flt(row.get("Discount") or row.get("LessAmt"))
        net      = _flt(row.get("NetAmt"))
        paid     = _flt(row.get("PaidAmt"))
        bal      = _flt(row.get("BalAmt"))

        reg_no     = (row.get("RegNo")  or "").strip() or None
        entered_by = (row.get("UserID") or "").strip() or CREATED_BY

        data.append((
            next_id, vrno, patient_id,
            entry_dt, entry_dt,            # EntryDate, EntryTime
            reg_no, "Pending", "Lab",
            acct_id, ref_doc_id, None,     # AccountId, ReferredByDoctorId, ConsultingDoctorId
            gross, disc_per, disc_amt, net, paid, bal,
            entered_by, None,              # EnteredBy, CompletedAt
            now, now, CREATED_BY, CREATED_BY, False,
        ))
        next_id += 1

    if data:
        psycopg2.extras.execute_values(
            cur,
            f"""INSERT INTO {_tbl(schema,"LabEntries")}
                ("Id","Vrno","PatientId","EntryDate","EntryTime","RegNo",
                 "Status","RegistrationType","AccountId",
                 "ReferredByDoctorId","ConsultingDoctorId",
                 "GrossAmount","DiscountPercent","DiscountAmount","NetAmount",
                 "PaidAmount","BalanceAmount","EnteredBy","CompletedAt",
                 "CreatedAt","UpdatedAt","CreatedBy","UpdatedBy","IsDeleted")
                VALUES %s""",
            data, page_size=500,
        )
    log(f"  ✓ {len(data):,} rows inserted, {skipped} skipped  ({time.time()-t0:.1f}s)", "OK")
    _reset_seq(cur, schema, "LabEntries", "Id", log)


# ─── LabTests ─────────────────────────────────────────────────────────────────
def migrate_lab_tests(cur, schema, lt_rows, log, now):
    log("── LabTests  →  LabTests", "HEAD")
    _truncate(cur, schema, "LabTests", log)

    # Build FK lookups
    cur.execute(f'SELECT "Id","Vrno" FROM {_tbl(schema,"LabEntries")}')
    vrno_entryid: dict[str, int] = {r[1]: r[0] for r in cur.fetchall()}
    vrno_set = set(vrno_entryid.keys())

    cur.execute(
        f'SELECT "Id","TCode","CategoryCode" FROM {_tbl(schema,"TestMasters")} '
        'WHERE "IsDeleted"=false'
    )
    tcode_rows = cur.fetchall()
    tcode_id:   dict[str, int] = {r[1]: r[0] for r in tcode_rows}
    tcode_ctgy: dict[str, str] = {r[1]: r[2] for r in tcode_rows}

    log(f"  ✓ Fetched {len(lt_rows):,} rows", "OK")

    def _flt(v):
        try: return float(v or 0)
        except (ValueError, TypeError): return 0.0

    t0 = time.time()
    data: list[tuple] = []
    skipped = 0
    next_id = 1

    for row in lt_rows:
        vrnosno = (row.get("VrNoSno") or "").strip()
        if not vrnosno:
            skipped += 1
            continue

        # Extract VrNo: find the longest prefix of VrNoSno that matches a known Vrno
        vrno: str | None = None
        for length in range(len(vrnosno), 0, -1):
            candidate = vrnosno[:length]
            if candidate in vrno_set:
                vrno = candidate
                break

        if vrno is None:
            skipped += 1
            continue

        entry_id = vrno_entryid[vrno]

        ivsub   = (row.get("IvSubCode") or "").strip()
        test_id = tcode_id.get(ivsub)
        if not test_id:
            skipped += 1
            continue

        ctgy_code = tcode_ctgy.get(ivsub)

        try:
            slno = int(row.get("Slno") or 1)
        except (ValueError, TypeError):
            slno = 1

        rate     = _flt(row.get("Rate"))
        disc_per = _flt(row.get("DiscPer"))
        disc_amt = _flt(row.get("DiscAmt"))
        net      = _flt(row.get("NetAmt"))

        test_date = row.get("TestDate")
        if not test_date:
            test_date = now

        data.append((
            next_id, entry_id, test_id, slno,
            rate, disc_per, disc_amt, net,
            ctgy_code, None, None,   # CategoryCode, CategorySortOrder, CategorySrNo
            False,                   # IsReported
            test_date,
            now, now, CREATED_BY, CREATED_BY, False,
        ))
        next_id += 1

    if data:
        psycopg2.extras.execute_values(
            cur,
            f"""INSERT INTO {_tbl(schema,"LabTests")}
                ("Id","LabEntryId","TestId","SerialNo","Rate","DiscountPercent",
                 "DiscountAmount","NetAmount","CategoryCode","CategorySortOrder",
                 "CategorySrNo","IsReported","TestDate",
                 "CreatedAt","UpdatedAt","CreatedBy","UpdatedBy","IsDeleted")
                VALUES %s""",
            data, page_size=500,
        )
    log(f"  ✓ {len(data):,} rows inserted, {skipped} skipped  ({time.time()-t0:.1f}s)", "OK")
    _reset_seq(cur, schema, "LabTests", "Id", log)


# ─────────────────────────────────────────────────────────────────────────────
# GUI helpers
# ─────────────────────────────────────────────────────────────────────────────
def _style(root: tk.Tk):
    s = ttk.Style(root)
    s.theme_use("clam")
    s.configure(".", background=BG, foreground=FG, font=("Segoe UI", 9))
    s.configure("TFrame", background=BG)
    s.configure("TLabelframe", background=BG2, bordercolor=EBORDER,
                relief="solid", borderwidth=1)
    s.configure("TLabelframe.Label", background=BG2, foreground=ACCENT,
                font=("Segoe UI Semibold", 9))
    s.configure("TCheckbutton", background=BG2, foreground=FG,
                indicatorcolor=BG4, indicatorrelief="flat", padding=2)
    s.map("TCheckbutton",
          indicatorcolor=[("selected", ACCENT)],
          foreground=[("selected", FG), ("active", FG)])
    s.configure("TCombobox", fieldbackground=BG4, foreground=FG,
                selectbackground=ACCENT, selectforeground="white",
                arrowcolor=FG_DIM, padding=3)
    s.map("TCombobox",
          fieldbackground=[("readonly", BG4)],
          foreground=[("readonly", FG)])

    for name, bg, fg_c, abg in [
        ("Blue.TButton",  ACCENT,    "white", "#2266cc"),
        ("Grey.TButton",  BG4,       FG,      BG3),
        ("Red.TButton",   "#7a1a1a", "white", "#a02020"),
        ("Green.TButton", "#1a5c20", "white", "#22782c"),
    ]:
        s.configure(name, background=bg, foreground=fg_c,
                    font=("Segoe UI Semibold", 9), relief="flat", padding=(10, 5))
        s.map(name,
              background=[("active", abg), ("disabled", BG3)],
              foreground=[("disabled", FG_DIM)])

    s.configure("TProgressbar", troughcolor=BG3, background=ACCENT, thickness=4)
    s.configure("TSeparator", background=EBORDER)
    s.configure("TScrollbar", background=BG3, troughcolor=BG2,
                arrowcolor=FG_DIM, bordercolor=BG2, darkcolor=BG3, lightcolor=BG3)
    s.map("TScrollbar", background=[("active", BG4)])


def _entry(parent, var, show="", width=None):
    kw: dict = dict(
        textvariable=var, show=show,
        bg=BG4, fg=FG, insertbackground=FG,
        relief="flat", font=("Segoe UI", 9), bd=0,
        highlightthickness=1, highlightbackground=EBORDER,
        highlightcolor=ACCENT,
    )
    if width:
        kw["width"] = width
    e = tk.Entry(parent, **kw)
    e.bind("<FocusIn>",  lambda _: e.config(highlightbackground=ACCENT))
    e.bind("<FocusOut>", lambda _: e.config(highlightbackground=EBORDER))
    return e


def _row(parent, label: str, var, show="", lw=14):
    f = tk.Frame(parent, bg=BG2)
    f.pack(fill="x", pady=2)
    tk.Label(f, text=label, bg=BG2, fg=FG_DIM,
             font=("Segoe UI", 9), width=lw, anchor="w").pack(side="left")
    _entry(f, var, show=show).pack(
        side="left", fill="x", expand=True, ipady=3, padx=(4, 0)
    )
    return f


def _lf(parent, title: str):
    frm = ttk.LabelFrame(parent, text=f"  {title}")
    frm.pack(fill="x", pady=(0, 6), ipady=6, ipadx=8)
    return frm


# ─────────────────────────────────────────────────────────────────────────────
# Main Application
# ─────────────────────────────────────────────────────────────────────────────
class App(tk.Tk):

    _TABLES = [
        ("accounts",    "ACnPMaster",    "AccountMasters"),
        ("patients",    "PatientMaster", "Patients"),
        ("doctors",     "DoctorMaster",  "Doctors"),
        ("tests",       "TstMaster",     "TestMasters"),
        ("rates",       "RateMaster",    "RateMasters"),
        ("lab_entries", "LabEntry",      "LabEntries"),
        ("lab_tests",   "LabTests src",  "LabTests"),
    ]

    def __init__(self):
        super().__init__()
        self.title("SQL → PostgreSQL DB Migration Tool")
        self.geometry("1300x900")
        self.minsize(1050, 780)
        self.configure(bg=BG)
        _style(self)

        self._q: queue.Queue = queue.Queue()
        self._cancel = threading.Event()
        self._busy   = False

        self._build()
        self._load_creds()
        self._poll()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build(self):
        # Title bar
        hdr = tk.Frame(self, bg="#111420", height=46)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="  🗄  SQL → PostgreSQL DB Migration Tool",
                 bg="#111420", fg=FG, font=("Segoe UI Semibold", 13)).pack(
            side="left", padx=14)
        tk.Label(hdr, text="SQL Server 2008 R2  →  PostgreSQL",
                 bg="#111420", fg=FG_DIM, font=("Segoe UI", 9)).pack(
            side="right", padx=14)

        # Body: left panel (scrollable) + right log
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=12, pady=10)

        # ── Scrollable left panel ──────────────────────────────────────────
        left_outer = tk.Frame(body, bg=BG, width=380)
        left_outer.pack(side="left", fill="y")
        left_outer.pack_propagate(False)

        left_canvas = tk.Canvas(
            left_outer, bg=BG, highlightthickness=0, width=370
        )
        left_sb = ttk.Scrollbar(
            left_outer, orient="vertical", command=left_canvas.yview
        )
        left_canvas.configure(yscrollcommand=left_sb.set)

        left_sb.pack(side="right", fill="y")
        left_canvas.pack(side="left", fill="both", expand=True)

        left = tk.Frame(left_canvas, bg=BG)
        left_window = left_canvas.create_window((0, 0), window=left, anchor="nw")

        def _on_left_configure(e):
            left_canvas.configure(scrollregion=left_canvas.bbox("all"))
            left_canvas.itemconfig(left_window, width=left_canvas.winfo_width())

        left.bind("<Configure>", _on_left_configure)
        left_canvas.bind(
            "<Configure>",
            lambda e: left_canvas.itemconfig(left_window, width=e.width),
        )

        # Mouse-wheel scrolling on left panel
        def _on_mousewheel(e):
            left_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        left_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        # ─────────────────────────────────────────────────────────────────────

        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))

        self._build_source(left)
        self._build_dest(left)
        self._build_migrations(left)
        self._build_log(right)

    # ── Source ────────────────────────────────────────────────────────────────
    def _build_source(self, parent):
        frm = _lf(parent, "Source — SQL Server 2008 R2")

        self.src_instance = tk.StringVar()
        self.src_db       = tk.StringVar()
        self.src_user     = tk.StringVar(value="sa")
        self.src_pass     = tk.StringVar()
        self.src_driver   = tk.StringVar(value="ODBC Driver 17 for SQL Server")

        _row(frm, "Server\\Instance", self.src_instance)
        _row(frm, "Database",         self.src_db)
        _row(frm, "Username",         self.src_user)
        _row(frm, "Password",         self.src_pass, show="●")

        # ODBC Driver
        dr = tk.Frame(frm, bg=BG2); dr.pack(fill="x", pady=2)
        tk.Label(dr, text="ODBC Driver", bg=BG2, fg=FG_DIM,
                 font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        ttk.Combobox(
            dr, textvariable=self.src_driver, state="readonly",
            values=[
                "ODBC Driver 17 for SQL Server",
                "ODBC Driver 18 for SQL Server",
                "SQL Server Native Client 10.0",
                "SQL Server",
            ],
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Test
        br = tk.Frame(frm, bg=BG2); br.pack(fill="x", pady=(6, 0))
        ttk.Button(br, text="⚡ Test Connection", style="Blue.TButton",
                   command=self._test_src).pack(side="left")
        self._src_lbl = tk.Label(br, text="", bg=BG2, fg=FG_DIM,
                                  font=("Segoe UI", 9))
        self._src_lbl.pack(side="left", padx=8)

    # ── Destination ───────────────────────────────────────────────────────────
    def _build_dest(self, parent):
        frm = _lf(parent, "Destination — PostgreSQL")

        self.dst_host   = tk.StringVar(value="localhost")
        self.dst_port   = tk.StringVar(value="5432")
        self.dst_db     = tk.StringVar()
        self.dst_schema = tk.StringVar()
        self.dst_user   = tk.StringVar()
        self.dst_pass   = tk.StringVar()

        # Host + Port on one line
        hr = tk.Frame(frm, bg=BG2); hr.pack(fill="x", pady=2)
        tk.Label(hr, text="Host", bg=BG2, fg=FG_DIM,
                 font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        _entry(hr, self.dst_host).pack(
            side="left", fill="x", expand=True, ipady=3, padx=(4, 0))
        tk.Label(hr, text="Port", bg=BG2, fg=FG_DIM,
                 font=("Segoe UI", 9), width=5).pack(side="left", padx=(8, 0))
        _entry(hr, self.dst_port, width=7).pack(side="left", ipady=3, padx=(4, 0))

        _row(frm, "Database", self.dst_db)
        _row(frm, "Username", self.dst_user)
        _row(frm, "Password", self.dst_pass, show="●")

        # Schema
        sr = tk.Frame(frm, bg=BG2); sr.pack(fill="x", pady=2)
        tk.Label(sr, text="Schema", bg=BG2, fg=FG_DIM,
                 font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        self._schema_cb = ttk.Combobox(
            sr, textvariable=self.dst_schema, state="readonly", width=20)
        self._schema_cb.pack(side="left", padx=(4, 4), ipady=2)
        ttk.Button(sr, text="⟳", style="Grey.TButton", width=3,
                   command=self._load_schemas).pack(side="left")

        # Save creds checkbox
        cr = tk.Frame(frm, bg=BG2); cr.pack(fill="x", pady=(4, 0))
        self._save_creds_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(cr, text="Save credentials",
                        variable=self._save_creds_var).pack(side="left")

        # Test
        br = tk.Frame(frm, bg=BG2); br.pack(fill="x", pady=(6, 0))
        ttk.Button(br, text="⚡ Test Connection", style="Blue.TButton",
                   command=self._test_dst).pack(side="left")
        self._dst_lbl = tk.Label(br, text="", bg=BG2, fg=FG_DIM,
                                  font=("Segoe UI", 9))
        self._dst_lbl.pack(side="left", padx=8)

    # ── Migration selector ────────────────────────────────────────────────────
    def _build_migrations(self, parent):
        frm = _lf(parent, "Select Migrations")
        self._mig_vars: dict[str, tk.BooleanVar] = {}

        for key, src, dst in self._TABLES:
            var = tk.BooleanVar(value=True)
            self._mig_vars[key] = var
            r = tk.Frame(frm, bg=BG2); r.pack(fill="x", pady=1)
            ttk.Checkbutton(r, variable=var).pack(side="left")
            tk.Label(r, text=f" {src}", bg=BG2, fg=FG,
                     font=("Segoe UI Semibold", 9), width=16,
                     anchor="w").pack(side="left")
            tk.Label(r, text=" →", bg=BG2, fg=ACCENT,
                     font=("Segoe UI", 9)).pack(side="left")
            tk.Label(r, text=f" {dst}", bg=BG2, fg=FG,
                     font=("Segoe UI", 9), anchor="w").pack(side="left")

        sel = tk.Frame(frm, bg=BG2); sel.pack(fill="x", pady=(6, 4))
        ttk.Button(sel, text="All",  style="Grey.TButton", width=5,
                   command=lambda: [v.set(True)  for v in self._mig_vars.values()]
                   ).pack(side="left", padx=(0, 4))
        ttk.Button(sel, text="None", style="Grey.TButton", width=5,
                   command=lambda: [v.set(False) for v in self._mig_vars.values()]
                   ).pack(side="left")

        ttk.Separator(frm, orient="horizontal").pack(fill="x", pady=6)

        self._start_btn = ttk.Button(
            frm, text="▶  Start Migration",
            style="Green.TButton", command=self._start)
        self._start_btn.pack(fill="x", pady=(0, 4))

        self._cancel_btn = ttk.Button(
            frm, text="■  Cancel",
            style="Red.TButton", command=self._do_cancel, state="disabled")
        self._cancel_btn.pack(fill="x")

        self._prog = ttk.Progressbar(frm, mode="indeterminate")
        self._prog.pack(fill="x", pady=(8, 0))

    # ── Log ───────────────────────────────────────────────────────────────────
    def _build_log(self, parent):
        hdr = tk.Frame(parent, bg=BG2, height=28)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="  Migration Log", bg=BG2, fg=FG,
                 font=("Segoe UI Semibold", 10)).pack(side="left", pady=4)
        ttk.Button(hdr, text="Clear Log", style="Grey.TButton",
                   command=self._clear_log).pack(side="right", padx=6, pady=2)
        ttk.Button(hdr, text="Save Log", style="Grey.TButton",
                   command=self._save_log).pack(side="right", pady=2)

        tf = tk.Frame(parent, bg=BG)
        tf.pack(fill="both", expand=True, pady=(2, 0))

        self._log = tk.Text(
            tf, bg="#0e1018", fg=FG, font=("Consolas", 9),
            relief="flat", state="disabled", wrap="none",
            highlightthickness=0, bd=0, selectbackground=BG4,
        )
        vsb = ttk.Scrollbar(tf, orient="vertical",   command=self._log.yview)
        hsb = ttk.Scrollbar(tf, orient="horizontal", command=self._log.xview)
        self._log.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right",  fill="y")
        hsb.pack(side="bottom", fill="x")
        self._log.pack(fill="both", expand=True)

        self._log.tag_configure("TS",       foreground="#4a6080")
        self._log.tag_configure("INFO",     foreground=FG)
        self._log.tag_configure("OK",       foreground=GREEN)
        self._log.tag_configure("HEAD",     foreground=ACCENT,
                                font=("Consolas", 9, "bold"))
        self._log.tag_configure("WARN",     foreground=ORANGE)
        self._log.tag_configure("WARN_DIM", foreground="#a07020")
        self._log.tag_configure("DIM",      foreground=FG_DIM)
        self._log.tag_configure("ERROR",    foreground=RED,
                                font=("Consolas", 9, "bold"))
        self._log.tag_configure("START",    foreground="white",
                                font=("Consolas", 10, "bold"))

    # ── Credentials ───────────────────────────────────────────────────────────
    def _load_creds(self):
        if not os.path.exists(CRED_FILE):
            return
        try:
            with open(CRED_FILE, encoding="utf-8") as f:
                c = json.load(f)
            s, d = c.get("source", {}), c.get("dest", {})
            for attr, val in [
                ("src_instance", s.get("instance")),
                ("src_db",       s.get("database")),
                ("src_user",     s.get("username")),
                ("src_pass",     s.get("password")),
                ("src_driver",   s.get("driver")),
                ("dst_host",     d.get("host")),
                ("dst_port",     d.get("port")),
                ("dst_db",       d.get("database")),
                ("dst_user",     d.get("username")),
                ("dst_pass",     d.get("password")),
                ("dst_schema",   d.get("schema")),
            ]:
                if val:
                    getattr(self, attr).set(val)
        except Exception:
            pass

    def _save_creds(self):
        if not self._save_creds_var.get():
            return
        c = {
            "source": {
                "instance": self.src_instance.get(),
                "database": self.src_db.get(),
                "username": self.src_user.get(),
                "password": self.src_pass.get(),
                "driver":   self.src_driver.get(),
            },
            "dest": {
                "host":     self.dst_host.get(),
                "port":     self.dst_port.get(),
                "database": self.dst_db.get(),
                "username": self.dst_user.get(),
                "password": self.dst_pass.get(),
                "schema":   self.dst_schema.get(),
            },
        }
        with open(CRED_FILE, "w", encoding="utf-8") as f:
            json.dump(c, f, indent=2)

    # ── Connections ───────────────────────────────────────────────────────────
    def _src_conn_str(self) -> str:
        drv = self.src_driver.get()
        srv = self.src_instance.get()
        db  = self.src_db.get()
        usr = self.src_user.get()
        pwd = self.src_pass.get()
        return (
            f"DRIVER={{{drv}}};SERVER={srv};DATABASE={db};"
            f"UID={usr};PWD={pwd};TrustServerCertificate=yes"
        )

    def _pg_conn(self):
        return psycopg2.connect(
            host=self.dst_host.get(),
            port=int(self.dst_port.get() or 5432),
            dbname=self.dst_db.get(),
            user=self.dst_user.get(),
            password=self.dst_pass.get(),
        )

    def _test_src(self):
        if not PYODBC_OK:
            self._src_lbl.config(text="✗ pyodbc not installed", fg=RED)
            return
        try:
            conn = pyodbc.connect(self._src_conn_str(), timeout=8)
            ver  = conn.execute("SELECT @@VERSION").fetchone()[0].split("\n")[0].strip()
            conn.close()
            self._src_lbl.config(text=f"✓ {ver[:70]}", fg=GREEN)
        except Exception as e:
            self._src_lbl.config(text=f"✗ {e}", fg=RED)

    def _test_dst(self):
        try:
            conn = self._pg_conn()
            cur  = conn.cursor()
            cur.execute("SELECT version()")
            ver  = cur.fetchone()[0].split(",")[0]
            conn.close()
            self._dst_lbl.config(text=f"✓ {ver}", fg=GREEN)
        except Exception as e:
            self._dst_lbl.config(text=f"✗ {e}", fg=RED)

    def _load_schemas(self):
        try:
            conn = self._pg_conn()
            cur  = conn.cursor()
            cur.execute("""
                SELECT schema_name FROM information_schema.schemata
                WHERE schema_name NOT LIKE 'pg_%'
                  AND schema_name NOT IN ('information_schema')
                ORDER BY schema_name
            """)
            schemas = [r[0] for r in cur.fetchall()]
            conn.close()
            self._schema_cb["values"] = schemas
            if schemas and not self.dst_schema.get():
                self._schema_cb.current(0)
            self._dst_lbl.config(
                text=f"✓ {len(schemas)} schema(s) loaded", fg=GREEN)
        except Exception as e:
            self._dst_lbl.config(text=f"✗ {e}", fg=RED)

    # ── Start ─────────────────────────────────────────────────────────────────
    def _start(self):
        if self._busy:
            return
        selected = [k for k, v in self._mig_vars.items() if v.get()]
        if not selected:
            messagebox.showwarning("Nothing selected",
                                   "Select at least one table.")
            return
        schema = self.dst_schema.get()
        if not schema:
            messagebox.showwarning("No schema",
                                   "Select a destination schema.\n"
                                   "Click ⟳ to load schemas from the server.")
            return
        if not messagebox.askyesno(
            "Confirm Migration",
            f"Migrate to schema  '{schema}' ?\n\n"
            + "\n".join(f"  • {k}" for k in selected),
        ):
            return

        self._busy = True
        self._cancel.clear()
        self._start_btn.config(state="disabled")
        self._cancel_btn.config(state="normal")
        self._prog.start(15)
        self._save_creds()

        threading.Thread(
            target=self._worker, args=(selected, schema), daemon=True
        ).start()

    def _worker(self, selected: list[str], schema: str):
        now = datetime.now(tz=timezone.utc)

        def log(msg: str, level: str = "INFO"):
            ts = datetime.now().strftime("%H:%M:%S")
            self._q.put((ts, msg, level))

        def stopped() -> bool:
            if self._cancel.is_set():
                log("⚠  Cancelled by user.", "WARN")
                return True
            return False

        log("Starting migration", "START")
        log("", "INFO")

        mssql = pg = pg_cur = None
        ok = False
        try:
            if not PYODBC_OK:
                raise RuntimeError(
                    "pyodbc not installed.\nRun:  pip install pyodbc"
                )

            log(f"• Connecting SQL Server: {self.src_instance.get()}", "INFO")
            mssql = pyodbc.connect(self._src_conn_str())
            ver = mssql.execute("SELECT @@VERSION").fetchone()[0].split("\n")[0].strip()
            log(f"  ✓ {ver[:80]}", "OK")

            pg_dsn = (f"{self.dst_host.get()}:{self.dst_port.get()}"
                      f"/{self.dst_db.get()}")
            log(f"• Connecting PostgreSQL: {pg_dsn}", "INFO")
            pg = self._pg_conn()
            pg.autocommit = False
            pg_cur = pg.cursor()
            pg_cur.execute("SELECT version()")
            pg_ver = pg_cur.fetchone()[0].split(",")[0]
            log(f"  ✓ {pg_ver}  (schema: {schema})", "OK")
            log("", "INFO")

            # Fetch all needed source tables upfront
            acnp = (_fetch(mssql, "ACnPMaster", log)
                    if any(k in selected for k in ("accounts", "patients", "rates"))
                    else [])
            pts  = _fetch(mssql, "PatientMaster", log) if "patients" in selected else []
            docs = _fetch(mssql, "DoctorMaster",  log) if "doctors"  in selected else []
            tsts = _fetch(mssql, "TstMaster",     log) if "tests"    in selected else []
            mmst = _fetch(mssql, "MMST",          log) if "tests"    in selected else []
            desr = _fetch(mssql, "tstMasterDesr", log) if "tests"    in selected else []
            rats  = _fetch(mssql, "RateMaster",    log) if "rates"       in selected else []
            lents = _fetch(mssql, "LabEntry",       log) if "lab_entries" in selected else []
            ltsts = _fetch(mssql, "LabTests",       log) if "lab_tests"   in selected else []
            mssql.close(); mssql = None
            log("", "INFO")

            # Ensure all target tables exist (recreates any that were dropped)
            _ensure_schema(pg_cur, schema, log)
            pg.commit()
            log("", "INFO")

            if "accounts" in selected and not stopped():
                migrate_accounts(pg_cur, schema, acnp, log, now)
                pg.commit(); log("", "INFO")

            if "patients" in selected and not stopped():
                migrate_patients(pg_cur, schema, pts, log, now)
                pg.commit(); log("", "INFO")

            if "doctors" in selected and not stopped():
                migrate_doctors(pg_cur, schema, docs, log, now)
                pg.commit(); log("", "INFO")

            if "tests" in selected and not stopped():
                migrate_tests(pg_cur, schema, tsts, mmst, desr, log, now)
                migrate_sample_specimen_rules(pg_cur, schema, log, now)
                pg.commit(); log("", "INFO")

            if "rates" in selected and not stopped():
                migrate_rate_masters(pg_cur, schema, rats, log, now)
                pg.commit(); log("", "INFO")

            if "lab_entries" in selected and not stopped():
                migrate_lab_entries(pg_cur, schema, lents, log, now)
                pg.commit(); log("", "INFO")

            if "lab_tests" in selected and not stopped():
                migrate_lab_tests(pg_cur, schema, ltsts, log, now)
                pg.commit(); log("", "INFO")

            ok = True
            log("✅  Migration completed successfully!", "OK")

        except Exception:
            if pg:
                try: pg.rollback()
                except Exception: pass
            log("", "ERROR")
            log("❌  Migration FAILED — rolled back.", "ERROR")
            for line in traceback.format_exc().splitlines():
                log(f"   {line}", "ERROR")
        finally:
            self._q.put(("__DONE__", "ok" if ok else "err", ""))
            for conn in (pg_cur, pg, mssql):
                try:
                    if conn: conn.close()
                except Exception: pass

    def _do_cancel(self):
        self._cancel.set()
        self._cancel_btn.config(state="disabled")

    # ── Log polling ───────────────────────────────────────────────────────────
    def _poll(self):
        try:
            while True:
                item = self._q.get_nowait()
                if item[0] == "__DONE__":
                    self._busy = False
                    self._prog.stop()
                    self._start_btn.config(state="normal")
                    self._cancel_btn.config(state="disabled")
                else:
                    ts, msg, level = item
                    self._append(ts, msg, level)
        except queue.Empty:
            pass
        self.after(60, self._poll)

    def _append(self, ts: str, msg: str, level: str):
        self._log.configure(state="normal")
        self._log.insert("end", f"[{ts}]  ", "TS")
        self._log.insert("end", msg + "\n", level)
        self._log.see("end")
        self._log.configure(state="disabled")

    def _clear_log(self):
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")

    def _save_log(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt")],
            initialfile=f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._log.get("1.0", "end"))


# ─── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
