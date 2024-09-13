# User stories

## Original User Stories from the Use Case Definition Document (*UC*)

- **UC68**: As a user, I want automated checks to verify the continued correct
end-to-end functioning of my published workflows, so that I can
receive notification when there is a problem
- **UC69**: As a user, I want automated checks to verify the continued
availability of my published datasets, so that I can receive
notification when there is a problem. Availability of the dataset
refers to discovery in the Catalogue and access via Data Retrieval
and Visualisation services
- **UC70**: As a user, I want KPIs to be recorded for my published service, in
order to demonstrate that I have met the SLA of my NoR offering.
In this context, as a published service includes published datasets,
workflows, ML models, Dashboards, etc.

## Original requirements from Statement of Work (SoW)
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

## Target users

### APEx

From page 9 of **UC**:
> The Algorithm Hosting Service will provide a registry of hosted services, in which hosted
applications are registered and published so that they are discoverable and available for
reuse by other projects. This is supported in EOEPCA+ by the Resource Register,
**Resource Health Check** and Resource Discovery use cases.

