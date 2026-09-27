import importlib
import os

def test_fastapi_importable():
    import fastapi
    assert fastapi.__version__ == "0.115.0"

def test_uvicorn_importable():
    import uvicorn
    assert uvicorn is not None

def test_apscheduler_importable():
    import apscheduler
    assert apscheduler is not None

def test_gspread_importable():
    import gspread
    assert gspread is not None

def test_requests_importable():
    import requests
    assert requests is not None

def test_dotenv_importable():
    import dotenv
    assert dotenv is not None

def test_httpx_importable():
    import httpx
    assert httpx is not None

def test_env_file_exists():
    assert os.path.exists(".env"), ".env file missing"

def test_requirements_file_exists():
    assert os.path.exists("requirements.txt")

def test_app_package_exists():
    assert os.path.isdir("app")
    assert os.path.exists(os.path.join("app", "__init__.py"))

def test_handlers_package_exists():
    assert os.path.isdir(os.path.join("app", "handlers"))
    assert os.path.exists(os.path.join("app", "handlers", "__init__.py"))
