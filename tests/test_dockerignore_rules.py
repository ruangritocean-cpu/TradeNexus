import os

def test_dockerignore_exclusions():
    """
    Verifies that .dockerignore exists and excludes virtual environment, database, and repository items.
    """
    assert os.path.exists(".dockerignore")
    with open(".dockerignore", "r", encoding="utf-8") as f:
        rules = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        
    # Check key exclusions are present
    assert ".venv/" in rules
    assert "data/*.sqlite" in rules
    assert ".git/" in rules
    assert ".pytest_cache/" in rules
