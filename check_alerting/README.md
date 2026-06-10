# Check Alerting

## Trace receiver

A gRPC server which accepts the OTel traces. Currently unauthenticated. Writes the error spans to a local key-value store `error_traces.sqlite3` by default. Writes the processing status of those traces to a local key-value store `trace_infos.sqlite3` by default.

To start trace receiver, first do the steps in [Setup](#setup), and then run:

    make start-trace-receiver

## Notifier

Reads error spans from `error_traces.sqlite3` by default, and trace processing status from `trace_infos.sqlite3` by default. Sends email notifications for users which have emails in `alert_user_emails.json`.

To start notifier, first do the steps in [Setup](#setup), and then run

    make start-notifier

## Setup

To use this, you need to create `.env` file and set the environment variables in there. See example file `.env.example`.
Alternatively, the environment variables can be set in the usual ways.

Also you need to set user alerting emails in `alert_user_emails.json` (you can change which file emails are in using environment variable `ALERT_USER_EMAILS`).

To run these, you need to have `uv` installed.
You can also install `make` to use the command defined in `Makefile`

## Testing

`test/Makefile` folder has commands how to launch an OTel collector which forwards traces to `trace_receiver`, and how to push an example trace to the collector. The `Makefile` assumes that there is an OTel collector executable in `test` folder, named `otelcol`. You can change the `test/Makefile` to point to where your OTel collector is.

Also make sure to create a `alert_user_emails.json` file based on `alert_user_emails.example.json` with `bob` email set, as the example error trace is from `bob`.

To test the whole setup, run `make make start-trace-receiver` and `make start-notifier` from the current folder, and run `make start-collector` and `make send-trace` from the `test` folder. The `trace_receiver` should print that it has received an error trace (if log level is `INFO` or `DEBUG`). In 60s by default (configured with `SEND_NOTIF_SECS`) `notifier` should print that it sent out an email (if log level is `INFO` or `DEBUG`), and the email attributed to `bob` should get a message about a failed check run.
