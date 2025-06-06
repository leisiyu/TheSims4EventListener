import mathfrom protocolbuffers.Localization_pb2 import LocalizedDateAndTimeData, LocalizedStringTokenfrom sims4.math import MAX_UINT64import enumimport sims4.commandsimport sims4.tuning.tunablewith sims4.reload.protected(globals()):
    TICKS_PER_REAL_WORLD_SECOND = 1000
    REAL_MILLISECONDS_PER_SIM_SECOND = 25
    MILLISECONDS_PER_SECOND = 1000
    SECONDS_PER_MINUTE = 60
    MINUTES_PER_HOUR = 60
    HOURS_PER_DAY = 24
    DAYS_PER_WEEK = 7
    SECONDS_PER_HOUR = SECONDS_PER_MINUTE*MINUTES_PER_HOUR
    SECONDS_PER_DAY = SECONDS_PER_HOUR*HOURS_PER_DAY
    SECONDS_PER_WEEK = SECONDS_PER_DAY*DAYS_PER_WEEK
    INVALID_TIME = MAX_UINT64
class TimeUnit(enum.Int):
    SECONDS = 0
    MINUTES = 1
    HOURS = 2
    DAYS = 3
    WEEKS = 4

def send_clock_tuning():
    sims4.commands.execute('clock._set_milliseconds_per_sim_second {0}'.format(REAL_MILLISECONDS_PER_SIM_SECOND), None)

def sim_ticks_per_day():
    return REAL_MILLISECONDS_PER_SIM_SECOND*SECONDS_PER_DAY

def sim_ticks_per_week():
    return REAL_MILLISECONDS_PER_SIM_SECOND*SECONDS_PER_WEEK

