"""
PostgreSQL Schema Clone Tool  v1.0
====================================
Drop & Clone one PostgreSQL schema into another on the same (or different) server.

Operations performed:
  Block 1 – Drop all tables in target schema
  Block 2 – Clone source → target  (LIKE … INCLUDING IDENTITY INCLUDING INDEXES …)
  Block 3 – Sync all IDENTITY / serial sequences to MAX(Id)
  Block 4 – Verify row counts

Requirements:  pip install psycopg2-binary
"""
from __future__ import annotations

import json
import os
import queue
import threading
import time
import tkinter as tk
import traceback
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import psycopg2
import psycopg2.extras

# ─── Colours ─────────────────────────────────────────────────────────────────
BG      = "#0e1a18"
BG2     = "#122420"
BG3     = "#172e29"
BG4     = "#1e3d36"
FG      = "#d4ede8"
FG_DIM  = "#5a9080"
ACCENT  = "#1abc9c"
GREEN   = "#2ecc71"
ORANGE  = "#f39c12"
RED     = "#e74c3c"
EBORDER = "#245048"

CRED_FILE = os.path.join(os.path.dirname(__file__), "credentials.json")

# ─── SQL blocks (parameterised at runtime) ───────────────────────────────────

def _sql_drop_tables(target: str) -> str:
    return f"""
DO $$
DECLARE r RECORD;
BEGIN
    FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = '{target}' ORDER BY tablename
    LOOP
        EXECUTE format('DROP TABLE IF EXISTS {target}.%I CASCADE', r.tablename);
        RAISE NOTICE 'Dropped: %', r.tablename;
    END LOOP;
END $$;
"""

def _sql_clone_tables(source: str, target: str) -> str:
    return f"""
DO $$
DECLARE
    r      RECORD;
    rowcnt BIGINT;
BEGIN
    FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = '{source}' ORDER BY tablename
    LOOP
        EXECUTE format(
            'CREATE TABLE {target}.%I '
            '(LIKE {source}.%I INCLUDING DEFAULTS INCLUDING CONSTRAINTS '
            'INCLUDING GENERATED INCLUDING IDENTITY INCLUDING INDEXES)',
            r.tablename, r.tablename
        );
        EXECUTE format('INSERT INTO {target}.%I SELECT * FROM {source}.%I', r.tablename, r.tablename);
        EXECUTE format('SELECT COUNT(*) FROM {target}.%I', r.tablename) INTO rowcnt;
        RAISE NOTICE 'Cloned: % → % rows', r.tablename, rowcnt;
    END LOOP;
END $$;
"""

def _sql_sync_sequences(target: str) -> str:
    return f"""
DO $$
DECLARE
    r      RECORD;
    maxval BIGINT;
    seq_ref TEXT;
BEGIN
    FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = '{target}' ORDER BY tablename
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = '{target}' AND table_name = r.tablename AND column_name = 'Id'
        ) THEN CONTINUE; END IF;

        EXECUTE format('SELECT COALESCE(MAX("Id"), 0) FROM {target}.%I', r.tablename) INTO maxval;
        IF maxval = 0 THEN CONTINUE; END IF;

        -- Find sequence via pg_depend (works for IDENTITY)
        SELECT quote_ident(n.nspname) || '.' || quote_ident(s.relname) INTO seq_ref
        FROM pg_class s
        JOIN pg_depend d  ON d.objid = s.oid
        JOIN pg_class t   ON t.oid = d.refobjid
        JOIN pg_namespace tn ON tn.oid = t.relnamespace
        JOIN pg_attribute a  ON a.attrelid = t.oid AND a.attnum = d.refobjsubid
        JOIN pg_namespace n  ON n.oid = s.relnamespace
        WHERE s.relkind = 'S' AND d.deptype IN ('a','i')
          AND tn.nspname = '{target}' AND t.relname = r.tablename AND a.attname = 'Id'
        LIMIT 1;

        IF seq_ref IS NULL THEN
            SELECT '{target}."' || r.tablename || '_Id_seq"' INTO seq_ref
            WHERE EXISTS (
                SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind = 'S' AND n.nspname = '{target}'
                  AND c.relname = r.tablename || '_Id_seq'
            );
        END IF;

        IF seq_ref IS NOT NULL THEN
            EXECUTE format('SELECT setval(%L, %s, true)', seq_ref, GREATEST(maxval, 1));
            RAISE NOTICE 'Synced: %.Id → % (next=%)', r.tablename, maxval, maxval + 1;
        ELSE
            RAISE NOTICE 'No sequence found for {target}.%.Id', r.tablename;
        END IF;
    END LOOP;
END $$;
"""

