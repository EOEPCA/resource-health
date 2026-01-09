# Check Alerting

## Trace receiver

A gRPC server which accepts the OTel traces. Currently unauthenticated. Writes the error spans to a local key-value store "error_traces.sqlite3" by default. Writes the processing status of those traces to a local key-value store "trace_infos.sqlite3" by default.

To start trace receiver, first do the steps in [Setup](#setup), and then run:

    make start-trace-receiver

## Notifier

Reads error spans from "error_traces.sqlite3" by default, and trace processing status from "trace_infos.sqlite3" by default. Sends email notifications for users which have emails in `alert_user_emails.json`.

To start notifier, first do the steps in [Setup](#setup), and then run

    make start-notifier

## Setup

To use this, you need to create `.env` file and set the environment variables in there. See example file `.env.example`.
Alternatively, the environment variables can be set in the usual ways.

Also you need to set user alerting emails in `alert_user_emails.json` (you can change which file emails are in using environment variable `ALERT_USER_EMAILS`).

To run these, you need to have `uv` installed.
You can also install `make` to use the command defined in `Makefile`