class DateAndTime(int):
    __slots__ = ()

    def __repr__(self):
        return 'DateAndTime({0:d})'.format(self.absolute_ticks())

    def __str__(self):
        ms = int(self.absolute_seconds()*MILLISECONDS_PER_SECOND % MILLISECONDS_PER_SECOND)
        return '{0:02}:{1:02}:{2:02}.{3:03} day:{4} week:{5}'.format(self.hour(), self.minute(), self.second(), ms, self.day(), self.week())

    def __format__(self, format_spec):
        if format_spec == 'h':
            return '{:02}'.format(self.hour())
        if format_spec == 'm':
            return '{:02}'.format(self.minute())
        if format_spec == 's':
            return '{:02}'.format(self.second())
        if format_spec == 'd':
            return str(self.day())
        if format_spec == 'D':
            return ('Su', ' M', 'Tu', ' W', 'Th', ' F', 'Sa')[self.day()]
        if format_spec == 'w':
            return str(self.week())
        if format_spec == 'as':
            return str(self.absolute_seconds()*MILLISECONDS_PER_SECOND % MILLISECONDS_PER_SECOND)
        return super().__format__(format_spec)

    def second(self):
        return int(self.absolute_seconds() % SECONDS_PER_MINUTE)

    def minute(self):
        return int(self.absolute_seconds()/SECONDS_PER_MINUTE % MINUTES_PER_HOUR)

    def hour(self):
        return int(self.absolute_seconds()/SECONDS_PER_HOUR % HOURS_PER_DAY)

    def day(self):
        return int(self.absolute_seconds()/SECONDS_PER_DAY % DAYS_PER_WEEK)

    def week(self):
        return int(self.absolute_seconds()/SECONDS_PER_WEEK)

    def absolute_ticks(self):
        return int(self)

    def absolute_seconds(self):
        return int(self)/REAL_MILLISECONDS_PER_SIM_SECOND

    def absolute_minutes(self):
        return self.absolute_seconds()/SECONDS_PER_MINUTE

    def absolute_hours(self):
        return self.absolute_seconds()/SECONDS_PER_HOUR

    def absolute_days(self):
        return self.absolute_seconds()/SECONDS_PER_DAY

    def absolute_weeks(self):
        return self.absolute_seconds()/SECONDS_PER_WEEK

    def _ticks_in_day(self):
        return int(self) % sim_ticks_per_day()

    def _ticks_in_week(self):
        return int(self) % sim_ticks_per_week()

    def time_to_week_time(self, time_of_week):
        tick_diff = time_of_week._ticks_in_week() - self._ticks_in_week()
        if tick_diff < 0:
            tick_diff += sim_ticks_per_week()
        return TimeSpan(tick_diff)

    def time_of_next_week_time(self, time_of_week):
        return self + self.time_to_week_time(time_of_week)

    def time_till_timespan_of_week(self, start_time_of_week, optional_end_time=None, min_duration_remaining=None):
        ticks_in_week = self._ticks_in_week()
        tick_diff = start_time_of_week.absolute_ticks() - ticks_in_week
        if tick_diff > 0:
            return TimeSpan(tick_diff)
        if optional_end_time is not None:
            tick_diff_before_end = optional_end_time.absolute_ticks() - ticks_in_week
            if tick_diff_before_end > 0 and (min_duration_remaining is None or tick_diff_before_end >= min_duration_remaining.in_ticks()):
                return TimeSpan.ZERO
            else:
                end_of_week = sim_ticks_per_week() - self._ticks_in_week()
                return TimeSpan(end_of_week + start_time_of_week.absolute_ticks())
        else:
            end_of_week = sim_ticks_per_week() - self._ticks_in_week()
            return TimeSpan(end_of_week + start_time_of_week.absolute_ticks())

    def time_between_day_times(self, start_time, end_time):
        ticks_in_day = self._ticks_in_day()
        start_ticks = start_time._ticks_in_day()
        end_ticks = end_time._ticks_in_day()
        if start_ticks > end_ticks:
            if ticks_in_day >= start_ticks or ticks_in_day <= end_ticks:
                return True
            return False
        elif ticks_in_day >= start_ticks and ticks_in_day <= end_ticks:
            return True
        return False

    def time_between_week_times(self, start_time, end_time):
        ticks_in_week = self._ticks_in_week()
        start_ticks = start_time._ticks_in_week()
        end_ticks = end_time._ticks_in_week()
        if start_ticks > end_ticks:
            if ticks_in_week >= start_ticks or ticks_in_week <= end_ticks:
                return True
            return False
        elif ticks_in_week >= start_ticks and ticks_in_week <= end_ticks:
            return True
        return False

    def time_till_next_day_time(self, day_time, rollover_same_time=False):
        ticks_in_day = self._ticks_in_day()
        ticks_in_day_time = day_time._ticks_in_day()
        time_till_next_day_time = ticks_in_day_time - ticks_in_day
        if rollover_same_time:
            if time_till_next_day_time <= 0:
                time_till_next_day_time += sim_ticks_per_day()
        elif time_till_next_day_time < 0:
            time_till_next_day_time += sim_ticks_per_day()
        return TimeSpan(time_till_next_day_time)

    def time_of_next_day_time(self, day_time):
        return self + self.time_till_next_day_time(day_time)

    def time_since_beginning_of_week(self):
        return self + TimeSpan(SECONDS_PER_WEEK*-self.week()*REAL_MILLISECONDS_PER_SIM_SECOND)

    def start_of_week(self):
        return DateAndTime(self.week()*sim_ticks_per_week())

    def start_of_next_week(self):
        return DateAndTime((self.week() + 1)*sim_ticks_per_week())

    def time_of_day(self):
        return DateAndTime(self % sim_ticks_per_day())

    def __sub__(self, other):
        return TimeSpan(int.__sub__(self, other))

    def __add__(self, other):
        return DateAndTime(int.__add__(self, other._delta))

    def debug_readable_time(self) -> str:
        day = ['Sun.', 'Mon.', 'Tue.', 'Wed.', 'Thu.', 'Fri.', 'Sat.'][self.day()]
        hour = (self.hour() % 12,)
        minute = self.minute()
        meridiem = 'AM' if self.hour() < 12 else 'PM'
        return '{} {}:{:02d} {}'.format(day, hour[0], minute, meridiem)

    def populate_localization_token(self, token):
        loc_data = LocalizedDateAndTimeData()
        loc_data.seconds = self.second()
        loc_data.minutes = self.minute()
        loc_data.hours = self.hour()
        day_of_week = self.day()
        if day_of_week == 0:
            day_of_week = 7
        loc_data.date = day_of_week
        loc_data.month = 0
        loc_data.full_year = 0
        token.type = LocalizedStringToken.DATE_AND_TIME
        token.date_and_time = loc_data
