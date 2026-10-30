import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).resolve().parent / "deployments.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_connection()
    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS deployments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL,
                status TEXT NOT NULL,
                deployed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.commit()
    finally:
        connection.close()


def create_deployment(version, status):
    if not version or not version.strip():
        raise ValueError("Version is required")

    if not status or not status.strip():
        raise ValueError("Status is required")

    connection = get_connection()
    try:
        cursor = connection.execute(
            """
            INSERT INTO deployments (version, status)
            VALUES (?, ?)
            """,
            (version.strip(), status.strip())
        )
        connection.commit()

        deployment_id = cursor.lastrowid
        row = connection.execute(
            "SELECT * FROM deployments WHERE id = ?",
            (deployment_id,)
        ).fetchone()

        return dict(row)
    finally:
        connection.close()


def get_all_deployments():
    connection = get_connection()
    try:
        rows = connection.execute(
            "SELECT * FROM deployments ORDER BY id DESC"
        ).fetchall()

        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_deployment_by_id(deployment_id):
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM deployments WHERE id = ?",
            (deployment_id,)
        ).fetchone()

        return dict(row) if row else None
    finally:
        connection.close()
