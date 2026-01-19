# tools/db.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


@st.cache_resource(show_spinner=False)
def get_engine() -> Engine:
    db_url: str = st.secrets["db"]["url"]

    if "sslmode=" not in db_url:
        joiner = "&" if "?" in db_url else "?"
        db_url = f"{db_url}{joiner}sslmode=require"

    return create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=2, 
        max_overflow=0, 
        pool_recycle=1800,
        future=True,
    )


def list_applications() -> pd.DataFrame:
    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                  id,
                  applied_date,
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
                  next_follow_up_date,
                  created_at,
                  updated_at
                FROM applications
                ORDER BY applied_date DESC NULLS LAST, created_at DESC
                """
            )
        ).mappings().all()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    desired = [
        "id",
        "applied_date",
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
        "next_follow_up_date",
        "created_at",
        "updated_at",
    ]
    df = df[[c for c in desired if c in df.columns]]

    return df


def get_application(app_id: int) -> Optional[Dict[str, Any]]:
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                  id,
                  applied_date,
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
                  next_follow_up_date,
                  created_at,
                  updated_at
                FROM applications
                WHERE id = :id
                """
            ),
            {"id": app_id},
        ).mappings().first()

    return dict(row) if row else None


def upsert_application(data: Dict[str, Any]) -> int:
    engine = get_engine()
    now = datetime.utcnow()

    with engine.begin() as conn:
        if data.get("id") is None:
            result = conn.execute(
                text(
                    """
                    INSERT INTO applications (
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
                      created_at,
                      updated_at
                    ) VALUES (
                      :company,
                      :title,
                      :location_type,
                      :location_detail,
                      :salary_min,
                      :salary_max,
                      :link_url,
                      :status,
                      :description_short,
                      :notes,
                      :applied_date,
                      :next_follow_up_date,
                      :created_at,
                      :updated_at
                    )
                    RETURNING id
                    """
                ),
                {
                    "company": data.get("company"),
                    "title": data.get("title"),
                    "location_type": data.get("location_type"),
                    "location_detail": data.get("location_detail"),
                    "salary_min": data.get("salary_min"),
                    "salary_max": data.get("salary_max"),
                    "link_url": data.get("link_url"),
                    "status": data.get("status"),
                    "description_short": data.get("description_short"),
                    "notes": data.get("notes"),
                    "applied_date": data.get("applied_date"),
                    "next_follow_up_date": data.get("next_follow_up_date"),
                    "created_at": now,
                    "updated_at": now,
                },
            )
            new_id = result.scalar_one()
            return int(new_id)

        conn.execute(
            text(
                """
                UPDATE applications
                SET
                  company = :company,
                  title = :title,
                  location_type = :location_type,
                  location_detail = :location_detail,
                  salary_min = :salary_min,
                  salary_max = :salary_max,
                  link_url = :link_url,
                  status = :status,
                  description_short = :description_short,
                  notes = :notes,
                  applied_date = :applied_date,
                  next_follow_up_date = :next_follow_up_date,
                  updated_at = :updated_at
                WHERE id = :id
                """
            ),
            {
                "id": data["id"],
                "company": data.get("company"),
                "title": data.get("title"),
                "location_type": data.get("location_type"),
                "location_detail": data.get("location_detail"),
                "salary_min": data.get("salary_min"),
                "salary_max": data.get("salary_max"),
                "link_url": data.get("link_url"),
                "status": data.get("status"),
                "description_short": data.get("description_short"),
                "notes": data.get("notes"),
                "applied_date": data.get("applied_date"),
                "next_follow_up_date": data.get("next_follow_up_date"),
                "updated_at": now,
            },
        )
        return int(data["id"])


def delete_application(app_id: int) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM snapshots WHERE application_id = :id"),
            {"id": app_id},
        )
        conn.execute(
            text("DELETE FROM applications WHERE id = :id"),
            {"id": app_id},
        )


def list_snapshots(app_id: int) -> List[Dict[str, Any]]:
    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, application_id, image_path, captured_at
                FROM snapshots
                WHERE application_id = :app_id
                ORDER BY captured_at DESC
                """
            ),
            {"app_id": app_id},
        ).mappings().all()

    return [dict(r) for r in rows]


def add_snapshot(app_id: int, image_path: str) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO snapshots (application_id, image_path, captured_at)
                VALUES (:app_id, :image_path, now())
                """
            ),
            {"app_id": app_id, "image_path": image_path},
        )