# Postgres Backup Master

Dark-themed desktop backup utility for PostgreSQL, inspired by SQL Backup Master.

## Features

- SQL Backup Master-like dark UI with left navigation
- Home dashboard (status, upcoming backups, recent history, scheduler state)
- Multiple backup jobs
- Manual backup (`Run Now`)
- Daily schedule per job (`HH:MM`)
- Destination types: `local`, `gdrive`, `onedrive`
- Direct cloud API upload/download with account sign-in
- Schema-aware backup selection per database
- Nested archive output: schema ZIP files inside database ZIP
- Retention cleanup:
  - max age in days
  - max backup copies
- Backup history panel
- Connection test per job
- Configurable `pg_dump` path


## Requirements

- Python 3.10+
- PostgreSQL client tools (`pg_dump`) installed
- `psycopg2-binary`
- Google Drive API + OneDrive API dependencies (see `requirements.txt`)

Install dependency:

```bash
pip install -r requirements.txt
```

## Run

Windows:

- Double-click `run.bat`

Or from terminal:

```bash
python backup_master.py
```

## First-time setup

1. Open app
2. Click **Add**
3. Fill database credentials
4. Choose schemas with **Select** (or enable **Backup all user schemas**)
5. Choose destination type + destination folder
6. Optional: enable schedule and set daily time
7. Save job
8. Select job and click **Run Now**

## Cloud sign-in (direct API)

Use **Settings**:

- **Sign In Google**
  - Set `google client secret json` first (OAuth desktop app credentials).
- **Sign In OneDrive**
  - Set `onedrive client id` (App Registration client ID)
  - Optional tenant: `common` (default)

After sign-in, backups can upload directly to cloud folders and restores can download directly from cloud.

You can also use **Cloud Setup Wizard** from Settings for guided sign-in and connection testing.

## Run when app is closed (Background)

By default, scheduled backups run only while the app is open.

To run schedules even when UI is closed:

1. Open **Settings**
2. Click **Install Background Scheduler**

This creates a Windows Task Scheduler task named `PostgresBackupMasterScheduler` that runs every 5 minutes and executes due jobs.

Main dashboard also shows **Scheduler** status: `Installed`, `Not Installed`, or `Unknown`.

Troubleshooting scheduler:

1. Click **Run Scheduler Now** in Settings
2. Click **Open Scheduler Log** and verify execution entries
3. If needed, remove and reinstall scheduler task

If log shows `No scheduled jobs due`, check:

- job `Enabled` is checked
- `Enable Daily Schedule` is checked
- schedule time has passed for today
- job not already run today (`last_scheduled_date`)

For server deployments with multiple app copies, scheduler runner now sets explicit config path. You can also override config file manually with environment variable `PBM_CONFIG_FILE`.

You can remove it later using **Remove Scheduler**.

## Notes

- Backup file format supports `custom`, `plain`, and `tar`.
- Compression applies to `custom` and `tar` format.
- Passwords are saved in plain text in `backup_config.json` (same folder). Keep this folder private.
- If `pg_dump` is not in `PATH`, set full path from **Settings**.
- Optional ZIP output for created backups

## Restore

- Select a job, then click **Restore**
- Choose a backup file: `.zip`, `.backup`, `.dump`, `.tar`, or `.sql`
- Safety lock: type the exact database name to continue
- Restore runs into that job's configured database
- If database ZIP contains schema ZIPs, restore auto-applies matching schemas from the job in one click
  - Example: if job has schemas `lab_demo2026, public`, only those schema archives are restored.
- Tool usage:
  - `.backup` / `.dump` / `.tar` → `pg_restore`
  - `.sql` → `psql`

Use **Settings** to configure `pg_dump`, `pg_restore`, and `psql` paths (or keep `auto`).

## CLI modes (used by scheduler)

- `python backup_master.py --run-due-jobs`
- `python backup_master.py --run-job "Job Name"`
