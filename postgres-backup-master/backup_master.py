"""
Postgres Backup Master  v1.0
=================================
Desktop utility for managing PostgreSQL backup jobs (similar to SQL Backup Master).

Features:
  - Multi-job backup management
  - Manual run (Run Now)
  - Built-in lightweight scheduler (daily time)
  - Retention by days and copy count
  - Backup history and live log

Requirements:
  pip install psycopg2-binary
  PostgreSQL client tools (pg_dump) available in PATH
"""

from __future__ import annotations

import argparse
import importlib
import io
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import traceback
import uuid
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

import psycopg2

# ─── Theme ───────────────────────────────────────────────────────────────────
BG = "#121417"
BG2 = "#1a1f24"
BG3 = "#242c33"
FG = "#d9e1e8"
FG_DIM = "#8ea0ad"
ACCENT = "#3da5ff"
GREEN = "#47c067"
ORANGE = "#f1aa2b"
RED = "#e05a5a"
BORDER = "#33404c"

APP_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_FILE = APP_DIR / "backup_config.json"
SCHEDULER_TASK_NAME = "PostgresBackupMasterScheduler"
SCHEDULER_RUNNER = APP_DIR / "scheduler_runner.bat"
SCHEDULER_LOG = APP_DIR / "scheduler.log"


def _config_file_path() -> Path:
	env = os.environ.get("PBM_CONFIG_FILE", "").strip()
	# Accept values like: "D:\path\backup_config.json"
	# (common when set via cmd scripts with quoted assignment)
	if env:
		env = env.strip().strip('"').strip("'")
		env = env.replace('"', "").replace("'", "")

		# Recover from malformed concatenated values like:
		# D:\base\"D:\base\backup_config.json"
		# Keep the last detected drive-root segment.
		first_drive = env.find(":\\")
		last_drive = env.rfind(":\\")
		if first_drive != -1 and last_drive != -1 and last_drive != first_drive:
			start = last_drive - 1
			if start >= 0 and env[start].isalpha():
				env = env[start:]
	if env:
		return Path(env).expanduser().resolve()
	return DEFAULT_CONFIG_FILE


def _now() -> datetime:
	return datetime.now()


def _now_str() -> str:
	return _now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_name(text: str) -> str:
	keep = []
	for ch in text.strip():
		keep.append(ch if ch.isalnum() or ch in ("-", "_") else "_")
	return "".join(keep).strip("_") or "backup"


def _fmt_bytes(size: int) -> str:
	units = ["B", "KB", "MB", "GB", "TB"]
	v = float(size)
	for u in units:
		if v < 1024 or u == units[-1]:
			return f"{v:.1f} {u}" if u != "B" else f"{int(v)} B"
		v /= 1024
	return f"{size} B"


def _default_job() -> dict:
	return {
		"id": str(uuid.uuid4()),
		"name": "New Backup Job",
		"enabled": True,
		"host": "localhost",
		"port": 5432,
		"database": "postgres",
		"backup_all_schemas": False,
		"schemas": [],
		"username": "postgres",
		"password": "",
		"destination_type": "local",  # local | gdrive | onedrive
		"destination": str(APP_DIR / "backups"),
		"format": "custom",  # custom | plain | tar
		"zip_backup": True,
		"compression": 6,
		"schedule_enabled": False,
		"schedule_time": "02:00",
		"retention_days": 7,
		"keep_copies": 20,
		"last_scheduled_date": "",
	}


def _default_config() -> dict:
	return {
		"pg_dump_path": "auto",
		"pg_restore_path": "auto",
		"psql_path": "auto",
		"google_client_secret": str(APP_DIR / "google_client_secret.json"),
		"google_token_file": str(APP_DIR / "google_token.json"),
		"onedrive_client_id": "",
		"onedrive_tenant_id": "common",
		"jobs": [],
		"history": [],
	}


def _load_config_file() -> dict:
	config_file = _config_file_path()
	try:
		config_file.parent.mkdir(parents=True, exist_ok=True)
	except Exception:
		config_file = DEFAULT_CONFIG_FILE
		config_file.parent.mkdir(parents=True, exist_ok=True)
	if not config_file.exists():
		cfg = _default_config()
		config_file.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
		return cfg
	try:
		data = json.loads(config_file.read_text(encoding="utf-8"))
		cfg = _default_config()
		cfg.update(data if isinstance(data, dict) else {})
		cfg["jobs"] = cfg.get("jobs") or []
		cfg["history"] = cfg.get("history") or []
		return cfg
	except Exception:
		cfg = _default_config()
		config_file.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
		return cfg


def _save_config_file(cfg: dict):
	config_file = _config_file_path()
	config_file.parent.mkdir(parents=True, exist_ok=True)
	config_file.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def _candidate_pg_tool_paths(tool_name: str) -> list[Path]:
	"""Return common Windows install paths for a PostgreSQL client executable."""
	base_dirs = [
		Path(r"C:\Program Files\PostgreSQL"),
		Path(r"C:\Program Files (x86)\PostgreSQL"),
	]
	cands: list[Path] = []
	for b in base_dirs:
		if not b.exists():
			continue
		for ver in sorted(b.glob("*"), reverse=True):
			p = ver / "bin" / f"{tool_name}.exe"
			if p.exists():
				cands.append(p)
	return cands


def _resolve_pg_tool(
	tool_name: str,
	config_value: str | None,
	sibling_hint: str | None = None,
	sibling_source_value: str | None = None,
) -> str:
	"""Resolve PostgreSQL client executable path from config and system."""
	val = (config_value or "").strip()

	# 1) Explicit full path from settings
	if val and val.lower() not in ("auto", tool_name, f"{tool_name}.exe"):
		p = Path(val)
		if p.exists() and p.is_file():
			return str(p)
		# If configured path points to pg_dump, try sibling executable in same folder.
		if sibling_hint and p.name.lower() in (sibling_hint.lower(), f"{sibling_hint.lower()}.exe"):
			sibling = p.parent / (f"{tool_name}.exe" if p.suffix.lower() == ".exe" else tool_name)
			if sibling.exists() and sibling.is_file():
				return str(sibling)
		raise FileNotFoundError(
			f"Configured {tool_name} path was not found: {val}"
		)

	# 2) PATH lookup
	which = shutil.which(tool_name) or shutil.which(f"{tool_name}.exe")
	if which:
		return which

	# 3) If sibling tool path is set explicitly, try same bin folder for this tool
	if sibling_hint and val and val.lower() not in ("auto", sibling_hint, f"{sibling_hint}.exe"):
		p = Path(val)
		candidate = p.parent / f"{tool_name}.exe"
		if candidate.exists() and candidate.is_file():
			return str(candidate)

	if sibling_hint and sibling_source_value:
		sv = sibling_source_value.strip()
		if sv and sv.lower() not in ("auto", sibling_hint, f"{sibling_hint}.exe"):
			sp = Path(sv)
			cand = sp.parent / f"{tool_name}.exe"
			if cand.exists() and cand.is_file():
				return str(cand)

	# 3) Common Windows install directories
	for p in _candidate_pg_tool_paths(tool_name):
		return str(p)

	raise FileNotFoundError(
		f"{tool_name} executable not found. Install PostgreSQL client tools or set it in Settings."
	)


def _resolve_pg_dump(config_value: str | None) -> str:
	return _resolve_pg_tool("pg_dump", config_value)


def _cloud_folder_norm(path_text: str) -> str:
	p = (path_text or "").strip().replace("\\", "/").strip("/")
	return p or "postgres-backups"


def _is_cloud_destination(job: dict) -> bool:
	return str(job.get("destination_type") or "local").lower() in ("gdrive", "onedrive")


def _google_get_creds(cfg: dict, interactive: bool):
	try:
		Request = importlib.import_module("google.auth.transport.requests").Request
		Credentials = importlib.import_module("google.oauth2.credentials").Credentials
		InstalledAppFlow = importlib.import_module("google_auth_oauthlib.flow").InstalledAppFlow
	except Exception as ex:
		raise RuntimeError("Google Drive dependencies missing. Install requirements.txt.") from ex

	scopes = ["https://www.googleapis.com/auth/drive.file"]
	secret = Path(str(cfg.get("google_client_secret") or "")).expanduser()
	token = Path(str(cfg.get("google_token_file") or (APP_DIR / "google_token.json"))).expanduser()

	creds = None
	if token.exists():
		creds = Credentials.from_authorized_user_file(str(token), scopes)

	if creds and creds.valid:
		return creds

	if creds and creds.expired and creds.refresh_token:
		creds.refresh(Request())
		token.write_text(creds.to_json(), encoding="utf-8")
		return creds

	if not interactive:
		raise RuntimeError("Google Drive is not signed in")

	if not secret.exists():
		raise RuntimeError(f"Google client secret file not found: {secret}")

	flow = InstalledAppFlow.from_client_secrets_file(str(secret), scopes)
	creds = flow.run_local_server(port=0)
	token.write_text(creds.to_json(), encoding="utf-8")
	return creds


def _google_service(cfg: dict, interactive: bool):
	try:
		build = importlib.import_module("googleapiclient.discovery").build
	except Exception as ex:
		raise RuntimeError("Google Drive dependencies missing. Install requirements.txt.") from ex
	creds = _google_get_creds(cfg, interactive=interactive)
	return build("drive", "v3", credentials=creds)


def _gdrive_find_child_folder(service, parent_id: str, name: str) -> str | None:
	q = (
		f"name = '{name.replace("'", "\\'")}' and "
		f"'{parent_id}' in parents and trashed = false and "
		"mimeType = 'application/vnd.google-apps.folder'"
	)
	res = service.files().list(q=q, spaces="drive", fields="files(id,name)", pageSize=10).execute()
	files = res.get("files", [])
	return files[0]["id"] if files else None


def _gdrive_ensure_folder(service, folder_path: str) -> str:
	parent = "root"
	for part in [p for p in _cloud_folder_norm(folder_path).split("/") if p]:
		fid = _gdrive_find_child_folder(service, parent, part)
		if not fid:
			body = {
				"name": part,
				"mimeType": "application/vnd.google-apps.folder",
				"parents": [parent],
			}
			fid = service.files().create(body=body, fields="id").execute()["id"]
		parent = fid
	return parent


def _gdrive_upload_file(cfg: dict, folder_path: str, local_file: Path) -> dict:
	try:
		MediaFileUpload = importlib.import_module("googleapiclient.http").MediaFileUpload
	except Exception as ex:
		raise RuntimeError("Google Drive dependencies missing. Install requirements.txt.") from ex

	service = _google_service(cfg, interactive=False)
	folder_id = _gdrive_ensure_folder(service, folder_path)
	body = {"name": local_file.name, "parents": [folder_id]}
	media = MediaFileUpload(str(local_file), resumable=True)
	created = service.files().create(
		body=body,
		media_body=media,
		fields="id,name,size,modifiedTime,webViewLink",
	).execute()
	return created


