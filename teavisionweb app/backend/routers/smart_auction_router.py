from fastapi import APIRouter

from integrations.smart_auction_client import smart_auction_client
from integrations.smart_auction_schemas import (
    UpstreamHealthResponse,
    InitStatusResponse,
    GradesResponse,
    MessageResponse,
    SimulationRequest,
    SimulationResponse,
    LearningRequest,
    TeaPriceMetadataResponse,
    TeaPriceRequest,
    TeaPriceResponse,
)

router = APIRouter(prefix="/smart-auction", tags=["Smart Auction Integration"])


@router.get("/health", response_model=UpstreamHealthResponse)
async def smart_auction_health():
    data = await smart_auction_client.get("health")
    return UpstreamHealthResponse(**data)


@router.get("/status/init", response_model=InitStatusResponse)
async def smart_auction_status_init():
    data = await smart_auction_client.get("status/init")
    return InitStatusResponse(**data)


@router.get("/grades/{elevation}", response_model=GradesResponse)
async def smart_auction_grades(elevation: str):
    data = await smart_auction_client.get(f"grades/{elevation}")
    return GradesResponse(**data)


@router.get("/tea-price/metadata", response_model=TeaPriceMetadataResponse)
async def smart_auction_tea_price_metadata():
    data = await smart_auction_client.get("tea-price/metadata")
    return TeaPriceMetadataResponse(**data)


@router.post("/tea-price/predict", response_model=TeaPriceResponse)
async def smart_auction_tea_price_predict(req: TeaPriceRequest):
    data = await smart_auction_client.post("tea-price/predict", req.model_dump())
    return TeaPriceResponse(**data)


@router.post("/simulate", response_model=SimulationResponse)
async def smart_auction_simulate(req: SimulationRequest):
    data = await smart_auction_client.post("simulate", req.model_dump())
    return SimulationResponse(**data)


@router.post("/learn", response_model=MessageResponse)
async def smart_auction_learn(req: LearningRequest):
    data = await smart_auction_client.post("learn", req.model_dump())
    return MessageResponse(**data)


@router.post("/reload", response_model=MessageResponse)
async def smart_auction_reload():
    data = await smart_auction_client.post("reload", {})
    return MessageResponse(**data)