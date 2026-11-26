"""`GET /cluster/facts` (#401): the SLURM cluster's partitions, nodes and the user's accounts,
read only and kept for ten minutes (`spectio_server.cluster`). Behind the session, as every
route; a host with no SLURM answers `scheduler: null`, never an error."""

from typing import Any

from fastapi import APIRouter, Request

from spectio_server.api import models

router = APIRouter(tags=["cluster"])


@router.get("/cluster/facts", response_model=models.ClusterFacts)
def cluster_facts(request: Request) -> dict[str, Any]:
    facts: dict[str, Any] = request.app.state.cluster.get()
    return facts