def _gdrive_list_files(cfg: dict, folder_path: str, prefix: str = "") -> list[dict]:
	service = _google_service(cfg, interactive=False)
	folder_id = _gdrive_ensure_folder(service, folder_path)
	q = f"'{folder_id}' in parents and trashed = false"
	if prefix:
		q += f" and name contains '{prefix.replace("'", "\\'")}'"
	res = service.files().list(
		q=q,
		spaces="drive",
		fields="files(id,name,size,modifiedTime,webViewLink)",
		pageSize=200,
		orderBy="modifiedTime desc",
	).execute()
	return res.get("files", [])


def _gdrive_download_file(cfg: dict, file_id: str, out_path: Path):
	try:
		MediaIoBaseDownload = importlib.import_module("googleapiclient.http").MediaIoBaseDownload
	except Exception as ex:
		raise RuntimeError("Google Drive dependencies missing. Install requirements.txt.") from ex
	service = _google_service(cfg, interactive=False)
	req = service.files().get_media(fileId=file_id)
	fh = io.FileIO(out_path, "wb")
	downloader = MediaIoBaseDownload(fh, req)
	done = False
	while not done:
		_, done = downloader.next_chunk()
	fh.close()


def _onedrive_token(cfg: dict, interactive: bool) -> str:
	try:
		import msal
	except Exception as ex:
		raise RuntimeError("OneDrive dependencies missing. Install requirements.txt.") from ex

	client_id = str(cfg.get("onedrive_client_id") or "").strip()
	tenant_id = str(cfg.get("onedrive_tenant_id") or "common").strip() or "common"
	if not client_id:
		raise RuntimeError("OneDrive Client ID is required in Settings")

	cache_file = APP_DIR / "onedrive_token_cache.bin"
	token_cache = msal.SerializableTokenCache()
	if cache_file.exists():
		token_cache.deserialize(cache_file.read_text(encoding="utf-8"))

	app = msal.PublicClientApplication(
		client_id=client_id,
		authority=f"https://login.microsoftonline.com/{tenant_id}",
		token_cache=token_cache,
	)
	scopes = ["Files.ReadWrite.All", "offline_access", "User.Read"]

	accounts = app.get_accounts()
	result = app.acquire_token_silent(scopes, account=accounts[0] if accounts else None)
	if not result and interactive:
		result = app.acquire_token_interactive(scopes=scopes, prompt="select_account")

	if token_cache.has_state_changed:
		cache_file.write_text(token_cache.serialize(), encoding="utf-8")

	if not result or "access_token" not in result:
		raise RuntimeError("OneDrive sign-in required")
	return result["access_token"]


def _graph_request(method: str, url: str, token: str, **kwargs):
	try:
		import requests
	except Exception as ex:
		raise RuntimeError("Requests dependency missing. Install requirements.txt.") from ex
	headers = kwargs.pop("headers", {})
	if token:
		headers["Authorization"] = f"Bearer {token}"
	r = requests.request(method, url, headers=headers, timeout=120, **kwargs)
	if not (200 <= r.status_code < 300):
		raise RuntimeError(f"Graph API error {r.status_code}: {r.text[:300]}")
	return r


def _onedrive_ensure_folder(cfg: dict, folder_path: str, interactive: bool) -> tuple[str, str]:
	token = _onedrive_token(cfg, interactive=interactive)
	base = "https://graph.microsoft.com/v1.0"
	root = _graph_request("GET", f"{base}/me/drive/root", token).json()
	parent_id = root["id"]

	for part in [p for p in _cloud_folder_norm(folder_path).split("/") if p]:
		children = _graph_request(
			"GET",
			f"{base}/me/drive/items/{parent_id}/children?$top=200",
			token,
		).json().get("value", [])
		found = None
		for item in children:
			if item.get("name") == part and "folder" in item:
				found = item
				break
		if not found:
			payload = {"name": part, "folder": {}, "@microsoft.graph.conflictBehavior": "rename"}
			found = _graph_request("POST", f"{base}/me/drive/items/{parent_id}/children", token, json=payload).json()
		parent_id = found["id"]

	return token, parent_id


def _onedrive_upload_file(cfg: dict, folder_path: str, local_file: Path) -> dict:
	token, parent_id = _onedrive_ensure_folder(cfg, folder_path, interactive=False)
	base = "https://graph.microsoft.com/v1.0"

	session_url = f"{base}/me/drive/items/{parent_id}:/{local_file.name}:/createUploadSession"
	session = _graph_request(
		"POST",
		session_url,
		token,
		json={"item": {"@microsoft.graph.conflictBehavior": "replace", "name": local_file.name}},
	).json()
	upload_url = session["uploadUrl"]

	chunk = 5 * 1024 * 1024
	total = local_file.stat().st_size
	with local_file.open("rb") as f:
		start = 0
		while start < total:
			end = min(start + chunk, total) - 1
			data = f.read(end - start + 1)
			headers = {
				"Content-Length": str(len(data)),
				"Content-Range": f"bytes {start}-{end}/{total}",
			}
			_graph_request("PUT", upload_url, token="", headers=headers, data=data)
			start = end + 1

	items = _graph_request("GET", f"{base}/me/drive/items/{parent_id}/children?$top=200", token).json().get("value", [])
	for it in items:
		if it.get("name") == local_file.name:
			return it
	raise RuntimeError("Uploaded file not found in OneDrive folder")


def _onedrive_list_files(cfg: dict, folder_path: str, prefix: str = "") -> list[dict]:
	token, parent_id = _onedrive_ensure_folder(cfg, folder_path, interactive=False)
	base = "https://graph.microsoft.com/v1.0"
	items = _graph_request("GET", f"{base}/me/drive/items/{parent_id}/children?$top=200", token).json().get("value", [])
	files = [x for x in items if "file" in x]
	if prefix:
		files = [x for x in files if prefix.lower() in str(x.get("name", "")).lower()]
	files.sort(key=lambda x: x.get("lastModifiedDateTime", ""), reverse=True)
	return files


def _onedrive_download_file(cfg: dict, file_id: str, out_path: Path):
	token = _onedrive_token(cfg, interactive=False)
	base = "https://graph.microsoft.com/v1.0"
	resp = _graph_request("GET", f"{base}/me/drive/items/{file_id}/content", token, stream=True)
	with out_path.open("wb") as f:
		for chunk in resp.iter_content(chunk_size=1024 * 256):
			if chunk:
				f.write(chunk)


def _parse_hhmm_value(text: str) -> tuple[int, int]:
	try:
		hh, mm = text.strip().split(":", 1)
		h = max(0, min(23, int(hh)))
		m = max(0, min(59, int(mm)))
		return h, m
	except Exception:
		return 2, 0


def _next_run_datetime(job: dict, now: datetime) -> datetime:
	hh, mm = _parse_hhmm_value(job.get("schedule_time", "02:00"))
	candidate = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
	if candidate <= now:
		candidate += timedelta(days=1)
	return candidate


def _apply_retention_files(job: dict, dest: Path, safe_job: str, safe_db: str, log):
	pattern = f"{safe_job}_{safe_db}_*"
	files = sorted(dest.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)

	keep_copies = max(1, int(job.get("keep_copies", 20)))
	retention_days = max(0, int(job.get("retention_days", 7)))
	cutoff = _now() - timedelta(days=retention_days)

	kept = 0
	for f in files:
		kept += 1
		remove_for_count = kept > keep_copies
		mtime = datetime.fromtimestamp(f.stat().st_mtime)
		remove_for_age = retention_days > 0 and mtime < cutoff
		if remove_for_count or remove_for_age:
			try:
				f.unlink(missing_ok=True)
				log(f"  Retention removed: {f.name}", "DIM")
			except Exception as ex:
				log(f"  Retention warning: {f.name}: {ex}", "WARN")


def _connect_job(job: dict):
	return psycopg2.connect(
		host=str(job["host"]),
		port=int(job["port"]),
		dbname=str(job["database"]),
		user=str(job["username"]),
		password=str(job.get("password") or ""),
		connect_timeout=10,
	)


def _fetch_user_schemas(job: dict) -> list[str]:
	conn = _connect_job(job)
	try:
		cur = conn.cursor()
		cur.execute(
			"SELECT nspname "
			"FROM pg_namespace "
			"WHERE nspname NOT LIKE 'pg_%' "
			"  AND nspname <> 'information_schema' "
			"ORDER BY nspname"
		)
		return [r[0] for r in cur.fetchall()]
	finally:
		conn.close()


def _resolve_schemas_for_backup(job: dict, log) -> list[str]:
	existing = _fetch_user_schemas(job)
	existing_set = {s.lower() for s in existing}

	if bool(job.get("backup_all_schemas", False)):
		if not existing:
			raise RuntimeError("No user schemas found in selected database")
		return existing

	selected = [str(s).strip() for s in (job.get("schemas") or []) if str(s).strip()]
	if not selected:
		if not existing:
			raise RuntimeError("No user schemas found in selected database")
		log("  No schemas configured in job. Using all user schemas.", "WARN")
		return existing

	missing = [s for s in selected if s.lower() not in existing_set]
	if missing:
		log(f"  Warning: missing schemas skipped: {', '.join(missing)}", "WARN")

	resolved = [s for s in selected if s.lower() in existing_set]
	if not resolved:
		raise RuntimeError("None of the selected schemas exist in this database")
	return resolved


def _build_pg_dump_cmd(
	pg_dump_exec: str,
	job: dict,
	out_file: Path,
	fmt: str,
	compression: int,
	schemas: list[str],
) -> list[str]:
	cmd = [pg_dump_exec]
	if fmt == "custom":
		cmd += ["-Fc"]
	elif fmt == "plain":
		cmd += ["-Fp"]
	elif fmt == "tar":
		cmd += ["-Ft"]

	if fmt in ("custom", "tar"):
		cmd += ["-Z", str(compression)]

	cmd += [
		"-h",
		str(job["host"]),
		"-p",
		str(job["port"]),
		"-U",
		str(job["username"]),
		"-d",
		str(job["database"]),
	]

	for schema in schemas:
		cmd += ["-n", schema]

	cmd += ["-f", str(out_file)]
	return cmd


