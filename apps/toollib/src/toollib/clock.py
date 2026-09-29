from datetime import UTC, datetime, timedelta


class AppClock:
    """The single source of "now" for the app.

    Runs on real time until frozen. Test mode freezes and advances it so that
    time-based rules (due dates, late fees) can be tested deterministically.
    """

    def __init__(self) -> None:
        self._frozen_at: datetime | None = None

    def now(self) -> datetime:
        return self._frozen_at or datetime.now(UTC)

    def freeze(self, at: datetime) -> None:
        if at.tzinfo is None:
            raise ValueError("clock time must be timezone-aware")
        self._frozen_at = at.astimezone(UTC)

    def advance(self, delta: timedelta) -> None:
        self._frozen_at = self.now() + delta

    def unfreeze(self) -> None:
        self._frozen_at = None
