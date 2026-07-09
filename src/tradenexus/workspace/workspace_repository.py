import sqlite3
import datetime
from typing import List, Optional
from tradenexus.journal.db import get_db_connection
from tradenexus.workspace.workspace_models import Workspace

def save_workspace(workspace: Workspace, db_path: str = None):
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO workspaces (
                    workspace_id, workspace_name, owner_label, created_at, updated_at, is_active, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (
                workspace.workspace_id,
                workspace.workspace_name,
                workspace.owner_label,
                workspace.created_at,
                workspace.updated_at,
                workspace.is_active,
                workspace.notes
            ))
    finally:
        conn.close()

def load_workspaces(db_path: str = None) -> List[Workspace]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM workspaces ORDER BY created_at ASC;")
        rows = cursor.fetchall()
        workspaces = []
        for r in rows:
            workspaces.append(Workspace(
                workspace_id=r["workspace_id"],
                workspace_name=r["workspace_name"],
                owner_label=r["owner_label"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                is_active=r["is_active"],
                notes=r["notes"]
            ))
        return workspaces
    finally:
        conn.close()

def get_workspace(workspace_id: str, db_path: str = None) -> Optional[Workspace]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM workspaces WHERE workspace_id = ?;", (workspace_id,))
        r = cursor.fetchone()
        if r:
            return Workspace(
                workspace_id=r["workspace_id"],
                workspace_name=r["workspace_name"],
                owner_label=r["owner_label"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                is_active=r["is_active"],
                notes=r["notes"]
            )
        return None
    finally:
        conn.close()

def set_workspace_active(workspace_id: str, db_path: str = None):
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("UPDATE workspaces SET is_active = 0;")
            conn.execute("UPDATE workspaces SET is_active = 1 WHERE workspace_id = ?;", (workspace_id,))
    finally:
        conn.close()

def create_workspace(workspace_id: str, workspace_name: str, notes: str = "", db_path: str = None) -> bool:
    if get_workspace(workspace_id, db_path):
        return False
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ws = Workspace(
        workspace_id=workspace_id,
        workspace_name=workspace_name,
        owner_label="User",
        created_at=now,
        updated_at=now,
        is_active=0,
        notes=notes
    )
    save_workspace(ws, db_path)
    return True
