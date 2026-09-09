# # """
# # db.py — SQLite storage for entities, recipients, email templates, and send history.

# # Everything the portal needs to remember lives here: which plants/entities are
# # configured, who should get the email for each, and what the email should say.
# # Adding a "new entity" is just an insert into these tables — no code changes.
# # """

# # import json
# # import sqlite3
# # from contextlib import contextmanager
# # from datetime import datetime
# # from pathlib import Path

# # DB_PATH = Path(__file__).parent / "data" / "portal.db"

# # DEFAULT_SUBJECT = "Schedule Punch Update — {display_name} — {date} ({revision})"

# # DEFAULT_BODY = """Dear Team,

# # Please find attached the updated schedule for {display_name} ({entity_key}).

# # Date: {date}
# # Revision: {revision}
# # Punched at: {punch_time}

# # Blocks updated in this revision:
# # {blocks_table}

# # Regards,
# # Scheduling Team
# # """


# # @contextmanager
# # def get_conn():
# #     DB_PATH.parent.mkdir(parents=True, exist_ok=True)
# #     conn = sqlite3.connect(DB_PATH)
# #     conn.row_factory = sqlite3.Row
# #     conn.execute("PRAGMA foreign_keys = ON")
# #     try:
# #         yield conn
# #         conn.commit()
# #     finally:
# #         conn.close()


# # def _column_names(conn, table):
# #     return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


# # def _migrate(conn):
# #     """Adds new columns to already-existing databases without wiping data."""
# #     entity_cols = _column_names(conn, "entities")
# #     if "pos_name" not in entity_cols:
# #         conn.execute("ALTER TABLE entities ADD COLUMN pos_name TEXT")
# #     if "energy_type" not in entity_cols:
# #         conn.execute("ALTER TABLE entities ADD COLUMN energy_type TEXT")

# #     recipient_cols = _column_names(conn, "recipients")
# #     if "kind" not in recipient_cols:
# #         conn.execute("ALTER TABLE recipients ADD COLUMN kind TEXT NOT NULL DEFAULT 'to'")

# #     send_log_cols = _column_names(conn, "send_log")
# #     if "file_blob" not in send_log_cols:
# #         conn.execute("ALTER TABLE send_log ADD COLUMN file_blob BLOB")


# # def init_db():
# #     with get_conn() as conn:
# #         conn.execute(
# #             """
# #             CREATE TABLE IF NOT EXISTS entities (
# #                 id INTEGER PRIMARY KEY AUTOINCREMENT,
# #                 entity_key TEXT UNIQUE NOT NULL,
# #                 display_name TEXT NOT NULL,
# #                 region TEXT,
# #                 pos_name TEXT,
# #                 energy_type TEXT,
# #                 subject_template TEXT NOT NULL,
# #                 body_template TEXT NOT NULL,
# #                 created_at TEXT NOT NULL
# #             )
# #             """
# #         )
# #         conn.execute(
# #             """
# #             CREATE TABLE IF NOT EXISTS recipients (
# #                 id INTEGER PRIMARY KEY AUTOINCREMENT,
# #                 entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
# #                 email TEXT NOT NULL,
# #                 kind TEXT NOT NULL DEFAULT 'to'   -- 'to' or 'cc'
# #             )
# #             """
# #         )
# #         conn.execute(
# #             """
# #             CREATE TABLE IF NOT EXISTS schedule_baseline (
# #                 entity_id INTEGER PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
# #                 date_str TEXT NOT NULL,
# #                 revision TEXT,
# #                 column_headers TEXT NOT NULL,   -- JSON list
# #                 blocks_json TEXT NOT NULL,      -- JSON: {"1": [...], "2": [...], ...}
# #                 updated_at TEXT NOT NULL
# #             )
# #             """
# #         )
# #         conn.execute(
# #             """
# #             CREATE TABLE IF NOT EXISTS send_log (
# #                 id INTEGER PRIMARY KEY AUTOINCREMENT,
# #                 entity_key TEXT,
# #                 display_name TEXT,
# #                 filename TEXT,
# #                 sent_at TEXT,
# #                 block1_num INTEGER,
# #                 block2_num INTEGER,
# #                 recipients TEXT,
# #                 status TEXT,
# #                 error TEXT,
# #                 file_blob BLOB
# #             )
# #             """
# #         )
# #         _migrate(conn)


# # # ---------- entities ----------

# # def list_entities():
# #     with get_conn() as conn:
# #         return conn.execute("SELECT * FROM entities ORDER BY display_name").fetchall()


# # def get_entity_by_key(entity_key: str):
# #     with get_conn() as conn:
# #         return conn.execute(
# #             "SELECT * FROM entities WHERE lower(entity_key) = lower(?)", (entity_key,)
# #         ).fetchone()


# # def get_entity_by_pos_name(pos_name: str):
# #     """
# #     Fallback lookup: an entity's `pos_name` field may hold a comma-separated
# #     list (hybrid plants can have more than one, e.g. solar + wind). Matches
# #     if `pos_name` appears anywhere in that list, case-insensitive.
# #     """
# #     pos_name = (pos_name or "").strip().lower()
# #     if not pos_name:
# #         return None
# #     with get_conn() as conn:
# #         rows = conn.execute("SELECT * FROM entities WHERE pos_name IS NOT NULL").fetchall()
# #     for row in rows:
# #         configured = [p.strip().lower() for p in (row["pos_name"] or "").split(",") if p.strip()]
# #         if pos_name in configured:
# #             return row
# #     return None


