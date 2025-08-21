from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from cron_converter import Cron

import check_hooks.hook_utils as hu

# The hooks are loaded one file at a time, so importing things from one file to another will not work.
# This trick ensures that UserInfo is imported only for type checking - and it can only be used for that
if TYPE_CHECKING:
    from auth_hooks import UserInfo
else:
    type UserInfo = Any


def on_check_create(userinfo: UserInfo, check: hu.InCheckAttributes) -> None:
    print("ON CHECK CREATE from disallow_frequent_check_hooks.py")
    min_allowed_days_between_runs = 3
    if check.metadata.template_id == "telemetry_access_template":
        raise_error_if_schedule_too_frequent(
            check.schedule,
            min_allowed_days_between_runs=3,
            error_detail=f"Check from template {check.metadata.template_id} must run at most once in {min_allowed_days_between_runs} day period.",
        )


# This is not a hook
def raise_error_if_schedule_too_frequent(
    cron_schedule: str, min_allowed_days_between_runs: int, error_detail: str
) -> None:
    error = hu.APIUserInputError(title="Schedule Too Frequent", detail=error_detail)
    cron_instance = Cron(cron_schedule)
    [minutes, hours, days, months, weekdays] = cron_instance.to_list()
    if len(minutes) > 1:
        # Means this will sometimes run at twice or more in one hour, which is too frequent
        raise error
    if len(hours) > 1:
        # Means this will sometimes run at twice or more in one day, which is too frequent
        raise error
    start_date = datetime.now()
    schedule = cron_instance.schedule(start_date)
    prev_date = schedule.next()
    # At this point we know that the schedule is not more frequence than once per day
    # This just creates schedules for next year (or more) and checks if any two consecutive
    # schedules have enough of a gap between them
    for i in range(365):
        date = schedule.next()
        if date - prev_date < timedelta(days=min_allowed_days_between_runs):
            raise error
        if date - start_date > timedelta(days=365):
            # Haven't found too frequent scheduled times in a year from now, that's enough
            return
        prev_date = date