DATE_AND_TIME_ZERO = DateAndTime(0)INVALID_DATE_AND_TIME = DateAndTime(INVALID_TIME)
class TimeSpan:
    __slots__ = ('_delta',)

    def __init__(self, delta):
        self._delta = math.ceil(delta)

    def populate_localization_token(self, token):
        token.number = self.in_minutes()
        token.type = LocalizedStringToken.NUMBER

    def in_ticks(self):
        return self._delta

    def in_seconds(self):
        return self._delta/REAL_MILLISECONDS_PER_SIM_SECOND

    def in_minutes(self):
        return self.in_seconds()/SECONDS_PER_MINUTE

    def in_hours(self):
        return self.in_seconds()/SECONDS_PER_HOUR

    def in_days(self):
        return self.in_seconds()/SECONDS_PER_DAY

    def in_weeks(self):
        return self.in_seconds()/SECONDS_PER_WEEK

    def in_real_world_seconds(self):
        return self._delta/TICKS_PER_REAL_WORLD_SECOND

    def __add__(self, other):
        return TimeSpan(self._delta + other._delta)

    def __sub__(self, other):
        return TimeSpan(self._delta - other._delta)

    def __mul__(self, other):
        return TimeSpan(self._delta*other)

    def __truediv__(self, other):
        return TimeSpan(self._delta/other)

    def __cmp__(self, other):
        return self._delta - other._delta

    def __lt__(self, other):
        return issubclass(type(other), type(self)) and self._delta < other._delta

    def __le__(self, other):
        return issubclass(type(other), type(self)) and self._delta <= other._delta

    def __gt__(self, other):
        return issubclass(type(other), type(self)) and self._delta > other._delta

    def __ge__(self, other):
        return issubclass(type(other), type(self)) and self._delta >= other._delta

    def __eq__(self, other):
        return issubclass(type(other), type(self)) and self._delta == other._delta

    def __ne__(self, other):
        return not (issubclass(type(other), type(self)) and self._delta == other._delta)

    def __neg__(self):
        return TimeSpan(-self._delta)

    def __hash__(self):
        return self._delta

    def __repr__(self):
        return 'TimeSpan({0})'.format(self._delta)

    def __str__(self):
        abs_delta = abs(self.in_seconds())
        if abs_delta < SECONDS_PER_MINUTE:
            return '{0:.2f} seconds'.format(self.in_seconds())
        if abs_delta < SECONDS_PER_MINUTE*MINUTES_PER_HOUR:
            return '{0:.2f} minutes'.format(self.in_minutes())
        if abs_delta < SECONDS_PER_MINUTE*MINUTES_PER_HOUR*HOURS_PER_DAY:
            return '{0:.2f} hours'.format(self.in_hours())
        if abs_delta < SECONDS_PER_MINUTE*MINUTES_PER_HOUR*HOURS_PER_DAY*DAYS_PER_WEEK:
            return '{0:.2f} days'.format(self.in_days())
        else:
            return '{0:.2f} weeks'.format(self.in_weeks())
TimeSpan.ZERO = TimeSpan(0)TimeSpan.ONE = TimeSpan(1)TimeSpan.NEGATIVE_ONE = TimeSpan(-1)
def create_date_and_time(days=0, hours=0, minutes=0):
    num_sim_seconds = days*SECONDS_PER_DAY + hours*SECONDS_PER_HOUR + minutes*SECONDS_PER_MINUTE
    time_in_ticks = num_sim_seconds*REAL_MILLISECONDS_PER_SIM_SECOND
    return DateAndTime(time_in_ticks)

def create_time_span(days=0, hours=0, minutes=0):
    num_sim_seconds = days*SECONDS_PER_DAY + hours*SECONDS_PER_HOUR + minutes*SECONDS_PER_MINUTE
    time_in_ticks = num_sim_seconds*REAL_MILLISECONDS_PER_SIM_SECOND
    return TimeSpan(time_in_ticks)

def date_and_time_from_week_time(num_weeks, week_time):
    total_ticks = num_weeks*sim_ticks_per_week() + week_time.absolute_ticks()
    return DateAndTime(total_ticks)

def ticks_to_time_unit(ticks, time_unit, use_sim_time):
    if use_sim_time:
        seconds = ticks/REAL_MILLISECONDS_PER_SIM_SECOND
    else:
        seconds = ticks/TICKS_PER_REAL_WORLD_SECOND
    if time_unit is TimeUnit.SECONDS:
        return seconds
    if time_unit is TimeUnit.MINUTES:
        return seconds/SECONDS_PER_MINUTE
    if time_unit is TimeUnit.HOURS:
        return seconds/SECONDS_PER_HOUR
    if time_unit is TimeUnit.DAYS:
        return seconds/SECONDS_PER_DAY
    elif time_unit is TimeUnit.WEEKS:
        return seconds/SECONDS_PER_WEEK
if __name__ == '__main__':
    import doctest
    doctest.testmod()
    TunableClock.SetSimSecondsPerRealSecond(30)