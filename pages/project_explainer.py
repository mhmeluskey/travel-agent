import streamlit as st

st.set_page_config(
    page_title="How TripWise Works",
    page_icon="📚",
    layout="wide",
)

st.title("How TripWise Works")
st.caption(
    "A presentation-friendly guide to the application's files, data flow, and AI steps."
)

st.info(
    "The app has two kinds of logic: AI logic, which understands requests and writes recommendations, "
    "and regular Python logic, which validates data, calls services, and ranks results."
)

st.header("The complete flow")

flow_steps = [
    ("1. User input", "The user enters a trip request in the main form or answers questions on the Friendly Travel Agent page."),
    ("2. Request text", "The UI converts those answers into one clear natural-language request."),
    ("3. AI extraction", "The language model extracts origin, destination, dates, travelers, currency, budget, and alternatives into TripRequest."),
    ("4. Normalization", "Dates become ISO values such as 2026-10-10, and currency aliases become codes such as USD or EUR."),
    ("5. Validation", "The graph checks that all required trip fields are present before external services are called."),
    ("6. Weather lookup", "Open-Meteo is used to check the requested destination and possible alternatives."),
    ("7. Destination decision", "The graph keeps the requested destination when weather is acceptable; otherwise it chooses good alternatives."),
    ("8. Flight search", "SerpApi searches for round-trip flights for each selected destination."),
    ("9. Ranking", "Flights are separated by budget and ordered by price and number of stops."),
    ("10. Final answer", "The language model turns the structured weather, destination, flight, and error data into a recommendation."),
]

for title, description in flow_steps:
    with st.container(border=True):
        st.subheader(title)
        st.write(description)

st.header("The LangGraph workflow")
st.code(
    "START\n"
    "  -> handle_small_talk\n"
    "      -> END                    if the message is casual conversation\n"
    "      -> extract_requirements    if it contains travel intent\n"
    "  -> validate_request\n"
    "      -> END                    if required information is missing\n"
    "      -> check_weather\n"
    "  -> choose_destinations\n"
    "  -> search_flights\n"
    "  -> rank_results\n"
    "  -> generate_answer\n"
    "  -> END",
    language="text",
)

st.header("Graph state")
st.write(
    "TravelState is the dictionary passed between graph nodes. Each node reads the values it needs "
    "and returns new values for the next node."
)

state_rows = [
    ("user_request", "The original natural-language request."),
    ("trip", "Structured trip fields extracted from the request."),
    ("missing", "Required fields that were not supplied."),
    ("weather", "Weather results keyed by destination."),
    ("selected_destinations", "Destinations that will be searched for flights."),
    ("destination_decision", "Explanation of why a destination was selected."),
    ("flights", "Raw round-trip flight records."),
    ("ranked_flights", "Flights split into matching and over_budget results."),
    ("errors", "Recoverable weather or flight lookup errors."),
    ("answer", "The final AI-generated recommendation."),
]

st.table({"State key": [row[0] for row in state_rows], "Purpose": [row[1] for row in state_rows]})

st.header("Explain each graph node")

node_explanations = {
    "handle_small_talk": (
        "Looks for travel-related keywords. If none are present, it asks a friendly follow-up question "
        "with the language model and ends the workflow."
    ),
    "extract_requirements": (
        "Sends the request to ChatOpenAI with REQUIREMENTS_PROMPT. Structured output maps the response "
        "to the TripRequest Pydantic model. It then normalizes dates, currency, and alternative limits."
    ),
    "validate_request": (
        "Checks origin, destination, departure date, return date, travelers, currency, and "
        "max_flight_price. Missing values are collected rather than causing an immediate crash."
    ),
    "check_weather": (
        "Checks the requested destination plus explicit alternatives. If no alternatives were provided, "
        "it uses the default list from models.py. Provider failures are recorded in errors."
    ),
    "choose_destinations": (
        "Keeps the requested destination when its weather is good. If not, it selects acceptable alternatives. "
        "If no alternative is suitable, it falls back to the requested destination."
    ),
    "search_flights": (
        "Creates a SerpApiClient and searches each selected destination. It passes dates, travelers, currency, "
        "and maximum price to the provider. Errors are collected so the workflow can still produce an answer."
    ),
    "rank_results": (
        "Keeps only complete round trips, separates flights within and above the budget, and sorts by price "
        "followed by stops."
    ),
    "generate_answer": (
        "Builds a prompt containing the trip, weather, decision, ranked flights, and errors. ChatOpenAI then "
        "writes the user-facing recommendation and notes that nothing was booked."
    ),
}

for node, explanation in node_explanations.items():
    with st.expander(node):
        st.write(explanation)

