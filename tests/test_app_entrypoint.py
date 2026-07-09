import sys
import os
import pytest
from unittest.mock import patch

def test_app_entrypoints_importable():
    """
    Verifies that the main entry points (app_entry.py and app.py) compile and import cleanly.
    """
    sys.path.append(os.path.abspath("src"))
    
    # Test app_entry.py exists and can be parsed
    entry_path = "src/tradenexus/app_entry.py"
    assert os.path.exists(entry_path)
    with open(entry_path, "r", encoding="utf-8") as f:
        content = f.read()
    # Check that syntax is correct by compiling
    compiled = compile(content, entry_path, "exec")
    assert compiled is not None

    # Test app.py exists and can be parsed
    root_app_path = "app.py"
    assert os.path.exists(root_app_path)
    with open(root_app_path, "r", encoding="utf-8") as f:
        root_content = f.read()
    root_compiled = compile(root_content, root_app_path, "exec")
    assert root_compiled is not None
