import datetime
import difflib
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.entry import Entry


ALLOWED_ACTIVITIES: set[str] = set()
PEOPLE: set[str] = set()


def register(activities: set[str]):
    global ALLOWED_ACTIVITIES, PEOPLE
    ALLOWED_ACTIVITIES = activities
    PEOPLE = {a for a in activities if a[0].isupper()}


class EntryCondition(ABC):
    def __and__(self, other: "EntryCondition") -> "And":
        return (
            And(self, other) if not isinstance(self, And) else And(*self.conds, other)
        )

    def __or__(self, other: "EntryCondition") -> "Or":
        return Or(self, other) if not isinstance(self, Or) else Or(*self.conds, other)

    def __invert__(self) -> "Not":
        return Not(self)

    @abstractmethod
    def __repr__(self) -> str: ...

    @abstractmethod
    def __str__(self) -> str: ...

    @abstractmethod
    def check(self, entry: "Entry") -> bool: ...


FMTS = ["%d.%m.%Y", "%d %b %Y", "%d %B %Y"]


class DateInterval(EntryCondition):
    @staticmethod
    def _parse_date(date: str) -> datetime.datetime:
        for fmt in FMTS:
            try:
                return datetime.datetime.strptime(date, fmt)
            except ValueError:
                pass
        raise ValueError(f"Could not parse date: {date}")

    def __init__(self, start: str = "", end: str = ""):
        assert start or end, "At least one of the bounds must be given"
        self.start_dt = self._parse_date(start) if start else None
        self.end_dt = self._parse_date(end) if end else None

    def check(self, entry: "Entry") -> bool:
        after_check = self.start_dt is None or entry.full_date >= self.start_dt
        before_check = self.end_dt is None or entry.full_date < self.end_dt
        return after_check and before_check

    def __repr__(self) -> str:
        after_str = f"{self.start_dt:%d.%m.%Y}" if self.start_dt else "..."
        before_str = f"{self.end_dt:%d.%m.%Y}" if self.end_dt else "..."
        return f"DateInterval({after_str}, {before_str})"

    def __str__(self) -> str:
        after_str = f"{self.start_dt:%d.%m.%Y}" if self.start_dt else ""
        before_str = f"{self.end_dt:%d.%m.%Y}" if self.end_dt else ""
        return f"({after_str}...{before_str})"


class MoodInterval(EntryCondition):
    def __init__(self, low: float = float("-inf"), high: float = float("inf")):
        self.low = low
        self.high = high

    def check(self, entry: "Entry") -> bool:
        return self.low <= entry.mood < self.high

    def __repr__(self) -> str:
        return f"MoodInterval({self.low}, {self.high})"

    def __str__(self) -> str:
        return f"({self.low:.2f} <= mood < {self.high:.2f})"


class NoteContains(EntryCondition):
    def __init__(self, word: str):
        self.word = word

    def check(self, entry: "Entry") -> bool:
        return self.word in entry.note.lower()

    def __repr__(self) -> str:
        return f"NoteContains({self.word})"

    def __str__(self) -> str:
        return f"(note with {self.word!r})"


class Has(EntryCondition):
    @staticmethod
    def _raise():
        if not ALLOWED_ACTIVITIES:
            raise ValueError(
                "No activities are registered. Run `register(activities)` first."
            )

    def __init__(self, activity: str):
        self._raise()
        if ALLOWED_ACTIVITIES and activity not in ALLOWED_ACTIVITIES:
            maybe_this = difflib.get_close_matches(activity, ALLOWED_ACTIVITIES, n=1)
            maybe_this = f" Did you mean {maybe_this[0]!r}?" if maybe_this else ""
            raise ValueError(f"Unknown activity: {activity!r}.{maybe_this}")
        self.activity = activity

    def check(self, entry: "Entry") -> bool:
        return self.activity in entry.activities

    def __repr__(self) -> str:
        return f"Has({self.activity})"

    def __str__(self) -> str:
        return self.activity

    @classmethod
    def people(cls) -> "HasPeople":
        cls._raise()
        return HasPeople(PEOPLE)


class HasPeople(EntryCondition):
    def __init__(self, people: set[str]):
        self._people = people

    def check(self, entry: "Entry") -> bool:
        return bool(entry.activities & self._people)

    def __repr__(self) -> str:
        return "Has(PEOPLE)"

    def __str__(self) -> str:
        return "PEOPLE"


class Not(EntryCondition):
    def __init__(self, cond: EntryCondition):
        self.cond = cond

    def check(self, entry: "Entry") -> bool:
        return not self.cond.check(entry)

    def __repr__(self) -> str:
        return f"not {self.cond!r}"

    def __str__(self) -> str:
        return f"!{self.cond}"


class Or(EntryCondition):
    def __init__(self, *conds: EntryCondition):
        self.conds = conds

    def check(self, entry: "Entry") -> bool:
        return any(cond.check(entry) for cond in self.conds)

    def __repr__(self) -> str:
        return f"Or({', '.join(map(repr, self.conds))})"

    def __str__(self) -> str:
        return f"({' | '.join(map(str, self.conds))})"


class And(EntryCondition):
    def __init__(self, *conds: EntryCondition):
        self.conds = conds

    def check(self, entry: "Entry") -> bool:
        return all(cond.check(entry) for cond in self.conds)

    def __repr__(self) -> str:
        return f"And({', '.join(map(repr, self.conds))})"

    def __str__(self) -> str:
        return f"{' & '.join(map(str, self.conds))}"


A = Has
