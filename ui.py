import streamlit as st

from app.graph import app as travel_agent

st.set_page_config(
    page_title="TripWise",
    page_icon="✈️",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background: #f7f9fc;
    }

    .hero {
        background: linear-gradient(135deg, #172554, #2563eb);
        padding: 42px;
        border-radius: 20px;
        color: white;
        margin-bottom: 25px;
    }

    .hero h1 {
        font-size: 42px;
        margin-bottom: 8px;
    }

    .hero p {
        font-size: 18px;
        color: #dbeafe;
    }

    .card {
        background: white;
        padding: 20px;
        border-radius: 16px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04);
        margin-bottom: 16px;
    }

    .price {
        color: #2563eb;
        font-size: 25px;
        font-weight: bold;
    }

    .good {
        color: #15803d;
        font-weight: bold;
    }

    .bad {
        color: #b91c1c;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <h1>✈️ TripWise</h1>
        <p>Find affordable flights to destinations with great weather.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("Plan your trip")

with st.form("travel_search_form"):
    col1, col2 = st.columns(2)

    with col1:
        origin = st.text_input(
            "From",
            placeholder="Tel Aviv or TLV",
        )

        destination = st.text_input(
            "Destination",
            placeholder="Paris or PAR",
        )

        departure_date = st.date_input(
            "Departure date"
        )

    with col2:
        travelers = st.number_input(
            "Travelers",
            min_value=1,
            max_value=9,
            value=1,
            step=1,
        )

        maximum_price = st.number_input(
            "Maximum flight price per traveler",
            min_value=1.0,
            value=500.0,
            step=25.0,
        )

        currency = st.selectbox(
            "Currency",
            ["USD", "EUR", "GBP", "ILS"],
        )

    return_date = st.date_input(
        "Return date"
    )

    alternatives = st.text_input(
        "Alternative destinations",
        placeholder="Lisbon, Barcelona, Rome, Athens, Madrid",
        help="Maximum of five alternatives.",
    )

    submitted = st.form_submit_button(
        "Search flights",
        use_container_width=True,
        type="primary",
    )

if submitted:
    if not origin or not destination:
        st.error("Please enter both an origin and destination.")

    elif return_date < departure_date:
        st.error("Return date cannot be before the departure date.")

    else:
        alternative_list = [
            item.strip()
            for item in alternatives.split(",")
            if item.strip()
        ][:5]

        alternatives_text = ", ".join(alternative_list)

        request = f"""
        Find a round-trip flight from {origin} to {destination}
        from {departure_date.isoformat()} to {return_date.isoformat()}
        for {travelers} traveler(s).

        The maximum flight price is {maximum_price}
        {currency} per traveler.

        If the weather in {destination} is not good, check these
        alternative destinations: {alternatives_text}.
        """

        with st.spinner(
            "Checking weather and searching for flights..."
        ):
            try:
                result = travel_agent.invoke(
                    {
                        "user_request": request
                    }
                )

                st.session_state["travel_result"] = result

            except Exception as error:
                st.error(
                    f"Something went wrong: {error}"
                )

result = st.session_state.get("travel_result")

if result:
    st.divider()

    missing = result.get("missing", [])

    if missing:
        st.warning(
            "Missing information: "
            + ", ".join(missing)
        )
        st.stop()

    st.subheader("Recommendation")

    answer = result.get("answer")

    if answer:
        st.markdown(answer)

    st.subheader("Weather results")

    weather_results = result.get(
        "weather",
        {},
    )

    if not weather_results:
        st.info("No weather results were returned.")

    weather_columns = st.columns(
        min(3, max(1, len(weather_results)))
    )

    for index, (city, weather) in enumerate(
        weather_results.items()
    ):
        with weather_columns[
            index % len(weather_columns)
        ]:
            if weather.get("good") is True:
                status = "Good weather"
                status_class = "good"
            elif weather.get("good") is False:
                status = "Poor weather"
                status_class = "bad"
            else:
                status = "Unavailable"
                status_class = "bad"

            average_high = weather.get(
                "average_high_c",
                "N/A",
            )

            rainy_days = weather.get(
                "rainy_days",
                "N/A",
            )

            st.markdown(
                f"""
                <div class="card">
                    <h3>{city}</h3>
                    <p class="{status_class}">{status}</p>
                    <p>Average high: {average_high}°C</p>
                    <p>Rainy days: {rainy_days}</p>
                    <p>{weather.get("reason", "")}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.subheader("Selected destinations")

    selected_destinations = result.get(
        "selected_destinations",
        [],
    )

    if selected_destinations:
        st.write(
            " • ".join(selected_destinations)
        )

    st.subheader("Flight options")

    ranked_flights = result.get(
        "ranked_flights",
        {},
    )

    matching_flights = ranked_flights.get(
        "matching",
        [],
    )

    if not matching_flights:
        st.warning(
            "No flights were found within your budget."
        )
    else:
        for flight in matching_flights:
            airlines = ", ".join(
                flight.get("airlines", [])
            )

            price = flight.get(
                "price",
                "N/A",
            )

            currency_code = flight.get(
                "currency",
                currency,
            )

            destination_name = flight.get(
                "destination",
                "Unknown",
            )

            stops = flight.get(
                "stops",
                0,
            )

            duration = flight.get(
                "duration",
                "N/A",
            )

            booking_url = flight.get(
                "booking_url"
            )

            st.markdown(
                f"""
                <div class="card">
                    <h3>
                        {flight.get("origin", origin)}
                        → {destination_name}
                    </h3>
                    <p>{airlines}</p>
                    <p>{stops} stop(s) · Duration: {duration}</p>
                    <p class="price">
                        {price} {currency_code}
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if booking_url:
                st.link_button(
                    "View flight",
                    booking_url,
                )

    errors = result.get(
        "errors",
        [],
    )

    if errors:
        with st.expander("Technical details"):
            for error in errors:
                st.write(error)
