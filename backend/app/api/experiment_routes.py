from __future__ import annotations

import csv
import io
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ..experiments.configurations import ExperimentConfig
from .schemas import ExperimentRunRequest, ExperimentStatus
from .state import experiments

router = APIRouter(prefix="/api/experiments")


def _status(job: dict, with_result: bool) -> ExperimentStatus:
    return ExperimentStatus(experiment_id=job["experiment_id"], status=job["status"], done=job["done"],
                            total=job["total"], error=job["error"], config=job["config"],
                            result=job["result"] if with_result else None)


@router.post("/run", response_model=ExperimentStatus)
def run(body: ExperimentRunRequest):
    try:
        cfg = ExperimentConfig.from_dict(body.model_dump())
    except (ValueError, TypeError) as exc:
        raise HTTPException(400, str(exc))
    eid = experiments.submit(cfg)
    return _status(experiments.jobs[eid], False)


@router.get("", response_model=list[ExperimentStatus])
def list_jobs():
    return [_status(j, False) for j in experiments.jobs.values()]


@router.get("/{experiment_id}", response_model=ExperimentStatus)
def get(experiment_id: str):
    job = experiments.jobs.get(experiment_id)
    if job is None:
        raise HTTPException(404, "unknown experiment")
    return _status(job, True)


@router.get("/{experiment_id}/export")
def export(experiment_id: str, format: str = "csv", table: str = "summary"):
    job = experiments.jobs.get(experiment_id)
    if job is None or job["result"] is None:
        raise HTTPException(404, "experiment not finished")
    res = job["result"]
    if format == "json":
        return Response(json.dumps(res, indent=2, default=str), media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="experiment_{experiment_id}.json"'})
    data = res["summary"] if table == "summary" else res["rows"]
    buf = io.StringIO()
    if data:
        cols: list[str] = []
        for r in data:
            for k in r:
                if k not in cols:
                    cols.append(k)
        w = csv.DictWriter(buf, fieldnames=cols)
        w.writeheader()
        w.writerows(data)
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="experiment_{experiment_id}_{table}.csv"'})
