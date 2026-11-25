"""The recruiters' calendar: the Schedule table of db_Tech.sql, one search query and one safe booking.

db_Tech.sql was written for SQL Server. The same table is built here in SQLite, so no database server is needed.

Run:  python -m app.scheduling_advisor.calendar_tools
"""
import numpy as np
import pandas as pd
from sqlalchemy import bindparam, create_engine, inspect, text

from app.scheduling_advisor.config import DB_FILE, POSITION

### WHERE = what must be true, ORDER BY = what the candidate wants, LIMIT = the three nearest slots
### agreed has two witnesses: the model (the candidate chose one exact time) and the calendar (exactly this slot is free)
### SQLite: || joins texts, unixepoch turns '10:30' into seconds, MAX(a, b) is the larger value (GREATEST in SQL Server)
SEARCH = text("""
    WITH free AS (
        SELECT date, date || ' ' || time AS slot,
               MAX(0, unixepoch(:first_hour) - unixepoch(time), unixepoch(time) - unixepoch(:last_hour)) AS seconds_away
        FROM   Schedule
        WHERE  position = :position AND date >= :first_day
        AND    (available = 1 OR date || ' ' || time = :booked)   -- a slot that this candidate already booked is still theirs
    )
    SELECT   slot,
             CASE WHEN :agreed AND slot = :wish                THEN 'agreed'
                  WHEN date <= :last_day AND seconds_away = 0  THEN 'offer'
                  ELSE 'not available' END AS status
    FROM     free
    WHERE    slot > :now AND slot NOT IN :refused AND date NOT IN :refused
    ORDER BY seconds_away > 0 AND :first_hour < :last_hour,   -- a range of hours is a limit ("only after 3 PM")
             MAX(date, :last_day),                            -- all the days of the wish are equally near
             seconds_away,                                    -- one hour is a wish, so the hours near it come first
             slot
    LIMIT    3
""").bindparams(bindparam("refused", expanding=True))   ### expanding: NOT IN gets all the values of the list

### takes the slot only if it is still free, so two candidates can never get the same slot
BOOK = text("""
    UPDATE Schedule SET available = 0
    WHERE  position = :position AND available = 1 AND date || ' ' || time = :slot
""")


class ScheduleDB:

    def __init__(self, db_file=DB_FILE):
        self.engine = create_engine(f"sqlite:///{db_file}")

        ### the calendar is created in the first run
        if not inspect(self.engine).has_table("Schedule"):
            self.create()

    def create(self, closed_days=("Saturday", "Monday"), all_free=False):
        """The steps of db_Tech.sql: the valid dates of 2024 x the hours 09:00-17:00 x four positions"""
        dates = pd.DataFrame({"date": pd.date_range("2024-01-01", "2024-12-31")})
        dates = dates[~dates["date"].dt.day_name().isin(closed_days)]
        times = pd.DataFrame({"time": [f"{hour:02}:00" for hour in range(9, 18)]})
        positions = pd.DataFrame({"position": ["Python Dev", "Sql Dev", "Analyst", "ML"]})

        ### CROSS JOIN
        df = dates.merge(times, how="cross").merge(positions, how="cross")
        df["date"] = df["date"].dt.strftime("%Y-%m-%d")

        ### about half of the slots are free, by the rule of db_Tech.sql. The seed gives the same calendar on every computer
        rng = np.random.default_rng(42)
        random_numbers = rng.integers(0, 100, len(df)) + rng.integers(0, 100, len(df))
        df["available"] = 1 if all_free else (random_numbers / 200 >= 0.5).astype(int)

        df.to_sql("Schedule", con=self.engine, if_exists="replace", index_label="ScheduleID")
        return len(df)

    def get_next_three_dates(self, now, days, hours, refused=(), agreed=False, booked=None):
        """The three free slots nearest to the wish. days and hours: [one value] or [first, last]"""
        ### one day + one hour = '2024-04-05 10:00', exactly like a slot. A range is a longer text, so it is never agreed
        wish = " ".join([*days, *hours])

        ### the day and the time that the candidate agreed to are no longer refused
        if agreed:
            refused = [r for r in refused if r not in [days[0], wish]]

        params = {
            "position": POSITION, "now": now, "agreed": agreed, "wish": wish, "refused": list(refused), "booked": booked,
            ### one value is a range with the same two ends
            "first_day": days[0], "last_day": days[-1], "first_hour": hours[0], "last_hour": hours[-1],
        }
        return pd.read_sql(SEARCH, con=self.engine, params=params)

    def book(self, slot):
        """True = the slot was free, and now it is ours"""
        with self.engine.begin() as connection:
            return connection.execute(BOOK, {"position": POSITION, "slot": slot}).rowcount == 1


if __name__ == "__main__":
    db = ScheduleDB()
    print("rows:", db.create())
    print(db.get_next_three_dates("2024-04-03 15:12", days=["2024-04-05"], hours=["09:00", "12:00"]))
