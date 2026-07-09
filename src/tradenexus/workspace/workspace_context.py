import os
import datetime
from tradenexus.workspace.workspace_models import Workspace
from tradenexus.workspace.workspace_repository import get_workspace, save_workspace, set_workspace_active

# Standard default workspace configuration
DEFAULT_WORKSPACE_ID = "default_workspace"

_active_workspace_id = None

def get_active_workspace_id() -> str:
    """
    Returns the currently active workspace ID.
    If run inside a Streamlit session, retrieves from session_state.
    Otherwise, returns fallback _active_workspace_id or 'default_workspace'.
    """
    global _active_workspace_id
    try:
        import streamlit as st
        # If in Streamlit context, check session_state
        if st.session_state is not None and "active_workspace_id" in st.session_state:
            return st.session_state["active_workspace_id"]
    except Exception:
        pass
        
    if _active_workspace_id is not None:
        return _active_workspace_id
        
    return DEFAULT_WORKSPACE_ID

def set_active_workspace_id(workspace_id: str, db_path: str = None):
    """
    Sets the active workspace ID in session state and updates DB active status.
    """
    global _active_workspace_id
    _active_workspace_id = workspace_id

    # 1. Update in-memory Streamlit state
    try:
        import streamlit as st
        if st.session_state is not None:
            st.session_state["active_workspace_id"] = workspace_id
    except Exception:
        pass
        
    # 2. Update DB persistent status
    try:
        set_workspace_active(workspace_id, db_path)
    except Exception:
        # Ignore if table doesn't exist yet (e.g. during migrations setup)
        pass

def ensure_default_workspace_exists(db_path: str = None):
    """
    Guarantees that the default workspace exists in the workspaces table.
    """
    existing = get_workspace(DEFAULT_WORKSPACE_ID, db_path)
    if not existing:
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        default_ws = Workspace(
            workspace_id=DEFAULT_WORKSPACE_ID,
            workspace_name="Default Workspace",
            owner_label="System",
            created_at=now_str,
            updated_at=now_str,
            is_active=1,
            notes="Default System Workspace"
        )
        save_workspace(default_ws, db_path)