# # def get_entity_by_id(entity_id: int):
# #     with get_conn() as conn:
# #         return conn.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()


# # def create_entity(entity_key, display_name, region, to_emails, cc_emails=None,
# #                    pos_name=None, energy_type=None,
# #                    subject_template=None, body_template=None):
# #     cc_emails = cc_emails or []
# #     with get_conn() as conn:
# #         cur = conn.execute(
# #             """
# #             INSERT INTO entities (entity_key, display_name, region, pos_name,
# #                                    energy_type, subject_template, body_template, created_at)
# #             VALUES (?, ?, ?, ?, ?, ?, ?, ?)
# #             """,
# #             (
# #                 entity_key.strip(),
# #                 display_name.strip(),
# #                 region.strip() if region else None,
# #                 pos_name.strip() if pos_name else None,
# #                 energy_type.strip() if energy_type else None,
# #                 subject_template or DEFAULT_SUBJECT,
# #                 body_template or DEFAULT_BODY,
# #                 datetime.now().isoformat(timespec="seconds"),
# #             ),
# #         )
# #         entity_id = cur.lastrowid
# #         for email in to_emails:
# #             email = email.strip()
# #             if email:
# #                 conn.execute(
# #                     "INSERT INTO recipients (entity_id, email, kind) VALUES (?, ?, 'to')",
# #                     (entity_id, email),
# #                 )
# #         for email in cc_emails:
# #             email = email.strip()
# #             if email:
# #                 conn.execute(
# #                     "INSERT INTO recipients (entity_id, email, kind) VALUES (?, ?, 'cc')",
# #                     (entity_id, email),
# #                 )
# #         return entity_id


# # def update_entity_templates(entity_id, subject_template, body_template):
# #     with get_conn() as conn:
# #         conn.execute(
# #             "UPDATE entities SET subject_template = ?, body_template = ? WHERE id = ?",
# #             (subject_template, body_template, entity_id),
# #         )


# # def update_entity_meta(entity_id, display_name, region, pos_name=None, energy_type=None):
# #     with get_conn() as conn:
# #         conn.execute(
# #             "UPDATE entities SET display_name = ?, region = ?, pos_name = ?, energy_type = ? WHERE id = ?",
# #             (display_name, region, pos_name, energy_type, entity_id),
# #         )


# # def delete_entity(entity_id):
# #     with get_conn() as conn:
# #         conn.execute("DELETE FROM entities WHERE id = ?", (entity_id,))


# # # ---------- recipients ----------

# # def list_recipients(entity_id, kind=None):
# #     with get_conn() as conn:
# #         if kind:
# #             return conn.execute(
# #                 "SELECT * FROM recipients WHERE entity_id = ? AND kind = ? ORDER BY email",
# #                 (entity_id, kind),
# #             ).fetchall()
# #         return conn.execute(
# #             "SELECT * FROM recipients WHERE entity_id = ? ORDER BY kind, email", (entity_id,)
# #         ).fetchall()


# # def add_recipient(entity_id, email, kind="to"):
# #     email = email.strip()
# #     if not email:
# #         return
# #     kind = "cc" if kind == "cc" else "to"
# #     with get_conn() as conn:
# #         conn.execute(
# #             "INSERT INTO recipients (entity_id, email, kind) VALUES (?, ?, ?)",
# #             (entity_id, email, kind),
# #         )


# # def remove_recipient(recipient_id):
# #     with get_conn() as conn:
# #         conn.execute("DELETE FROM recipients WHERE id = ?", (recipient_id,))


# # def replace_recipients(entity_id, to_emails, cc_emails):
# #     """Wipes and re-sets an entity's recipient list — used when the inline
# #     setup form on the Upload page updates an existing entity's config."""
# #     with get_conn() as conn:
# #         conn.execute("DELETE FROM recipients WHERE entity_id = ?", (entity_id,))
# #         for email in to_emails:
# #             email = email.strip()
# #             if email:
# #                 conn.execute(
# #                     "INSERT INTO recipients (entity_id, email, kind) VALUES (?, ?, 'to')",
# #                     (entity_id, email),
# #                 )
# #         for email in cc_emails:
# #             email = email.strip()
# #             if email:
# #                 conn.execute(
# #                     "INSERT INTO recipients (entity_id, email, kind) VALUES (?, ?, 'cc')",
# #                     (entity_id, email),
# #                 )


# # # ---------- schedule baseline (protects already-punched blocks) ----------

