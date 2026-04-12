"""Pydantic request/response schemas for the Amazon Tracker API."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class AddProductRequest(BaseModel):
    """Request body for adding a product to track."""

    url: str | None = None
    asin: str | None = None
    marketplace: str | None = None


class ProductResponse(BaseModel):
    """Response schema for a tracked product."""

    id: int
    asin: str
    marketplace: str
    url: str
    title: str | None
    brand: str | None
    main_image_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SnapshotResponse(BaseModel):
    """Response schema for a product snapshot."""

    id: int
    product_id: int
    current_price: float | None
    currency: str | None
    list_price: float | None
    rating: float | None
    review_count: int | None
    availability_text: str | None
    seller_info: str | None
    bullet_points: list[str] | None
    crawl_timestamp: datetime

    model_config = {"from_attributes": True}


class ChangeResponse(BaseModel):
    """Response schema for a detected change record."""

    id: int
    product_id: int
    field_name: str
    old_value: str | None
    new_value: str | None
    detected_at: datetime

    model_config = {"from_attributes": True}


class WasPriceResponse(BaseModel):
    """Was Price 조회 응답."""

    reference_date: date
    was_price: float | None
    data_points: int


class T30Response(BaseModel):
    """T30 조회 응답."""

    reference_date: date
    t30: float | None
    data_points: int


class PriceIndicatorsResponse(BaseModel):
    """Was Price + T30 통합 조회 응답."""

    reference_date: date
    was_price: float | None
    was_price_data_points: int
    t30: float | None
    t30_data_points: int


class SimulationRequest(BaseModel):
    """시뮬레이션 요청."""

    simulation_date: date
    simulation_price: float = Field(ge=0)
    evaluation_date: date


class SimulationResult(BaseModel):
    """시뮬레이션 결과."""

    evaluation_date: date
    before_was_price: float | None
    after_was_price: float | None
    before_t30: float | None
    after_t30: float | None
    simulation_date: date
    simulation_price: float
