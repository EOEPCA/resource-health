# Introduction

The documentation for the Resource Health building block is organised as follows...

* **Introduction**
  Introduction to the BB - including summary of purpose and capabilities.
* **Getting Started**<br>
  Quick start instructions - including installation, e.g. of a local instance.
* **Design**<br>
  Description of the BB design - including its subcomponent architecture and interfaces.
* **Usage**<br>
  Tutorials, How-tos, etc. to communicate usage of the BB.
* **Administration**<br>
  Configuration and maintenance of the BB.
* **API**<br>
  Details of APIs provided by the BB - including endpoints, usage descriptions and examples etc.

## About Resource Health BB

The Resource Health BB offers a generalised capability that allows all types of users to specify and schedule checks relating to their resources of interest, to visualise the outcome of the checks, and to receive notifications according to the outcome.

## Capabilities

- General capability to specify and schedule checks:
  - Manage life cycle of checks
  - Means to comply with ownership/access restrictions of individual checks
  - Ensure timely execution and required input retrieval of health checks
  - Availability-type check specification
  - Specification of checks that verify if resources meet end-user expectations
- Ablity to observe check outcomes and receive notifications according to outcomes:
  - Mechanism that ensures timely notification issuance
  - Mechanism to specify types of events that shall trigger notifications
- Check specification via:
  - REST API
  - Dashboard (web UI)
  - Git repository (Gitops-style)
- Support for checks whose outcomes are linked to events reported in the log of specified resources:
  - Presence/absence of specified entries in resource logs
  - Maintenance of traceability to check for "evidence" of an event
- Check invocation according to variety of triggers:
  - Time schedule
  - Resource registration changes
  - Platform/component updates
- Dashboard to visualize status of any health checks defined by the user
  - Graphical UI for access and summary of the history of check outcomes
  - Graphical UI for access and summary of performance statistics to assess correctnes of the execution of the check itself
- API to interrogate any health check status
  - API access to the history of check outcomes sufficient to produce functionality available in the Graphical UI
  - API access to execution performance statistics of check logic sufficient to produce functionality available in the Graphical UI
