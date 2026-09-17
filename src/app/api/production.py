from fastapi import APIRouter, Depends

from app.auth.security import get_current_user
from app.services.production_validation_service import validate_environment, summarize

router = APIRouter(
    prefix="/production",
    tags=["Production Validation"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/validation")
def production_validation():
    """Run non-destructive production readiness checks."""
    return summarize(validate_environment(include_tools=True))
