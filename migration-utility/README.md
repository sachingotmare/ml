# NIDAN Migration Utility — v3.0

GUI tool to migrate data from **SQL Server 2008 R2 (NIDANNEW)** to **PostgreSQL (MLab)**.

---

## Quick Start

```
python migration_tool.py
```

Requires Python 3.10+. Install dependencies once:

```
pip install pyodbc psycopg2-binary
```

---

## Requirements

| Component | Version |
|---|---|
| Python | 3.10 + |
| pyodbc | Any recent |
| psycopg2-binary | Any recent |
| SQL Server ODBC Driver | 17 or 18 |
| Tkinter | Bundled with Python (Windows) |

---

## Files

| File | Purpose |
|---|---|
| `migration_tool.py` | Main GUI application (~1,364 lines) |
| `schema_setup.sql` | PostgreSQL DDL for all 5 core tables (`pg_dump --schema-only` of `mlab_demo/lab_demo2026`) — used by `_ensure_schema` to auto-create missing tables |
| `README.md` | This document |

---

## Credentials

### Source — SQL Server

| Field | Value |
|---|---|
| Server | `SGSOFTECH\SGSOFTECHSQL2008` |
| Database | `NIDANNEW` |
| Username | `sa` |

### Destination — PostgreSQL (Server)

| Field | Value |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Username | `MLabUser` |
| Password | `MLabUser@123456` |

### Destination — PostgreSQL (Local Dev)

| Field | Value |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Username | `postgres` |
| Password | `poSt1234` |
| Database | `mlab_demo` |

### Server PostgreSQL Databases & Schemas

| Database | Schemas |
|---|---|
| `MLab_DEMO` | `lab_demo2026`, `lab_test` |
| `MLab_GUNJAN` | `lab_gunjangg`, `lab_gunjanmain`, `lab_gunjanrly` |
| `MLab_NIDAN` | `lab_nidanmain` |

---

## Usage

1. Fill in **Source** (SQL Server) connection details
2. Fill in **Destination** (PostgreSQL) connection details
3. Click **? Load** to populate the schema dropdown, then select your schema
4. Click **Test Connection** on both panels to verify
5. Check the tables you want to migrate
6. Click **? Start Migration**
7. Watch the live log — colour-coded by level (INFO / WARNING / ERROR)
8. Use **Save Log** to export the run log for auditing

---

## Tables Migrated

| Source (SQL Server) | Destination (PostgreSQL) | Strategy |
|---|---|---|
| `ACnPMaster` | `AccountMasters` | **No truncate — Upsert by Name** — preserves existing system/default entries |
| `PatientMaster` | `Patients` | Truncate ? bulk insert (5,000-row batches) |
| `DoctorMaster` | `Doctors` | Truncate ? bulk insert (500-row batches) |
| `TstMaster` + `MMST` | `TestMasters` + `TestGroupMappings` | Truncate ? 3-phase insert; orphan GROUP tests auto-created |
| `RateMaster` | `RateMasters` | Truncate ? insert explicit rates; Rate=0 auto-filled for missing tests |

---

## Migration Logic — Table by Table

### Schema Auto-Setup (`_ensure_schema`)

Before any migration runs, the tool checks whether the 5 core tables exist in the target schema.
If any are missing it reads `schema_setup.sql` and creates them automatically.

