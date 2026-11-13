import os
import sqlite3
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor


DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_PATH = Path(
    os.getenv(
        "DATABASE_PATH",
        str(Path(__file__).resolve().parent / "deployments.db")
    )
)


class PostgreSQLConnection:
    """Small compatibility wrapper for SQLite-style database operations."""

    is_postgres = True

    def __init__(self, database_url):
        self.connection = psycopg2.connect(database_url)

    def execute(self, query, params=()):
        query = query.replace("?", "%s")
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params)
        return cursor

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()


class SQLiteConnection:
    is_postgres = False

    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, params=()):
        return self.connection.execute(query, params)

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()


def get_connection():
    if DATABASE_URL:
        return PostgreSQLConnection(DATABASE_URL)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return SQLiteConnection(connection)


def init_db():
    connection = get_connection()

    try:
        if connection.is_postgres:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS deployments (
                    id BIGSERIAL PRIMARY KEY,
                    version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    deployed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER NOT NULL DEFAULT 0,
                    commit_sha TEXT,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    run_id TEXT
                )
            """)

            migrations = {
                "is_active": "INTEGER NOT NULL DEFAULT 0",
                "commit_sha": "TEXT",
                "started_at": "TIMESTAMP",
                "completed_at": "TIMESTAMP",
                "run_id": "TEXT"
            }

            columns = {
                row["column_name"]
                for row in connection.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'deployments'
                """).fetchall()
            }

        else:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS deployments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    deployed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER NOT NULL DEFAULT 0,
                    commit_sha TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    run_id TEXT
                )
            """)

            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(deployments)"
                ).fetchall()
            }

            migrations = {
                "is_active": "INTEGER NOT NULL DEFAULT 0",
                "commit_sha": "TEXT",
                "started_at": "TEXT",
                "completed_at": "TEXT",
                "run_id": "TEXT"
            }

        for column, definition in migrations.items():
            if column not in columns:
                connection.execute(
                    f"ALTER TABLE deployments ADD COLUMN {column} {definition}"
                )

        active = connection.execute(
            "SELECT id FROM deployments WHERE is_active = 1 LIMIT 1"
        ).fetchone()

        if active is None:
            latest = connection.execute("""
                SELECT id FROM deployments
                WHERE status = 'success'
                ORDER BY id DESC LIMIT 1
            """).fetchone()

            if latest:
                connection.execute(
                    "UPDATE deployments SET is_active = 1 WHERE id = ?",
                    (latest["id"],)
                )

        connection.commit()

    finally:
        connection.close()


def create_deployment(version, status, commit_sha=None, run_id=None):
    if not isinstance(version, str) or not version.strip():
        raise ValueError("Version is required")

    if status not in ("success", "failed", "pending"):
        raise ValueError("Invalid deployment status")

    if commit_sha is not None and not isinstance(commit_sha, str):
        raise ValueError("Commit SHA must be a string")

    if run_id is not None and not isinstance(run_id, str):
        raise ValueError("Run ID must be a string")

    connection = get_connection()

    try:
        if status == "success":
            connection.execute(
                "UPDATE deployments SET is_active = 0"
            )

        query = """
            INSERT INTO deployments (
                version, status, is_active, commit_sha,
                started_at, completed_at, run_id
            )
            VALUES (
                ?, ?, ?, ?, CURRENT_TIMESTAMP,
                CASE WHEN ? IN ('success', 'failed')
                THEN CURRENT_TIMESTAMP ELSE NULL END,
                ?
            )
        """

        params = (
            version.strip(),
            status,
            1 if status == "success" else 0,
            commit_sha,
            status,
            run_id
        )

        if connection.is_postgres:
            cursor = connection.execute(query + " RETURNING id", params)
            deployment_id = cursor.fetchone()["id"]
        else:
            cursor = connection.execute(query, params)
            deployment_id = cursor.lastrowid

        row = connection.execute(
            "SELECT * FROM deployments WHERE id = ?",
            (deployment_id,)
        ).fetchone()

        connection.commit()
        return dict(row)

    finally:
        connection.close()


def update_deployment_status(deployment_id, status):
    if status not in ("success", "failed"):
        raise ValueError("Final status must be success or failed")

    connection = get_connection()

    try:
        connection.execute("BEGIN")

        deployment = connection.execute(
            "SELECT * FROM deployments WHERE id = ?",
            (deployment_id,)
        ).fetchone()

        if deployment is None:
            connection.rollback()
            return None

        if deployment["status"] != "pending":
            connection.rollback()
            raise ValueError("Only pending deployments can be completed")

        if status == "success":
            connection.execute(
                "UPDATE deployments SET is_active = 0"
            )

        connection.execute("""
            UPDATE deployments
            SET status = ?,
                completed_at = CURRENT_TIMESTAMP,
                is_active = ?
            WHERE id = ?
        """, (
            status,
            1 if status == "success" else 0,
            deployment_id
        ))

        updated = connection.execute(
            "SELECT * FROM deployments WHERE id = ?",
            (deployment_id,)
        ).fetchone()

        connection.commit()
        return dict(updated)

    except Exception:
        connection.rollback()
        raise

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


def get_active_deployment():
    connection = get_connection()

    try:
        row = connection.execute(
            "SELECT * FROM deployments WHERE is_active = 1 LIMIT 1"
        ).fetchone()

        return dict(row) if row else None

    finally:
        connection.close()


def rollback_deployment(deployment_id):
    connection = get_connection()

    try:
        connection.execute("BEGIN")

        deployment = connection.execute(
            "SELECT * FROM deployments WHERE id = ?",
            (deployment_id,)
        ).fetchone()

        if deployment is None:
            connection.rollback()
            return None, "Deployment not found"

        if deployment["status"] != "success":
            connection.rollback()
            return None, "Only successful deployments can be activated"

        connection.execute(
            "UPDATE deployments SET is_active = 0"
        )

        connection.execute(
            "UPDATE deployments SET is_active = 1 WHERE id = ?",
            (deployment_id,)
        )

        updated = connection.execute(
            "SELECT * FROM deployments WHERE id = ?",
            (deployment_id,)
        ).fetchone()

        connection.commit()
        return dict(updated), None

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
