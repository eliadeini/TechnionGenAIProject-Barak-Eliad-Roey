"""Tests of the Scheduling Advisor. They need no API key and no internet.  Run:  python -m pytest -q app/scheduling_advisor"""
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.scheduling_advisor.calendar_tools import ScheduleDB
from app.scheduling_advisor.scheduling_advisor import SchedulingAdvisor, list_dates, slots_text
from app.scheduling_advisor.schemas import SchedulingAdvisorResult

NOW = datetime(2024, 4, 3, 15, 12)   ### Wednesday
NOW_TEXT = "2024-04-03 15:12"


### ---------- a fake model: plays a fixed list of function calls instead of calling OpenAI ----------

class FakeLLM(BaseChatModel):
    answers: list
    seen: list = []

    @property
    def _llm_type(self):
        return "fake"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(messages)
        return ChatResult(generations=[ChatGeneration(message=self.answers.pop(0))])


def fake_llm(*answers):
    return FakeLLM(answers=list(answers), seen=[])


def call(name, **args):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call_{name}"}])


@pytest.fixture
def db(tmp_path):
    db = ScheduleDB(tmp_path / "tech.db")   ### the calendar is created in the first run
    yield db
    db.engine.dispose()


### ---------- calendar (SQL) ----------

def test_calendar_has_no_monday_and_saturday(db):
    dates = pd.read_sql("SELECT DISTINCT date FROM Schedule", con=db.engine)["date"]
    assert set(pd.to_datetime(dates).dt.day_name()) == {"Sunday", "Tuesday", "Wednesday", "Thursday", "Friday"}


def search(db, *args, **kwargs):
    return db.get_next_three_dates(NOW_TEXT, *args, **kwargs)["slot"].tolist()


def test_three_slots_never_in_the_past(db):
    slots = search(db, days=["2024-04-01"], hours=["09:00"])   ### the wish is in the past
    assert len(slots) == 3 and all(s > NOW_TEXT for s in slots)


def test_wish_can_be_one_value_or_a_range(db):
    slots = search(db, days=["2024-04-07", "2024-04-13"], hours=["12:00", "17:00"])   ### next week, afternoon
    assert all("2024-04-07" <= s[:10] <= "2024-04-13" and s[11:] >= "12:00" for s in slots)


def test_range_of_hours_is_a_limit(db):
    slots = search(db, days=["2024-04-12"], hours=["12:00", "17:00"])   ### Friday afternoon has only two free slots
    assert len(slots) == 3 and all(s[11:] >= "12:00" for s in slots)


def test_every_free_slot_is_the_nearest_to_itself(db):
    free = pd.read_sql("SELECT date, time FROM Schedule WHERE position = 'Python Dev' AND available = 1 AND date > '2024-04-03'", con=db.engine)
    for date, time in free.sample(100, random_state=42).to_numpy():
        assert search(db, [date], [time])[0] == f"{date} {time}"


def test_nearest_day_comes_first_and_then_the_nearest_hour(db):
    slots = search(db, ["2024-04-08"], ["15:00"])   ### there are no Mondays
    assert {s[:10] for s in slots} == {"2024-04-09"} and slots[0] == "2024-04-09 15:00"


def test_refused_day_and_refused_hour(db):
    first = search(db, ["2024-04-04"], ["09:00"])[0]
    assert first not in search(db, ["2024-04-04"], ["09:00"], refused=[first])
    assert not any(s.startswith("2024-04-04") for s in search(db, ["2024-04-04"], ["09:00"], refused=["2024-04-04"]))


def test_nothing_is_found_after_the_end_of_the_calendar(db):
    assert search(db, ["2025-06-01"], ["10:00"]) == []
    assert search(db, ["next Friday"], ["morning"]) == []   ### not a date and not an hour


def test_slot_cannot_be_booked_twice(db):
    slot = search(db, ["2024-04-04"], ["09:00"])[0]
    assert db.book(slot) is True
    assert db.book(slot) is False


### ---------- Scheduling Advisor ----------

def advise(db, answer, booked=None):
    llm = fake_llm(answer)
    advice = SchedulingAdvisor(llm, db).propose_slots([{"speaker": "candidate", "text": "Friday at 10?", "timestamp_utc": "2024-04-03T15:12:00Z"}], booked)
    assert len(llm.seen) == 1   ### one call to the model is enough
    return advice, llm


def test_agreed_time_is_validated_by_sql(db):
    free = search(db, ["2024-04-05"], ["10:00"])[0]
    advice, _ = advise(db, call("sched", reason="", agreed=True, days=[free[:10]], hours=[free[11:]]))
    assert advice.status == "agreed" and advice.proposed_slots == [free]


def test_agreed_time_that_is_taken_gets_three_options(db):
    advice, _ = advise(db, call("sched", reason="", agreed=True, days=["2024-04-08"], hours=["15:00"]))   ### there are no Mondays
    assert advice.status == "not available" and len(advice.proposed_slots) == 3


