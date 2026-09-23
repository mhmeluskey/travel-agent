import streamlit as st
from datetime import date

from app.graph import app as travel_agent

st.set_page_config(
    page_title="Friendly Travel Agent",
    page_icon="🤖",
    layout="wide",
)

st.title("Friendly Travel Agent")
st.caption("I’ll ask a few questions and help plan your trip.")

if "agent_data" not in st.session_state:
    st.session_state.agent_data = {
        "origin": "",
        "destination": "",
        "departure_date": date.today(),
        "return_date": date.today(),
        "travelers": 1,
        "currency": "USD",
        "max_flight_price": 500.0,
        "alternatives": "",
        "result": None,
        "step": 0,
    }

state = st.session_state.agent_data


def normalize_answer(value, key):
    if key == "travelers":
        return int(value)
    if key == "max_flight_price":
        return float(value)
    return value

questions = [
    ("origin", "Where are you flying from?", "text"),
    ("destination", "What destination would you like to visit?", "text"),
    ("departure_date", "When will you leave?", "date"),
    ("return_date", "When will you return?", "date"),
    ("travelers", "How many travelers are going?", "number"),
    ("currency", "Which currency should I use?", "select"),
    ("max_flight_price", "What is your maximum flight budget per traveler?", "number"),
    ("alternatives", "Optional: list alternate destinations separated by commas.", "text"),
]

if state["result"] is None:
    if state["step"] < len(questions):
        key, prompt, field_type = questions[state["step"]]

        st.chat_message("assistant").write(f"{prompt}")

        with st.form("agent_question_form", clear_on_submit=True):
            if field_type == "text":
                value = st.text_input("Answer", key=f"agent_{key}")
            elif field_type == "date":
                value = st.date_input("Answer", key=f"agent_{key}")
            elif field_type == "number":
                value = st.number_input(
                    "Answer",
                    min_value=1 if key == "travelers" else 1.0,
                    value=state.get(key, 1 if key == "travelers" else 500.0),
                    step=1 if key == "travelers" else 25.0,
                    key=f"agent_{key}",
                )
            else:
                value = st.selectbox(
                    "Answer",
                    ["USD", "EUR", "GBP", "ILS"],
                    index=["USD", "EUR", "GBP", "ILS"].index(state.get(key, "USD")),
                    key=f"agent_{key}",
                )

            submitted = st.form_submit_button("Send")

        if submitted:
            if field_type == "text" and not value.strip():
                st.warning("Please provide an answer before continuing.")
            elif key == "return_date" and value < state["departure_date"]:
                st.warning("Return date must be after the departure date.")
            elif key == "max_flight_price" and (value is None or float(value) <= 0):
                st.warning("Please enter a maximum flight price greater than zero.")
            else:
                state[key] = normalize_answer(value, key)
                state["step"] += 1
                st.rerun()

    else:
        st.chat_message("assistant").write(
            "Thanks! I’ve got everything I need. I’m checking the weather and flight options now."
        )

        alternatives_text = state["alternatives"]
        if isinstance(alternatives_text, str):
            alternatives_text = ", ".join(
                item.strip()
                for item in alternatives_text.split(",")
                if item.strip()
            )

        request = f"""
        Find a round-trip flight from {state['origin']} to {state['destination']}
        from {state['departure_date'].isoformat()} to {state['return_date'].isoformat()}
        for {state['travelers']} traveler(s).

        The maximum flight price is {float(state['max_flight_price'])} {state['currency']} per traveler.

        If the weather in {state['destination']} is not good, check these
        alternative destinations: {alternatives_text}.
        """

        with st.spinner("Checking weather and flights..."):
            state["result"] = travel_agent.invoke({"user_request": request})

        st.session_state.agent_data = state

if state["result"] is not None:
    result = state["result"]
    st.subheader("Trip Recommendation")

    missing = result.get("missing", [])
    if missing:
        st.warning("Missing information: " + ", ".join(missing))
        st.stop()

    answer = result.get("answer")
    if answer:
        st.markdown(answer)

    if result.get("weather"):
        st.subheader("Weather")
        weather = result.get("weather", {})
        for city, details in weather.items():
            status = "Good weather" if details.get("good") is True else "Weather check"
            st.write(f"**{city}:** {status}")

    if result.get("ranked_flights"):
        ranked = result.get("ranked_flights", {})
        st.subheader("Flights")
        st.write(f"Matching flights: {len(ranked.get('matching', []))}")
        st.write(f"Over budget flights: {len(ranked.get('over_budget', []))}")

    if st.button("Start a new trip"):
        st.session_state.agent_data = {
            "origin": "",
            "destination": "",
            "departure_date": date.today(),
            "return_date": date.today(),
            "travelers": 1,
            "currency": "USD",
            "max_flight_price": 500.0,
            "alternatives": "",
            "result": None,
            "step": 0,
        }
        st.rerun()
