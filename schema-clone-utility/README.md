# PostgreSQL Schema Clone Tool

A dark-themed GUI utility to **drop and clone** a PostgreSQL schema into another schema on the same or a different server.  
Based on the logic from `fix_identity_server.sql`.

---

## Features

| Block | Operation |
|-------|-----------|
| **Block 1** | Drop all tables in the **target** schema (CASCADE) |
| **Block 2** | Clone every table from **source** → **target** using `LIKE … INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING GENERATED INCLUDING IDENTITY INCLUDING INDEXES` then copies all rows |
| **Block 3** | Sync all `IDENTITY` / serial sequences to `MAX(Id)` so inserts work correctly after clone |
| **Block 4** | Verify row counts in the target schema |

- **Save credentials** — connection details are stored in `credentials.json` next to the script (passwords included — keep the file private)
- **Source & Target** can be the same server/database (different schemas) or entirely separate servers
- **"Same as Source server"** button copies all source connection fields to target in one click
- **Schema dropdowns** — click **⟳** to load available schemas from the connected server
- **Cancel** button stops the operation mid-way
- **Save Log** exports the full session log to a `.log` file

---

## Requirements

- Python 3.15+
- `psycopg2-binary`

```bash
pip install psycopg2-binary
```

---

## Run

**Windows (double-click):**
```
run.bat
```

**Any platform:**
```bash
python clone_tool.py
```

---

## Typical Workflow

1. Fill in **Source** connection (host, port, database, user, password) and click **⚡ Test Connection**  
   → Schemas are loaded automatically into the dropdown
2. Select the **source schema** (e.g. `lab_test1`)
3. Fill in **Target** connection — or click **⬇ Same as Source server** if cloning within the same DB
4. Select / type the **target schema** (e.g. `lab_demo2026`)
5. Choose which blocks to run (all 4 are selected by default)
6. Click **▶ Start Clone** and confirm

---

## credentials.json (auto-generated)

```json
{
  "source": {
    "host": "localhost",
    "port": "5432",
    "database": "mydb",
    "username": "postgres",
    "password": "secret",
    "schema": "lab_test1"
  },
  "dest": {
    "host": "localhost",
    "port": "5432",
    "database": "mydb",
    "username": "postgres",
    "password": "secret",
    "schema": "lab_demo2026"
  }
}
```

> **Security note:** Do not commit `credentials.json` to source control.  
> Add it to `.gitignore`.

---

## Based on

`fix_identity_server.sql` — the four DO $$ blocks for drop, clone, sequence sync, and verification.