def test_wish_that_is_not_free(db):
    free, closed = "2024-04-12", "2024-04-08"   ### there are no Mondays
    assert advise(db, call("sched", reason="", agreed=False, days=[free]))[0].status == "offer"
    assert advise(db, call("sched", reason="", agreed=False, days=[closed]))[0].status == "not available"


def test_day_without_an_hour_is_never_agreed(db):
    ### a mistake of the model: agreed=True, but nobody said an hour
    advice, _ = advise(db, call("sched", reason="", agreed=True, days=["2024-04-04"], refused=["2024-04-04 09:00"]))
    assert advice.status == "offer" and len(advice.proposed_slots) == 3 and "2024-04-04 09:00" not in advice.proposed_slots


def test_order_of_days_and_hours_does_not_matter(db):
    ### "Tuesday or Thursday, at noon or at 9" on a Wednesday: the Thursday is first
    advice, _ = advise(db, call("sched", reason="", agreed=False, days=["2024-04-09", "2024-04-04"], hours=["12:00", "9:00"]))
    assert advice.status == "offer" and advice.proposed_slots[0] == "2024-04-04 09:00"


def test_hour_without_the_zero(db):
    advice, _ = advise(db, call("sched", reason="", agreed=True, days=["2024-04-04"], hours=["9:00"]))
    assert advice.status == "agreed" and advice.proposed_slots == ["2024-04-04 09:00"]


def test_refused_hour_without_the_zero(db):
    advice, _ = advise(db, call("sched", reason="", agreed=False, days=["2024-04-04"], hours=["09:00"], refused=["2024-04-04 9:00"]))
    assert "2024-04-04 09:00" not in advice.proposed_slots


def test_thanks_after_the_booking(db):
    ### the slot is not free any more, but it belongs to this candidate
    slot = search(db, ["2024-04-04"], ["09:00"])[0]
    assert db.book(slot)
    thanks = call("sched", reason="", agreed=True, days=[slot[:10]], hours=[slot[11:]])
    advice, _ = advise(db, thanks, booked=slot)
    assert advice.status == "agreed" and advice.proposed_slots == [slot]

    ### the same time is not available for another candidate
    advice, _ = advise(db, thanks)
    assert advice.status == "not available" and slot not in advice.proposed_slots


def test_half_an_hour_is_not_a_slot(db):
    advice, _ = advise(db, call("sched", reason="", agreed=True, days=["2024-04-04"], hours=["09:30"]))
    assert advice.status == "not available" and advice.proposed_slots[0] == "2024-04-04 09:00"


def test_wrong_argument_does_not_stop_the_program(db):
    advice, _ = advise(db, call("sched", reason="", agreed="maybe", days="Friday"))
    assert advice == SchedulingAdvisorResult() and advice.decision == "No answer"


def test_no_wish_means_from_tomorrow(db):
    advice, _ = advise(db, call("sched", reason="", agreed=False))
    assert advice.status == "offer" and all(s >= "2024-04-04" for s in advice.proposed_slots)


def test_no_free_slots(db):
    assert SchedulingAdvisor(None, db).find_slots(datetime(2024, 12, 31, 18, 0)).status == "no free slots"


def test_time_that_was_turned_down_can_be_chosen_later(db):
    free = search(db, ["2024-04-05"], ["10:00"])[0]
    advice, _ = advise(db, call("sched", reason="", agreed=True, days=[free[:10]], hours=[free[11:]], refused=[free]))
    assert advice.status == "agreed"


def test_dont_sched(db):
    advice, _ = advise(db, call("dont_sched", reason="open question"))
    assert advice == SchedulingAdvisorResult(decision="Don't Sched", status="open question")


def test_the_model_gets_the_time_of_the_conversation(db):
    _, llm = advise(db, call("dont_sched", reason="too early"))
    system_prompt = llm.seen[0][0].content
    assert "Wednesday 2024-04-03 15:12" in system_prompt
    assert "Friday 2024-04-12 (next week)" in system_prompt


def test_the_week_starts_on_sunday():
    lines = list_dates(NOW).split("\n")
    assert lines[0] == "Wednesday 2024-04-03 (today, this week)"
    assert lines[3] == "Saturday 2024-04-06 (this week)"
    assert lines[4] == "Sunday 2024-04-07 (next week)"
    assert lines[-1] == "Tuesday 2024-05-07 (in 5 weeks)"


def test_slots_text():
    assert slots_text(["2024-04-04 14:00", "2024-04-04 09:00"]) == "Thursday, April 4 at 9 AM or 2 PM"
    assert slots_text(["2024-04-04 12:00", "2024-04-05 09:00"]) == "Thursday, April 4 at 12 PM, or Friday, April 5 at 9 AM"
    assert slots_text(["2024-04-04 09:00", "2024-04-04 10:00", "2024-04-04 14:00"]) == "Thursday, April 4 at 9 AM, 10 AM or 2 PM"