# # def get_baseline(entity_id):
# #     """Returns dict(date_str, revision, column_headers, blocks) or None."""
# #     with get_conn() as conn:
# #         row = conn.execute(
# #             "SELECT * FROM schedule_baseline WHERE entity_id = ?", (entity_id,)
# #         ).fetchone()
# #     if row is None:
# #         return None
# #     blocks_raw = json.loads(row["blocks_json"])
# #     blocks = {int(k): v for k, v in blocks_raw.items()}
# #     return {
# #         "date_str": row["date_str"],
# #         "revision": row["revision"],
# #         "column_headers": json.loads(row["column_headers"]),
# #         "blocks": blocks,
# #     }


# # def save_baseline(entity_id, date_str, revision, column_headers, blocks: dict):
# #     blocks_json = json.dumps({str(k): v for k, v in blocks.items()})
# #     headers_json = json.dumps(column_headers)
# #     with get_conn() as conn:
# #         conn.execute(
# #             """
# #             INSERT INTO schedule_baseline (entity_id, date_str, revision,
# #                                             column_headers, blocks_json, updated_at)
# #             VALUES (?, ?, ?, ?, ?, ?)
# #             ON CONFLICT(entity_id) DO UPDATE SET
# #                 date_str = excluded.date_str,
# #                 revision = excluded.revision,
# #                 column_headers = excluded.column_headers,
# #                 blocks_json = excluded.blocks_json,
# #                 updated_at = excluded.updated_at
# #             """,
# #             (entity_id, date_str, revision, headers_json, blocks_json,
# #              datetime.now().isoformat(timespec="seconds")),
# #         )


# # # ---------- send log (also persists each punched file's content) ----------

# # def log_send(entity_key, display_name, filename, block1_num, block2_num,
# #              recipients, status, error=None, file_bytes=None):
# #     with get_conn() as conn:
# #         conn.execute(
# #             """
# #             INSERT INTO send_log (entity_key, display_name, filename, sent_at,
# #                                    block1_num, block2_num, recipients, status, error, file_blob)
# #             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
# #             """,
# #             (
# #                 entity_key,
# #                 display_name,
# #                 filename,
# #                 datetime.now().isoformat(timespec="seconds"),
# #                 block1_num,
# #                 block2_num,
# #                 ", ".join(recipients),
# #                 status,
# #                 error,
# #                 file_bytes,
# #             ),
# #         )


# # def list_send_log(limit=100, include_blob=False, date_from=None, date_to=None):
# #     """
# #     date_from / date_to: optional 'YYYY-MM-DD' strings. When both given,
# #     filters to sent_at within that inclusive range. When only date_from is
# #     given, filters to that single day.
# #     """
# #     cols = "*" if include_blob else (
# #         "id, entity_key, display_name, filename, sent_at, block1_num, "
# #         "block2_num, recipients, status, error"
# #     )
# #     where = ""
# #     params = []
# #     if date_from and date_to:
# #         where = "WHERE date(sent_at) BETWEEN ? AND ?"
# #         params = [date_from, date_to]
# #     elif date_from:
# #         where = "WHERE sent_at LIKE ?"
# #         params = [f"{date_from}%"]

# #     with get_conn() as conn:
# #         return conn.execute(
# #             f"SELECT {cols} FROM send_log {where} ORDER BY id DESC LIMIT ?",
# #             (*params, limit),
# #         ).fetchall()


# # def list_today_files():
# #     """Returns today's punched files (with content) — the persisted context
# #     the portal keeps for the current day, downloadable even after a
# #     page reload or restart."""
# #     today_str = datetime.now().date().isoformat()
# #     with get_conn() as conn:
# #         rows = conn.execute(
# #             """
# #             SELECT id, entity_key, display_name, filename, sent_at,
# #                    block1_num, block2_num, status, file_blob
# #             FROM send_log
# #             WHERE status = 'sent' AND sent_at LIKE ?
# #             ORDER BY id DESC
# #             """,
# #             (f"{today_str}%",),
# #         ).fetchall()
# #     return rows


# """
# db.py — SQLite storage for entities, recipients, email templates, and send history.

# Everything the portal needs to remember lives here: which plants/entities are
# configured, who should get the email for each, and what the email should say.
# Adding a "new entity" is just an insert into these tables — no code changes.
# """

# import json
# import sqlite3
# from contextlib import contextmanager
# from datetime import datetime
# from pathlib import Path

# DB_PATH = Path(__file__).parent / "data" / "portal.db"

# DEFAULT_SUBJECT = "Schedule Punch Update — {display_name} — {date} ({revision})"

# DEFAULT_BODY = """Dear Team,

# Please find attached the updated schedule for {display_name} ({entity_key}).

# Date: {date}
# Revision: {revision}
# Sent at: {punch_time}

# Regards,
# Scheduling Team
# """


# @contextmanager
# def get_conn():
#     DB_PATH.parent.mkdir(parents=True, exist_ok=True)
#     conn = sqlite3.connect(DB_PATH)
#     conn.row_factory = sqlite3.Row
#     conn.execute("PRAGMA foreign_keys = ON")
#     try:
#         yield conn
#         conn.commit()
#     finally:
#         conn.close()


# def _column_names(conn, table):
#     return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


# def _migrate(conn):
#     """Adds new columns to already-existing databases without wiping data."""
#     entity_cols = _column_names(conn, "entities")
#     if "pos_name" not in entity_cols:
#         conn.execute("ALTER TABLE entities ADD COLUMN pos_name TEXT")
#     if "energy_type" not in entity_cols:
#         conn.execute("ALTER TABLE entities ADD COLUMN energy_type TEXT")

