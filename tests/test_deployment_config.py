import os

def test_dockerfile_contents():
    """
    Verifies that the Dockerfile exists and contains required runtime setup directives.
    """
    assert os.path.exists("Dockerfile")
    with open("Dockerfile", "r", encoding="utf-8") as f:
        content = f.read()
    
    assert "FROM" in content
    assert "8501" in content
    assert "streamlit run" in content

def test_docker_compose_contents():
    """
    Verifies that docker-compose.yml has correct layout and persistence settings.
    """
    assert os.path.exists("docker-compose.yml")
    with open("docker-compose.yml", "r", encoding="utf-8") as f:
        content = f.read()
        
    assert "services" in content
    assert "tradenexus-app" in content
    assert "8501:8501" in content
    assert "volumes" in content

def test_env_example_contents():
    """
    Verifies that .env.example contains configuration templates.
    """
    assert os.path.exists(".env.example")
    with open(".env.example", "r", encoding="utf-8") as f:
        content = f.read()
        
    assert "DISCORD_WEBHOOK_URL" in content
    assert "TELEGRAM_BOT_TOKEN" in content
    assert "TELEGRAM_CHAT_ID" in content
