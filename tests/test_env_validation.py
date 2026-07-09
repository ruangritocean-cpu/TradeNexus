import sys
import os
import pytest
from unittest.mock import patch

def test_startup_diagnostics_missing_secrets():
    """
    Verifies that run_startup_diagnostics returns alert config info warnings
    rather than crashing when environment variables are missing.
    """
    sys.path.append(os.path.abspath("src"))
    from tradenexus.ui.dashboard import run_startup_diagnostics
    
    # Force empty environment keys
    with patch.dict(os.environ, {
        "DISCORD_WEBHOOK_URL": "",
        "TELEGRAM_BOT_TOKEN": "",
        "TELEGRAM_CHAT_ID": ""
    }):
        warnings = run_startup_diagnostics()
        
        # Should contain optional alerts notification warning info
        assert any("alert integrations" in w for w in warnings)
        
        # Verify it runs safely and returns a list of warnings
        assert isinstance(warnings, list)