#     recipient_cols = _column_names(conn, "recipients")
#     if "kind" not in recipient_cols:
#         conn.execute("ALTER TABLE recipients ADD COLUMN kind TEXT NOT NULL DEFAULT 'to'")

#     send_log_cols = _column_names(conn, "send_log")
#     if "file_blob" not in send_log_cols:
#         conn.execute("ALTER TABLE send_log ADD COLUMN file_blob BLOB")


# def init_db():
#     with get_conn() as conn:
#         conn.execute(
#             """
#             CREATE TABLE IF NOT EXISTS entities (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 entity_key TEXT UNIQUE NOT NULL,
#                 display_name TEXT NOT NULL,
#                 region TEXT,
#                 pos_name TEXT,
#                 energy_type TEXT,
#                 subject_template TEXT NOT NULL,
#                 body_template TEXT NOT NULL,
#                 created_at TEXT NOT NULL
#             )
#             """
#         )
#         conn.execute(
#             """
#             CREATE TABLE IF NOT EXISTS recipients (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
#                 email TEXT NOT NULL,
#                 kind TEXT NOT NULL DEFAULT 'to'   -- 'to' or 'cc'
#             )
#             """
#         )
#         conn.execute(
#             """
#             CREATE TABLE IF NOT EXISTS schedule_baseline (
#                 entity_id INTEGER PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
#                 date_str TEXT NOT NULL,
#                 revision TEXT,
#                 column_headers TEXT NOT NULL,   -- JSON list
#                 blocks_json TEXT NOT NULL,      -- JSON: {"1": [...], "2": [...], ...}
#                 updated_at TEXT NOT NULL
#             )
#             """
#         )
#         conn.execute(
#             """
#             CREATE TABLE IF NOT EXISTS send_log (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 entity_key TEXT,
#                 display_name TEXT,
#                 filename TEXT,
#                 sent_at TEXT,
#                 block1_num INTEGER,
#                 block2_num INTEGER,
#                 recipients TEXT,
#                 status TEXT,
#                 error TEXT,
#                 file_blob BLOB
#             )
#             """
#         )
#         _migrate(conn)


# # ---------- entities ----------

# def list_entities():
#     with get_conn() as conn:
#         return conn.execute("SELECT * FROM entities ORDER BY display_name").fetchall()


# def get_entity_by_key(entity_key: str):
#     with get_conn() as conn:
#         return conn.execute(
#             "SELECT * FROM entities WHERE lower(entity_key) = lower(?)", (entity_key,)
#         ).fetchone()


# def get_entity_by_pos_name(pos_name: str):
#     """
#     Fallback lookup: an entity's `pos_name` field may hold a comma-separated
#     list (hybrid plants can have more than one, e.g. solar + wind). Matches
#     if `pos_name` appears anywhere in that list, case-insensitive.
#     """
#     pos_name = (pos_name or "").strip().lower()
#     if not pos_name:
#         return None
#     with get_conn() as conn:
#         rows = conn.execute("SELECT * FROM entities WHERE pos_name IS NOT NULL").fetchall()
#     for row in rows:
#         configured = [p.strip().lower() for p in (row["pos_name"] or "").split(",") if p.strip()]
#         if pos_name in configured:
#             return row
#     return None


# def get_entity_by_id(entity_id: int):
#     with get_conn() as conn:
#         return conn.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()


# def create_entity(entity_key, display_name, region, to_emails, cc_emails=None,
#                    pos_name=None, energy_type=None,
#                    subject_template=None, body_template=None):
#     cc_emails = cc_emails or []
#     with get_conn() as conn:
#         cur = conn.execute(
#             """
#             INSERT INTO entities (entity_key, display_name, region, pos_name,
#                                    energy_type, subject_template, body_template, created_at)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#             """,
#             (
#                 entity_key.strip(),
#                 display_name.strip(),
#                 region.strip() if region else None,
#                 pos_name.strip() if pos_name else None,
#                 energy_type.strip() if energy_type else None,
#                 subject_template or DEFAULT_SUBJECT,
#                 body_template or DEFAULT_BODY,
#                 datetime.now().isoformat(timespec="seconds"),
#             ),
#         )
#         entity_id = cur.lastrowid
#         for email in to_emails:
#             email = email.strip()
#             if email:
#                 conn.execute(
#                     "INSERT INTO recipients (entity_id, email, kind) VALUES (?, ?, 'to')",
#                     (entity_id, email),
#                 )
#         for email in cc_emails:
#             email = email.strip()
#             if email:
#                 conn.execute(
#                     "INSERT INTO recipients (entity_id, email, kind) VALUES (?, ?, 'cc')",
#                     (entity_id, email),
#                 )
#         return entity_id


# def update_entity_templates(entity_id, subject_template, body_template):
#     with get_conn() as conn:
#         conn.execute(
#             "UPDATE entities SET subject_template = ?, body_template = ? WHERE id = ?",
#             (subject_template, body_template, entity_id),
#         )


