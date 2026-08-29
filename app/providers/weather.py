import os
from datetime import date

import httpx

RAIN_WEATHER_CODES = {
    51, 53, 55,
    56, 57,
    61, 63, 65,
    66, 67,
    80, 81, 82,
    95, 96, 99,
}

def geocode_city(city: str) -> dict:
    response = httpx.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={
            "name": city,
            "count": 1,
            "language": "en",
            "format": "json",
        },
        timeout=20,
    )

    response.raise_for_status()

    results = response.json().get("results", [])

    if not results:
        raise ValueError(
            f"Could not find coordinates for {city}"
        )

    result = results[0]

    return {
        "name": result["name"],
        "country": result.get("country", ""),
        "latitude": result["latitude"],
        "longitude": result["longitude"],
    }

def get_weather(
    city: str,
    departure_date: str,
    return_date: str,
) -> dict:
    start = date.fromisoformat(departure_date)
    end = date.fromisoformat(return_date)
    today = date.today()

    if end < start:
        raise ValueError(
            "Return date cannot be before departure date."
        )

    if start < today or (end - today).days > 16:
        return {
            "city": city,
            "available": False,
            "good": None,
            "reason": (
                "Weather forecasts are available only for "
                "dates within the forecast range."
            ),
        }

    location = geocode_city(city)

    response = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "daily": (
                "temperature_2m_max,"
                "temperature_2m_min,"
                "precipitation_probability_max,"
                "weather_code"
            ),
            "timezone": "auto",
            "start_date": departure_date,
            "end_date": return_date,
        },
        timeout=20,
    )

    response.raise_for_status()

    daily = response.json().get("daily", {})

    dates = daily.get("time", [])
    max_temperatures = daily.get(
        "temperature_2m_max",
        [],
    )
    min_temperatures = daily.get(
        "temperature_2m_min",
        [],
    )
    rain_probabilities = daily.get(
        "precipitation_probability_max",
        [],
    )
    weather_codes = daily.get(
        "weather_code",
        [],
    )

    if not dates:
        return {
            "city": city,
            "available": False,
            "good": None,
            "reason": "No weather forecast was returned.",
        }

    max_rain_probability = int(
        os.getenv(
            "WEATHER_MAX_RAIN_PROBABILITY",
            "40",
        )
    )

    min_temperature = float(
        os.getenv(
            "WEATHER_MIN_TEMPERATURE_C",
            "15",
        )
    )

    max_temperature = float(
        os.getenv(
            "WEATHER_MAX_TEMPERATURE_C",
            "32",
        )
    )

    forecast = []

    for index, forecast_date in enumerate(dates):
        rain_probability = (
            rain_probabilities[index]
            if index < len(rain_probabilities)
            and rain_probabilities[index] is not None
            else 0
        )

        weather_code = (
            weather_codes[index]
            if index < len(weather_codes)
            else None
        )

        forecast.append(
            {
                "date": forecast_date,
                "temperature_max_c": max_temperatures[index],
                "temperature_min_c": min_temperatures[index],
                "rain_probability": rain_probability,
                "weather_code": weather_code,
            }
        )

    rainy_days = sum(
        1
        for day in forecast
        if (
            day["rain_probability"] >= max_rain_probability
            or day["weather_code"] in RAIN_WEATHER_CODES
        )
    )

    average_high = sum(
        day["temperature_max_c"]
        for day in forecast
    ) / len(forecast)

    acceptable_rainy_days = max(
        1,
        len(forecast) // 3,
    )

    good_weather = (
        rainy_days <= acceptable_rainy_days
        and min_temperature <= average_high <= max_temperature
    )

    return {
        "city": city,
        "country": location["country"],
        "available": True,
        "good": good_weather,
        "average_high_c": round(average_high, 1),
        "rainy_days": rainy_days,
        "total_days": len(forecast),
        "forecast": forecast,
        "reason": (
            "Weather is acceptable."
            if good_weather
            else "Weather does not meet the configured criteria."
        ),
    }
