import os

import httpx
from dotenv import load_dotenv

from app.providers.locations import AirportResolver

load_dotenv()


class SerpApiClient:
    def __init__(self) -> None:
        self.api_key = os.environ["SERPAPI_API_KEY"]

        self.base_url = os.getenv(
            "SERPAPI_BASE_URL",
            "https://serpapi.com/search",
        )

        self.no_cache = os.getenv(
            "SERPAPI_NO_CACHE",
            "false",
        )

        self.deep_search = os.getenv(
            "SERPAPI_DEEP_SEARCH",
            "false",
        )

        self.airports = AirportResolver()

    def _request(self, params: dict) -> dict:
        response = httpx.get(
            self.base_url,
            params=params,
            timeout=60,
        )

        if response.status_code == 429:
            raise RuntimeError(
                "SerpApi quota or rate limit reached."
            )

        response.raise_for_status()
        data = response.json()

        if data.get("error"):
            raise RuntimeError(data["error"])

        return data

    @staticmethod
    def _extract_booking_url(
        result: dict,
    ) -> str | None:
        booking_options = result.get(
            "booking_options",
            [],
        )

        if booking_options:
            return booking_options[0].get("link")

        return None

    @staticmethod
    def _build_leg(
        segments: list[dict],
    ) -> dict | None:
        if not segments:
            return None

        first_segment = segments[0]
        last_segment = segments[-1]

        return {
            "from_airport": first_segment.get(
                "departure_airport",
                {},
            ).get("id"),
            "to_airport": last_segment.get(
                "arrival_airport",
                {},
            ).get("id"),
            "departure_time": first_segment.get(
                "departure_airport",
                {},
            ).get("time"),
            "arrival_time": last_segment.get(
                "arrival_airport",
                {},
            ).get("time"),
            "stops": max(0, len(segments) - 1),
            "duration": sum(
                int(segment.get("duration", 0) or 0)
                for segment in segments
            ),
        }

    def _search_return_options(
        self,
        departure_token: str,
        departure_id: str,
        arrival_id: str,
        outbound_date: str,
        return_date: str,
        travelers: int,
        currency: str,
        maximum_price: float,
    ) -> list[dict]:
        data = self._request(
            {
                "engine": "google_flights",
                "api_key": self.api_key,
                "departure_token": departure_token,
                "departure_id": departure_id,
                "arrival_id": arrival_id,
                "type": "1",
                "outbound_date": outbound_date,
                "return_date": return_date,
                "adults": travelers,
                "currency": currency,
                "max_price": int(maximum_price),
                "sort_by": "2",
                "output": "json",
                "no_cache": self.no_cache,
                "deep_search": self.deep_search,
            }
        )

        return (
            data.get("best_flights", [])
            + data.get("other_flights", [])
        )

    def _build_round_trip(
        self,
        *,
        origin: str,
        destination: str,
        origin_code: str,
        destination_code: str,
        currency: str,
        outbound_segments: list[dict],
        return_segments: list[dict],
        outbound_result: dict,
        return_result: dict | None = None,
    ) -> dict:
        outbound_leg = self._build_leg(
            outbound_segments
        )
        return_leg = self._build_leg(
            return_segments
        )

        airlines = sorted(
            {
                segment.get("airline")
                for segment in outbound_segments + return_segments
                if segment.get("airline")
            }
        )

        price_result = return_result or outbound_result
        price = price_result.get("price")
        if price is not None:
            price = float(price)

        duration = price_result.get("total_duration")
        if duration is None:
            duration = (
                (outbound_leg or {}).get("duration", 0)
                + (return_leg or {}).get("duration", 0)
            )

        return {
            "origin": origin,
            "destination": destination,
            "origin_code": origin_code,
            "destination_code": destination_code,
            "airlines": airlines,
            "price": price,
            "currency": currency,
            "stops": (
                (outbound_leg or {}).get("stops", 0)
                + (return_leg or {}).get("stops", 0)
            ),
            "duration": duration,
            "outbound_leg": outbound_leg,
            "return_leg": return_leg,
            "booking_url": self._extract_booking_url(
                return_result or {}
            )
            or self._extract_booking_url(outbound_result),
            "provider": "SerpApi Google Flights",
        }

    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
        travelers: int,
        currency: str,
        maximum_price: float,
    ) -> list[dict]:
        origin_code = self.airports.resolve(origin)
        destination_code = self.airports.resolve(destination)

        data = self._request(
            {
                "engine": "google_flights",
                "api_key": self.api_key,
                "departure_id": origin_code,
                "arrival_id": destination_code,
                "type": "1",
                "outbound_date": departure_date,
                "return_date": return_date,
                "adults": travelers,
                "currency": currency,
                "max_price": int(maximum_price),
                "sort_by": "2",
                "output": "json",
                "no_cache": self.no_cache,
                "deep_search": self.deep_search,
            }
        )

        results = (
            data.get("best_flights", [])
            + data.get("other_flights", [])
        )

        flights = []
        discarded_without_return = 0
        followup_errors = 0

        for result in results:
            outbound_segments = result.get("flights", [])
            return_segments = result.get("return_flights", [])

            if return_segments:
                flights.append(
                    self._build_round_trip(
                        origin=origin,
                        destination=destination,
                        origin_code=origin_code,
                        destination_code=destination_code,
                        currency=currency,
                        outbound_segments=outbound_segments,
                        return_segments=return_segments,
                        outbound_result=result,
                    )
                )
                continue

            departure_token = result.get(
                "departure_token"
            )
            if not departure_token:
                discarded_without_return += 1
                continue

            try:
                return_options = self._search_return_options(
                    departure_token=departure_token,
                    departure_id=origin_code,
                    arrival_id=destination_code,
                    outbound_date=departure_date,
                    return_date=return_date,
                    travelers=travelers,
                    currency=currency,
                    maximum_price=maximum_price,
                )
            except Exception:
                followup_errors += 1
                discarded_without_return += 1
                continue

            paired = False
            for return_result in return_options[:3]:
                return_leg_segments = return_result.get(
                    "flights",
                    [],
                )
                if not return_leg_segments:
                    continue

                flights.append(
                    self._build_round_trip(
                        origin=origin,
                        destination=destination,
                        origin_code=origin_code,
                        destination_code=destination_code,
                        currency=currency,
                        outbound_segments=outbound_segments,
                        return_segments=return_leg_segments,
                        outbound_result=result,
                        return_result=return_result,
                    )
                )
                paired = True

            if not paired:
                discarded_without_return += 1

        if not flights:
            raise RuntimeError(
                "No round-trip itineraries found. "
                f"Resolved origin={origin_code}, "
                f"destination={destination_code}. "
                f"Initial results={len(results)}, "
                "discarded_without_return="
                f"{discarded_without_return}, "
                f"followup_errors={followup_errors}."
            )

        return flights