# def update_entity_meta(entity_id, display_name, region, pos_name=None, energy_type=None):
#     with get_conn() as conn:
#         conn.execute(
#             "UPDATE entities SET display_name = ?, region = ?, pos_name = ?, energy_type = ? WHERE id = ?",
#             (display_name, region, pos_name, energy_type, entity_id),
#         )


# def delete_entity(entity_id):
#     with get_conn() as conn:
#         conn.execute("DELETE FROM entities WHERE id = ?", (entity_id,))


# # ---------- recipients ----------

# def list_recipients(entity_id, kind=None):
#     with get_conn() as conn:
#         if kind:
#             return conn.execute(
#                 "SELECT * FROM recipients WHERE entity_id = ? AND kind = ? ORDER BY email",
#                 (entity_id, kind),
#             ).fetchall()
#         return conn.execute(
#             "SELECT * FROM recipients WHERE entity_id = ? ORDER BY kind, email", (entity_id,)
#         ).fetchall()


# def add_recipient(entity_id, email, kind="to"):
#     email = email.strip()
#     if not email:
#         return
#     kind = "cc" if kind == "cc" else "to"
#     with get_conn() as conn:
#         conn.execute(
#             "INSERT INTO recipients (entity_id, email, kind) VALUES (?, ?, ?)",
#             (entity_id, email, kind),
#         )


# def remove_recipient(recipient_id):
#     with get_conn() as conn:
#         conn.execute("DELETE FROM recipients WHERE id = ?", (recipient_id,))


# def replace_recipients(entity_id, to_emails, cc_emails):
#     """Wipes and re-sets an entity's recipient list — used when the inline
#     setup form on the Upload page updates an existing entity's config."""
#     with get_conn() as conn:
#         conn.execute("DELETE FROM recipients WHERE entity_id = ?", (entity_id,))
#         for email in to_emails:
#             email = email.strip()
#             if email:
#                 conn.execute(
#                     "INSERT INTO recipients (entity_id, email, kind) VALUES (?, ?, 'to')",
#                     (entity_id, email),
#                 )
#         for email in cc_emails:
#             email = email.strip()
#             if email:
#                 conn.execute(
#                     "INSERT INTO recipients (entity_id, email, kind) VALUES (?, ?, 'cc')",
#                     (entity_id, email),
#                 )


# # ---------- schedule baseline (protects already-punched blocks) ----------

# def get_baseline(entity_id):
#     """Returns dict(date_str, revision, column_headers, blocks) or None."""
#     with get_conn() as conn:
#         row = conn.execute(
#             "SELECT * FROM schedule_baseline WHERE entity_id = ?", (entity_id,)
#         ).fetchone()
#     if row is None:
#         return None
#     blocks_raw = json.loads(row["blocks_json"])
#     blocks = {int(k): v for k, v in blocks_raw.items()}
#     return {
#         "date_str": row["date_str"],
#         "revision": row["revision"],
#         "column_headers": json.loads(row["column_headers"]),
#         "blocks": blocks,
#     }


# def save_baseline(entity_id, date_str, revision, column_headers, blocks: dict):
#     blocks_json = json.dumps({str(k): v for k, v in blocks.items()})
#     headers_json = json.dumps(column_headers)
#     with get_conn() as conn:
#         conn.execute(
#             """
#             INSERT INTO schedule_baseline (entity_id, date_str, revision,
#                                             column_headers, blocks_json, updated_at)
#             VALUES (?, ?, ?, ?, ?, ?)
#             ON CONFLICT(entity_id) DO UPDATE SET
#                 date_str = excluded.date_str,
#                 revision = excluded.revision,
#                 column_headers = excluded.column_headers,
#                 blocks_json = excluded.blocks_json,
#                 updated_at = excluded.updated_at
#             """,
#             (entity_id, date_str, revision, headers_json, blocks_json,
#              datetime.now().isoformat(timespec="seconds")),
#         )


# # ---------- send log (also persists each punched file's content) ----------

# def log_send(entity_key, display_name, filename, block1_num, block2_num,
#              recipients, status, error=None, file_bytes=None):
#     with get_conn() as conn:
#         conn.execute(
#             """
#             INSERT INTO send_log (entity_key, display_name, filename, sent_at,
#                                    block1_num, block2_num, recipients, status, error, file_blob)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#             """,
#             (
#                 entity_key,
#                 display_name,
#                 filename,
#                 datetime.now().isoformat(timespec="seconds"),
#                 block1_num,
#                 block2_num,
#                 ", ".join(recipients),
#                 status,
#                 error,
#                 file_bytes,
#             ),
#         )


# def list_send_log(limit=100, include_blob=False, date_from=None, date_to=None):
#     """
#     date_from / date_to: optional 'YYYY-MM-DD' strings. When both given,
#     filters to sent_at within that inclusive range. When only date_from is
#     given, filters to that single day.
#     """
#     cols = "*" if include_blob else (
#         "id, entity_key, display_name, filename, sent_at, block1_num, "
#         "block2_num, recipients, status, error"
#     )
#     where = ""
#     params = []
#     if date_from and date_to:
#         where = "WHERE date(sent_at) BETWEEN ? AND ?"
#         params = [date_from, date_to]
#     elif date_from:
#         where = "WHERE sent_at LIKE ?"
#         params = [f"{date_from}%"]

