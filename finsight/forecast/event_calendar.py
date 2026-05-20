"""Known macro event calendar for proactive drift forecasting."""

from datetime import date

# FOMC announcement dates (last day of each meeting) for 2025–2026.
# Source: federalreserve.gov/monetarypolicy/fomccalendars.htm
FOMC_DATES: list[date] = [
    # 2025
    date(2025, 1, 29),
    date(2025, 3, 19),
    date(2025, 5, 7),
    date(2025, 6, 18),
    date(2025, 7, 30),
    date(2025, 9, 17),
    date(2025, 10, 29),
    date(2025, 12, 10),
    # 2026
    date(2026, 1, 28),
    date(2026, 3, 18),
    date(2026, 5, 6),
    date(2026, 6, 17),
    date(2026, 7, 29),
    date(2026, 9, 16),
    date(2026, 10, 28),
    date(2026, 12, 9),
]


def days_to_next_fomc(as_of: date | None = None) -> int | None:
    """
    Return days until the next FOMC announcement date.
    Returns None when no future date is in the calendar.
    """
    today = as_of or date.today()
    upcoming = [d for d in FOMC_DATES if d >= today]
    if not upcoming:
        return None
    return (min(upcoming) - today).days
