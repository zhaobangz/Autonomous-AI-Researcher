"""Regression tests for application importability."""


def test_api_server_imports():
    """FastAPI app should import cleanly for uvicorn/Docker startup."""
    from api.server import app

    assert app.title == "Autonomous AI Researcher"