#     with get_conn() as conn:
#         return conn.execute(
#             f"SELECT {cols} FROM send_log {where} ORDER BY id DESC LIMIT ?",
#             (*params, limit),
#         ).fetchall()


# def list_today_files():
#     """Returns today's punched files (with content) — the persisted context
#     the portal keeps for the current day, downloadable even after a
#     page reload or restart."""
#     today_str = datetime.now().date().isoformat()
#     with get_conn() as conn:
#         rows = conn.execute(
#             """
#             SELECT id, entity_key, display_name, filename, sent_at,
#                    block1_num, block2_num, status, file_blob
#             FROM send_log
#             WHERE status = 'sent' AND sent_at LIKE ?
#             ORDER BY id DESC
#             """,
#             (f"{today_str}%",),
#         ).fetchall()
#     return rows


"""
db.py — SQLite storage for entities, recipients, email templates, and send history.

IMPORTANT: entity_key ("Scheduling entity") is NOT a unique identifier for
routing. Some scheduling entities (e.g. a QCA code like PVG_RES_QCA) bundle
several independent plants together — the same entity_key shows up in files
for completely different plants, each needing its own recipients and even
its own sending mailbox. POS Name is what actually distinguishes them, so
multiple entity rows are allowed to share the same entity_key, and matching
is done primarily by POS Name (see get_entity_by_pos_name / app.py's
resolve_entity), with entity_key kept only as informational metadata.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "portal.db"

DEFAULT_SUBJECT = "Schedule Punch Update — {display_name} — {date} ({revision})"

DEFAULT_BODY = """Dear Team,

Please find attached the updated schedule for {display_name} ({entity_key}).

Date: {date}
Revision: {revision}
Sent at: {punch_time}

Regards,
Scheduling Team
"""

DEFAULT_SMTP_ACCOUNT = "default"


@contextmanager
def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _column_names(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _entities_table_has_unique_entity_key(conn) -> bool:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='entities'"
    ).fetchone()
    if row is None or row[0] is None:
        return False
    return "entity_key TEXT UNIQUE" in row[0]


def _drop_unique_constraint_on_entity_key(conn):
    """
    SQLite can't drop a UNIQUE constraint with ALTER TABLE, so this rebuilds
    the table without it, preserving all existing rows and their ids (so
    recipients/schedule_baseline/send_log foreign keys stay valid).
    """
    conn.execute(
        """
        CREATE TABLE entities_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_key TEXT NOT NULL,
            display_name TEXT NOT NULL,
            region TEXT,
            pos_name TEXT,
            energy_type TEXT,
            smtp_account TEXT,
            subject_template TEXT NOT NULL,
            body_template TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    old_cols = _column_names(conn, "entities")
    has_smtp = "smtp_account" in old_cols
    select_smtp = "smtp_account" if has_smtp else "NULL"
    conn.execute(
        f"""
        INSERT INTO entities_new (id, entity_key, display_name, region, pos_name,
                                   energy_type, smtp_account, subject_template,
                                   body_template, created_at)
        SELECT id, entity_key, display_name, region, pos_name, energy_type,
               {select_smtp}, subject_template, body_template, created_at
        FROM entities
        """
    )
    conn.execute("DROP TABLE entities")
    conn.execute("ALTER TABLE entities_new RENAME TO entities")


def _migrate(conn):
    """Adds new columns / fixes constraints on already-existing databases
    without wiping data."""
    if _entities_table_has_unique_entity_key(conn):
        _drop_unique_constraint_on_entity_key(conn)

    entity_cols = _column_names(conn, "entities")
    if "pos_name" not in entity_cols:
        conn.execute("ALTER TABLE entities ADD COLUMN pos_name TEXT")
    if "energy_type" not in entity_cols:
        conn.execute("ALTER TABLE entities ADD COLUMN energy_type TEXT")
    if "smtp_account" not in entity_cols:
        conn.execute("ALTER TABLE entities ADD COLUMN smtp_account TEXT")

    recipient_cols = _column_names(conn, "recipients")
    if "kind" not in recipient_cols:
        conn.execute("ALTER TABLE recipients ADD COLUMN kind TEXT NOT NULL DEFAULT 'to'")

    send_log_cols = _column_names(conn, "send_log")
    if "file_blob" not in send_log_cols:
        conn.execute("ALTER TABLE send_log ADD COLUMN file_blob BLOB")
    if "entity_id" not in send_log_cols:
        conn.execute("ALTER TABLE send_log ADD COLUMN entity_id INTEGER")


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_key TEXT NOT NULL,
                display_name TEXT NOT NULL,
                region TEXT,
                pos_name TEXT,
                energy_type TEXT,
                smtp_account TEXT,
                subject_template TEXT NOT NULL,
                body_template TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recipients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                email TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'to'   -- 'to' or 'cc'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schedule_baseline (
                entity_id INTEGER PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
                date_str TEXT NOT NULL,
                revision TEXT,
                column_headers TEXT NOT NULL,   -- JSON list
                blocks_json TEXT NOT NULL,      -- JSON: {"1": [...], "2": [...], ...}
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS send_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER,
                entity_key TEXT,
                display_name TEXT,
                filename TEXT,
                sent_at TEXT,
                block1_num INTEGER,
                block2_num INTEGER,
                recipients TEXT,
                status TEXT,
                error TEXT,
                file_blob BLOB
            )
            """
        )
        _migrate(conn)


# ---------- entities ----------

def list_entities():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM entities ORDER BY display_name").fetchall()


def list_regions():
    """Distinct, non-empty region values across all entities — used to
    populate the File Archive's region filter."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT region FROM entities WHERE region IS NOT NULL AND region != '' "
            "ORDER BY region"
        ).fetchall()
    return [r["region"] for r in rows]


