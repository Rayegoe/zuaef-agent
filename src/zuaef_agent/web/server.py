"""Console server assembly — Starlette app, static UI, loopback-only MVP.

Local mode (SPEC §9/§14): binds loopback only and rejects anything else
before a socket opens; production auth mode (T012) is out of scope for
v0.2 and is the only path that may ever relax this.
"""

from __future__ import annotations

import threading
import webbrowser
from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from ..config import AgentSettings
from .api import api_routes

LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
_DIST_DIR = Path(__file__).parent / "static" / "dist"


def validate_host(host: str) -> str:
    normalized = host.strip("[]").lower()
    if normalized not in LOOPBACK_HOSTS:
        raise ValueError(
            f"refusing to bind {host!r}: local console mode serves 127.0.0.1 "
            "only; remote access needs the production auth profile (not part of v0.2)"
        )
    return host


def create_app(settings: AgentSettings) -> Starlette:
    routes = list(api_routes())

    async def index(request):  # type: ignore[no-untyped-def]
        if (_DIST_DIR / "index.html").exists():
            return FileResponse(_DIST_DIR / "index.html")
        return JSONResponse(
            {
                "error": {
                    "code": "UI_NOT_BUILT",
                    "message": "web-ui build output missing; run `npm ci && npm run build` in web-ui/",
                }
            },
            status_code=503,
        )

    routes.append(Route("/", index, methods=["GET"]))
    if _DIST_DIR.exists():
        routes.append(Mount("/", app=StaticFiles(directory=_DIST_DIR), name="static"))

    app = Starlette(routes=routes)
    app.state.settings = settings
    return app


def serve(
    settings: AgentSettings,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
) -> None:
    """Blocking console server entry point (used by ``zuaef-agent web``)."""
    validate_host(host)
    # Import here so `import zuaef_agent.web` never pays uvicorn's cost.
    import uvicorn

    app = create_app(settings)
    url = f"http://{host}:{port}/"
    if open_browser:
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()
    uvicorn.run(app, host=host, port=port, log_level="info")
