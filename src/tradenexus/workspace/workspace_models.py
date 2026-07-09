from dataclasses import dataclass
from typing import Optional

@dataclass
class Workspace:
    workspace_id: str
    workspace_name: str
    owner_label: str
    created_at: str
    updated_at: str
    is_active: int = 1
    notes: Optional[str] = None
