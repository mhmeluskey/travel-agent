import re
from difflib import get_close_matches
from datetime import date, datetime, time
from typing import Optional

from dateparser import parse
from dateparser.search import search_dates

MONTHS = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    "jan",
    "feb",
    "mar",
    "apr",
    "jun",
    "jul",
    "aug",
    "sep",
    "sept",
    "oct",
    "nov",
    "dec",
]


def _settings(
    reference_date: date,
    date_order: str | None = None,
) -> dict:
    settings = {
        "PREFER_DATES_FROM": "future",
        "PREFER_DAY_OF_MONTH": "first",
        "RELATIVE_BASE": datetime.combine(
            reference_date,
            time.min,
        ),
        "RETURN_AS_TIMEZONE_AWARE": False,
    }

    if date_order:
        settings["DATE_ORDER"] = date_order

    return settings


def _fix_month_typos(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        token = match.group(0)

        if token.lower() in MONTHS:
            return token

        fixed = get_close_matches(
            token.lower(),
            MONTHS,
            n=1,
            cutoff=0.75,
        )

        if not fixed:
            return token

        return fixed[0].capitalize()

    return re.sub(
        r"[A-Za-z]{3,12}",
        replace,
        text,
    )


def parse_one_date(
    value: Optional[str],
    reference_date: Optional[date] = None,
) -> Optional[date]:
    if not value:
        return None

    reference_date = reference_date or date.today()
    text = _fix_month_typos(value.strip())

    for order in [None, "DMY", "MDY", "YMD"]:
        parsed = parse(
            text,
            settings=_settings(reference_date, order),
        )

        if parsed:
            return parsed.date()

    return None


def extract_dates_from_text(
    text: str,
    reference_date: Optional[date] = None,
) -> list[date]:
    if not text:
        return []

    reference_date = reference_date or date.today()
    normalized = _fix_month_typos(text)

    matches = search_dates(
        normalized,
        settings=_settings(reference_date),
    ) or []

    dates: list[date] = []

    for _, parsed_datetime in matches:
        parsed_date = parsed_datetime.date()

        if parsed_date not in dates:
            dates.append(parsed_date)

    return dates


def normalize_date_range(
    departure_text: Optional[str],
    return_text: Optional[str],
    fallback_text: str = "",
    reference_date: Optional[date] = None,
) -> tuple[Optional[date], Optional[date]]:
    reference_date = reference_date or date.today()

    departure_date = parse_one_date(
        departure_text,
        reference_date,
    )

    return_date = parse_one_date(
        return_text,
        reference_date,
    )

    if departure_date is None or return_date is None:
        extracted_dates = extract_dates_from_text(
            fallback_text,
            reference_date,
        )

        if departure_date is None and len(extracted_dates) >= 1:
            departure_date = extracted_dates[0]

        if return_date is None and len(extracted_dates) >= 2:
            return_date = extracted_dates[1]

    if departure_date and return_date and return_date < departure_date:
        raise ValueError(
            "The return date cannot be before the departure date."
        )

    return departure_date, return_date