| Step | Detail |
|---|---|
| Existence check | Queries `information_schema.tables` for all 5 tables |
| DDL source | `schema_setup.sql` — full DDL stripped of `\` psql meta-commands |
| Schema substitution | Every occurrence of `lab_demo2026` in the DDL is replaced with the target schema name |
| CREATE SCHEMA | Executed in an isolated savepoint; `42P06` (duplicate schema) is silently skipped |
| Statement execution | DDL is parsed **line-by-line** (not by `;` split, to avoid false splits inside `--` comments); only lines starting with a recognised SQL keyword are executed |
| Error handling | Per-statement savepoints — the following pgcodes are silently skipped: `42P07` (dup table), `42710` (dup object), `42P06` (dup schema), `42P16` (multiple PKs), `42830` (invalid FK), `23503` (FK violation), `23505` (unique violation), `42704` (undefined object) |
| Post-verification | After DDL execution, the existence check is repeated; migration aborts if any table is still missing |

---

### 1 · ACnPMaster ? AccountMasters

**Strategy: No TRUNCATE. Upsert by Name — existing system/default entries are never touched.**

> Why no truncate? The application pre-creates essential rows (`ZZZZZZ` — General walk-in,
> `CASH01`, `BANK01`) during initial setup. Truncating would break patient and rate links.

| Step | Detail |
|---|---|
| Load existing | Reads all current `Id`, `Name` (uppercase), `Code` (uppercase) into memory |
| Next Id | `MAX(existing Id) + 1` — never reuses an existing Id |
| Skip rule | Row skipped if `Name` already exists (case-insensitive) **or** `Code` already taken |
| Field mapping | `Code` ? Code (=20 chars), `Name` ? Name, `Type` ? AccountType (1 char, default `C`), `CreditBal` ? OpeningBalance, `PhNo`/`PhNoM` ? Phone/Mobile, `PAN` ? GSTNumber |
| Defaults | `AccountGroupId = NULL`, `IsActive = True`, `IsDeleted = False` |
| Batch size | 500 rows per insert |

Log output example:
```
? 48 rows inserted, 5 skipped (name already exists)  (0.0s)
```

---

### 2 · PatientMaster ? Patients

**Strategy: Full truncate + bulk re-insert in 5,000-row batches.**

| Step | Detail |
|---|---|
| TRUNCATE | `TRUNCATE … RESTART IDENTITY CASCADE` clears all existing rows |
| Default account | Looks up `AccountMasters` where `Code = 'ZZZZZZ'`; its `Id` is used as `AccountId` for every patient |
| Skip rule | Row skipped if `PtCode` is blank |
| Batch size | 5,000 rows per flush; progress logged after each batch |
| Sequence reset | `_reset_seq` called after insert to sync the identity sequence |

**Field mapping:**

| Source | Destination | Notes |
|---|---|---|
| `PtCode` | `PtCode` | Max 20 chars |
| `PtName` | `PtName` | Max 200 chars; default `Unknown` |
| `Title` | `Title` | Normalised via TITLE_MAP (see below) |
| `Gender` | `Gender` | `M`?`Male`, `F`?`Female`, others?`Unknown` |
| `Age` | `Age` | Integer |
| `AgeType` | `AgeUnit` | `YEARS`/`Y`?`Y`, `MONTHS`/`M`?`M`, `DAYS`/`D`?`D` |
| `DateOfBirth` | `DateOfBirth` | Always `NULL` (source values unreliable) |
| `BloodGrp` | `BloodGroup` | Default `O+` if blank |
| `PhNoM` | `Mobile` + `WhatsApp` | Same value used for both |
| `CtCode` | `City` | |
| `Address` | `Address` | |
| `Email` | `Email` | |
| `History` | `History` | |

**Title normalisation (TITLE_MAP):**

| Source value(s) | Mapped to | Note |
|---|---|---|
| `MR`, `MR.`, `SHRI`, `MD.` | `Mr` | |
| `MRS`, `MRS.`, `SMT`, `SMT.` | `Mrs` | |
| `MISS`, `KU`, `KU.`, `MS`, `MS.` | `Miss` | |
| `DR`, `DR.` | `Dr` | |
| `MASTER` | `Master` | |
| `BABY` | `Baby` | |
| `B/O`, `B/O.` | `Baby` | **Fixed** — was `"Baby of"`, which caused EF Core enum deserialisation failure (enum values cannot contain spaces) |
| *(anything else)* | `Mr` | Safe fallback |

Log output example:
```
? 94,500 rows inserted in 6.6s
```

---

### 3 · DoctorMaster ? Doctors

**Strategy: Full truncate + bulk re-insert.**

| Step | Detail |
|---|---|
| TRUNCATE | `TRUNCATE … RESTART IDENTITY CASCADE` |
| Skip rule | Row skipped if `Code` is blank |
| Batch size | 500 rows per insert |
| Sequence reset | `_reset_seq` called after insert |

**Field mapping:**

| Source | Destination | Notes |
|---|---|---|
| `Code` | `Code` | Max 20 chars |
| `Name` | `Name` | Max 200 chars; default `Unknown` |
| `Title` | `Title` | `DR`?`Dr`, `MR`?`Mr`, `MRS`?`Mrs`, `MISS`?`Miss`; default `Dr` |
| `DocType` | `DoctorType` | `P`?`REFERRAL`, `I`?`INTERNAL`, `B`?`BOTH`; default `REFERRAL` |
| `Designation` | `Designation` | |
| `Qualification` | `Qualification` | Default `MBBS` if blank |
| `PhoneNo` | `Phone` | |
| `MobNo` | `Mobile` | |
| `EmailId` | `Email` | |
| `VisitCharges` | `VisitCharges` | Float |
| `TimeIn` / `TimeOut` | `TimeIn` / `TimeOut` | Time portion only |
| — | `CommissionPercent` | Always `0` |
| — | `DepartmentId`, `CategoryId` | Always `NULL` |

Log output example:
```
? 708 rows inserted in 0.0s
```

---

### 4 · TstMaster + MMST ? TestMasters + TestGroupMappings

**Strategy: Full truncate of both tables, then three-phase insert.**

#### Phase A — TestMasters from TstMaster

| Step | Detail |
|---|---|
| TRUNCATE | Clears `TestMasters` **and** `TestGroupMappings` (CASCADE) |
| Skip rule | Row skipped if `SubTCode` or `SubTName` is blank |
| Duplicate TName | If TName already used in this batch, suffix `[SubTCode]` is appended to make it unique; logged as WARNING |
| TestType mapping | `GRP`?`GROUP`, `CALC`?`FORMULA`, `TEXT`?`FORMATTED`, others?`READING` |
| DepartmentCode / CategoryCode | Derived from first characters of `TCode` via `_lookup_tcode()` |
| Batch size | 200 rows per insert |

#### Phase B — Orphan GROUP tests from MMST

Some panel groups are referenced in `MMST` (as `CODE1` values) but have no matching row in
`TstMaster`. These are auto-created as minimal `GROUP`-type tests so that mapping foreign keys
are satisfied:

- `TCode` = `CODE1`
- `TName` = `[GROUP] CODE1`
- `TestType` = `GROUP`
- All other fields set to safe defaults

#### Phase C — TestGroupMappings from MMST GRIV rows

| Step | Detail |
|---|---|
| Source filter | Only MMST rows where `MTYPE = 'GRIV'` (group-member relationships) |
| Valid codes | Both `CODE1` (group) and `CODE2` (member) must exist in TestMasters |
| Skip rules | Either code missing ? skipped; duplicate `(CODE1, CODE2)` pair ? skipped |
| Field mapping | `CODE1`?`GroupTestCode`, `CODE2`?`SubTestCode`, `SlNo`?`SortOrder` |

Log output example:
```
? 25 duplicate TName rows skipped
? 631 rows inserted in 0.1s
? 16 orphan GROUP tests added from MMST
? 256 mappings inserted  (skipped=25)
```

---

### 5 · RateMaster ? RateMasters

**Strategy: Full truncate + explicit rates + auto-fill default Rate=0.**

#### Phase A — Explicit rates from RateMaster

| Step | Detail |
|---|---|
| TRUNCATE | `TRUNCATE … RESTART IDENTITY CASCADE` |
| Lookup maps | Builds `TCode ? TestId` and `AccountCode ? AccountId` from current DB state (after tests and accounts are already migrated) |
| TCode parsing | `TCodeSlno[:7]` = TCode (first 7 chars); remainder = SlNo (unused) |
| Skip rules | TCode not in TestMasters ? skipped; AccountCode not in AccountMasters ? skipped; duplicate `(TestId, AccountId)` pair ? skipped |
| Field mapping | `Rate` ? Rate (float), `Desr` ? Description |
| Insert | Sequential `Id` prepended; `ON CONFLICT DO NOTHING` as safety net |

#### Phase B — Default Rate=0 auto-fill

Every test must have at least one rate entry (required by the application). After Phase A, the
tool inserts `Rate = 0.00` for every test in `TestMasters` that has **no** rate entry under the
`ZZZZZZ` (General/Walk-in) account. IDs are assigned as `MAX(Id) + ROW_NUMBER()`.

Log output example:
```
? 9,579 rates inserted  skipped=4341  total=9,747  (0.5s)
```

---

## Sequence Reset (`_reset_seq`)

After every TRUNCATE + bulk insert, the tool calls `_reset_seq` to bring the PostgreSQL identity
sequence back in sync with the actual `MAX(Id)` in the table.

### Why it is needed

PostgreSQL identity sequences are **not** updated by bulk `INSERT … VALUES (explicit_id, …)`.
After migration the sequence may still be at 1, causing the next application INSERT to fail with
`duplicate key violates unique constraint`.

### How it works

```
1.  Try pg_get_serial_sequence(schema.table, col)
      ? works for SERIAL columns
