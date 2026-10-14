import pytest


@pytest.fixture(autouse=True)
def isolated_runtime(monkeypatch, tmp_path):
    monkeypatch.setenv("STACKRADAR_MODE", "seed")
    monkeypatch.setenv("STACKRADAR_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
