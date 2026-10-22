import os, sys, threading
import pytest
from werkzeug.serving import make_server

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "prototipo"))
from app import crear_app  # noqa: E402


@pytest.fixture(scope="session")
def app():
    return crear_app()


@pytest.fixture()
def cliente(app):
    return app.test_client()


@pytest.fixture(scope="session")
def servidor(app):
    srv = make_server("127.0.0.1", 5055, app, threaded=True)
    hilo = threading.Thread(target=srv.serve_forever, daemon=True)
    hilo.start()
    yield "http://127.0.0.1:5055"
    srv.shutdown()


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "locale": "es-PE", "viewport": {"width": 1280, "height": 900}}
