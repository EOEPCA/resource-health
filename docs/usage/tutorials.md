# Tutorials

Tutorials as a learning aid.

Note that all the links in the tutorial are for the development cluster, and you need to authenticate as one of the three standard users to create checks and view their results.
In other deployments the links will be different. I will also note all deployment dependant aspects as they come up. 

## Basic tutorial for users

In this tutorial we will learn:

* How to navigate the Health Check Web UI
* How to define a simple health check
* How to specify when the check runs (or run it on demand)
* How to view the health check generated telemetry and diagnose simple issues from it

You should follow along the following steps to get used to how things work.

1. Go to the Health Check website [https://resource-health.apx.develop.eoepca.org/](https://resource-health.apx.develop.eoepca.org/). As noted above, you should log in as one of the standard users.
2. Click on `Create new check`.
   ![Create new check](./img/basic-user-tutorial/01-Create-new-check.png)
   From the dropdown shown below choose `simple ping template` check template (keep in mind that the platform might be configured to not have a check template exactly like this - the name of check template might be different, or it might not even exist, for example)
   ![Choose check template](./img/basic-user-tutorial/02-Choose-check-template.png)
   Enter the values as you see below
   ![Submit a simple check](./img/basic-user-tutorial/03-Submit-a-simple-check.png)
   Note that `https://example.om/` deliberately contains a typo for us to see how to debug errors.  
   `schedule` is a CRON-style schedule specifying when the health check is to be executed. The schedule `0 0 1,15 * *` means the check will run `At 00:00 on day-of-month 1 and 15`. See [Cron Schedule](#cron-schedule) for more detailed information.
   Then click sumbit. Note that you might get an `AxiosError`, and that just means that it's been too long since you logged in. Just reload the page, log in, and fill in the details again.
3. After submitting the check, click on `Create new check` again (to hide the check creation form).  
   Your new check `Ping example.com` (or however you named it) should appear somewhere in the list, usually near the top.  
   Since the new check hasn't executed yet, all the stats in the table show empty values for it.  
   Click `Run Check`. The check should now run in the background, and you can click reload (**&#10227;**) button next to it to refresh the telemetry for this check. Once run information appears (the run should have failed, as indicated by `problematic run count` being non-zero), click on the check to get more details on the check runs.
   ![Checks list](./img/basic-user-tutorial/04-Show-non-zero-run-count.png)
4. A page for a single check should open. Scroll to the bottom of the page. It should look something like below.
   ![Check error messages](./img/basic-user-tutorial/05-Check-error-messages.png)
   In particular, you can see the error message, the end of which is
   ```
   Failed to resolve 'example.om' ([Errno -2] Name or service not known)"))
   ```
   We see that it couldn't ping `example.om` as no such domain exists.
5. We conclude that we defined the check incorrectly. We will remove it, and create a new one without the typo. Click on `Remove Check`. Confirm check removal when the popup appears.
   ![Remove check](./img/basic-user-tutorial/06-Remove-check.png)
6. Now go create the check using step 2. but without the typo, of course. Then go do step 3. and 4., the check should now run successfully.
   Below is how the website home page should look when the check run succeeds, and after that how the individual check page should look.
   ![Successful check summary](./img/basic-user-tutorial/07-Success-summary.png)
   ![Successful check details](./img/basic-user-tutorial/08-Success-details.png)

<!-- 
- `id` represents an internal identifier (in the REST API) used for `DELETE`ing or `PATCH`ing the health check;
- `metadata` contains information such as human readable labels/names as well as provenance (such as the template form which it was produced);
- `schedule` is the CRON-style schedule according to which the health check is executed; and
- `outcome_filter` contains a (OpenTelemetry trace data) filtering criterion for identifying spans pertinent to this health check.  -->

## Advanced tutorial for users

In this tutorial it is assumed that you are familiar with the basics, such as having followed [Basic tutorial for users](#basic-tutorial-for-users)

In this tutorial we will learn:

* How to define more complex health checks
* How to inspect detailed check telemetry
* How to use detailed check telemetry

Follow along the following steps:

1. Go to the Health Check website [https://resource-health.apx.develop.eoepca.org/](https://resource-health.apx.develop.eoepca.org/). Again, you should log in as one of the standard users.
2. We will create a health check which will execute the Python script below using the [Pytest](https://docs.pytest.org/en/stable/) testing framework.
   ```python
   import random
   import pytest

   ## Utility functions that will be moved into library

   from opentelemetry import trace
   from opentelemetry.util import types
   def report_custom(attributes: dict[str, types.AttributeValue]) -> None:
       cur_span = trace.get_current_span()
       cur_span.set_attributes(attributes)

   # USER DEFINED CODE START

   def test_that_generates_custom_telemetry1() -> None:
       ## Something returned by a service, or similar
       outcome = random.random()
       report_custom({"resourcehealth.example.random_outcome": outcome})
       assert outcome <= 1

   def test_that_generates_custom_telemetry2() -> None:
       ## Something returned by a service, or similar
       outcome1 = random.random()
       outcome2 = random.random()

       ## To simplify filtering when you have multiple
       ## values, include a "has_xyz"
       report_custom(
           {
               "resourcehealth.example.has_outcome": True,
               "resourcehealth.example.random_outcome1": outcome1,
               "resourcehealth.example.random_outcome2": outcome2,
           }
       )
       assert abs(outcome1 - outcome2) <= 1
   ```
   See [Health Check Script](#health-check-script) for more details about health check scripts.  
   Create new check just like before. This time you should use `generic script template`. Set `Name`, `Description`, and `Schedule` to whatever you like (see [Cron Schedule](#cron-schedule) for a refresher on scheduling). Then input [https://gist.githubusercontent.com/tilowiklundSensmetry/aa8a28ab9bc432b8a76635a238c9aa11/raw/9dc5847959a909ffbaeb1a9239bbf10ad442266f/test_producing_custom_data.py](https://gist.githubusercontent.com/tilowiklundSensmetry/aa8a28ab9bc432b8a76635a238c9aa11/raw/9dc5847959a909ffbaeb1a9239bbf10ad442266f/test_producing_custom_data.py) in the `Script` field (this is a link to the script above). Alternatively, you could put the script encoded as a Data URL in there, see [Data URL](TODO: add link to place explaining this)  
   The check creation should look something like this
   ![Create report check](./img/advanced-user-tutorial/01-Create-Report-Check.png)
   Click `Submit`
3. Run the check once, just as before. The check should succeed. Now go to the check results table and click on the check ID (TODO: show screenshot). A page with the raw telemetry for that check run should open up - in here you see what information is stored about each check run in the database. See [Raw Health Check Telemetry](#raw-health-check-telemetry). In particular, you can search (with ctrl + F) for `resourcehealth.example.random_outcome` or `resourcehealth.example.random_outcome1` and see those results.
4. We will now see one way to use the detailed health check telemetry. We will create a health check which looks into the telemetry generated from the above checks and verifies that the results from above overall are as expected. The check code is shown below
   ```python
   from datetime import timedelta
   from statistics import median
   import pytest

   ## Utility functions that will be moved into library

   from typing import Any
   from opensearchpy import AsyncOpenSearch
   import asyncio

   from python_opentelemetry_access.proxy import Proxy
   from python_opentelemetry_access.proxy.opensearch.ss4o import OpenSearchSS40Proxy


   def get_opensearch_proxy() -> Proxy:
       opensearch_params: dict[str, Any] = {}
       opensearch_params.update({"verify_certs": False, "ssl_show_warn": False})
       client = AsyncOpenSearch(
           # hosts=[{"host": "opensearch-cluster-master-headless", "port": 9200}],
           hosts=[{"host": "127.0.0.1", "port": 8080}],
           use_ssl=False,
           **opensearch_params,
       )
       return OpenSearchSS40Proxy(client)


   @pytest.fixture
   def telemetry_proxy() -> Proxy:
       proxy = get_opensearch_proxy()
       yield proxy
       async def proxy_close():
           await proxy.aclose()
       asyncio.run(proxy_close())

   # USER DEFINED CODE START

   @pytest.mark.filterwarnings("ignore:enable_cleanup_closed.*:DeprecationWarning")
   def test_that_inspects_custom_telemetry1(telemetry_proxy: Proxy) -> None:
       previous_outcomes = [
           span.attributes["resourcehealth.example.random_outcome"]
           for span in telemetry_proxy.load_span_data_sync(
               span_attributes={
                   # None means "any value" for now, will change
                   "resourcehealth.example.random_outcome": None
               },
               max_data_age=timedelta(weeks=4),
           )
       ]

       print(f"random_outcomes: {previous_outcomes[:10]}{'' if len(previous_outcomes) < 10 else '...'}")

       assert len(previous_outcomes) > 0
       assert median(previous_outcomes) < 0.8

   @pytest.mark.filterwarnings("ignore:enable_cleanup_closed.*:DeprecationWarning")
   def test_that_inspects_custom_telemetry2(telemetry_proxy: Proxy) -> None:
       previous_outcome_diffs = [
           span.attributes["resourcehealth.example.random_outcome1"]
           - span.attributes["resourcehealth.example.random_outcome1"]
           for span in telemetry_proxy.load_span_data_sync(
               span_attributes={
                   "resourcehealth.example.has_outcome": [True],
               },
               max_data_age=timedelta(weeks=4),
           )
       ]

       print(f"random_diffs: {previous_outcome_diffs[:10]}{'' if len(previous_outcome_diffs) < 10 else '...'}")

       assert median(previous_outcome_diffs) - min(previous_outcome_diffs) < 1.8
       assert max(previous_outcome_diffs) - median(previous_outcome_diffs) < 1.8
   ```
   Create a new check just like before, and put [https://gist.githubusercontent.com/tilowiklundSensmetry/47d5a9bb2a9aa66ca4cfc71ba70814ff/raw/72755d75c4e85dd9ea651e1c963502c4244119f7/test_consuming_custom_data.py](https://gist.githubusercontent.com/tilowiklundSensmetry/47d5a9bb2a9aa66ca4cfc71ba70814ff/raw/72755d75c4e85dd9ea651e1c963502c4244119f7/test_consuming_custom_data.py) in the `Script` field.  
   Click `Submit`
4. So that this check has more data to inspect, run the previous check a few times manually (you don't need to wait for one run to finish to run the check again). Then run the current check once. TODO: CONTINUE HERE


## Appendix

### Cron Schedule

`schedule` is a CRON-style schedule specifying when the health check is to be executed. The schedule `0 0 1,15 * *` means the check will run `At 00:00 on day-of-month 1 and 15`. You can go to [https://www.baeldung.com/cron-expressions](https://www.baeldung.com/cron-expressions#cron-expression) to learn about Cron expression syntax, and to [https://crontab.guru](https://crontab.guru/#0_0_1,15_*_*) to see an explanation for your own schedule expression.  
**Caution**: not all tools which support CRON schedule expressions support exactly the same syntax. Some tools support more than the 5 standard parts of the expression, for example.

### Health Check Script

By default, health checks are just Python tests using [Pytest framework](TODO: add link), with some helper functionality provided by Resource Health BB. In principle, a program in any language could be considered a health check as long as it generates [Opentelemetry](TODO: add link) traces, but Resource Health BB currently only provides means to execute Pytest-based checks.

The most important thing you need to remember is that **test function names must start with `test`, and test class names must start with `Test`**.

#### Getting Started

To get a simplest check going all you need to do is have a Python function starting with `test`, and use `assert` to check that results are as you expect, for example
```python
import requests

def test_simple_ping() -> None:
    response = requests.get("https://example.com/")
    assert response.status_code == 200
```

#### Check features

In the check file you can import any Python packages (though you need to specify them in requirements.txt field) and use any Python 3.12 language features (such as loops, functions, match statements, etc.), and any Pytest features (such as fixtures, parametrization, etc.) in your test or outside of it. There are many great guides for writing Pytest tests, and you can also take a look at [Pytest official documentation](https://docs.pytest.org/en/stable/index.html) to learn more. For the rest of this chapter we will focus the other available functionality.

The below code (also used above to create a check) demonstrates how to add some custom data to the current span. This could be used to log things like computation results to be checked for consistency among different runs later, for example.  
Just as the comments note, the top part of this will later be moved into a library.
```python
import random
import pytest

## Utility functions that will be moved into library

from opentelemetry import trace
from opentelemetry.util import types


def report_custom(attributes: dict[str, types.AttributeValue]) -> None:
    cur_span = trace.get_current_span()
    cur_span.set_attributes(attributes)


# USER DEFINED CODE START


def test_that_generates_custom_telemetry1() -> None:
    ## Something returned by a service, or similar
    outcome = random.random()

    report_custom({"resourcehealth.example.random_outcome": outcome})

    assert outcome <= 1


def test_that_generates_custom_telemetry2() -> None:
    ## Something returned by a service, or similar
    outcome1 = random.random()
    outcome2 = random.random()

    ## To simplify filtering when you have multiple
    ## values, include a "has_xyz"
    report_custom(
        {
            "resourcehealth.example.has_outcome": True,
            "resourcehealth.example.random_outcome1": outcome1,
            "resourcehealth.example.random_outcome2": outcome2,
        }
    )

    assert abs(outcome1 - outcome2) <= 1
```

The code below demonstrates checking the telemetry added by the test above.
```python
from datetime import timedelta
from statistics import median
import pytest

## Utility functions that will be moved into library

from typing import Any
from opensearchpy import AsyncOpenSearch
import asyncio

from python_opentelemetry_access.proxy import Proxy
from python_opentelemetry_access.proxy.opensearch.ss4o import OpenSearchSS40Proxy


def get_opensearch_proxy() -> Proxy:
    opensearch_params: dict[str, Any] = {}

    opensearch_params.update({"verify_certs": False, "ssl_show_warn": False})

    client = AsyncOpenSearch(
        # hosts=[{"host": "opensearch-cluster-master-headless", "port": 9200}],
        hosts=[{"host": "127.0.0.1", "port": 8080}],
        use_ssl=False,
        **opensearch_params,
    )
    return OpenSearchSS40Proxy(client)


@pytest.fixture
def telemetry_proxy() -> Proxy:
    proxy = get_opensearch_proxy()
    yield proxy

    async def proxy_close():
        await proxy.aclose()

    asyncio.run(proxy_close())


# USER DEFINED CODE START

@pytest.mark.filterwarnings("ignore:enable_cleanup_closed.*:DeprecationWarning")
def test_that_inspects_custom_telemetry1(telemetry_proxy: Proxy) -> None:
    previous_outcomes = [
        span.attributes["resourcehealth.example.random_outcome"]
        for span in telemetry_proxy.load_span_data_sync(
            span_attributes={
                # None means "any value" for now, will change
                "resourcehealth.example.random_outcome": None
            },
            max_data_age=timedelta(weeks=4),
        )
    ]

    print(f"random_outcomes: {previous_outcomes[:10]}{'' if len(previous_outcomes) < 10 else '...'}")

    assert len(previous_outcomes) > 0
    assert median(previous_outcomes) < 0.8

@pytest.mark.filterwarnings("ignore:enable_cleanup_closed.*:DeprecationWarning")
def test_that_inspects_custom_telemetry2(telemetry_proxy: Proxy) -> None:
    previous_outcome_diffs = [
        span.attributes["resourcehealth.example.random_outcome1"]
        - span.attributes["resourcehealth.example.random_outcome1"]
        for span in telemetry_proxy.load_span_data_sync(
            span_attributes={
                "resourcehealth.example.has_outcome": [True],
            },
            max_data_age=timedelta(weeks=4),
        )
    ]

    print(f"random_diffs: {previous_outcome_diffs[:10]}{'' if len(previous_outcome_diffs) < 10 else '...'}")

    assert median(previous_outcome_diffs) - min(previous_outcome_diffs) < 1.8
    assert max(previous_outcome_diffs) - median(previous_outcome_diffs) < 1.8
```

#### Raw Health Check Telemetry

Raw check telemetry is just OpenTelemetry traces in [OTLP/JSON](https://opentelemetry.io/docs/specs/otlp/#json-protobuf-encoding) format.

You can read more about distributed tracing in OpenTelemetry [here](https://opentelemetry.io/docs/concepts/observability-primer/#understanding-distributed-tracing) (For now we don't have log support, so you should skip that part).

https://opentelemetry.io/docs/concepts/observability-primer/#understanding-distributed-tracing