def get_entity_by_key(entity_key: str):
    """
    Returns the first entity matching this entity_key, if any. NOT a
    reliable routing lookup on its own since entity_key can be shared by
    several distinct plants (see module docstring) — use
    get_entity_by_pos_name for actual routing decisions. This is kept for
    informational/hint purposes (e.g. "this scheduling entity is already
    used by another registered plant").
    """
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM entities WHERE lower(entity_key) = lower(?)", (entity_key,)
        ).fetchone()


def get_entity_by_pos_name(pos_name: str):
    """
    The real routing lookup. An entity's `pos_name` field may hold a
    comma-separated list (a plant can have more than one POS Name, e.g.
    solar + wind under one hybrid entity). Matches if `pos_name` appears
    anywhere in that list, case-insensitive.
    """
    pos_name = (pos_name or "").strip().lower()
    if not pos_name:
        return None
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM entities WHERE pos_name IS NOT NULL").fetchall()
    for row in rows:
        configured = [p.strip().lower() for p in (row["pos_name"] or "").split(",") if p.strip()]
        if pos_name in configured:
            return row
    return None


def get_entity_by_id(entity_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()


def create_entity(entity_key, display_name, region, to_emails, cc_emails=None,
                   pos_name=None, energy_type=None, smtp_account=None,
                   subject_template=None, body_template=None):
    cc_emails = cc_emails or []
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO entities (entity_key, display_name, region, pos_name,
                                   energy_type, smtp_account, subject_template,
                                   body_template, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity_key.strip(),
                display_name.strip(),
                region.strip() if region else None,
                pos_name.strip() if pos_name else None,
                energy_type.strip() if energy_type else None,
                smtp_account.strip() if smtp_account else None,
                subject_template or DEFAULT_SUBJECT,
                body_template or DEFAULT_BODY,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        entity_id = cur.lastrowid
        for email in to_emails:
            email = email.strip()
            if email:
                conn.execute(
                    "INSERT INTO recipients (entity_id, email, kind) VALUES (?, ?, 'to')",
                    (entity_id, email),
                )
        for email in cc_emails:
            email = email.strip()
            if email:
                conn.execute(
                    "INSERT INTO recipients (entity_id, email, kind) VALUES (?, ?, 'cc')",
                    (entity_id, email),
                )
        return entity_id


def update_entity_templates(entity_id, subject_template, body_template):
    with get_conn() as conn:
        conn.execute(
            "UPDATE entities SET subject_template = ?, body_template = ? WHERE id = ?",
            (subject_template, body_template, entity_id),
        )


def update_entity_meta(entity_id, display_name, region, pos_name=None, energy_type=None,
                        smtp_account=None):
    with get_conn() as conn:
        conn.execute(
            "UPDATE entities SET display_name = ?, region = ?, pos_name = ?, "
            "energy_type = ?, smtp_account = ? WHERE id = ?",
            (display_name, region, pos_name, energy_type, smtp_account, entity_id),
        )


def delete_entity(entity_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM entities WHERE id = ?", (entity_id,))


# ---------- recipients ----------

def list_recipients(entity_id, kind=None):
    with get_conn() as conn:
        if kind:
            return conn.execute(
                "SELECT * FROM recipients WHERE entity_id = ? AND kind = ? ORDER BY email",
                (entity_id, kind),
            ).fetchall()
        return conn.execute(
            "SELECT * FROM recipients WHERE entity_id = ? ORDER BY kind, email", (entity_id,)
        ).fetchall()


def add_recipient(entity_id, email, kind="to"):
    email = email.strip()
    if not email:
        return
    kind = "cc" if kind == "cc" else "to"
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO recipients (entity_id, email, kind) VALUES (?, ?, ?)",
            (entity_id, email, kind),
        )


def remove_recipient(recipient_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM recipients WHERE id = ?", (recipient_id,))


def replace_recipients(entity_id, to_emails, cc_emails):
    """Wipes and re-sets an entity's recipient list — used when the inline
    setup form on the Upload page updates an existing entity's config."""
    with get_conn() as conn:
        conn.execute("DELETE FROM recipients WHERE entity_id = ?", (entity_id,))
        for email in to_emails:
            email = email.strip()
            if email:
                conn.execute(
                    "INSERT INTO recipients (entity_id, email, kind) VALUES (?, ?, 'to')",
                    (entity_id, email),
                )
        for email in cc_emails:
            email = email.strip()
            if email:
                conn.execute(
                    "INSERT INTO recipients (entity_id, email, kind) VALUES (?, ?, 'cc')",
                    (entity_id, email),
                )


# ---------- schedule baseline (kept for reference; not used to restrict
# editing anymore since time-block protection was removed, but still handy
# for anyone wanting historical block values later) ----------

def get_baseline(entity_id):
    """Returns dict(date_str, revision, column_headers, blocks) or None."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM schedule_baseline WHERE entity_id = ?", (entity_id,)
        ).fetchone()
    if row is None:
        return None
    blocks_raw = json.loads(row["blocks_json"])
    blocks = {int(k): v for k, v in blocks_raw.items()}
    return {
        "date_str": row["date_str"],
        "revision": row["revision"],
        "column_headers": json.loads(row["column_headers"]),
        "blocks": blocks,
    }


def save_baseline(entity_id, date_str, revision, column_headers, blocks: dict):
    blocks_json = json.dumps({str(k): v for k, v in blocks.items()})
    headers_json = json.dumps(column_headers)
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO schedule_baseline (entity_id, date_str, revision,
                                            column_headers, blocks_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_id) DO UPDATE SET
                date_str = excluded.date_str,
                revision = excluded.revision,
                column_headers = excluded.column_headers,
                blocks_json = excluded.blocks_json,
                updated_at = excluded.updated_at
            """,
            (entity_id, date_str, revision, headers_json, blocks_json,
             datetime.now().isoformat(timespec="seconds")),
        )


# ---------- send log (also persists each punched file's content forever —
# nothing here is ever auto-deleted, so past files stay accessible) ----------

def log_send(entity_key, display_name, filename, block1_num, block2_num,
             recipients, status, error=None, file_bytes=None, entity_id=None):
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO send_log (entity_id, entity_key, display_name, filename, sent_at,
                                   block1_num, block2_num, recipients, status, error, file_blob)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity_id,
                entity_key,
                display_name,
                filename,
                datetime.now().isoformat(timespec="seconds"),
                block1_num,
                block2_num,
                ", ".join(recipients),
                status,
                error,
                file_bytes,
            ),
        )


