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
                deployed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER NOT NULL DEFAULT 0
            )
        """)

        # Migrate existing databases that don't have is_active.
        columns = [
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(deployments)"
            ).fetchall()
        ]

        if "is_active" not in columns:
            connection.execute("""
                ALTER TABLE deployments
                ADD COLUMN is_active INTEGER NOT NULL DEFAULT 0
            """)

        # If no deployment is active, select the latest successful one.
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


def create_deployment(version, status):
    if not isinstance(version, str) or not version.strip():
        raise ValueError("Version is required")

    if status not in ("success", "failed", "pending"):
        raise ValueError("Invalid deployment status")

    connection = get_connection()

    try:
        # A successful new deployment replaces the active deployment.
        if status == "success":
            connection.execute(
                "UPDATE deployments SET is_active = 0"
            )

        cursor = connection.execute(
            """
            INSERT INTO deployments (version, status, is_active)
            VALUES (?, ?, ?)
            """,
            (version.strip(), status, 1 if status == "success" else 0)
        )

        deployment_id = cursor.lastrowid

        row = connection.execute(
            "SELECT * FROM deployments WHERE id = ?",
            (deployment_id,)
        ).fetchone()

        connection.commit()
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
        connection.execute("BEGIN IMMEDIATE")

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
