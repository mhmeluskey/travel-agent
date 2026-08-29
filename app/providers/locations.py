import re

import airportsdata

CITY_CODE_OVERRIDES = {
    "tel aviv": "TLV",
    "paris": "CDG",
    "london": "LHR",
    "new york": "JFK",
    "rome": "FCO",
    "madrid": "MAD",
    "lisbon": "LIS",
    "barcelona": "BCN",
    "athens": "ATH",
    "malta": "MLA",
}

class AirportResolver:
    def __init__(self) -> None:
        self.airports = airportsdata.load("IATA")

    def resolve(
        self,
        value: str,
        max_airports: int = 1,
    ) -> str:
        cleaned = re.sub(
            r"\s*\([^)]+\)\s*$",
            "",
            value.strip(),
        ).strip()
        uppercase_value = cleaned.upper()

        if re.fullmatch(r"[A-Z]{3}", uppercase_value):
            metro_to_airport = {
                "PAR": "CDG",
                "LON": "LHR",
                "NYC": "JFK",
                "ROM": "FCO",
            }
            normalized_code = metro_to_airport.get(
                uppercase_value,
                uppercase_value,
            )

            if normalized_code in self.airports:
                return normalized_code

        override = CITY_CODE_OVERRIDES.get(
            cleaned.lower()
        )

        if override:
            return override

        for code, airport in self.airports.items():
            city = str(airport.get("city", ""))
            name = str(airport.get("name", ""))
            country = str(airport.get("country", ""))

            searchable_text = (
                f"{city} {name} {country}"
            ).lower()

            if cleaned.lower() in searchable_text:
                return code

        raise ValueError(
            f"Could not resolve '{value}' to an airport code."
        )
