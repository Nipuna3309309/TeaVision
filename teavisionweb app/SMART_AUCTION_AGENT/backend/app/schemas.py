from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SimulationRequest(BaseModel):
    lot_volume: float = Field(..., gt=0)
    elevation: str
    grade: str
    use_current_price: bool = False
    current_price: Optional[float] = None
    storage_cost: float = Field(..., ge=0)
    demand: str
    competition: str
    use_production_cost: bool = False
    production_cost: Optional[float] = None
    year: int
    month: int
    week_in_month: int


class LearningRequest(BaseModel):
    lot_volume: float = Field(..., gt=0)
    elevation: str
    grade: str
    use_current_price: bool = False
    current_price: Optional[float] = None
    storage_cost: float = Field(..., ge=0)
    demand: str
    competition: str
    use_production_cost: bool = False
    production_cost: Optional[float] = None
    year: int
    month: int
    week_in_month: int
    buyer_online_steps: int = 0
    factory_online_steps: int = 0
    broker_online_steps: int = 0


class GradesResponse(BaseModel):
    grades: List[str]


class MessageResponse(BaseModel):
    message: str


class SimulationResponse(BaseModel):
    forecast_price: float
    current_price_used: float
    actual_price: Optional[float]
    target_sale_no: int
    target_date: str
    steps_ahead: int

    sold: bool
    reserve_price: float
    bid_price: float
    sold_volume: float
    unsold_volume: float

    commission_rate: float
    broker_signal: int
    broker_guidance: str

    factory_profit: float
    broker_profit: float

    buyer_action: int
    buyer_action_label: str

    reserve_factor: float
    release_factor: float

    buyer_explanation: Dict[str, Any]
    factory_explanation: Dict[str, Any]
    broker_explanation: Dict[str, Any]

    confidence_score: Optional[float] = None


class TeaPriceMetadataResponse(BaseModel):
    elevations: List[str]
    grades_by_elevation: Dict[str, List[str]]


class TeaPriceRequest(BaseModel):
    elevation: str
    grade: str
    target_year: int = Field(..., ge=2000, le=2100)
    target_month: int = Field(..., ge=1, le=12)
    target_week_in_month: int = Field(..., ge=1, le=5)
    return_last_n_weeks: int = Field(8, ge=1, le=60)


class TeaPricePoint(BaseModel):
    year: int
    sale_no: int
    date: str
    predicted_price: float
    lower_band: float
    upper_band: float


class TeaPriceResponse(BaseModel):
    elevation: str
    grade: str

    model_last_train_date: str
    model_last_train_year: int
    model_last_train_sale_no: int

    target_year: int
    target_month: int
    target_week_in_month: int
    target_date: str
    target_sale_no: int

    steps_ahead: int
    predicted_price: float

    band_pct: float
    predicted_lower_band: float
    predicted_upper_band: float

    series: List[TeaPricePoint]