def _perform_backup(job: dict, cfg: dict, log) -> tuple[Path, int]:
	dest = Path(job["destination"]).expanduser().resolve()
	dest.mkdir(parents=True, exist_ok=True)

	stamp = _now().strftime("%Y%m%d_%H%M%S")
	jn = _safe_name(job["name"])
	db = _safe_name(job["database"])
	schemas = _resolve_schemas_for_backup(job, log)
	fmt = (job.get("format") or "custom").lower()
	ext = {"custom": "backup", "plain": "sql", "tar": "tar"}.get(fmt, "backup")

	pg_dump_exec = _resolve_pg_dump(cfg.get("pg_dump_path"))
	comp = int(job.get("compression", 6))
	comp = max(0, min(9, comp))

	env = os.environ.copy()
	env["PGPASSWORD"] = str(job.get("password") or "")

	log(f"  Running schema backup for database '{job['database']}'", "DIM")
	log(f"  Schemas: {', '.join(schemas)}", "DIM")
	log(f"  pg_dump: {pg_dump_exec}", "DIM")

	final_file: Path
	if bool(job.get("zip_backup", True)):
		db_zip = dest / f"{jn}_{db}_{stamp}.zip"
		with tempfile.TemporaryDirectory(prefix="pg_schema_backup_") as td:
			tmp = Path(td)
			schema_items: list[tuple[str, Path]] = []

			for schema in schemas:
				safe_schema = _safe_name(schema)
				dump_file = tmp / f"{safe_schema}_{stamp}.{ext}"
				cmd = _build_pg_dump_cmd(pg_dump_exec, job, dump_file, fmt, comp, [schema])
				run = subprocess.run(cmd, capture_output=True, text=True, env=env)
				if run.returncode != 0:
					msg = (run.stderr or run.stdout or "pg_dump returned non-zero exit code").strip()
					raise RuntimeError(f"Schema '{schema}' backup failed: {msg.splitlines()[-1] if msg else 'pg_dump failed'}")
				if not dump_file.exists():
					raise RuntimeError(f"Schema '{schema}' backup file was not created")

				schema_zip = tmp / f"{safe_schema}_{stamp}.zip"
				with zipfile.ZipFile(schema_zip, "w", compression=zipfile.ZIP_DEFLATED) as sz:
					sz.write(dump_file, arcname=dump_file.name)
					sz.writestr(
						"schema_manifest.json",
						json.dumps(
							{
								"database": job.get("database"),
								"schema": schema,
								"created_at": _now_str(),
								"format": fmt,
							},
							indent=2,
						),
					)
				dump_file.unlink(missing_ok=True)
				schema_items.append((schema, schema_zip))
				log(f"  Schema zipped: {schema_zip.name}", "DIM")

			with zipfile.ZipFile(db_zip, "w", compression=zipfile.ZIP_DEFLATED) as dz:
				manifest = {
					"job": job.get("name"),
					"database": job.get("database"),
					"created_at": _now_str(),
					"format": fmt,
					"schemas": [],
				}
				for schema, schema_zip in schema_items:
					arc = f"schemas/{schema_zip.name}"
					dz.write(schema_zip, arcname=arc)
					manifest["schemas"].append({"name": schema, "file": arc})
				dz.writestr("db_manifest.json", json.dumps(manifest, indent=2))

		final_file = db_zip
		log(f"  Database ZIP created: {db_zip.name}", "DIM")
	else:
		out_file = dest / f"{jn}_{db}_{stamp}.{ext}"
		cmd = _build_pg_dump_cmd(pg_dump_exec, job, out_file, fmt, comp, schemas)
		run = subprocess.run(cmd, capture_output=True, text=True, env=env)
		if run.returncode != 0:
			msg = (run.stderr or run.stdout or "pg_dump returned non-zero exit code").strip()
			raise RuntimeError(msg.splitlines()[-1] if msg else "pg_dump failed")
		if not out_file.exists():
			raise RuntimeError("Backup file was not created")
		final_file = out_file

	size = final_file.stat().st_size

	dtype = str(job.get("destination_type") or "local").lower()
	if dtype in ("gdrive", "onedrive"):
		remote_folder = _cloud_folder_norm(str(job.get("destination") or "postgres-backups"))
		if dtype == "gdrive":
			meta = _gdrive_upload_file(cfg, remote_folder, final_file)
			log(f"  Uploaded to Google Drive: {meta.get('name')} (id={meta.get('id')})", "OK")
		elif dtype == "onedrive":
			meta = _onedrive_upload_file(cfg, remote_folder, final_file)
			log(f"  Uploaded to OneDrive: {meta.get('name')} (id={meta.get('id')})", "OK")

	_apply_retention_files(job, dest, jn, db, log)
	return final_file, size