2.  Fall back to:
      SELECT sequencename FROM pg_sequences
       WHERE schemaname = %s
         AND sequencename ILIKE %s || '_{col}%'
      ? works for GENERATED BY DEFAULT AS IDENTITY columns
3.  SELECT MAX(col) FROM schema.table
4.  SELECT setval(seq, GREATEST(maxv, 1), true)
```

Each `_reset_seq` call is wrapped in a `SAVEPOINT` so a failure (e.g. table has no rows) does
not abort the outer transaction.

> **Bug fixed:** Earlier versions used `sequence_schema` / `sequence_name` column names in
> `pg_sequences`, which do not exist in PostgreSQL 18. Corrected to `schemaname` /
> `sequencename`.

---

## Transaction Model

Each table is committed independently:

```
_ensure_schema()  --- commit
AccountMasters    --- commit
Patients          --- commit
Doctors           --- commit
TestMasters       --- commit
RateMasters       --- commit
```

A failure in any table rolls back **only that table** and stops the migration immediately,
showing the full traceback in the log. Previously committed tables remain in the database.

---

## Last Known Good Run (Server)

| Table | Rows inserted |
|---|---|
| AccountMasters | 53 (upserted; ~5 skipped as already existing) |
| Patients | 94,500 |
| Doctors | 708 |
| TestMasters | 647 |
| TestGroupMappings | 256 |
| RateMasters | 9,747 (9,579 explicit + ~168 default Rate=0) |

---

## Known Behaviours & Fixes Applied

| Behaviour / Bug | Explanation / Fix |
|---|---|
| `DateOfBirth` always `NULL` | Source DOB values are unreliable (zeroes / invalid dates) |
| `BloodGroup` defaults to `O+` | Source field is often blank |
| `B/O` maps to `Baby` (not `Baby of`) | **Fixed** — EF Core cannot deserialise enum values that contain spaces; 317 existing rows updated on server |
| AccountMasters not truncated | Preserves system/default accounts (`ZZZZZZ`, `CASH01`, `BANK01`) created by the application at setup |
| `_ensure_schema` SyntaxError at `\\` | **Fixed** — psql meta-commands (`\restrict`, `\unrestrict`) stripped before DDL execution |
| `_ensure_schema` SyntaxError on `--` comment with `;` | **Fixed** — DDL parsed line-by-line by SQL keyword, not by splitting on `;` |
| Duplicate table/object errors in `_ensure_schema` | **Fixed** — per-statement savepoints; pgcodes `42P07`, `42710`, `42P06`, `42P16`, `42830`, `23503`, `23505`, `42704` all silently skipped |
| `PK_Patients duplicate key` after migration | **Fixed** — `_reset_seq` syncs identity sequences after bulk inserts |
| `column "sequence_schema" does not exist` | **Fixed** — corrected to `schemaname` / `sequencename` (PostgreSQL 18 `pg_sequences` column names) |
| ~4,300 RateMaster rows skipped | Rates reference test codes that no longer exist in `TstMaster` |
| ~25 TestMaster duplicate TNames | Same test name registered under multiple dept codes in source; suffix `[SubTCode]` applied |