def _sql_verify(target: str) -> str:
    return f"""
SELECT schemaname, relname AS table_name, n_live_tup AS rows
FROM pg_stat_user_tables
WHERE schemaname = '{target}'
ORDER BY n_live_tup DESC;
"""

# ─── Worker logic ─────────────────────────────────────────────────────────────

def _pg_connect(cfg: dict):
    return psycopg2.connect(
        host=cfg["host"],
        port=int(cfg.get("port") or 5432),
        dbname=cfg["database"],
        user=cfg["username"],
        password=cfg["password"],
    )


def _schema_exists(cur, schema: str) -> bool:
    cur.execute(
        "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s", (schema,)
    )
    return cur.fetchone() is not None


def run_clone(
    src_cfg: dict,
    dst_cfg: dict,
    source_schema: str,
    target_schema: str,
    steps: list[str],
    log,
    cancel_evt: threading.Event,
):
    """
    src_cfg / dst_cfg: dicts with host/port/database/username/password
    steps: subset of ["drop", "clone", "sync", "verify"]
    log(msg, level): callback to emit log messages
    """
    src_conn = dst_conn = None
    ok = False
    try:
        same_server = (
            src_cfg["host"] == dst_cfg["host"]
            and str(src_cfg.get("port", 5432)) == str(dst_cfg.get("port", 5432))
            and src_cfg["database"] == dst_cfg["database"]
        )

        log(f"• Connecting source PostgreSQL: {src_cfg['host']}:{src_cfg.get('port',5432)}/{src_cfg['database']}", "INFO")
        src_conn = _pg_connect(src_cfg)
        src_conn.autocommit = True
        src_cur = src_conn.cursor()
        src_cur.execute("SELECT version()")
        log(f"  ✓ {src_cur.fetchone()[0].split(',')[0]}", "OK")

        if same_server:
            dst_conn = src_conn
            dst_cur  = src_cur
            log(f"• Target is on the same server/db — reusing connection.", "INFO")
        else:
            log(f"• Connecting target PostgreSQL: {dst_cfg['host']}:{dst_cfg.get('port',5432)}/{dst_cfg['database']}", "INFO")
            dst_conn = _pg_connect(dst_cfg)
            dst_conn.autocommit = True
            dst_cur  = dst_conn.cursor()
            dst_cur.execute("SELECT version()")
            log(f"  ✓ {dst_cur.fetchone()[0].split(',')[0]}", "OK")
        log("", "INFO")

        # Validate schemas
        if not _schema_exists(src_cur, source_schema):
            raise ValueError(f"Source schema '{source_schema}' does not exist!")
        if not _schema_exists(dst_cur, target_schema):
            log(f"  ⚠  Target schema '{target_schema}' not found — creating it …", "WARN")
            dst_cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{target_schema}"')
            log(f"  ✓ Schema '{target_schema}' created.", "OK")

        # ── Block 1: Drop ───────────────────────────────────────────────────
        if "drop" in steps:
            if cancel_evt.is_set():
                return
            log("── Block 1 — Drop all tables in target schema", "HEAD")
            t0 = time.time()
            dst_cur.execute(_sql_drop_tables(target_schema))
            notices = dst_conn.notices[-50:] if hasattr(dst_conn, "notices") else []
            for n in notices:
                log(f"  {n.strip()}", "DIM")
            log(f"  ✓ Done  ({time.time()-t0:.1f}s)", "OK")
            log("", "INFO")

        # ── Block 2: Clone ──────────────────────────────────────────────────
        if "clone" in steps:
            if cancel_evt.is_set():
                return
            log(f"── Block 2 — Clone  '{source_schema}'  →  '{target_schema}'", "HEAD")
            t0 = time.time()
            dst_cur.execute(_sql_clone_tables(source_schema, target_schema))
            notices = dst_conn.notices[-200:] if hasattr(dst_conn, "notices") else []
            for n in notices:
                log(f"  {n.strip()}", "DIM")
            log(f"  ✓ Clone complete  ({time.time()-t0:.1f}s)", "OK")
            log("", "INFO")

        # ── Block 3: Sync sequences ─────────────────────────────────────────
        if "sync" in steps:
            if cancel_evt.is_set():
                return
            log("── Block 3 — Sync IDENTITY / serial sequences", "HEAD")
            t0 = time.time()
            dst_cur.execute(_sql_sync_sequences(target_schema))
            notices = dst_conn.notices[-200:] if hasattr(dst_conn, "notices") else []
            for n in notices:
                log(f"  {n.strip()}", "DIM")
            log(f"  ✓ Sequences synced  ({time.time()-t0:.1f}s)", "OK")
            log("", "INFO")

        # ── Block 4: Verify ─────────────────────────────────────────────────
        if "verify" in steps:
            if cancel_evt.is_set():
                return
            log("── Block 4 — Verify row counts", "HEAD")
            dst_cur.execute(_sql_verify(target_schema))
            rows = dst_cur.fetchall()
            if rows:
                log(f"  {'Schema':<20} {'Table':<40} {'Rows':>10}", "DIM")
                log(f"  {'-'*20} {'-'*40} {'-'*10}", "DIM")
                for schema, tbl, cnt in rows:
                    log(f"  {schema:<20} {tbl:<40} {cnt:>10,}", "INFO")
            else:
                log("  (no rows found — schema may be empty)", "WARN")
            log("", "INFO")

        ok = True
        log("✅  Schema clone completed successfully!", "OK")
    except Exception:
        log("", "ERROR")
        log("❌  Clone FAILED.", "ERROR")
        for line in traceback.format_exc().splitlines():
            log(f"   {line}", "ERROR")
    finally:
        if dst_conn and dst_conn is not src_conn:
            try: dst_conn.close()
            except Exception: pass
        if src_conn:
            try: src_conn.close()
            except Exception: pass
        return ok


