import os
import sys
import tempfile
import pytest

# Add scripts directory to sys.path to import release_check
sys.path.append(os.path.abspath("scripts"))
import release_check

def test_secrets_scanning_logic():
    """
    Verifies that the secret scanning regex detects forbidden patterns and ignores template guides.
    """
    secret_patterns = [
        r"ghp_[a-zA-Z0-9]{36}",
        r"discord\.com/api/webhooks/[0-9]+/[a-zA-Z0-9_-]+"
    ]
    
    # Create temp file with a real-looking secret
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("my_key = 'ghp_abc123xyz789012345678901234567890123'\n")
        temp_path = f.name
        
    try:
        violations = release_check.scan_file_for_secrets(temp_path, secret_patterns)
        assert violations == 1
    finally:
        os.remove(temp_path)

def test_secrets_scanning_ignores_template():
    """
    Verifies that example variables are ignored by secret scanning.
    """
    secret_patterns = [
        r"discord\.com/api/webhooks/[0-9]+/[a-zA-Z0-9_-]+"
    ]
    
    # Create temp file with template guides
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("DISCORD_WEBHOOK_URL=your_discord_webhook_url_here\n")
        temp_path = f.name
        
    try:
        violations = release_check.scan_file_for_secrets(temp_path, secret_patterns)
        assert violations == 0
    finally:
        os.remove(temp_path)