class BackupApp(tk.Tk):
	def __init__(self):
		super().__init__()
		self.title("Postgres Backup Master v1.0")
		self.geometry("1300x760")
		self.minsize(1120, 650)
		self.configure(bg=BG)

		self._style()
		self.cfg = self._load_config()
		self.log_q: queue.Queue[tuple[str, str]] = queue.Queue()
		self.stop_evt = threading.Event()
		self.running_job_ids: set[str] = set()
		self._sched_status_cache: str = "Checking..."
		self._sched_status_checked_at: float = 0.0

		self._build_ui()
		self._refresh_jobs()
		self._refresh_history()
		self._update_status_cards()

		self.after(150, self._poll_log_queue)
		self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
		self.scheduler_thread.start()
		self.protocol("WM_DELETE_WINDOW", self._on_close)

	# ─── Config ─────────────────────────────────────────────────────────────
	def _load_config(self) -> dict:
		return _load_config_file()

	def _save_config(self):
		_save_config_file(self.cfg)

	# ─── UI ─────────────────────────────────────────────────────────────────
	def _style(self):
		s = ttk.Style(self)
		s.theme_use("clam")
		s.configure(".", background=BG, foreground=FG, font=("Segoe UI", 9))
		s.configure("TFrame", background=BG)
		s.configure("Header.TLabel", background=BG, foreground=FG, font=("Segoe UI Semibold", 13))
		s.configure("Sub.TLabel", background=BG, foreground=FG_DIM, font=("Segoe UI", 9))
		s.configure("Card.TFrame", background=BG2, borderwidth=1, relief="solid")
		s.configure("TLabelframe", background=BG2, borderwidth=1, relief="solid")
		s.configure("TLabelframe.Label", background=BG2, foreground=ACCENT, font=("Segoe UI Semibold", 9))
		s.configure("TEntry", fieldbackground=BG3, foreground=FG)
		s.configure("TCombobox", fieldbackground=BG3, foreground=FG)
		s.configure("Treeview", background=BG2, fieldbackground=BG2, foreground=FG, bordercolor=BORDER, rowheight=24)
		s.configure("Treeview.Heading", background=BG3, foreground=FG, font=("Segoe UI Semibold", 9))
		s.map("Treeview", background=[("selected", "#1f3f57")])

		for name, bgc, fgc, active in [
			("Primary.TButton", ACCENT, "white", "#3388ce"),
			("Good.TButton", GREEN, "white", "#3ca85a"),
			("Warn.TButton", ORANGE, "#1a1a1a", "#d19222"),
			("Danger.TButton", RED, "white", "#c24b4b"),
			("Soft.TButton", BG3, FG, "#2e3841"),
			("Nav.TButton", BG2, FG, BG3),
		]:
			s.configure(name, background=bgc, foreground=fgc, relief="flat", padding=(10, 5), font=("Segoe UI Semibold", 9))
			s.map(name, background=[("active", active)])

	def _build_ui(self):
		root = ttk.Frame(self, padding=8)
		root.pack(fill="both", expand=True)

		side = ttk.Frame(root, width=120)
		side.pack(side="left", fill="y", padx=(0, 8))
		side.pack_propagate(False)

		ttk.Label(side, text="Postgres\nBackup Master", style="Header.TLabel", justify="left").pack(anchor="w", pady=(4, 12))
		self._nav_buttons: dict[str, ttk.Button] = {}
		for key, title, cmd in [
			("home", "Home", lambda: self._show_page("home")),
			("backups", "Backups", lambda: self._show_page("backups")),
			("tools", "Tools", self._open_settings),
			("reports", "Reports", lambda: self._show_page("home")),
			("settings", "Settings", self._open_settings),
			("help", "Help", self._show_help),
		]:
			b = ttk.Button(side, text=title, style="Nav.TButton", command=cmd)
			b.pack(fill="x", pady=3)
			self._nav_buttons[key] = b

		main = ttk.Frame(root)
		main.pack(side="left", fill="both", expand=True)

		hdr = ttk.Frame(main)
		hdr.pack(fill="x", pady=(0, 8))
		ttk.Label(hdr, text="Postgres Backup Master", style="Header.TLabel").pack(side="left")
		ttk.Label(hdr, text="Dashboard", style="Sub.TLabel").pack(side="left", padx=14)
		ttk.Button(hdr, text="Settings", style="Soft.TButton", command=self._open_settings).pack(side="right")

		self.page_host = ttk.Frame(main)
		self.page_host.pack(fill="both", expand=True)
		self.page_home = ttk.Frame(self.page_host)
		self.page_backups = ttk.Frame(self.page_host)

		self._build_home_page(self.page_home)
		self._build_backups_page(self.page_backups)
		self._show_page("home")

	def _build_home_page(self, parent):
		cards = ttk.Frame(parent)
		cards.pack(fill="x", pady=(0, 8))
		self.card_total = self._make_card(cards, "Enabled Job", "0")
		self.card_disabled = self._make_card(cards, "Disabled Job", "0")
		self.card_running = self._make_card(cards, "Running", "0")
		self.card_fail = self._make_card(cards, "Failed (24h)", "0")
		self.card_scheduler = self._make_card(cards, "Scheduler", "Checking...")

		grid = ttk.Frame(parent)
		grid.pack(fill="both", expand=True)

		left = ttk.Frame(grid)
		right = ttk.Frame(grid)
		left.pack(side="left", fill="both", expand=True)
		right.pack(side="left", fill="both", expand=True, padx=(8, 0))

		status_box = ttk.Labelframe(left, text="Current Job Status")
		status_box.pack(fill="x")
		self.home_status = tk.Text(status_box, height=7, bg="#0f1317", fg=FG, borderwidth=0)
		self.home_status.pack(fill="both", expand=True, padx=8, pady=8)

		upcoming_box = ttk.Labelframe(left, text="Upcoming Backups")
		upcoming_box.pack(fill="both", expand=True, pady=(8, 0))
		self.home_upcoming = tk.Text(upcoming_box, bg="#0f1317", fg=FG, borderwidth=0)
		self.home_upcoming.pack(fill="both", expand=True, padx=8, pady=8)

		recent_box = ttk.Labelframe(right, text="Recent History")
		recent_box.pack(fill="both", expand=True)
		self.home_recent = tk.Text(recent_box, bg="#0f1317", fg=FG, borderwidth=0)
		self.home_recent.pack(fill="both", expand=True, padx=8, pady=8)

	def _build_backups_page(self, parent):
		body = ttk.Panedwindow(parent, orient="horizontal")
		body.pack(fill="both", expand=True)

		left = ttk.Frame(body)
		right = ttk.Frame(body)
		body.add(left, weight=3)
		body.add(right, weight=2)

		job_box = ttk.Labelframe(left, text="Backups")
		job_box.pack(fill="both", expand=True)

		cols = ("name", "db", "schedule", "next", "status")
		self.job_tree = ttk.Treeview(job_box, columns=cols, show="headings", selectmode="browse")
		self.job_tree.heading("name", text="Job")
		self.job_tree.heading("db", text="Database")
		self.job_tree.heading("schedule", text="Schedule")
		self.job_tree.heading("next", text="Next Run")
		self.job_tree.heading("status", text="Status")
		self.job_tree.column("name", width=210)
		self.job_tree.column("db", width=170)
		self.job_tree.column("schedule", width=120)
		self.job_tree.column("next", width=155)
		self.job_tree.column("status", width=110)
		self.job_tree.pack(fill="both", expand=True, padx=8, pady=8)

		btns = ttk.Frame(job_box)
		btns.pack(fill="x", padx=8, pady=(0, 8))
		ttk.Button(btns, text="Add", style="Primary.TButton", command=self._add_job).pack(side="left")
		ttk.Button(btns, text="Edit", style="Soft.TButton", command=self._edit_job).pack(side="left", padx=6)
		ttk.Button(btns, text="Delete", style="Danger.TButton", command=self._delete_job).pack(side="left")
		ttk.Button(btns, text="Run Now", style="Good.TButton", command=self._run_selected_now).pack(side="left", padx=(16, 6))
		ttk.Button(btns, text="Restore", style="Soft.TButton", command=self._restore_selected).pack(side="left")
		ttk.Button(btns, text="Test Connection", style="Warn.TButton", command=self._test_selected).pack(side="left")
		ttk.Button(btns, text="Refresh", style="Soft.TButton", command=self._refresh_jobs).pack(side="right")

		hist_box = ttk.Labelframe(right, text="Recent History")
		hist_box.pack(fill="both", expand=True)
		hcols = ("time", "job", "result", "size", "file")
		self.hist_tree = ttk.Treeview(hist_box, columns=hcols, show="headings")
		for c, t, w in [
			("time", "Time", 145),
			("job", "Job", 135),
			("result", "Result", 70),
			("size", "Size", 75),
			("file", "File", 210),
		]:
			self.hist_tree.heading(c, text=t)
			self.hist_tree.column(c, width=w)
		self.hist_tree.pack(fill="both", expand=True, padx=8, pady=8)

		log_box = ttk.Labelframe(right, text="Live Log")
		log_box.pack(fill="both", expand=True, pady=(8, 0))
		self.log_text = tk.Text(log_box, height=10, bg="#0f1317", fg=FG, insertbackground=FG, borderwidth=0)
		self.log_text.pack(fill="both", expand=True, padx=8, pady=8)
		self.log_text.tag_configure("INFO", foreground=FG)
		self.log_text.tag_configure("OK", foreground=GREEN)
		self.log_text.tag_configure("WARN", foreground=ORANGE)
		self.log_text.tag_configure("ERR", foreground=RED)
		self.log_text.tag_configure("DIM", foreground=FG_DIM)

	def _show_page(self, page: str):
		for child in self.page_host.winfo_children():
			child.pack_forget()
		if page == "backups":
			self.page_backups.pack(fill="both", expand=True)
		else:
			self.page_home.pack(fill="both", expand=True)
		self._update_nav_style(page)

	def _update_nav_style(self, active: str):
		for k, b in self._nav_buttons.items():
			if k == active:
				b.configure(style="Primary.TButton")
			else:
				b.configure(style="Nav.TButton")

	def _show_help(self):
		messagebox.showinfo(
			"Help",
			"Use Home for status and schedule health.\n"
			"Use Backups to add/edit jobs, run backups, and restore files.",
		)

	def _open_cloud_setup_wizard(self):
		win = tk.Toplevel(self)
		win.title("Cloud Setup Wizard")
		win.configure(bg=BG)
		win.transient(self)
		win.grab_set()
		win.geometry("860x460")

		outer = ttk.Frame(win, padding=12)
		outer.pack(fill="both", expand=True)

		ttk.Label(outer, text="Cloud Setup Wizard", style="Header.TLabel").pack(anchor="w")
		ttk.Label(
			outer,
			text="Configure direct API sign-in for Google Drive and OneDrive.",
			style="Sub.TLabel",
		).pack(anchor="w", pady=(0, 10))

		nb = ttk.Notebook(outer)
		nb.pack(fill="both", expand=True)

		gfrm = ttk.Frame(nb, padding=10)
		ofrm = ttk.Frame(nb, padding=10)
		nb.add(gfrm, text="Google Drive")
		nb.add(ofrm, text="OneDrive")

		# Google tab
		gsecret = tk.StringVar(value=self.cfg.get("google_client_secret") or str(APP_DIR / "google_client_secret.json"))
		gfolder = tk.StringVar(value="postgres-backups")
		ttk.Label(gfrm, text="OAuth client secret JSON", style="Sub.TLabel").grid(row=0, column=0, sticky="w", pady=4)
		ttk.Entry(gfrm, textvariable=gsecret).grid(row=0, column=1, sticky="ew", pady=4)
		ttk.Button(gfrm, text="Browse", style="Soft.TButton", command=lambda: self._browse_exe(gsecret, "Select Google OAuth client secret JSON")).grid(row=0, column=2, padx=6)
		ttk.Label(gfrm, text="Test folder path", style="Sub.TLabel").grid(row=1, column=0, sticky="w", pady=4)
		ttk.Entry(gfrm, textvariable=gfolder).grid(row=1, column=1, sticky="ew", pady=4)
		gfrm.columnconfigure(1, weight=1)

		def g_signin():
			try:
				self.cfg["google_client_secret"] = gsecret.get().strip() or str(APP_DIR / "google_client_secret.json")
				_google_service(self.cfg, interactive=True)
				self._save_config()
				messagebox.showinfo("Google Drive", "Sign-in successful.")
			except Exception as ex:
				messagebox.showerror("Google Drive", f"Sign-in failed.\n{ex}")

		def g_test():
			try:
				self.cfg["google_client_secret"] = gsecret.get().strip() or str(APP_DIR / "google_client_secret.json")
				files = _gdrive_list_files(self.cfg, gfolder.get().strip() or "postgres-backups", prefix="")
				messagebox.showinfo("Google Drive", f"Connected. Files visible: {len(files)}")
			except Exception as ex:
				messagebox.showerror("Google Drive", f"Connection test failed.\n{ex}")

		gbtn = ttk.Frame(gfrm)
		gbtn.grid(row=2, column=0, columnspan=3, sticky="w", pady=(10, 0))
		ttk.Button(gbtn, text="Sign In Google", style="Soft.TButton", command=g_signin).pack(side="left")
		ttk.Button(gbtn, text="Test Connection", style="Soft.TButton", command=g_test).pack(side="left", padx=6)

		# OneDrive tab
		ocid = tk.StringVar(value=self.cfg.get("onedrive_client_id") or "")
		otid = tk.StringVar(value=self.cfg.get("onedrive_tenant_id") or "common")
		ofolder = tk.StringVar(value="postgres-backups")
		ttk.Label(ofrm, text="Client ID", style="Sub.TLabel").grid(row=0, column=0, sticky="w", pady=4)
		ttk.Entry(ofrm, textvariable=ocid).grid(row=0, column=1, sticky="ew", pady=4)
		ttk.Label(ofrm, text="Tenant ID", style="Sub.TLabel").grid(row=1, column=0, sticky="w", pady=4)
		ttk.Entry(ofrm, textvariable=otid).grid(row=1, column=1, sticky="ew", pady=4)
		ttk.Label(ofrm, text="Test folder path", style="Sub.TLabel").grid(row=2, column=0, sticky="w", pady=4)
		ttk.Entry(ofrm, textvariable=ofolder).grid(row=2, column=1, sticky="ew", pady=4)
		ofrm.columnconfigure(1, weight=1)

		def o_signin():
			try:
				self.cfg["onedrive_client_id"] = ocid.get().strip()
				self.cfg["onedrive_tenant_id"] = otid.get().strip() or "common"
				_onedrive_token(self.cfg, interactive=True)
				self._save_config()
				messagebox.showinfo("OneDrive", "Sign-in successful.")
			except Exception as ex:
				messagebox.showerror("OneDrive", f"Sign-in failed.\n{ex}")

		def o_test():
			try:
				self.cfg["onedrive_client_id"] = ocid.get().strip()
				self.cfg["onedrive_tenant_id"] = otid.get().strip() or "common"
				files = _onedrive_list_files(self.cfg, ofolder.get().strip() or "postgres-backups", prefix="")
				messagebox.showinfo("OneDrive", f"Connected. Files visible: {len(files)}")
			except Exception as ex:
				messagebox.showerror("OneDrive", f"Connection test failed.\n{ex}")

		obtn = ttk.Frame(ofrm)
		obtn.grid(row=3, column=0, columnspan=3, sticky="w", pady=(10, 0))
		ttk.Button(obtn, text="Sign In OneDrive", style="Soft.TButton", command=o_signin).pack(side="left")
		ttk.Button(obtn, text="Test Connection", style="Soft.TButton", command=o_test).pack(side="left", padx=6)

		foot = ttk.Frame(outer)
		foot.pack(fill="x", pady=(10, 0))
		ttk.Button(foot, text="Close", style="Primary.TButton", command=win.destroy).pack(side="right")

	def _make_card(self, parent, title: str, value: str):
		frame = ttk.Frame(parent, style="Card.TFrame", padding=10)
		frame.pack(side="left", fill="x", expand=True, padx=(0, 8))
		ttk.Label(frame, text=title, style="Sub.TLabel").pack(anchor="w")
		val = ttk.Label(frame, text=value, style="Header.TLabel")
		val.pack(anchor="w")
		return val

	# ─── Job operations ─────────────────────────────────────────────────────
	def _selected_job(self) -> dict | None:
		sel = self.job_tree.selection()
		if not sel:
			return None
		jid = sel[0]
		for j in self.cfg["jobs"]:
			if j.get("id") == jid:
				return j
		return None

	def _add_job(self):
		d = JobDialog(self, "Add Backup Job", _default_job())
		self.wait_window(d)
		if not d.result:
			return
		self.cfg["jobs"].append(d.result)
		self._save_config()
		self._refresh_jobs()

	def _edit_job(self):
		job = self._selected_job()
		if not job:
			messagebox.showinfo("Edit", "Select a job first.")
			return
		d = JobDialog(self, "Edit Backup Job", dict(job))
		self.wait_window(d)
		if not d.result:
			return
		for i, j in enumerate(self.cfg["jobs"]):
			if j.get("id") == job.get("id"):
				self.cfg["jobs"][i] = d.result
				break
		self._save_config()
		self._refresh_jobs()

	def _delete_job(self):
		job = self._selected_job()
		if not job:
			messagebox.showinfo("Delete", "Select a job first.")
			return
		if not messagebox.askyesno("Delete", f"Delete job '{job['name']}'?"):
			return
		self.cfg["jobs"] = [j for j in self.cfg["jobs"] if j.get("id") != job.get("id")]
		self._save_config()
		self._refresh_jobs()

	def _run_selected_now(self):
		job = self._selected_job()
		if not job:
			messagebox.showinfo("Run", "Select a job first.")
			return
		self._start_job_thread(job, manual=True)

	def _restore_selected(self):
		job = self._selected_job()
		if not job:
			messagebox.showinfo("Restore", "Select a job first.")
			return

		file_path: str | None = None
		if _is_cloud_destination(job):
			file_path = self._download_cloud_backup_for_restore(job)
			if not file_path:
				return
		else:
			initial = job.get("destination") or str(APP_DIR / "backups")
			file_path = filedialog.askopenfilename(
				title="Select backup file to restore",
				initialdir=initial,
				filetypes=[
					("Backup files", "*.zip *.backup *.dump *.tar *.sql"),
					("All files", "*.*"),
				],
			)
			if not file_path:
				return

		db_name = str(job.get("database") or "").strip()
		typed = simpledialog.askstring(
			"Safety Confirmation",
			f"Type database name to confirm restore:\n\n{db_name}",
			parent=self,
		)
		if typed is None:
			return
		if typed.strip() != db_name:
			messagebox.showwarning("Restore", "Database name did not match. Restore cancelled.")
			return

		ok = messagebox.askyesno(
			"Restore",
			f"Final confirmation: restore backup into '{db_name}'?\n\n{file_path}\n\n"
			"This can overwrite existing objects/data.",
		)
		if not ok:
			return

		self._start_restore_thread(job, Path(file_path))

	def _download_cloud_backup_for_restore(self, job: dict) -> str | None:
		dtype = str(job.get("destination_type") or "local").lower()
		folder = _cloud_folder_norm(str(job.get("destination") or "postgres-backups"))
		prefix = f"{_safe_name(job.get('name','backup'))}_{_safe_name(job.get('database','db'))}_"
		try:
			if dtype == "gdrive":
				items = _gdrive_list_files(self.cfg, folder, prefix=prefix)
			elif dtype == "onedrive":
				items = _onedrive_list_files(self.cfg, folder, prefix=prefix)
			else:
				messagebox.showerror("Restore", "Unsupported cloud destination type")
				return None
		except Exception as ex:
			messagebox.showerror("Restore", f"Failed to list cloud backups.\n{ex}")
			return None

		if not items:
			messagebox.showwarning("Restore", "No cloud backup files found for this job.")
			return None

		choice = self._choose_cloud_file_dialog(items, dtype)
		if choice is None:
			return None

		tmp_dir = APP_DIR / "cloud-downloads"
		tmp_dir.mkdir(parents=True, exist_ok=True)
		name = str(choice.get("name") or "cloud_backup.zip")
		out_path = tmp_dir / name
		self._log(f"  Downloading cloud backup: {name}", "DIM")
		try:
			if dtype == "gdrive":
				_gdrive_download_file(self.cfg, str(choice.get("id")), out_path)
			else:
				_onedrive_download_file(self.cfg, str(choice.get("id")), out_path)
		except Exception as ex:
			messagebox.showerror("Restore", f"Failed to download cloud backup.\n{ex}")
			return None

		self._log(f"  Cloud backup downloaded: {out_path}", "DIM")
		return str(out_path)

	def _choose_cloud_file_dialog(self, items: list[dict], provider: str) -> dict | None:
		win = tk.Toplevel(self)
		win.title(f"Select {provider} backup")
		win.configure(bg=BG)
		win.transient(self)
		win.grab_set()
		win.geometry("640x420")

		frm = ttk.Frame(win, padding=10)
		frm.pack(fill="both", expand=True)
		ttk.Label(frm, text="Select backup file to restore", style="Sub.TLabel").pack(anchor="w", pady=(0, 6))

		lb = tk.Listbox(frm, bg=BG3, fg=FG, selectbackground="#1f3f57")
		lb.pack(fill="both", expand=True)

		labels = []
		for it in items:
			name = str(it.get("name") or "")
			size = it.get("size") or "-"
			if size != "-":
				try:
					size = _fmt_bytes(int(size))
				except Exception:
					pass
			mod = it.get("modifiedTime") or it.get("lastModifiedDateTime") or ""
			labels.append(f"{name}   |   {size}   |   {mod}")
		for line in labels:
			lb.insert("end", line)

		chosen: dict | None = None

		def ok():
			nonlocal chosen
			sel = lb.curselection()
			if not sel:
				return
			chosen = items[sel[0]]
			win.destroy()

		btn = ttk.Frame(frm)
		btn.pack(fill="x", pady=(8, 0))
		ttk.Button(btn, text="Cancel", style="Soft.TButton", command=win.destroy).pack(side="right")
		ttk.Button(btn, text="Download & Restore", style="Primary.TButton", command=ok).pack(side="right", padx=(0, 6))

		self.wait_window(win)
		return chosen

	def _test_selected(self):
		job = self._selected_job()
		if not job:
			messagebox.showinfo("Test", "Select a job first.")
			return
		try:
			conn = psycopg2.connect(
				host=job["host"],
				port=int(job["port"]),
				dbname=job["database"],
				user=job["username"],
				password=job["password"],
				connect_timeout=8,
			)
			conn.close()
			messagebox.showinfo("Connection", "Connection successful.")
		except Exception as ex:
			messagebox.showerror("Connection", f"Failed:\n{ex}")

	# ─── Data views ─────────────────────────────────────────────────────────
	def _refresh_jobs(self):
		selected = self.job_tree.selection()
		for item in self.job_tree.get_children():
			self.job_tree.delete(item)

		for j in self.cfg["jobs"]:
			sched = j.get("schedule_time", "") if j.get("schedule_enabled") else "-"
			nxt = self._next_run_str(j)
			status = "Running" if j.get("id") in self.running_job_ids else ("Enabled" if j.get("enabled") else "Disabled")
			self.job_tree.insert("", "end", iid=j["id"], values=(j["name"], j["database"], sched, nxt, status))

		if selected:
			sid = selected[0]
			if self.job_tree.exists(sid):
				self.job_tree.selection_set(sid)

		self._update_status_cards()

	def _refresh_history(self):
		for item in self.hist_tree.get_children():
			self.hist_tree.delete(item)

		recent = list(reversed(self.cfg.get("history", [])[-200:]))
		for h in recent:
			self.hist_tree.insert(
				"",
				"end",
				values=(
					h.get("time", ""),
					h.get("job", ""),
					h.get("result", ""),
					h.get("size", ""),
					h.get("file", ""),
				),
			)
		self._update_status_cards()

	def _update_status_cards(self):
		total = len(self.cfg.get("jobs", []))
		enabled = sum(1 for j in self.cfg.get("jobs", []) if j.get("enabled"))
		disabled = max(0, total - enabled)
		running = len(self.running_job_ids)
		since = _now() - timedelta(hours=24)
		failed = 0
		for h in self.cfg.get("history", []):
			try:
				t = datetime.strptime(h.get("time", ""), "%Y-%m-%d %H:%M:%S")
				if t >= since and h.get("result") == "FAIL":
					failed += 1
			except Exception:
				pass

		self.card_total.config(text=str(enabled))
		self.card_disabled.config(text=str(disabled))
		self.card_running.config(text=str(running))
		self.card_fail.config(text=str(failed))

		now_ts = time.time()
		if now_ts - self._sched_status_checked_at > 15:
			self._sched_status_cache = self._get_scheduler_status_text()
			self._sched_status_checked_at = now_ts
		self.card_scheduler.config(text=self._sched_status_cache)
		self._refresh_home_panels()

	def _refresh_home_panels(self):
		self.home_status.delete("1.0", "end")
		self.home_upcoming.delete("1.0", "end")
		self.home_recent.delete("1.0", "end")

		jobs = self.cfg.get("jobs", [])
		enabled_jobs = [j for j in jobs if j.get("enabled")]
		scheduled_jobs = [j for j in enabled_jobs if j.get("schedule_enabled")]

		self.home_status.insert("end", f"Connected jobs: {len(jobs)}\n")
		self.home_status.insert("end", f"Enabled jobs: {len(enabled_jobs)}\n")
		self.home_status.insert("end", f"Scheduled jobs: {len(scheduled_jobs)}\n")
		self.home_status.insert("end", f"Running now: {len(self.running_job_ids)}\n")
		self.home_status.insert("end", f"Scheduler: {self._sched_status_cache}\n")

		now = _now()
		next_items: list[tuple[datetime, str, str]] = []
		for j in scheduled_jobs:
			nxt = _next_run_datetime(j, now)
			next_items.append((nxt, j.get("name", "Job"), j.get("database", "")))
		next_items.sort(key=lambda x: x[0])
		if not next_items:
			self.home_upcoming.insert("end", "No scheduled backups configured.\n")
		else:
			for dt, name, db in next_items[:15]:
				self.home_upcoming.insert("end", f"{dt.strftime('%d %b %Y %H:%M')}  |  {name}  |  {db}\n")

		recent = list(reversed(self.cfg.get("history", [])[-15:]))
		if not recent:
			self.home_recent.insert("end", "No backup history yet.\n")
		else:
			for h in recent:
				self.home_recent.insert(
					"end",
					f"{h.get('time','')}  |  {h.get('job','')}  |  {h.get('result','')}  |  {h.get('size','-')}\n",
				)

	def _get_scheduler_status_text(self) -> str:
		if os.name != "nt":
			return "N/A"
		d = self._query_scheduler_details()
		if d is None:
			return "Not Installed"
		status = d.get("Status", "").strip()
		if not status:
			return "Installed"
		if "Ready" in status:
			return "Installed (Ready)"
		if "Running" in status:
			return "Installed (Running)"
		if "Disabled" in status:
			return "Installed (Disabled)"
		return f"Installed ({status})"

	def _query_scheduler_details(self) -> dict[str, str] | None:
		if os.name != "nt":
			return None
		cmd = ["schtasks", "/Query", "/TN", SCHEDULER_TASK_NAME, "/V", "/FO", "LIST"]
		run = subprocess.run(cmd, capture_output=True, text=True)
		if run.returncode != 0:
			err = (run.stderr or run.stdout or "").lower()
			if "cannot find" in err:
				return None
			return {"Status": "Unknown"}
		data: dict[str, str] = {}
		for ln in run.stdout.splitlines():
			if ":" not in ln:
				continue
			k, v = ln.split(":", 1)
			data[k.strip()] = v.strip()
		return data

	# ─── Scheduler ──────────────────────────────────────────────────────────
	def _scheduler_loop(self):
		while not self.stop_evt.is_set():
			try:
				self._run_scheduled_jobs()
			except Exception as ex:
				self._log(f"Scheduler error: {ex}", "ERR")
			self.stop_evt.wait(20)

	def _run_scheduled_jobs(self):
		now = _now()
		today = now.strftime("%Y-%m-%d")
		changed = False

		for job in self.cfg.get("jobs", []):
			if not job.get("enabled") or not job.get("schedule_enabled"):
				continue
			if job.get("id") in self.running_job_ids:
				continue

			hh, mm = self._parse_hhmm(job.get("schedule_time", "02:00"))
			run_at = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
			last_mark = job.get("last_scheduled_date", "")

			if now >= run_at and last_mark != today:
				job["last_scheduled_date"] = today
				changed = True
				self._start_job_thread(job, manual=False)

		if changed:
			self._save_config()

		self.after(0, self._refresh_jobs)

	def _next_run_str(self, job: dict) -> str:
		if not job.get("enabled") or not job.get("schedule_enabled"):
			return "-"
		now = _now()
		hh, mm = self._parse_hhmm(job.get("schedule_time", "02:00"))
		candidate = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
		if candidate <= now:
			candidate += timedelta(days=1)
		return candidate.strftime("%d %b %H:%M")

	@staticmethod
	def _parse_hhmm(text: str) -> tuple[int, int]:
		return _parse_hhmm_value(text)

	# ─── Backup execution ───────────────────────────────────────────────────
	def _start_job_thread(self, job: dict, manual: bool):
		jid = job["id"]
		if jid in self.running_job_ids:
			self._log(f"Job already running: {job['name']}", "WARN")
			return

		self.running_job_ids.add(jid)
		self._refresh_jobs()
		thread = threading.Thread(target=self._run_job, args=(dict(job), manual), daemon=True)
		thread.start()

	def _start_restore_thread(self, job: dict, backup_file: Path):
		jid = job["id"]
		if jid in self.running_job_ids:
			self._log(f"Job already running: {job['name']}", "WARN")
			return

		self.running_job_ids.add(jid)
		self._refresh_jobs()
		thread = threading.Thread(target=self._run_restore_job, args=(dict(job), backup_file), daemon=True)
		thread.start()

	def _run_job(self, job: dict, manual: bool):
		jid = job["id"]
		jname = job["name"]
		started = _now_str()
		self._log(f"▶ Starting backup: {jname} ({'manual' if manual else 'scheduled'})", "INFO")

		result = "OK"
		size_str = "-"
		file_out = "-"

		try:
			file_path, size = self._execute_backup(job)
			size_str = _fmt_bytes(size)
			file_out = str(file_path)
			self._log(f"✓ Backup completed: {jname}  →  {file_path.name} ({size_str})", "OK")
		except Exception as ex:
			result = "FAIL"
			self._log(f"✗ Backup failed: {jname} :: {ex}", "ERR")
			for line in traceback.format_exc().splitlines()[-6:]:
				self._log(f"  {line}", "DIM")

		self.cfg["history"].append(
			{
				"time": started,
				"job": jname,
				"result": result,
				"size": size_str,
				"file": file_out,
			}
		)
		self.cfg["history"] = self.cfg["history"][-1000:]
		self._save_config()

		self.running_job_ids.discard(jid)
		self.after(0, self._refresh_jobs)
		self.after(0, self._refresh_history)

	def _run_restore_job(self, job: dict, backup_file: Path):
		jid = job["id"]
		jname = job["name"]
		started = _now_str()
		self._log(f"▶ Starting restore: {jname} from {backup_file.name}", "INFO")

		result = "OK"
		try:
			self._execute_restore(job, backup_file)
			self._log(f"✓ Restore completed: {jname}", "OK")
		except Exception as ex:
			result = "FAIL"
			self._log(f"✗ Restore failed: {jname} :: {ex}", "ERR")
			for line in traceback.format_exc().splitlines()[-8:]:
				self._log(f"  {line}", "DIM")

		self.cfg["history"].append(
			{
				"time": started,
				"job": f"{jname} [RESTORE]",
				"result": result,
				"size": "-",
				"file": str(backup_file),
			}
		)
		self.cfg["history"] = self.cfg["history"][-1000:]
		self._save_config()

		self.running_job_ids.discard(jid)
		self.after(0, self._refresh_jobs)
		self.after(0, self._refresh_history)

	def _execute_restore(self, job: dict, backup_file: Path):
		if not backup_file.exists():
			raise FileNotFoundError(f"Backup file not found: {backup_file}")

		env = os.environ.copy()
		env["PGPASSWORD"] = str(job.get("password") or "")

		if backup_file.suffix.lower() != ".zip":
			self._restore_dump_file(job, backup_file, env, schema_hint=None)
			return

		with tempfile.TemporaryDirectory(prefix="pg_restore_dbzip_") as td:
			tmp_root = Path(td)
			with zipfile.ZipFile(backup_file, "r") as zf:
				zf.extractall(tmp_root)

			schema_zips = sorted([p for p in tmp_root.rglob("*.zip") if p.is_file()])
			if schema_zips:
				configured = {str(s).strip().lower() for s in (job.get("schemas") or []) if str(s).strip()}
				restore_all = bool(job.get("backup_all_schemas", False)) or not configured
				restored = 0
				for sz in schema_zips:
					schema_name = self._schema_name_from_schema_zip(sz)
					if (not restore_all) and schema_name and schema_name.lower() not in configured:
						continue

					with tempfile.TemporaryDirectory(prefix="pg_restore_schemazip_") as sd:
						target_file = self._extract_backup_payload(sz, Path(sd))
						self._restore_dump_file(job, target_file, env, schema_hint=schema_name)
						restored += 1
						if schema_name:
							self._log(f"  Restored schema: {schema_name}", "DIM")

				if restored == 0:
					raise RuntimeError("No matching schema backups found in database ZIP for this job")
				return

			# Fallback: zip directly contains a backup payload
			target_file = self._extract_backup_payload(backup_file, tmp_root)
			self._restore_dump_file(job, target_file, env, schema_hint=None)

	def _schema_name_from_schema_zip(self, schema_zip_path: Path) -> str | None:
		try:
			with zipfile.ZipFile(schema_zip_path, "r") as zf:
				if "schema_manifest.json" in zf.namelist():
					data = json.loads(zf.read("schema_manifest.json").decode("utf-8"))
					s = str(data.get("schema") or "").strip()
					if s:
						return s
		except Exception:
			pass

		name = schema_zip_path.stem
		parts = name.split("_")
		if len(parts) >= 3 and parts[-1].isdigit() and parts[-2].isdigit():
			return "_".join(parts[:-2])
		return name

	def _extract_backup_payload(self, zip_path: Path, to_dir: Path) -> Path:
		with zipfile.ZipFile(zip_path, "r") as zf:
			zf.extractall(to_dir)

		files = [p for p in to_dir.rglob("*") if p.is_file()]
		candidates = [p for p in files if p.suffix.lower() in (".backup", ".dump", ".tar", ".sql")]
		if not candidates:
			raise RuntimeError(f"ZIP does not contain a supported backup file: {zip_path.name}")

		candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
		picked = candidates[0]
		self._log(f"  ZIP extracted, selected: {picked.name}", "DIM")
		return picked

	def _restore_dump_file(self, job: dict, target_file: Path, env: dict, schema_hint: str | None):
		suffix = target_file.suffix.lower()

		if suffix in (".backup", ".dump", ".tar"):
			pg_restore_exec = _resolve_pg_tool(
				"pg_restore",
				self.cfg.get("pg_restore_path"),
				sibling_hint="pg_dump",
				sibling_source_value=self.cfg.get("pg_dump_path"),
			)
			cmd = [
				pg_restore_exec,
				"-h",
				str(job["host"]),
				"-p",
				str(job["port"]),
				"-U",
				str(job["username"]),
				"-d",
				str(job["database"]),
				"--clean",
				"--if-exists",
				"--no-owner",
				"--no-privileges",
			]
			if schema_hint:
				cmd += ["--schema", schema_hint]
			cmd += [str(target_file)]
			self._log(f"  Running pg_restore: {pg_restore_exec}", "DIM")
			run = subprocess.run(cmd, capture_output=True, text=True, env=env)
			if run.returncode != 0:
				msg = (run.stderr or run.stdout or "pg_restore returned non-zero exit code").strip()
				raise RuntimeError(msg.splitlines()[-1] if msg else "pg_restore failed")
			return

		if suffix == ".sql":
			psql_exec = _resolve_pg_tool(
				"psql",
				self.cfg.get("psql_path"),
				sibling_hint="pg_dump",
				sibling_source_value=self.cfg.get("pg_dump_path"),
			)
			cmd = [
				psql_exec,
				"-h",
				str(job["host"]),
				"-p",
				str(job["port"]),
				"-U",
				str(job["username"]),
				"-d",
				str(job["database"]),
				"-v",
				"ON_ERROR_STOP=1",
				"-f",
				str(target_file),
			]
			self._log(f"  Running psql: {psql_exec}", "DIM")
			run = subprocess.run(cmd, capture_output=True, text=True, env=env)
			if run.returncode != 0:
				msg = (run.stderr or run.stdout or "psql returned non-zero exit code").strip()
				raise RuntimeError(msg.splitlines()[-1] if msg else "psql restore failed")
			return

		raise RuntimeError(
			f"Unsupported backup extension '{suffix}'. Use .zip, .backup, .dump, .tar, or .sql"
		)

	def _execute_backup(self, job: dict) -> tuple[Path, int]:
		return _perform_backup(job, self.cfg, self._log)

	def _apply_retention(self, job: dict, dest: Path, safe_job: str, safe_db: str):
		_apply_retention_files(job, dest, safe_job, safe_db, self._log)

	# ─── Settings / Log ─────────────────────────────────────────────────────
	def _open_settings(self):
		dump_var = tk.StringVar(value=self.cfg.get("pg_dump_path") or "auto")
		restore_var = tk.StringVar(value=self.cfg.get("pg_restore_path") or "auto")
		psql_var = tk.StringVar(value=self.cfg.get("psql_path") or "auto")
		gsecret_var = tk.StringVar(value=self.cfg.get("google_client_secret") or str(APP_DIR / "google_client_secret.json"))
		od_client_var = tk.StringVar(value=self.cfg.get("onedrive_client_id") or "")
		od_tenant_var = tk.StringVar(value=self.cfg.get("onedrive_tenant_id") or "common")

		win = tk.Toplevel(self)
		win.title("Settings")
		win.configure(bg=BG)
		win.transient(self)
		win.grab_set()
		win.geometry("860x420")

		frm = ttk.Frame(win, padding=12)
		frm.pack(fill="both", expand=True)
		frm.columnconfigure(1, weight=1)

		def add_row(row: int, label: str, var: tk.StringVar, browse_title: str):
			ttk.Label(frm, text=label, style="Sub.TLabel").grid(row=row, column=0, sticky="w", pady=4)
			ttk.Entry(frm, textvariable=var).grid(row=row, column=1, sticky="ew", pady=4)
			ttk.Button(
				frm,
				text="Browse",
				style="Soft.TButton",
				command=lambda v=var, t=browse_title: self._browse_exe(v, t),
			).grid(row=row, column=2, sticky="w", padx=6)

		add_row(0, "pg_dump path", dump_var, "Select pg_dump executable")
		add_row(1, "pg_restore path", restore_var, "Select pg_restore executable")
		add_row(2, "psql path", psql_var, "Select psql executable")
		add_row(3, "google client secret json", gsecret_var, "Select Google OAuth client secret JSON")

		ttk.Label(frm, text="onedrive client id", style="Sub.TLabel").grid(row=4, column=0, sticky="w", pady=4)
		ttk.Entry(frm, textvariable=od_client_var).grid(row=4, column=1, sticky="ew", pady=4)
		ttk.Label(frm, text="onedrive tenant id", style="Sub.TLabel").grid(row=5, column=0, sticky="w", pady=4)
		ttk.Entry(frm, textvariable=od_tenant_var).grid(row=5, column=1, sticky="ew", pady=4)

		ttk.Label(
			frm,
			text="Use 'auto' to auto-detect binaries. Cloud sign-in uses direct OAuth APIs.",
			style="Sub.TLabel",
		).grid(row=6, column=0, columnspan=3, sticky="w", pady=(8, 0))

		btnrow = ttk.Frame(frm)
		btnrow.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(14, 0))

		def detect_all():
			try:
				dump = _resolve_pg_tool("pg_dump", "auto")
				dump_var.set(dump)
				try:
					restore_var.set(_resolve_pg_tool("pg_restore", "auto", sibling_hint="pg_dump", sibling_source_value=dump))
				except Exception:
					restore_var.set("auto")
				try:
					psql_var.set(_resolve_pg_tool("psql", "auto", sibling_hint="pg_dump", sibling_source_value=dump))
				except Exception:
					psql_var.set("auto")
				messagebox.showinfo("Settings", f"Detected pg_dump:\n{dump}")
			except Exception as ex:
				messagebox.showerror("Settings", f"Could not detect PostgreSQL tools.\n{ex}")

		def save():
			self.cfg["pg_dump_path"] = dump_var.get().strip() or "auto"
			self.cfg["pg_restore_path"] = restore_var.get().strip() or "auto"
			self.cfg["psql_path"] = psql_var.get().strip() or "auto"
			self.cfg["google_client_secret"] = gsecret_var.get().strip() or str(APP_DIR / "google_client_secret.json")
			self.cfg["onedrive_client_id"] = od_client_var.get().strip()
			self.cfg["onedrive_tenant_id"] = od_tenant_var.get().strip() or "common"
			self._save_config()
			win.destroy()

		def sign_in_google():
			try:
				self.cfg["google_client_secret"] = gsecret_var.get().strip() or str(APP_DIR / "google_client_secret.json")
				_google_service(self.cfg, interactive=True)
				self._save_config()
				messagebox.showinfo("Google Drive", "Google Drive sign-in successful.")
			except Exception as ex:
				messagebox.showerror("Google Drive", f"Sign-in failed.\n{ex}")

		def sign_in_onedrive():
			try:
				self.cfg["onedrive_client_id"] = od_client_var.get().strip()
				self.cfg["onedrive_tenant_id"] = od_tenant_var.get().strip() or "common"
				_onedrive_token(self.cfg, interactive=True)
				self._save_config()
				messagebox.showinfo("OneDrive", "OneDrive sign-in successful.")
			except Exception as ex:
				messagebox.showerror("OneDrive", f"Sign-in failed.\n{ex}")

		def install_bg_task():
			try:
				self._install_background_task()
				messagebox.showinfo("Scheduler", "Background scheduler installed (runs every 5 minutes).")
			except Exception as ex:
				messagebox.showerror("Scheduler", f"Failed to install scheduler.\n{ex}")

		def remove_bg_task():
			try:
				self._remove_background_task()
				messagebox.showinfo("Scheduler", "Background scheduler removed.")
			except Exception as ex:
				messagebox.showerror("Scheduler", f"Failed to remove scheduler.\n{ex}")

		def run_bg_now():
			try:
				self._run_background_task_now()
				messagebox.showinfo("Scheduler", "Background scheduler task triggered.")
			except Exception as ex:
				messagebox.showerror("Scheduler", f"Failed to run scheduler now.\n{ex}")

		def open_scheduler_log():
			try:
				if not SCHEDULER_LOG.exists():
					SCHEDULER_LOG.write_text("", encoding="utf-8")
				os.startfile(str(SCHEDULER_LOG))
			except Exception as ex:
				messagebox.showerror("Scheduler", f"Could not open scheduler log.\n{ex}")

		def cloud_wizard():
			self._open_cloud_setup_wizard()

		ttk.Button(btnrow, text="Auto Detect", style="Soft.TButton", command=detect_all).pack(side="left")
		ttk.Button(btnrow, text="Sign In Google", style="Soft.TButton", command=sign_in_google).pack(side="left", padx=6)
		ttk.Button(btnrow, text="Sign In OneDrive", style="Soft.TButton", command=sign_in_onedrive).pack(side="left")
		ttk.Button(btnrow, text="Install Background Scheduler", style="Soft.TButton", command=install_bg_task).pack(side="left", padx=6)
		ttk.Button(btnrow, text="Remove Scheduler", style="Soft.TButton", command=remove_bg_task).pack(side="left")
		ttk.Button(btnrow, text="Run Scheduler Now", style="Soft.TButton", command=run_bg_now).pack(side="left", padx=6)
		ttk.Button(btnrow, text="Open Scheduler Log", style="Soft.TButton", command=open_scheduler_log).pack(side="left")
		ttk.Button(btnrow, text="Cloud Setup Wizard", style="Soft.TButton", command=cloud_wizard).pack(side="left", padx=6)
		ttk.Button(btnrow, text="Save", style="Primary.TButton", command=save).pack(side="right")

	def _browse_exe(self, var: tk.StringVar, title: str):
		p = filedialog.askopenfilename(title=title)
		if p:
			var.set(p)

	def _install_background_task(self):
		python_exe = Path(sys.executable).resolve()
		script_path = Path(__file__).resolve()
		runner = self._write_scheduler_runner(python_exe, script_path)
		tr = f'cmd.exe /c "\"{runner}\""'
		cmd = [
			"schtasks",
			"/Create",
			"/F",
			"/SC",
			"MINUTE",
			"/MO",
			"5",
			"/RL",
			"HIGHEST",
			"/TN",
			SCHEDULER_TASK_NAME,
			"/TR",
			tr,
		]
		run = subprocess.run(cmd, capture_output=True, text=True)
		if run.returncode != 0:
			msg = (run.stderr or run.stdout or "Failed to create task").strip()
			raise RuntimeError(msg)
		self._sched_status_cache = "Installed"
		self._sched_status_checked_at = time.time()
		self._update_status_cards()

	def _write_scheduler_runner(self, python_exe: Path, script_path: Path) -> Path:
		cfg_file = _config_file_path()
		content = (
			"@echo off\r\n"
			f"cd /d \"{APP_DIR}\"\r\n"
			f"set \"PBM_CONFIG_FILE={cfg_file}\"\r\n"
			f"\"{python_exe}\" \"{script_path}\" --run-due-jobs >> \"{SCHEDULER_LOG}\" 2>&1\r\n"
		)
		SCHEDULER_RUNNER.write_text(content, encoding="utf-8")
		return SCHEDULER_RUNNER

	def _remove_background_task(self):
		cmd = ["schtasks", "/Delete", "/F", "/TN", SCHEDULER_TASK_NAME]
		run = subprocess.run(cmd, capture_output=True, text=True)
		if run.returncode != 0 and "cannot find the file specified" not in (run.stderr or "").lower():
			msg = (run.stderr or run.stdout or "Failed to delete task").strip()
			raise RuntimeError(msg)
		try:
			SCHEDULER_RUNNER.unlink(missing_ok=True)
		except Exception:
			pass
		self._sched_status_cache = "Not Installed"
		self._sched_status_checked_at = time.time()
		self._update_status_cards()

	def _run_background_task_now(self):
		cmd = ["schtasks", "/Run", "/TN", SCHEDULER_TASK_NAME]
		run = subprocess.run(cmd, capture_output=True, text=True)
		if run.returncode != 0:
			msg = (run.stderr or run.stdout or "Failed to run scheduler task").strip()
			raise RuntimeError(msg)

	def _log(self, msg: str, level: str = "INFO"):
		self.log_q.put((msg, level))

	def _poll_log_queue(self):
		try:
			while True:
				msg, level = self.log_q.get_nowait()
				tag = level if level in ("INFO", "OK", "WARN", "ERR", "DIM") else "INFO"
				self.log_text.insert("end", f"[{_now_str()}] {msg}\n", tag)
				self.log_text.see("end")
		except queue.Empty:
			pass
		self.after(200, self._poll_log_queue)

	def _on_close(self):
		self.stop_evt.set()
		self.destroy()


