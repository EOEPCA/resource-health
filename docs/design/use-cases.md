# User stories

## Original Use Cases from the Use Case Definition Document (*UC*)

- **UC68**: As a user, I want automated checks to verify the continued correct
end-to-end functioning of my published workflows, so that I can
receive notification when there is a problem
  - **UC68_1**: As a user I want to be able to invoke a check upon issuing a request.
  - **UC68_2**: As a user I want to be able to visualize the raster data with highlighted areas that were reproduced incorrectly as an evidence to the check outcome.
- **UC69**: As a user, I want automated checks to verify the continued
availability of my published datasets, so that I can receive
notification when there is a problem. Availability of the dataset
refers to discovery in the Catalogue and access via Data Retrieval
and Visualisation services
- **UC70**: As a user, I want KPIs to be recorded for my published service, in
order to demonstrate that I have met the SLA of my NoR offering.
In this context, as a published service includes published datasets,
workflows, ML models, Dashboards, etc.

## Derived Use Cases (*DUC*)

- **DUC001**: Ability to run checks at regular intervals (Monthly being currently the only explicitly requested schedule)
- **DUC002**: Ability to run checks upon user's request.
- **DUC003**: Check to verify if hosted algorithms are visible/callable (including cases where the algorithm ought to be callable under specific conditions, such as random spatial/temporal locations). If check verification is negative, notification shall be issued.
- **DUC004**: Check to verify if hosted algorithms satisfy certain conventions (e.g. publishes a specification that satisfies a set of linting rules). If check verification is negative, notification shall be issued.
- **DUC005**: Check to verify if hosted environment satisfy certain conventions (e.g. publishes a specification that satisfies a set of linting rules). If check verification is negative, notification shall be issued.
- **DUC006**: Check to verify if third party backends successfully finish certain typical test cases (e.g. access data of a given size). If check verification is negative, notification shall be issued.
- **DUC007**: Check to verify if third party backends comply with API specification and profiles (such as for example openEO API profile). If check verification is negative, notification shall be issued.
- **DUC008**: Check to verify if third party backends comply with API specification and profiles (such as for example openEO API profile). If check verification is negative, notification shall be issued.
- **DUC009**: Check to verify if published dataset is accessible via Data Retrieval and Visualization (Data Access BB). If check verification is negative, notification shall be issued.
- **DUC010**: Check to verify if KPIs for published EO data have been met.
- **DUC011**: Check to verify if KPIs for hosted algorithms have been met.
- **DUC012**: Check to verify if KPIs for hosting environments have been met.
- **DUC013**: Check to verify if KPIs for third party backends have been met.
- **DUC014**: Requirements and use case discussion with APEx group 2024-08-30 and later communication over email
- **DUC015**: Check to verify if KPIs for Dashboards have been met.
- **DUC016**: Check to verify ability of a resource to reproduce reference data with a certain difference margin (that would act as a threshold health criteria).

## Target user categories

 - **Developer** - someone that understands how the underlying platform functionality was implemented and operates (BB developer, Application package specialist).
 - **End user** - someone that will want to exploit the functionality of the platform, but will not have in-depth understanding how it was implemented and operates (Platform user).

## Original requirements from Statement of Work (*BR*)
**BR125**: The Resource Health BB shall provide a general purpose capability that allows users (of all
type) to specify and schedule checks that confirm the availability and function of
specified resources.
Checks shall include proactive (end-to-end) invocation of capabilities, including the
following resource types:
* A platform service, such as a building-block – the service is ‘up’ and responsive
* A published dataset – discovery, access and visualisation
* A published Processing Workflow – discovery, deployment and execution
* A published Workflow-as-a-Service (i.e. a pre-deployed processing workflow) – end-to-end execution
* Access to other published resources, such as documentation

**BR126**: The Resource Health BB shall allow the user to observe the outcome of their checks, and
to receive notifications according to the outcome.

**BR127**: The Resource Health BB shall support specification of checks via the following means:
* REST API
* Dashboard (web UI)
* Git repository (Gitops-style)
It shall be possible to specify all aspects of the check – including the target
(endpoint/resource) of the check, the tests to be performed and the expected outcomes.

**BR128**: The Resource Health BB shall support checks whose outcome is linked to occurrence of
‘events’ reported in the log output of specified resources.

**BR129**: The Resource Health BB shall support invocation of checks according a variety of triggers
– including according to a time schedule, registration of new data, tag of a new software
release, etc.
Where appropriate, the Resource Health BB shall rely upon the Notification &
Automation BB as a source of triggers.

**BR130**: The Resource Health BB shall provide a Dashboard to visualize the status of any health
checks that the user has defined. The status reported for each check shall include
pertinent metrics – such as uptime, number of checks performed vs number of failures,
etc.

**BR131**: The Resource Health BB shall provide an API through which the status of any health
checks can be interrogated (machine-to-machine) – for example to integrate the status
into a portal.

## Derived requirements (*REQ*)

