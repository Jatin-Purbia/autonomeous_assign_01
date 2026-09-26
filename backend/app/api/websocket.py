from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .state import sim

router = APIRouter()


@router.websocket("/ws/simulation")
async def ws_simulation(ws: WebSocket) -> None:
    """Server pushes ``{"type": "state", state, events, running}`` after every timestep / disruption.

    Clients may send ``{"cmd": "start" | "pause" | "step" | "reset" | "speed", "value": <float>}``."""
    await ws.accept()
    sim.sockets.add(ws)
    try:
        if sim.engine is not None:
            await ws.send_json(sim.payload(include_events=False))
        while True:
            msg = await ws.receive_json()
            cmd = msg.get("cmd")
            try:
                if cmd == "start":
                    sim.start()
                elif cmd == "pause":
                    sim.pause()
                elif cmd == "step":
                    async with sim.lock:
                        sim.require().step()
                elif cmd == "reset":
                    async with sim.lock:
                        sim.reset()
                elif cmd == "speed":
                    sim.speed = max(0.1, min(60.0, float(msg.get("value", 2))))
            except ValueError as exc:
                await ws.send_json({"type": "error", "message": str(exc)})
                continue
            await sim.broadcast()
    except WebSocketDisconnect:
        pass
    finally:
        sim.sockets.discard(ws)