st.header("What each file does")

file_explanations = {
    "ui.py": "The main Streamlit search page. It collects all trip fields in one form, builds user_request, invokes the graph, and displays the answer, weather, and flights.",
    "pages/friendly_agent.py": "The guided page. It asks one question at a time, stores answers in st.session_state, validates dates and budget, then sends a completed request to the graph.",
    "app/graph.py": "The central orchestration layer. It defines TravelState, configures ChatOpenAI, implements graph nodes, and connects them with StateGraph edges.",
    "app/models.py": "Defines TripRequest and the maximum/default alternative-destination settings.",
    "app/date_utils.py": "Parses natural-language dates, fixes month typos, extracts date ranges, converts dates to ISO format, and rejects reversed ranges.",
    "app/prompts.py": "Stores the instructions used for requirement extraction and final answer generation.",
    "app/providers/locations.py": "AirportResolver converts user input into an IATA airport code. It accepts codes, known city overrides, and airport database matches.",
    "app/providers/weather.py": "Calls Open-Meteo geocoding and forecast endpoints, then decides whether weather meets the configured rain and temperature rules.",
    "app/providers/serpapi.py": "Calls SerpApi Google Flights, resolves airport codes, pairs outbound and return itineraries, and produces normalized flight dictionaries.",
    "app/providers/ranking.py": "Filters out incomplete itineraries and ranks complete flights by budget, price, and stops.",
    "app/main.py": "Command-line entry point that repeatedly accepts a trip request and asks for missing information.",
    "app/api.py": "FastAPI entry point with a health check and a POST /search endpoint.",
}

for path, explanation in file_explanations.items():
    with st.expander(path):
        st.write(explanation)

st.header("How AirportResolver works")
st.write(
    "AirportResolver is the location adapter between human input and flight APIs. "
    "Flight providers need IATA codes, while users may type a city or a metro code."
)

st.code(
    "Input: 'Paris'\n"
    "  -> clean whitespace and parenthetical text\n"
    "  -> check whether input is a three-letter code\n"
    "  -> check metro-code mappings such as PAR -> CDG\n"
    "  -> check CITY_CODE_OVERRIDES\n"
    "  -> search airportsdata by city, airport name, or country\n"
    "  -> return one IATA code\n"
    "  -> raise ValueError if nothing matches",
    language="text",
)

st.write(
    "The resolver works for many cities because it loads the full airportsdata IATA database. "
    "The explicit overrides handle locations where a predictable airport should be preferred, such as Paris, "
    "London, New York, and Rome."
)

st.header("Where the AI is used")
ai_rows = [
    ("Requirement extraction", "ChatOpenAI converts natural language into TripRequest fields."),
    ("Small talk", "ChatOpenAI responds to non-travel messages."),
    ("Final answer", "ChatOpenAI explains weather, destination choices, flights, errors, and booking limitations."),
]
st.table({"AI step": [row[0] for row in ai_rows], "What it does": [row[1] for row in ai_rows]})

st.header("Where regular code is used")
st.write(
    "The application does not ask the AI to perform every operation. Regular Python code handles the parts "
    "that need predictable behavior: required-field validation, date normalization, airport resolution, HTTP "
    "requests, round-trip parsing, weather thresholds, budget filtering, and sorting."
)

st.header("Example walkthrough")
with st.expander("Example: a user asks for a trip"):
    st.markdown(
        """
**User input**

> Find a round-trip flight from Tel Aviv to Paris from 2026-10-10 to 2026-10-17 for 2 travelers. The maximum flight price is 500 EUR per traveler.

**After extraction**

```text
origin: Tel Aviv
 destination: Paris
 departure_date: 2026-10-10
 return_date: 2026-10-17
 travelers: 2
 currency: EUR
 max_flight_price: 500.0
```

**After location resolution**

```text
Tel Aviv -> TLV
Paris -> CDG
```

**After ranking**

Flights are divided into options at or below 500 EUR and options above 500 EUR.

**Final response**

The AI explains the weather decision and presents the best available flight options. The system does not book a flight.
"""
    )

st.header("Configuration and run commands")
st.write(
    "The graph requires API_KEY, MODEL, OPENAI_BASE_URL, and SERPAPI_API_KEY in .env. "
    "Install dependencies with pip install -r requirements.txt, then run the main interface with streamlit run ui.py."
)
st.code(
    "pip install -r requirements.txt\n"
    "streamlit run ui.py",
    language="powershell",
)

st.success(
    "Presentation summary: the UI gathers information, the AI structures it, regular code validates and enriches it, "
    "external providers supply weather and flights, and the AI explains the final result."
)
