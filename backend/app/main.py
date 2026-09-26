from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import experiment_routes, simulation_routes, websocket

app = FastAPI(title="Incremental Multi-Agent Path Repair", version="1.0.0",
              description="Dynamic warehouse simulation with incremental, negotiated plan repair.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(simulation_routes.router)
app.include_router(experiment_routes.router)
app.include_router(websocket.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
