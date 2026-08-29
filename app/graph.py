import json
import os
from typing import TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from app.models import (
    DEFAULT_ALTERNATIVE_DESTINATIONS,
    MAX_ALTERNATIVE_DESTINATIONS,
    TripRequest,
)
from app.prompts import (
    FINAL_ANSWER_PROMPT,
    REQUIREMENTS_PROMPT,
)
from app.date_utils import normalize_date_range
from app.providers.ranking import rank_flights
from app.providers.serpapi import SerpApiClient
from app.providers.weather import get_weather

load_dotenv()
required_variables = [
    "GROVE_API_KEY",
    "GROVE_MODEL",
    "OPENAI_BASE_URL",
    "SERPAPI_API_KEY",
]

missing_variables = [
    name
    for name in required_variables
    if not os.getenv(name)
]

if missing_variables:
    raise RuntimeError(
        "Missing environment variables: "
        + ", ".join(missing_variables)
    )


class TravelState(TypedDict, total=False):
    user_request: str
    trip: dict
    missing: list[str]
    weather: dict
    selected_destinations: list[str]
    destination_decision: str
    flights: list[dict]
    ranked_flights: dict
    errors: list[str]
    answer: str

llm = ChatOpenAI(
    model=os.environ["GROVE_MODEL"],
    api_key=os.environ["GROVE_API_KEY"],
    base_url=os.environ["OPENAI_BASE_URL"],
    default_headers={
        "api-key": os.environ["GROVE_API_KEY"]
    },
    temperature=0,
)

extractor = llm.with_structured_output(TripRequest)

