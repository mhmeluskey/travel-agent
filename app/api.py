from fastapi import FastAPI
from pydantic import BaseModel

from app.graph import app as graph_app

api = FastAPI(
    title="Weather and Flight Agent"
)

class SearchRequest(BaseModel):
    request: str

@api.get("/health")
def health() -> dict:
    return {
        "status": "ok"
    }

@api.post("/search")
def search(
    payload: SearchRequest,
) -> dict:
    result = graph_app.invoke(
        {
            "user_request": payload.request
        }
    )

    return {
        "answer": result.get("answer"),
        "missing": result.get("missing", []),
        "weather": result.get("weather", {}),
        "selected_destinations": result.get(
            "selected_destinations",
            [],
        ),
        "flights": result.get(
            "ranked_flights",
            {},
        ),
        "errors": result.get(
            "errors",
            [],
        ),
    }
