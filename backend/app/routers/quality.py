"""Quality dashboard routes (Phase 4: Error Case Dashboard)."""

import logging
from fastapi import APIRouter, Query
from app.schemas.chat import ErrorCasesResponse, ErrorCaseStatsResponse, ErrorCaseItem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/quality", tags=["quality"])


@router.get("/stats", response_model=ErrorCaseStatsResponse)
async def get_quality_stats():
    """Get error case statistics: reason distribution and stage-error cross stats."""
    try:
        from app.services.storage import get_error_case_stats
        return get_error_case_stats()
    except Exception as e:
        logger.warning(f"Failed to get quality stats: {e}")
        return ErrorCaseStatsResponse()


@router.get("/errors", response_model=ErrorCasesResponse)
async def get_error_cases(
    limit: int = Query(20, ge=1, le=100, description="Number of cases to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """Get paginated error cases with tag info."""
    try:
        from app.services.storage import get_error_cases as fetch_error_cases
        result = fetch_error_cases(limit=limit, offset=offset)
        cases = [ErrorCaseItem(**case) for case in result["cases"]]
        return ErrorCasesResponse(cases=cases, total=result["total"])
    except Exception as e:
        logger.warning(f"Failed to get error cases: {e}")
        return ErrorCasesResponse(cases=[], total=0)
