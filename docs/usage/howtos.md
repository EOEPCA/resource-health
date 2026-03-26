# How-Tos

How-tos to communicate usage by example.

## Hooks

[OIDC auth hooks](https://github.com/EOEPCA/resource-health/blob/58087ff26eca34e6aeaf58216fd87b18b745e36b/check_manager/example_hooks/oidc_auth) is an example Health Check API hooks implementation for authentication with OpenID Connect protocol, and implements examples for all available Health Check API hooks.

### Authorization

Here is how to forbid some user (eric in this case) from creating a ping-an-endpoint check.

```python
def on_check_create(userinfo: UserInfo, check: hu.InCheckAttributes) -> None:
    if userinfo["username"] == "eric" and check.metadata.template_id == "simple_ping":
        raise hu.APIForbiddenError(
            title="Check creation disallowed",
            detail="You are not authorized to create this check",
        )
```

### Disallow too frequent schedule

Here is how to forbid creating checks from a certain template if they're scheduled to run more than once in any 3 days. This is useful to ensure that any expensive computation is not executed too frequently.

```python
def on_check_create(userinfo: UserInfo, check: hu.InCheckAttributes) -> None:
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
    # At this point we know that the schedule is not more frequent than once per day
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
```
