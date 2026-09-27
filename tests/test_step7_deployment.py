import os
import yaml


def test_gitignore_exists():
    assert os.path.exists(".gitignore")


def test_gitignore_excludes_venv():
    content = open(".gitignore").read()
    assert "venv/" in content


def test_gitignore_excludes_env():
    content = open(".gitignore").read()
    assert ".env" in content


def test_gitignore_excludes_pycache():
    content = open(".gitignore").read()
    assert "__pycache__/" in content


def test_procfile_exists():
    assert os.path.exists("Procfile")


def test_procfile_has_uvicorn_command():
    content = open("Procfile").read()
    assert "uvicorn main:app" in content
    assert "$PORT" in content


def test_render_yaml_exists():
    assert os.path.exists("render.yaml")


def test_render_yaml_is_valid():
    with open("render.yaml") as f:
        config = yaml.safe_load(f)
    assert "services" in config
    assert len(config["services"]) == 1


def test_render_yaml_service_config():
    with open("render.yaml") as f:
        config = yaml.safe_load(f)
    svc = config["services"][0]
    assert svc["runtime"] == "python"
    assert "uvicorn main:app" in svc["startCommand"]
    assert svc["plan"] == "free"


def test_render_yaml_has_all_env_vars():
    with open("render.yaml") as f:
        config = yaml.safe_load(f)
    env_keys = {e["key"] for e in config["services"][0]["envVars"]}
    required = {
        "KAPSO_API_KEY",
        "KAPSO_PHONE_NUMBER_ID",
        "KAPSO_WEBHOOK_SECRET",
        "GROQ_API_KEY",
        "SHEET_ID",
        "GOOGLE_SERVICE_ACCOUNT_JSON",
        "USER_PHONE_NUMBER",
        "PORT",
    }
    assert required.issubset(env_keys)


def test_main_py_exists():
    assert os.path.exists("main.py")


def test_requirements_txt_has_uvicorn():
    content = open("requirements.txt").read()
    assert "uvicorn" in content


def test_requirements_txt_has_fastapi():
    content = open("requirements.txt").read()
    assert "fastapi" in content


def test_all_source_files_exist():
    expected = [
        "main.py",
        "app/__init__.py",
        "app/config.py",
        "app/security.py",
        "app/classifier.py",
        "app/kapso.py",
        "app/scheduler.py",
        "app/handlers/__init__.py",
        "app/handlers/link_handler.py",
        "app/handlers/reminder_handler.py",
        "app/handlers/qa_handler.py",
    ]
    for path in expected:
        assert os.path.exists(path), f"Missing: {path}"
