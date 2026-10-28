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

## Try out alerting proof of concept

Health check alerting is currently only a proof of concept. See [Check Alerting](../development-state.md#check-alerting) for its development state.

Here are the steps to try the Resource Health alerting proof of concept:

1. Configure which SMTP mailer service to use, and an account credentials for the email alert sender. This means setting `SMTP_MAILER_HOST`, `SMTP_MAILER_PORT`, `FROM_EMAIL`, and `FROM_EMAIL_PASSWORD` environment variables of the alerting service. See [here](https://github.com/EOEPCA/eoepca-plus/blob/7c6be3bad2b5252d420e111798ad344363b243e4/argocd/eoepca/resource-health/parts/app-resource-health-core.yaml#L746) for reference.
2. Configure the user-to-email mapping. The mapping is a json file in the service container consisting of a top-level dictionary from user id to email for their alerts, e.g. the file could be `{"example-user": "user@example.com"}`. The file can be mounted from a volume. Also set the environment variable `ALERT_USER_EMAILS` of the alerting service to user email json file.
3. Forward the health check trace data to the alerting service, for example you can make your OTel Collector(s) send a copy of the traces there. [Resource Health Reference Deployment HELM chart](https://github.com/EOEPCA/helm-charts-dev/tree/8080f0b1ce5bc93ca9b7d6ac1408a3e3f58e9a96/charts/resource-health-reference-deployment) already does this, see [here](https://github.com/EOEPCA/helm-charts-dev/blob/8080f0b1ce5bc93ca9b7d6ac1408a3e3f58e9a96/charts/resource-health-reference-deployment/values.yaml#L210) for reference. Make sure to point to the port that the alerting service expects. To change that port, set the environment variable `TRACE_RECEIVER_ADDRESS` of the alerting service, see [here](https://github.com/EOEPCA/eoepca-plus/blob/7c6be3bad2b5252d420e111798ad344363b243e4/argocd/eoepca/resource-health/parts/app-resource-health-core.yaml#L735).
4. Now try out if the setup worked. For one of the users with an email specified in step 2, create a health check which will fail. Trigger the run manually (or wait for the health check to run according to the schedule). The configured email for the user should get the failed check alert email in a few minutes.
