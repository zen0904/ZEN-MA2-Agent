from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .core import AgentCore
from .portable import app_root


def _token(authorization: str | None) -> str | None:
    return authorization[7:] if authorization and authorization.lower().startswith("bearer ") else None


def create_app(core: AgentCore, root: Path | None = None) -> FastAPI:
    root = root or app_root()
    web = root / "web"
    app = FastAPI(title="ZEN MA2 Agent LAN API")
    app.mount("/assets", StaticFiles(directory=web), name="assets")

    def require(authorization: str | None) -> None:
        if not core.pairing.valid(_token(authorization)):
            raise HTTPException(status_code=401, detail="Pairing required")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(web / "index.html")

    @app.get("/manifest.json")
    def manifest() -> FileResponse:
        return FileResponse(web / "manifest.json", media_type="application/manifest+json")

    @app.post("/api/pair")
    def pair(payload: dict[str, Any]) -> dict[str, str]:
        token = core.pairing.pair(str(payload.get("code", "")), str(payload.get("nonce", "")) or None)
        if not token:
            raise HTTPException(status_code=403, detail="Invalid pairing code")
        core.events.emit("phone", core.snapshot())
        return {"token": token}

    @app.get("/api/state")
    def state(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        require(authorization)
        return core.snapshot()

    @app.post("/api/chat")
    def chat(payload: dict[str, Any], authorization: str | None = Header(default=None)) -> dict[str, Any]:
        require(authorization)
        return core.submit_request(str(payload.get("text", "")), source="mobile")

    @app.post("/api/actions/{action_id}/approve")
    def approve(action_id: str, payload: dict[str, Any], authorization: str | None = Header(default=None)) -> dict[str, Any]:
        require(authorization)
        try:
            return core.approve_action(action_id, danger_confirmed=bool(payload.get("danger_confirmed")))
        except PermissionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/actions/{action_id}/cancel")
    def cancel(action_id: str, authorization: str | None = Header(default=None)) -> dict[str, bool]:
        require(authorization)
        return {"cancelled": core.cancel_action(action_id)}

    @app.websocket("/ws")
    async def websocket(ws: WebSocket) -> None:
        if not core.pairing.valid(ws.query_params.get("token")):
            await ws.close(code=4401)
            return
        await ws.accept()
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        unsubscribe = core.events.subscribe(lambda event: loop.call_soon_threadsafe(queue.put_nowait, event))
        try:
            await ws.send_json({"type": "snapshot", "data": core.snapshot()})
            while True:
                try:
                    await ws.send_json(await asyncio.wait_for(queue.get(), timeout=20))
                except TimeoutError:
                    await ws.send_json({"type": "heartbeat", "data": {}})
        except WebSocketDisconnect:
            pass
        finally:
            unsubscribe()

    return app


class MobileServer:
    def __init__(self, core: AgentCore, port: int = 8765, root: Path | None = None):
        self.core, self.port = core, port
        self.app = create_app(core, root)
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._server = uvicorn.Server(uvicorn.Config(self.app, host="0.0.0.0", port=self.port, log_level="warning"))
        self._thread = threading.Thread(target=self._server.run, name="zen-ma2-mobile", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server:
            self._server.should_exit = True