- **REQ001**: The Resource Health BB shall provide a means for general end-users to manage the life cycle (definition, observation, termination, ...) of checks that they own/have access to.
  - Derived from SoW BR125.
- **REQ002**: The Resource Health BB shall provide a means to ensure ownership/access restrictions of individual checks are respected (presumably utilising the Identity and Access Management BB).
  - Derived from SoW BR125.
- **REQ003**: The Resource Health BB shall ensure that the outcomes of current (active) specified checks are determined in a timely manner (meaning the execution of the checking logic is executed when necessary and that the necessary data/information is available to the check when it is executed).
  - Derived from SoW BR125.
- **REQ004**: The Resource Health BB shall allow specifying checks that determine the responsiveness of platform capabilities/services (such as determining ping/watchdog timer state/API timeouts/404 responses/...) sufficient for checking general availability of all/relevant other platform services/capabilities.
  - Derived from SoW BR125.
- **REQ005**: The Resource Health BB shall allow specifying checks that determine that resources provided by the platform meet end-user expectations (such as appearing in certain queries/enumerations, have the right metadata, have the right shape, contains expected columns, produce certain outputs ...) sufficient for all/relevant other platform services/capabilities.
  - Derived from SoW BR125.
- **REQ006**: The Resource Health BB shall allow specifying checks that determine the presence or absence of specified entries in resource logs (such as the absence of error 'event').
  - Derived from SoW BR128.
- **REQ007**: The Resource Health BB shall provide some mechanism for the timely notification of end-users, of events related to (the determination of) check outcomes (for example through a generic mechanism like web hooks, or through a capability provided by other BBs such as the notification and automation BB).
  - Derived from SoW BR126.
- **REQ008**: The Resource Health BB shall provide a mechanism by which end-users can specify which events to be notified of.
  - Derived from SoW BR126.
- **REQ009**: The Resource Health BB shall provide a means to manage the life cycle (definition, termination, ...) of checks through a REST-style API.
  - Derived from SoW BR127, BR130.
- **REQ010**: The Resource Health BB shall provide a means to manage the life cycle (definition, termination, ...) of checks in a textual file-based format (for use in e.g. git repositories).
  - Derived from SoW BR127, BR131.
- **REQ011**: The Resource Health BB shall provide a means to manage the life cycle (definition, termination, ...) of checks through a graphical user interface accessible through standard web browsers.
  - Derived from SoW BR127, BR131.
- **REQ012**: The Resource Health BB shall provide a means to maintain traceability to check "evidence" of an 'event' (such as location of a triggering lines in a log or timestamp of a threshold breach in a metric) when such "evidence" is available.
  - Derived from SoW BR128.
- **REQ013**: The Resource Health BB shall rely on capabilities of the Notification & Automation BB to ensure the timely determination of check outcomes, unless the capabilities of the Notification & Automation BB are insufficient to determine the check outcome in a timely manner (such as fast enough for ephemeral data to not have been lost).
  - Derived from SoW BR129.
- **REQ014**: The Resource Health BB shall rely on capabilities of the Notification & Automation BB to ensure the timely notification of check outcomes, unless the capabilities of the Notification & Automation BB are insufficient to determine the check outcome in a timely manner (such as in order to meet end-user expectations of notification latency).
  - Derived from SoW BR129.
- **REQ015**: The Resource Health BB shall provide an end-users graphical user interface for accessing and summarising the history of check outcomes (of checks accessible to the end user).
  - Derived from SoW BR130.
- **REQ016**: The Resource Health BB shall provide an API access to the history of check outcomes sufficient to reproduce the functionality exposed in the graphical user interface.
  - Derived from SoW BR131.
- **REQ017**: The Resource Health BB shall provide an end-users graphical user interface for accessing and summarising execution performance statistics of check logic (such as number of times executed, time since last execution, execution time, ...) sufficient for end-user to assess the sufficient "health" of a check itself (such as meeting expectations of timeliness).
  - Derived from SoW BR130.
- **REQ018**: The Resource Health BB shall provide an API access to execution performance statistics of check logic sufficient to reproduce the functionality exposed in the graphical user interface.
  - Derived from SoW BR131.
- **REQ019**: The Resource Health BB shall allow specifying timeliness requirements of individual (active) checks as requiring (re)determination/execution at a specific sequence of potentially recurrent time points.
  - Derived from SoW BR129.
- **REQ020**: The Resource Health BB shall allow specifying timeliness requirements of individual (active) checks as requiring (re)determination/execution on platform/component updates.
  - Derived from SoW BR129.
- **REQ021**: The Resource Health BB shall allow specifying timeliness requirements of individual (active) checks as requiring (re)determination/execution on resource registration changes.
  - Derived from SoW BR129.
- **REQ022**: The Resource Health BB shall provide a means for general end users to specify and schedule checks that confirm the availability and function of the following resource types: hosted algorithms, hosting environments, third party backends, published datasets, ML models, dashboards.
  - Derived from SoW BR125.
- **REQ023**: The Resource Health BB shall allow the user to issue a check upon their request.
  - Derived from SoW BR129.
