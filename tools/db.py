# tools/db.py
from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

DB_PATH = os.path.join("data", "application_tracker.db")


def _get_conn() -> sqlite3.Connection:
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_conn()
    cur = conn.cursor()

    # Main applications table, now including response_type and response_date
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS applications (
            id TEXT PRIMARY KEY,
            company TEXT,
            title TEXT,
            location_type TEXT,
            location_detail TEXT,
            salary_min REAL,
            salary_max REAL,
            link_url TEXT,
            status TEXT,
            description_short TEXT,
            notes TEXT,
            applied_date TEXT,
            next_follow_up_date TEXT,
            response_type TEXT,
            response_date TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )

    # Snapshots table for screenshots
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id TEXT,
            image_path TEXT,
            captured_at TEXT,
            FOREIGN KEY (application_id) REFERENCES applications(id)
        )
        """
    )

    conn.commit()
    conn.close()


def list_applications() -> pd.DataFrame:
    conn = _get_conn()
    try:
        df = pd.read_sql_query(
            """
            SELECT
                id,
                company,
                title,
                location_type,
                location_detail,
                salary_min,
                salary_max,
                link_url,
                status,
                description_short,
                notes,
                applied_date,
                next_follow_up_date,
                response_type,
                response_date,
                created_at,
                updated_at
            FROM applications
            ORDER BY
                CASE WHEN applied_date IS NULL THEN 1 ELSE 0 END,
                applied_date DESC,
                created_at DESC
            """,
            conn,
        )
    except Exception:
        df = pd.DataFrame(
            columns=[
                "id",
                "company",
                "title",
                "location_type",
                "location_detail",
                "salary_min",
                "salary_max",
                "link_url",
                "status",
                "description_short",
                "notes",
                "applied_date",
                "next_follow_up_date",
                "response_type",
                "response_date",
                "created_at",
                "updated_at",
            ]
        )
    finally:
        conn.close()
    return df


def get_application(app_id: str) -> Optional[Dict]:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
    row = cur.fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def upsert_application(data: Dict) -> str:
    """
    Insert or update an application.
    If data['id'] is None, we insert and return the new id.
    """
    conn = _get_conn()
    cur = conn.cursor()

    now = _now_iso()

    app_id = data.get("id")
    if not app_id:
        # New application
        import uuid

        app_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO applications (
                id,
                company,
                title,
                location_type,
                location_detail,
                salary_min,
                salary_max,
                link_url,
                status,
                description_short,
                notes,
                applied_date,
                next_follow_up_date,
                response_type,
                response_date,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                app_id,
                data.get("company"),
                data.get("title"),
                data.get("location_type"),
                data.get("location_detail"),
                data.get("salary_min"),
                data.get("salary_max"),
                data.get("link_url"),
                data.get("status"),
                data.get("description_short"),
                data.get("notes"),
                data.get("applied_date"),
                data.get("next_follow_up_date"),
                data.get("response_type"),
                data.get("response_date"),
                now,
                now,
            ),
        )
    else:
        # Update existing
        cur.execute(
            """
            UPDATE applications
            SET
                company = ?,
                title = ?,
                location_type = ?,
                location_detail = ?,
                salary_min = ?,
                salary_max = ?,
                link_url = ?,
                status = ?,
                description_short = ?,
                notes = ?,
                applied_date = ?,
                next_follow_up_date = ?,
                response_type = ?,
                response_date = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                data.get("company"),
                data.get("title"),
                data.get("location_type"),
                data.get("location_detail"),
                data.get("salary_min"),
                data.get("salary_max"),
                data.get("link_url"),
                data.get("status"),
                data.get("description_short"),
                data.get("notes"),
                data.get("applied_date"),
                data.get("next_follow_up_date"),
                data.get("response_type"),
                data.get("response_date"),
                now,
                app_id,
            ),
        )

    conn.commit()
    conn.close()
    return app_id


def delete_application(app_id: str):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM snapshots WHERE application_id = ?", (app_id,))
    cur.execute("DELETE FROM applications WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()


def add_snapshot(app_id: str, image_path: str):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO snapshots (application_id, image_path, captured_at)
        VALUES (?, ?, ?)
        """,
        (app_id, image_path, _now_iso()),
    )
    conn.commit()
    conn.close()


def list_snapshots(app_id: str) -> List[Dict]:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, application_id, image_path, captured_at
        FROM snapshots
        WHERE application_id = ?
        ORDER BY captured_at DESC, id DESC
        """,
        (app_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]