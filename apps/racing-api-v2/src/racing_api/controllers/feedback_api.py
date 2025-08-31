import asyncio

from fastapi import APIRouter, Depends, HTTPException

from ..models.feedback_date import DateRequest, FeedbackDate
from ..models.horse_race_info import RaceDataResponse
from ..models.race_details import RaceDetailsResponse
from ..models.race_form import RaceFormResponse, RaceFormResponseFull
from ..models.race_form_graph import RaceFormGraphResponse
from ..models.race_result import RaceResultsResponse
from ..models.race_times import RaceTimesResponse
from ..services.feedback_service import FeedbackService, get_feedback_service
from ..repository.feedback_repository import FeedbackRepository
from ..storage.database_session_manager import sessionmanager, with_new_session

router = APIRouter()


# SINGLE CALLS --------------------------------------------------------------


@router.get("/feedback/current-date", response_model=FeedbackDate)
async def get_current_date_today(
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    return await feedback_service.get_current_date_today()


@router.post("/feedback/current-date")
async def store_current_date_today(
    date_request: DateRequest,
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    await feedback_service.store_current_date_today(date=date_request.date)

@router.get(
    "/feedback/race-result/{race_id}",
    response_model=RaceResultsResponse,
)
async def get_race_result(
    race_id: int,
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    return await feedback_service.get_race_result(race_id=race_id)


@router.get("/feedback/todays-race-times", response_model=RaceTimesResponse)
async def get_todays_race_times(
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    return await feedback_service.get_todays_race_times()


# SINGLE CALLS --------------------------------------------------------------


@router.get("/feedback/horse-race-info/{race_id}", response_model=RaceDataResponse)
async def get_horse_race_info(
    race_id: int,
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    return await feedback_service.get_horse_race_info(race_id=race_id)


@router.get("/feedback/race-details/{race_id}", response_model=RaceDetailsResponse)
async def get_race_details(
    race_id: int,
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    return await feedback_service.get_race_details(race_id=race_id)


@router.get("/feedback/race-form-graph/{race_id}", response_model=RaceFormGraphResponse)
async def get_race_form_graph(
    race_id: int,
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    return await feedback_service.get_race_form_graph(race_id=race_id)


@router.get("/feedback/race-form/{race_id}", response_model=RaceFormResponse)
async def get_race_form(
    race_id: int,
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    return await feedback_service.get_race_form(race_id=race_id)


@router.get("/feedback/race-form/{race_id}/full", response_model=RaceFormResponseFull)
async def get_race_form_full(
    race_id: int,
):
    # Use separate DB sessions for each concurrent task to avoid sharing one AsyncSession
    sessionmanager.init_db()

    race_form, race_info, race_form_graph, race_details = await asyncio.gather(
        with_new_session(
            lambda s: FeedbackService(FeedbackRepository(s)),
            lambda svc: svc.get_race_form(race_id=race_id),
        ),
        with_new_session(
            lambda s: FeedbackService(FeedbackRepository(s)),
            lambda svc: svc.get_horse_race_info(race_id=race_id),
        ),
        with_new_session(
            lambda s: FeedbackService(FeedbackRepository(s)),
            lambda svc: svc.get_race_form_graph(race_id=race_id),
        ),
        with_new_session(
            lambda s: FeedbackService(FeedbackRepository(s)),
            lambda svc: svc.get_race_details(race_id=race_id),
        ),
    )

    return RaceFormResponseFull(
        race_form=race_form,
        race_info=race_info,
        race_form_graph=race_form_graph,
        race_details=race_details,
    )
