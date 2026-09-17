from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.auth.security import get_current_user
from app.observability.metrics import metrics

router = APIRouter(prefix="/observability", tags=["Observability"])


@router.get("/metrics", response_class=PlainTextResponse, dependencies=[Depends(get_current_user)])
def prometheus_metrics():
    return PlainTextResponse(metrics.prometheus(), media_type="text/plain; version=0.0.4")