def normalize_currency_code(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    normalized = value.strip().lower()

    aliases = {
        "eur": "EUR",
        "euro": "EUR",
        "euros": "EUR",
        "€": "EUR",
        "usd": "USD",
        "dollar": "USD",
        "dollars": "USD",
        "$": "USD",
        "gbp": "GBP",
        "pound": "GBP",
        "pounds": "GBP",
        "sterling": "GBP",
        "£": "GBP",
        "ils": "ILS",
        "nis": "ILS",
        "shekel": "ILS",
        "shekels": "ILS",
        "₪": "ILS",
    }

    if normalized in aliases:
        return aliases[normalized]

    if len(normalized) == 3 and normalized.isalpha():
        return normalized.upper()

    return None

def extract_requirements(
    state: TravelState,
) -> TravelState:
    result = extractor.invoke(
        [
            SystemMessage(
                content=REQUIREMENTS_PROMPT
            ),
            HumanMessage(
                content=state["user_request"]
            ),
        ]
    )

    trip = result.model_dump(mode="json")

    alternatives = trip.get(
        "alternative_destinations",
        [],
    )

    trip["alternative_destinations"] = alternatives[
        :MAX_ALTERNATIVE_DESTINATIONS
    ]

    departure_date, return_date = normalize_date_range(
        departure_text=trip.get("departure_date"),
        return_text=trip.get("return_date"),
        fallback_text=state["user_request"],
    )

    trip["departure_date"] = (
        departure_date.isoformat()
        if departure_date
        else None
    )
    trip["return_date"] = (
        return_date.isoformat()
        if return_date
        else None
    )
    trip["currency"] = normalize_currency_code(
        trip.get("currency")
    )

    return {
        "trip": trip,
        "errors": [],
    }

def validate_request(
    state: TravelState,
) -> TravelState:
    trip = state["trip"]
    missing = []

    required_fields = {
        "origin": "origin",
        "destination": "destination",
        "departure_date": "departure date",
        "return_date": "return date",
        "travelers": "number of travelers",
        "currency": "currency",
        "max_flight_price": "maximum flight price",
    }

    for field, description in required_fields.items():
        if trip.get(field) is None:
            missing.append(description)

    return {
        "missing": missing,
    }

def route_after_validation(
    state: TravelState,
) -> str:
    if state.get("missing"):
        return "finish"

    return "check_weather"

def check_weather(
    state: TravelState,
) -> TravelState:
    trip = state["trip"]
    requested_destination = trip["destination"]

    destinations = [
        requested_destination
    ]

    alternatives = (
        trip.get("alternative_destinations")
        or DEFAULT_ALTERNATIVE_DESTINATIONS
    )

    alternatives = alternatives[
        :MAX_ALTERNATIVE_DESTINATIONS
    ]

    existing_destinations = {
        destination.lower()
        for destination in destinations
    }

    for alternative in alternatives:
        if alternative.lower() not in existing_destinations:
            destinations.append(alternative)
            existing_destinations.add(
                alternative.lower()
            )

    weather_results = {}
    errors = state.get("errors", [])

    for destination in destinations:
        try:
            weather_results[destination] = get_weather(
                city=destination,
                departure_date=trip["departure_date"],
                return_date=trip["return_date"],
            )
        except Exception as error:
            errors.append(
                f"Weather lookup failed for {destination}: {error}"
            )

    return {
        "weather": weather_results,
        "errors": errors,
    }

def choose_destinations(
    state: TravelState,
) -> TravelState:
    trip = state["trip"]
    weather = state.get("weather", {})

    requested_destination = trip["destination"]
    requested_weather = weather.get(
        requested_destination
    )

    if (
        requested_weather
        and requested_weather.get("good") is True
    ):
        return {
            "selected_destinations": [
                requested_destination
            ],
            "destination_decision": (
                "The requested destination has acceptable weather."
            ),
        }

    good_alternatives = [
        destination
        for destination, result in weather.items()
        if destination != requested_destination
        and result.get("good") is True
    ]

    good_alternatives = good_alternatives[
        :MAX_ALTERNATIVE_DESTINATIONS
    ]

    if good_alternatives:
        return {
            "selected_destinations": good_alternatives,
            "destination_decision": (
                "The requested destination did not have "
                "acceptable weather, so alternatives were selected."
            ),
        }

    return {
        "selected_destinations": [
            requested_destination
        ],
        "destination_decision": (
            "No alternative with acceptable weather was found. "
            "The requested destination will be searched."
        ),
    }

def search_flights(
    state: TravelState,
) -> TravelState:
    trip = state["trip"]
    client = SerpApiClient()

    all_flights = []
    errors = state.get("errors", [])

    for destination in state.get(
        "selected_destinations",
        [],
    ):
        try:
            flights = client.search_flights(
                origin=trip["origin"],
                destination=destination,
                departure_date=trip["departure_date"],
                return_date=trip["return_date"],
                travelers=trip["travelers"],
                currency=trip["currency"],
                maximum_price=trip["max_flight_price"],
            )

            all_flights.extend(flights)

        except Exception as error:
            errors.append(
                f"Flight lookup failed for {destination}: {error}"
            )

    if not all_flights:
        errors.append(
            "No round-trip flights collected after SerpApi parsing."
        )

    return {
        "flights": all_flights,
        "errors": errors,
    }

def rank_results(
    state: TravelState,
) -> TravelState:
    trip = state["trip"]

    ranked = rank_flights(
        flights=state.get("flights", []),
        maximum_price=trip["max_flight_price"],
    )

    return {
        "ranked_flights": ranked,
    }

def generate_answer(
    state: TravelState,
) -> TravelState:
    trip = state["trip"]
    ranked = state.get("ranked_flights", {})

    prompt = f"""
{FINAL_ANSWER_PROMPT}

Trip request:
{json.dumps(trip, indent=2)}

Weather results:
{json.dumps(state.get("weather", {}), indent=2)}

Destination decision:
{state.get("destination_decision", "")}

Flights within budget:
{json.dumps(ranked.get("matching", []), indent=2)}

Flights over budget:
{json.dumps(ranked.get("over_budget", []), indent=2)}

Errors:
{json.dumps(state.get("errors", []), indent=2)}
"""

    response = llm.invoke(prompt)

    return {
        "answer": response.content,
    }

builder = StateGraph(TravelState)

builder.add_node(
    "extract_requirements",
    extract_requirements,
)

builder.add_node(
    "validate_request",
    validate_request,
)

builder.add_node(
    "check_weather",
    check_weather,
)

builder.add_node(
    "choose_destinations",
    choose_destinations,
)

builder.add_node(
    "search_flights",
    search_flights,
)

builder.add_node(
    "rank_results",
    rank_results,
)

builder.add_node(
    "generate_answer",
    generate_answer,
)

builder.add_edge(
    START,
    "extract_requirements",
)

builder.add_edge(
    "extract_requirements",
    "validate_request",
)

builder.add_conditional_edges(
    "validate_request",
    route_after_validation,
    {
        "finish": END,
        "check_weather": "check_weather",
    },
)

builder.add_edge(
    "check_weather",
    "choose_destinations",
)

builder.add_edge(
    "choose_destinations",
    "search_flights",
)

builder.add_edge(
    "search_flights",
    "rank_results",
)

builder.add_edge(
    "rank_results",
    "generate_answer",
)

builder.add_edge(
    "generate_answer",
    END,
)

app = builder.compile()
