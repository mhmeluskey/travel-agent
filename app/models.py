from pydantic import BaseModel, Field

MAX_ALTERNATIVE_DESTINATIONS = 5

DEFAULT_ALTERNATIVE_DESTINATIONS = [
    "Lisbon",
    "Barcelona",
    "Rome",
    "Athens",
    "Madrid",
]

class TripRequest(BaseModel):
    origin: str | None = None
    destination: str | None = None
    departure_date: str | None = None
    return_date: str | None = None
    travelers: int | None = None
    currency: str = "USD"
    max_flight_price: float | None = None

    alternative_destinations: list[str] = Field(
        default_factory=list
    )