class JobDialog(tk.Toplevel):
	def __init__(self, parent: tk.Tk, title: str, job: dict):
		super().__init__(parent)
		self.title(title)
		self.configure(bg=BG)
		self.transient(parent)
		self.grab_set()
		self.geometry("650x560")
		self.minsize(620, 520)
		self.result: dict | None = None
		self.selected_schemas: list[str] = [str(s).strip() for s in (job.get("schemas") or []) if str(s).strip()]

		self.job = job
		self.vars: dict[str, tk.Variable] = {
			"id": tk.StringVar(value=job.get("id", str(uuid.uuid4()))),
			"name": tk.StringVar(value=job.get("name", "")),
			"enabled": tk.BooleanVar(value=bool(job.get("enabled", True))),
			"host": tk.StringVar(value=job.get("host", "localhost")),
			"port": tk.StringVar(value=str(job.get("port", 5432))),
			"database": tk.StringVar(value=job.get("database", "postgres")),
			"backup_all_schemas": tk.BooleanVar(value=bool(job.get("backup_all_schemas", False))),
			"schemas_text": tk.StringVar(value=", ".join(self.selected_schemas)),
			"username": tk.StringVar(value=job.get("username", "postgres")),
			"password": tk.StringVar(value=job.get("password", "")),
			"destination_type": tk.StringVar(value=job.get("destination_type", "local")),
			"destination": tk.StringVar(value=job.get("destination", str(APP_DIR / "backups"))),
			"format": tk.StringVar(value=job.get("format", "custom")),
			"zip_backup": tk.BooleanVar(value=bool(job.get("zip_backup", True))),
			"compression": tk.StringVar(value=str(job.get("compression", 6))),
			"schedule_enabled": tk.BooleanVar(value=bool(job.get("schedule_enabled", False))),
			"schedule_time": tk.StringVar(value=job.get("schedule_time", "02:00")),
			"retention_days": tk.StringVar(value=str(job.get("retention_days", 7))),
			"keep_copies": tk.StringVar(value=str(job.get("keep_copies", 20))),
			"last_scheduled_date": tk.StringVar(value=job.get("last_scheduled_date", "")),
		}

		self._build()

	def _build(self):
		frm = ttk.Frame(self, padding=12)
		frm.pack(fill="both", expand=True)

		ttk.Label(frm, text="Job Details", style="Header.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))

		r = 1
		self._row(frm, r, "Job Name", "name"); r += 1
		ttk.Checkbutton(frm, text="Enabled", variable=self.vars["enabled"]).grid(row=r, column=1, sticky="w", pady=2); r += 1

		ttk.Separator(frm).grid(row=r, column=0, columnspan=3, sticky="ew", pady=8); r += 1
		ttk.Label(frm, text="PostgreSQL Connection", style="Sub.TLabel").grid(row=r, column=0, sticky="w", pady=(0, 4)); r += 1
		self._row(frm, r, "Host", "host"); r += 1
		self._row(frm, r, "Port", "port"); r += 1
		self._row(frm, r, "Database", "database"); r += 1
		ttk.Checkbutton(frm, text="Backup all user schemas", variable=self.vars["backup_all_schemas"]).grid(row=r, column=1, sticky="w", pady=2); r += 1
		self._row(frm, r, "Schemas", "schemas_text", width=44); r += 1
		ttk.Button(frm, text="Select", style="Soft.TButton", command=self._select_schemas).grid(row=r - 1, column=2, padx=6, sticky="w")
		self._row(frm, r, "Username", "username"); r += 1
		self._row(frm, r, "Password", "password", show="*"); r += 1

		ttk.Separator(frm).grid(row=r, column=0, columnspan=3, sticky="ew", pady=8); r += 1
		self._combo_row(frm, r, "Destination Type", "destination_type", ["local", "gdrive", "onedrive"]); r += 1
		self._row(frm, r, "Destination", "destination", width=44); r += 1
		ttk.Button(frm, text="Browse", style="Soft.TButton", command=self._browse_dest).grid(row=r - 1, column=2, padx=6, sticky="w")
		ttk.Button(frm, text="Use Default", style="Soft.TButton", command=self._apply_destination_default).grid(row=r - 1, column=2, padx=(72, 0), sticky="w")

		self._combo_row(frm, r, "Format", "format", ["custom", "plain", "tar"]); r += 1
		ttk.Checkbutton(frm, text="Also create ZIP file", variable=self.vars["zip_backup"]).grid(row=r, column=1, sticky="w", pady=2); r += 1
		self._row(frm, r, "Compression (0-9)", "compression"); r += 1

		ttk.Separator(frm).grid(row=r, column=0, columnspan=3, sticky="ew", pady=8); r += 1
		ttk.Checkbutton(frm, text="Enable Daily Schedule", variable=self.vars["schedule_enabled"]).grid(row=r, column=1, sticky="w", pady=2); r += 1
		self._row(frm, r, "Time (HH:MM)", "schedule_time"); r += 1
		self._row(frm, r, "Retention Days", "retention_days"); r += 1
		self._row(frm, r, "Keep Last Copies", "keep_copies"); r += 1

		frm.columnconfigure(1, weight=1)

		btn = ttk.Frame(frm)
		btn.grid(row=r, column=0, columnspan=3, sticky="ew", pady=(14, 0))
		ttk.Button(btn, text="Cancel", style="Soft.TButton", command=self.destroy).pack(side="right")
		ttk.Button(btn, text="Save", style="Primary.TButton", command=self._save).pack(side="right", padx=(0, 6))

	def _row(self, parent, row: int, label: str, key: str, show: str | None = None, width: int = 28):
		ttk.Label(parent, text=label, style="Sub.TLabel").grid(row=row, column=0, sticky="w", pady=3)
		e = ttk.Entry(parent, textvariable=self.vars[key], width=width, show=show)
		e.grid(row=row, column=1, sticky="ew", pady=3)

	def _combo_row(self, parent, row: int, label: str, key: str, values: list[str]):
		ttk.Label(parent, text=label, style="Sub.TLabel").grid(row=row, column=0, sticky="w", pady=3)
		cb = ttk.Combobox(parent, textvariable=self.vars[key], values=values, state="readonly")
		cb.grid(row=row, column=1, sticky="ew", pady=3)

	def _browse_dest(self):
		p = filedialog.askdirectory(title="Select backup destination")
		if p:
			self.vars["destination"].set(p)

	def _apply_destination_default(self):
		t = str(self.vars["destination_type"].get() or "local").lower()
		base = Path.home()
		if t == "gdrive":
			for cand in [base / "Google Drive", base / "My Drive"]:
				if cand.exists():
					self.vars["destination"].set(str(cand / "postgres-backups"))
					return
			self.vars["destination"].set(str(base / "Google Drive" / "postgres-backups"))
			return
		if t == "onedrive":
			for cand in [base / "OneDrive", Path(os.environ.get("OneDrive", ""))]:
				if str(cand) and cand.exists():
					self.vars["destination"].set(str(cand / "postgres-backups"))
					return
			self.vars["destination"].set(str(base / "OneDrive" / "postgres-backups"))
			return
		self.vars["destination"].set(str(APP_DIR / "backups"))

	def _select_schemas(self):
		job_cfg = {
			"host": self.vars["host"].get().strip(),
			"port": self.vars["port"].get().strip(),
			"database": self.vars["database"].get().strip(),
			"username": self.vars["username"].get().strip(),
			"password": self.vars["password"].get(),
		}
		try:
			schemas = _fetch_user_schemas(job_cfg)
		except Exception as ex:
			messagebox.showerror("Schemas", f"Failed to load schemas.\n{ex}")
			return

		if not schemas:
			messagebox.showwarning("Schemas", "No user schemas found.")
			return

		win = tk.Toplevel(self)
		win.title("Select Schemas")
		win.configure(bg=BG)
		win.transient(self)
		win.grab_set()
		win.geometry("420x420")

		frm = ttk.Frame(win, padding=10)
		frm.pack(fill="both", expand=True)

		ttk.Label(frm, text="Choose schemas to backup", style="Sub.TLabel").pack(anchor="w", pady=(0, 6))
		lb = tk.Listbox(frm, selectmode="multiple", bg=BG3, fg=FG, selectbackground="#1f3f57")
		lb.pack(fill="both", expand=True)
		for s in schemas:
			lb.insert("end", s)

		current = {s.lower() for s in self.selected_schemas}
		for i, s in enumerate(schemas):
			if s.lower() in current:
				lb.selection_set(i)

		btn = ttk.Frame(frm)
		btn.pack(fill="x", pady=(8, 0))

		def save_sel():
			idx = lb.curselection()
			self.selected_schemas = [schemas[i] for i in idx]
			self.vars["schemas_text"].set(", ".join(self.selected_schemas))
			win.destroy()

		ttk.Button(btn, text="Cancel", style="Soft.TButton", command=win.destroy).pack(side="right")
		ttk.Button(btn, text="Save", style="Primary.TButton", command=save_sel).pack(side="right", padx=(0, 6))

	def _save(self):
		try:
			_ = int(self.vars["port"].get().strip())
			c = int(self.vars["compression"].get().strip())
			if c < 0 or c > 9:
				raise ValueError("Compression must be 0 to 9")
			_ = int(self.vars["retention_days"].get().strip())
			k = int(self.vars["keep_copies"].get().strip())
			if k < 1:
				raise ValueError("Keep copies must be at least 1")
			hh, mm = self.vars["schedule_time"].get().strip().split(":", 1)
			if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
				raise ValueError
		except Exception:
			messagebox.showerror("Validation", "Please check numeric fields and time format (HH:MM).")
			return

		name = self.vars["name"].get().strip()
		if not name:
			messagebox.showerror("Validation", "Job name is required.")
			return

		manual_schemas = [s.strip() for s in self.vars["schemas_text"].get().split(",") if s.strip()]
		if manual_schemas:
			self.selected_schemas = manual_schemas
		if not bool(self.vars["backup_all_schemas"].get()) and not self.selected_schemas:
			messagebox.showerror("Validation", "Select at least one schema or enable 'Backup all user schemas'.")
			return

		self.result = {
			k: (v.get() if not isinstance(v, tk.BooleanVar) else bool(v.get()))
			for k, v in self.vars.items()
		}
		self.result["port"] = int(self.result["port"])
		self.result["compression"] = int(self.result["compression"])
		self.result["retention_days"] = int(self.result["retention_days"])
		self.result["keep_copies"] = int(self.result["keep_copies"])
		self.result["name"] = name
		self.result["destination_type"] = str(self.result.get("destination_type") or "local").lower()
		self.result["schemas"] = list(self.selected_schemas)
		self.destroy()


def _run_job_headless(cfg: dict, job: dict, manual: bool) -> bool:
	started = _now_str()
	tag = "manual" if manual else "scheduled"
	_start_msg = f"[{started}] Starting backup: {job['name']} ({tag})"
	print(_start_msg)
	_append_scheduler_log(_start_msg)
	result = "OK"
	size_str = "-"
	file_out = "-"

	def _cli_log(msg: str, level: str = "INFO"):
		line = f"[{_now_str()}] {msg}"
		print(line)
		_append_scheduler_log(line)

	try:
		file_path, size = _perform_backup(job, cfg, _cli_log)
		size_str = _fmt_bytes(size)
		file_out = str(file_path)
		done = f"[{_now_str()}] Backup completed: {job['name']} -> {file_path.name} ({size_str})"
		print(done)
		_append_scheduler_log(done)
	except Exception as ex:
		result = "FAIL"
		fail = f"[{_now_str()}] Backup failed: {job['name']} :: {ex}"
		print(fail)
		_append_scheduler_log(fail)

	cfg["history"].append(
		{
			"time": started,
			"job": job["name"],
			"result": result,
			"size": size_str,
			"file": file_out,
		}
	)
	cfg["history"] = cfg["history"][-1000:]
	return result == "OK"


def _run_due_jobs_headless() -> int:
	cfg = _load_config_file()
	now = _now()
	today = now.strftime("%Y-%m-%d")
	jobs = cfg.get("jobs", [])
	ran_any = False
	_append_scheduler_log(f"[{_now_str()}] Triggered run-due-jobs")
	_append_scheduler_log(f"[{_now_str()}] Config: {_config_file_path()}")
	_append_scheduler_log(f"[{_now_str()}] CWD: {Path.cwd()}")
	_append_scheduler_log(f"[{_now_str()}] Jobs loaded: {len(jobs)}")

	disabled_count = 0
	no_schedule_count = 0
	already_ran_count = 0
	not_time_count = 0

	for job in jobs:
		if not job.get("enabled") or not job.get("schedule_enabled"):
			if not job.get("enabled"):
				disabled_count += 1
			if not job.get("schedule_enabled"):
				no_schedule_count += 1
			continue
		hh, mm = _parse_hhmm_value(job.get("schedule_time", "02:00"))
		run_at = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
		last_mark = job.get("last_scheduled_date", "")
		if now >= run_at and last_mark != today:
			job["last_scheduled_date"] = today
			ran_any = True
			_append_scheduler_log(
				f"[{_now_str()}] Due: {job.get('name','(unnamed)')} @ {job.get('schedule_time','02:00')}"
			)
			_run_job_headless(cfg, job, manual=False)
		elif last_mark == today:
			already_ran_count += 1
		else:
			not_time_count += 1

	if ran_any:
		_save_config_file(cfg)
	else:
		line = f"[{_now_str()}] No scheduled jobs due."
		print(line)
		_append_scheduler_log(line)
		_append_scheduler_log(
			f"[{_now_str()}] Skip summary -> disabled:{disabled_count}, schedule_off:{no_schedule_count}, already_ran_today:{already_ran_count}, before_time:{not_time_count}"
		)
	return 0


def _append_scheduler_log(line: str):
	try:
		with SCHEDULER_LOG.open("a", encoding="utf-8") as f:
			f.write(line + "\n")
	except Exception:
		pass


def _run_single_job_headless(selector: str) -> int:
	cfg = _load_config_file()
	jobs = cfg.get("jobs", [])
	match = None
	for j in jobs:
		if j.get("id") == selector or j.get("name", "").lower() == selector.lower():
			match = j
			break
	if not match:
		print(f"[{_now_str()}] Job not found: {selector}")
		return 2
	ok = _run_job_headless(cfg, match, manual=True)
	_save_config_file(cfg)
	return 0 if ok else 1


def _try_cli_mode() -> int | None:
	parser = argparse.ArgumentParser(add_help=True)
	parser.add_argument("--run-due-jobs", action="store_true", help="Run all due scheduled jobs and exit")
	parser.add_argument("--run-job", help="Run one job by id or exact name and exit")
	args = parser.parse_args()

	if args.run_due_jobs:
		return _run_due_jobs_headless()
	if args.run_job:
		return _run_single_job_headless(args.run_job)
	return None


if __name__ == "__main__":
	cli_exit = _try_cli_mode()
	if cli_exit is not None:
		raise SystemExit(cli_exit)
	app = BackupApp()
	app.mainloop()
