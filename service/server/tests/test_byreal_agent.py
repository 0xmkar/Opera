import os
import sys
import tempfile

import pytest

SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_DIR = os.path.abspath(os.path.join(SERVER_DIR, "..", ".."))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from database import init_database, get_db_connection


@pytest.fixture()
def byreal_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["DATABASE_URL"] = ""
    os.environ["DB_PATH"] = path
    os.environ["ALLOW_SQLITE"] = "true"
    init_database()
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


def test_byreal_agent_run_lifecycle(byreal_db):
    from byreal_agent import create_agent_run, get_agent_run, _update_run

    run_id = create_agent_run(1, "test goal", mode="paper", product="dex")
    run = get_agent_run(run_id)
    assert run is not None
    assert run["status"] == "pending"

    _update_run(run_id, status="completed", result_json='{"summary":"ok"}')
    run = get_agent_run(run_id)
    assert run["status"] == "completed"
    assert run["result"]["summary"] == "ok"


def test_skill_routes_serve_byreal():
    from routes_misc import _resolve_skill_path

    path = _resolve_skill_path("byreal")
    assert path is not None
    content = path.read_text(encoding="utf-8")
    assert "byreal-cli" in content

    perps_path = _resolve_skill_path("byreal-perps")
    assert perps_path is not None
    assert "byreal-perps-cli" in perps_path.read_text(encoding="utf-8")