def list_send_log(limit=100, include_blob=False, date_from=None, date_to=None):
    """
    date_from / date_to: optional 'YYYY-MM-DD' strings. When both given,
    filters to sent_at within that inclusive range. When only date_from is
    given, filters to that single day.
    """
    cols = "*" if include_blob else (
        "id, entity_id, entity_key, display_name, filename, sent_at, block1_num, "
        "block2_num, recipients, status, error"
    )
    where = ""
    params = []
    if date_from and date_to:
        where = "WHERE date(sent_at) BETWEEN ? AND ?"
        params = [date_from, date_to]
    elif date_from:
        where = "WHERE sent_at LIKE ?"
        params = [f"{date_from}%"]

    with get_conn() as conn:
        return conn.execute(
            f"SELECT {cols} FROM send_log {where} ORDER BY id DESC LIMIT ?",
            (*params, limit),
        ).fetchall()


def list_today_files():
    """Returns today's punched files (with content) — a quick-glance subset
    of the full archive below."""
    today_str = datetime.now().date().isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, entity_key, display_name, filename, sent_at,
                   block1_num, block2_num, status, file_blob
            FROM send_log
            WHERE status = 'sent' AND sent_at LIKE ?
            ORDER BY id DESC
            """,
            (f"{today_str}%",),
        ).fetchall()
    return rows


def list_file_archive(region=None, search=None, date_from=None, date_to=None, limit=300):
    """
    The full, persistent, region-aware file archive — every successfully
    sent file stays available here indefinitely, searchable regardless of
    date. Joins to entities (via entity_id) to pull region/POS Name so
    files from different regions never get mixed together.

    region: exact region string to filter to, or None/'' for all regions.
    search: matches against filename, display_name, or entity_key (LIKE, case-insensitive).
    date_from / date_to: optional 'YYYY-MM-DD' strings, same semantics as list_send_log.
    """
    where_clauses = ["s.status = 'sent'"]
    params = []

    if region:
        where_clauses.append("e.region = ?")
        params.append(region)
    if search:
        where_clauses.append(
            "(s.filename LIKE ? OR s.display_name LIKE ? OR s.entity_key LIKE ?)"
        )
        like = f"%{search}%"
        params.extend([like, like, like])
    if date_from and date_to:
        where_clauses.append("date(s.sent_at) BETWEEN ? AND ?")
        params.extend([date_from, date_to])
    elif date_from:
        where_clauses.append("s.sent_at LIKE ?")
        params.append(f"{date_from}%")

    where_sql = " AND ".join(where_clauses)
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT s.id, s.entity_id, s.entity_key, s.display_name, s.filename,
                   s.sent_at, s.recipients, s.file_blob,
                   e.region AS region, e.pos_name AS pos_name
            FROM send_log s
            LEFT JOIN entities e ON s.entity_id = e.id
            WHERE {where_sql}
            ORDER BY s.id DESC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
    return rows