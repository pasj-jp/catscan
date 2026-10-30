import os
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from catscan.main import create_app
from catscan.settings import get_settings

EXAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "example"


def load_example(name: str) -> bytes:
    """Read raw bytes of an example manuscript file."""
    path = EXAMPLE_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"Example file not found: {path}")
    return path.read_bytes()


@pytest.fixture
def example_dir() -> Path:
    return EXAMPLE_DIR


@pytest.fixture
def example_file():
    return load_example


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


@pytest.fixture(autouse=True)
def isolated_reports_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Ensure every test operates on an isolated temporary reports directory,
    preventing disk pollution and inter-test crosstalk.
    """
    reports_path = tmp_path / "reports"
    reports_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("REPORTS_DIR", str(reports_path))
    get_settings.cache_clear()
    yield reports_path
    get_settings.cache_clear()