# ─── GUI helpers ──────────────────────────────────────────────────────────────

def _style(root: tk.Tk):
    s = ttk.Style(root)
    s.theme_use("clam")
    s.configure(".", background=BG, foreground=FG, font=("Segoe UI", 9))
    s.configure("TFrame",       background=BG)
    s.configure("TLabelframe",  background=BG2, bordercolor=EBORDER,
                relief="solid", borderwidth=1)
    s.configure("TLabelframe.Label", background=BG2, foreground=ACCENT,
                font=("Segoe UI Semibold", 9))
    s.configure("TCheckbutton", background=BG2, foreground=FG,
                indicatorcolor=BG4, indicatorrelief="flat", padding=2)
    s.map("TCheckbutton",
          indicatorcolor=[("selected", ACCENT)],
          foreground=[("selected", FG), ("active", FG)])
    s.configure("TCombobox",    fieldbackground=BG4, foreground=FG,
                selectbackground=ACCENT, selectforeground="white",
                arrowcolor=FG_DIM, padding=3)
    s.map("TCombobox",
          fieldbackground=[("readonly", BG4)],
          foreground=[("readonly", FG)])

    for name, bg, fg_c, abg in [
        ("Blue.TButton",  ACCENT,    "#071410", "#149478"),
        ("Grey.TButton",  BG4,       FG,        BG3),
        ("Red.TButton",   "#5c1a14", "white",   "#7a2218"),
        ("Green.TButton", "#0e4a30", "white",   "#16643e"),
    ]:
        s.configure(name, background=bg, foreground=fg_c,
                    font=("Segoe UI Semibold", 9), relief="flat", padding=(10, 5))
        s.map(name,
              background=[("active", abg), ("disabled", BG3)],
              foreground=[("disabled", FG_DIM)])

    s.configure("TProgressbar", troughcolor=BG3, background=ACCENT, thickness=4)
    s.configure("TSeparator",   background=EBORDER)
    s.configure("TScrollbar",   background=BG3, troughcolor=BG2,
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
    _entry(f, var, show=show).pack(side="left", fill="x", expand=True, ipady=3, padx=(4, 0))
    return f


def _lf(parent, title: str):
    frm = ttk.LabelFrame(parent, text=f"  {title}")
    frm.pack(fill="x", pady=(0, 6), ipady=6, ipadx=8)
    return frm


def _schema_combo(parent, var, label="Schema", lw=14):
    """Returns (frame, combobox) — caller stores the combobox for later updates."""
    f = tk.Frame(parent, bg=BG2)
    f.pack(fill="x", pady=2)
    tk.Label(f, text=label, bg=BG2, fg=FG_DIM,
             font=("Segoe UI", 9), width=lw, anchor="w").pack(side="left")
    cb = ttk.Combobox(f, textvariable=var, width=24)
    cb.pack(side="left", padx=(4, 4), ipady=2)
    return f, cb


# ─── Main Application ─────────────────────────────────────────────────────────

class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("PostgreSQL Schema Clone Tool")
        self.geometry("1280x820")
        self.minsize(1000, 680)
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
        hdr = tk.Frame(self, bg="#071410", height=46)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="  🔁  PostgreSQL Schema Clone Tool",
                 bg="#071410", fg=FG, font=("Segoe UI Semibold", 13)).pack(
            side="left", padx=14)
        tk.Label(hdr, text="Drop & Clone schema on PostgreSQL",
                 bg="#071410", fg=FG_DIM, font=("Segoe UI", 9)).pack(
            side="right", padx=14)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=12, pady=10)

        left = tk.Frame(body, bg=BG, width=400)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))

        self._build_source(left)
        self._build_target(left)
        self._build_operations(left)
        self._build_log(right)

    # ── Source panel ──────────────────────────────────────────────────────────
    def _build_source(self, parent):
        frm = _lf(parent, "Source — PostgreSQL")

        self.src_host   = tk.StringVar(value="localhost")
        self.src_port   = tk.StringVar(value="5432")
        self.src_db     = tk.StringVar()
        self.src_user   = tk.StringVar(value="postgres")
        self.src_pass   = tk.StringVar()
        self.src_schema = tk.StringVar()

        # Host + Port
        hr = tk.Frame(frm, bg=BG2); hr.pack(fill="x", pady=2)
        tk.Label(hr, text="Host", bg=BG2, fg=FG_DIM,
                 font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        _entry(hr, self.src_host).pack(side="left", fill="x", expand=True, ipady=3, padx=(4, 0))
        tk.Label(hr, text="Port", bg=BG2, fg=FG_DIM,
                 font=("Segoe UI", 9), width=5).pack(side="left", padx=(8, 0))
        _entry(hr, self.src_port, width=7).pack(side="left", ipady=3, padx=(4, 0))

        _row(frm, "Database", self.src_db)
        _row(frm, "Username", self.src_user)
        _row(frm, "Password", self.src_pass, show="●")

        # Schema combobox + reload button
        sr = tk.Frame(frm, bg=BG2); sr.pack(fill="x", pady=2)
        tk.Label(sr, text="Source Schema", bg=BG2, fg=FG_DIM,
                 font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        self._src_schema_cb = ttk.Combobox(sr, textvariable=self.src_schema, width=22)
        self._src_schema_cb.pack(side="left", padx=(4, 4), ipady=2)
        ttk.Button(sr, text="⟳", style="Grey.TButton", width=3,
                   command=self._load_src_schemas).pack(side="left")

        # Test
        br = tk.Frame(frm, bg=BG2); br.pack(fill="x", pady=(6, 0))
        ttk.Button(br, text="⚡ Test Connection", style="Blue.TButton",
                   command=self._test_src).pack(side="left")
        self._src_lbl = tk.Label(br, text="", bg=BG2, fg=FG_DIM, font=("Segoe UI", 9))
        self._src_lbl.pack(side="left", padx=8)

    # ── Target panel ──────────────────────────────────────────────────────────
    def _build_target(self, parent):
        frm = _lf(parent, "Target — PostgreSQL")

        self.dst_host   = tk.StringVar(value="localhost")
        self.dst_port   = tk.StringVar(value="5432")
        self.dst_db     = tk.StringVar()
        self.dst_user   = tk.StringVar(value="postgres")
        self.dst_pass   = tk.StringVar()
        self.dst_schema = tk.StringVar()

        hr = tk.Frame(frm, bg=BG2); hr.pack(fill="x", pady=2)
        tk.Label(hr, text="Host", bg=BG2, fg=FG_DIM,
                 font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        _entry(hr, self.dst_host).pack(side="left", fill="x", expand=True, ipady=3, padx=(4, 0))
        tk.Label(hr, text="Port", bg=BG2, fg=FG_DIM,
                 font=("Segoe UI", 9), width=5).pack(side="left", padx=(8, 0))
        _entry(hr, self.dst_port, width=7).pack(side="left", ipady=3, padx=(4, 0))

        _row(frm, "Database", self.dst_db)
        _row(frm, "Username", self.dst_user)
        _row(frm, "Password", self.dst_pass, show="●")

        # Target schema — free text + combobox
        sr = tk.Frame(frm, bg=BG2); sr.pack(fill="x", pady=2)
        tk.Label(sr, text="Target Schema", bg=BG2, fg=FG_DIM,
                 font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        self._dst_schema_cb = ttk.Combobox(sr, textvariable=self.dst_schema, width=22)
        self._dst_schema_cb.pack(side="left", padx=(4, 4), ipady=2)
        ttk.Button(sr, text="⟳", style="Grey.TButton", width=3,
                   command=self._load_dst_schemas).pack(side="left")

        # Copy-source shortcut
        cs = tk.Frame(frm, bg=BG2); cs.pack(fill="x", pady=(2, 0))
        ttk.Button(cs, text="⬇  Same as Source server", style="Grey.TButton",
                   command=self._copy_src_to_dst).pack(side="left")

        # Save creds
        cr = tk.Frame(frm, bg=BG2); cr.pack(fill="x", pady=(4, 0))
        self._save_creds_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(cr, text="Save credentials", variable=self._save_creds_var).pack(side="left")

        # Test
        br = tk.Frame(frm, bg=BG2); br.pack(fill="x", pady=(6, 0))
        ttk.Button(br, text="⚡ Test Connection", style="Blue.TButton",
                   command=self._test_dst).pack(side="left")
        self._dst_lbl = tk.Label(br, text="", bg=BG2, fg=FG_DIM, font=("Segoe UI", 9))
        self._dst_lbl.pack(side="left", padx=8)

    # ── Operations panel ─────────────────────────────────────────────────────
    def _build_operations(self, parent):
        frm = _lf(parent, "Clone Operations")

        self._step_vars: dict[str, tk.BooleanVar] = {}
        steps = [
            ("drop",   "Block 1",  "Drop all tables in target schema"),
            ("clone",  "Block 2",  "Clone source → target (with IDENTITY)"),
            ("sync",   "Block 3",  "Sync IDENTITY / serial sequences"),
            ("verify", "Block 4",  "Verify row counts"),
        ]

        for key, block, desc in steps:
            var = tk.BooleanVar(value=True)
            self._step_vars[key] = var
            r = tk.Frame(frm, bg=BG2); r.pack(fill="x", pady=3)
            ttk.Checkbutton(r, variable=var).pack(side="left")
            tk.Label(r, text=f" {block}", bg=BG2, fg=ACCENT,
                     font=("Segoe UI Semibold", 9), width=10, anchor="w").pack(side="left")
            tk.Label(r, text=f" {desc}", bg=BG2, fg=FG,
                     font=("Segoe UI", 9), anchor="w").pack(side="left")

        sel = tk.Frame(frm, bg=BG2); sel.pack(fill="x", pady=(6, 4))
        ttk.Button(sel, text="All",  style="Grey.TButton", width=5,
                   command=lambda: [v.set(True)  for v in self._step_vars.values()]
                   ).pack(side="left", padx=(0, 4))
        ttk.Button(sel, text="None", style="Grey.TButton", width=5,
                   command=lambda: [v.set(False) for v in self._step_vars.values()]
                   ).pack(side="left")

        ttk.Separator(frm, orient="horizontal").pack(fill="x", pady=6)

        self._start_btn = ttk.Button(
            frm, text="▶  Start Clone",
            style="Green.TButton", command=self._start)
        self._start_btn.pack(fill="x", pady=(0, 4))

        self._cancel_btn = ttk.Button(
            frm, text="■  Cancel",
            style="Red.TButton", command=self._do_cancel, state="disabled")
        self._cancel_btn.pack(fill="x")

        self._prog = ttk.Progressbar(frm, mode="indeterminate")
        self._prog.pack(fill="x", pady=(8, 0))

    # ── Log panel ─────────────────────────────────────────────────────────────
    def _build_log(self, parent):
        hdr = tk.Frame(parent, bg=BG2, height=28)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="  Clone Log", bg=BG2, fg=FG,
                 font=("Segoe UI Semibold", 10)).pack(side="left", pady=4)
        ttk.Button(hdr, text="Clear Log", style="Grey.TButton",
                   command=self._clear_log).pack(side="right", padx=6, pady=2)
        ttk.Button(hdr, text="Save Log", style="Grey.TButton",
                   command=self._save_log).pack(side="right", pady=2)

        tf = tk.Frame(parent, bg=BG)
        tf.pack(fill="both", expand=True, pady=(2, 0))

        self._log = tk.Text(
            tf, bg="#060f0d", fg=FG, font=("Consolas", 9),
            relief="flat", state="disabled", wrap="none",
            highlightthickness=0, bd=0, selectbackground=BG4,
        )
        vsb = ttk.Scrollbar(tf, orient="vertical",   command=self._log.yview)
        hsb = ttk.Scrollbar(tf, orient="horizontal", command=self._log.xview)
        self._log.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right",  fill="y")
        hsb.pack(side="bottom", fill="x")
        self._log.pack(fill="both", expand=True)

        self._log.tag_configure("TS",    foreground="#4a6080")
        self._log.tag_configure("INFO",  foreground=FG)
        self._log.tag_configure("OK",    foreground=GREEN)
        self._log.tag_configure("HEAD",  foreground=ACCENT, font=("Consolas", 9, "bold"))
        self._log.tag_configure("WARN",  foreground=ORANGE)
        self._log.tag_configure("DIM",   foreground=FG_DIM)
        self._log.tag_configure("ERROR", foreground=RED, font=("Consolas", 9, "bold"))
        self._log.tag_configure("START", foreground="white", font=("Consolas", 10, "bold"))

    # ── Credentials ───────────────────────────────────────────────────────────
    def _load_creds(self):
        if not os.path.exists(CRED_FILE):
            return
        try:
            with open(CRED_FILE, encoding="utf-8") as f:
                c = json.load(f)
            s = c.get("source", {})
            d = c.get("dest",   {})
            for attr, val in [
                ("src_host",   s.get("host")),
                ("src_port",   s.get("port")),
                ("src_db",     s.get("database")),
                ("src_user",   s.get("username")),
                ("src_pass",   s.get("password")),
                ("src_schema", s.get("schema")),
                ("dst_host",   d.get("host")),
                ("dst_port",   d.get("port")),
                ("dst_db",     d.get("database")),
                ("dst_user",   d.get("username")),
                ("dst_pass",   d.get("password")),
                ("dst_schema", d.get("schema")),
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
                "host":     self.src_host.get(),
                "port":     self.src_port.get(),
                "database": self.src_db.get(),
                "username": self.src_user.get(),
                "password": self.src_pass.get(),
                "schema":   self.src_schema.get(),
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

    # ── Connection helpers ────────────────────────────────────────────────────
    def _src_cfg(self) -> dict:
        return {
            "host":     self.src_host.get(),
            "port":     self.src_port.get() or "5432",
            "database": self.src_db.get(),
            "username": self.src_user.get(),
            "password": self.src_pass.get(),
        }

    def _dst_cfg(self) -> dict:
        return {
            "host":     self.dst_host.get(),
            "port":     self.dst_port.get() or "5432",
            "database": self.dst_db.get(),
            "username": self.dst_user.get(),
            "password": self.dst_pass.get(),
        }

    def _test_src(self):
        try:
            conn = _pg_connect(self._src_cfg())
            cur  = conn.cursor()
            cur.execute("SELECT version()")
            ver  = cur.fetchone()[0].split(",")[0]
            conn.close()
            self._src_lbl.config(text=f"✓ {ver[:70]}", fg=GREEN)
            self._load_src_schemas()
        except Exception as e:
            self._src_lbl.config(text=f"✗ {e}", fg=RED)

    def _test_dst(self):
        try:
            conn = _pg_connect(self._dst_cfg())
            cur  = conn.cursor()
            cur.execute("SELECT version()")
            ver  = cur.fetchone()[0].split(",")[0]
            conn.close()
            self._dst_lbl.config(text=f"✓ {ver[:70]}", fg=GREEN)
            self._load_dst_schemas()
        except Exception as e:
            self._dst_lbl.config(text=f"✗ {e}", fg=RED)

    def _load_schemas_for(self, cfg: dict, combobox: ttk.Combobox, lbl: tk.Label):
        try:
            conn = _pg_connect(cfg)
            cur  = conn.cursor()
            cur.execute("""
                SELECT schema_name FROM information_schema.schemata
                WHERE schema_name NOT LIKE 'pg_%'
                  AND schema_name NOT IN ('information_schema')
                ORDER BY schema_name
            """)
            schemas = [r[0] for r in cur.fetchall()]
            conn.close()
            combobox["values"] = schemas
            lbl.config(text=f"✓ {len(schemas)} schema(s) loaded", fg=GREEN)
        except Exception as e:
            lbl.config(text=f"✗ {e}", fg=RED)

    def _load_src_schemas(self):
        self._load_schemas_for(self._src_cfg(), self._src_schema_cb, self._src_lbl)

    def _load_dst_schemas(self):
        self._load_schemas_for(self._dst_cfg(), self._dst_schema_cb, self._dst_lbl)

    def _copy_src_to_dst(self):
        self.dst_host.set(self.src_host.get())
        self.dst_port.set(self.src_port.get())
        self.dst_db.set(self.src_db.get())
        self.dst_user.set(self.src_user.get())
        self.dst_pass.set(self.src_pass.get())

    # ── Start / Cancel ────────────────────────────────────────────────────────
    def _start(self):
        if self._busy:
            return

        selected = [k for k, v in self._step_vars.items() if v.get()]
        if not selected:
            messagebox.showwarning("Nothing selected", "Select at least one operation.")
            return

        src_schema = self.src_schema.get().strip()
        dst_schema = self.dst_schema.get().strip()

        if not src_schema:
            messagebox.showwarning("No source schema", "Enter or select a source schema.")
            return
        if not dst_schema:
            messagebox.showwarning("No target schema", "Enter or select a target schema.")
            return
        if src_schema == dst_schema and self._src_cfg() == self._dst_cfg():
            messagebox.showerror("Same schema", "Source and target schema must be different.")
            return

        step_labels = {
            "drop":   "Drop all tables in target",
            "clone":  "Clone source → target",
            "sync":   "Sync sequences",
            "verify": "Verify row counts",
        }
        confirm_msg = (
            f"Clone  '{src_schema}'  →  '{dst_schema}'\n\n"
            + "\n".join(f"  • {step_labels[k]}" for k in selected)
            + "\n\n⚠  All tables in the target schema will be DROPPED first if 'drop' is selected."
        )
        if not messagebox.askyesno("Confirm Clone", confirm_msg):
            return

        self._busy = True
        self._cancel.clear()
        self._start_btn.config(state="disabled")
        self._cancel_btn.config(state="normal")
        self._prog.start(15)
        self._save_creds()

        threading.Thread(
            target=self._worker,
            args=(self._src_cfg(), self._dst_cfg(), src_schema, dst_schema, selected),
            daemon=True,
        ).start()

    def _worker(self, src_cfg, dst_cfg, src_schema, dst_schema, steps):
        def log(msg: str, level: str = "INFO"):
            ts = datetime.now().strftime("%H:%M:%S")
            self._q.put((ts, msg, level))

        log(f"Starting clone  '{src_schema}'  →  '{dst_schema}'", "START")
        log("", "INFO")
        ok = run_clone(src_cfg, dst_cfg, src_schema, dst_schema, steps, log, self._cancel)
        self._q.put(("__DONE__", "ok" if ok else "err", ""))

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
            initialfile=f"clone_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._log.get("1.0", "end"))


# ─── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
