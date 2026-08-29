def rank_flights(
    flights: list[dict],
    maximum_price: float,
) -> dict:
    round_trip_flights = [
        flight
        for flight in flights
        if flight.get("outbound_leg")
        and flight.get("return_leg")
    ]

    matching = [
        flight
        for flight in round_trip_flights
        if flight.get("price") is not None
        and flight["price"] <= maximum_price
    ]

    over_budget = [
        flight
        for flight in round_trip_flights
        if flight.get("price") is not None
        and flight["price"] > maximum_price
    ]

    matching.sort(
        key=lambda flight: (
            flight["price"],
            flight.get("stops", 0),
        )
    )

    over_budget.sort(
        key=lambda flight: flight["price"]
    )

    return {
        "matching": matching[:10],
        "over_budget": over_budget[:3],
        "discarded_without_return": (
            len(flights) - len(round_trip_flights)
        ),
    }
