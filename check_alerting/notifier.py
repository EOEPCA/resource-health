import dbm
import json
import logging
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import Message
from email.mime.text import MIMEText
from time import sleep
from types import TracebackType
from typing import Any, Self

from opentelemetry_betterproto.opentelemetry.proto.trace.v1 import ResourceSpans

from common import (
    ERROR_TRACES_FILE,
    TRACE_INFO_STATUS_CODE_PROCESSED,
    TRACE_INFO_STATUS_CODE_PROCESSING,
    TRACE_INFOS_FILE,
    MutableMappingBytes,
    get_env_var_or_throw,
    get_resource_spans_list,
    get_trace_info,
)
from proto import TraceInfo, TraceInfoStatusCode

logger = logging.getLogger()
logging.basicConfig()
logger.setLevel(logging.DEBUG)


class Mailer:
    def __init__(self, from_email: str, from_email_password: str) -> None:
        self._from_email = from_email
        self._smtp = smtplib.SMTP_SSL(
            "smtp.gmail.com", port=465, context=ssl.create_default_context()
        )
        self._smtp.login(user=from_email, password=from_email_password)

    def send_email(self, to_email: str, subject: str, message: Message) -> None:
        message["From"] = self._from_email
        message["To"] = to_email
        message["Subject"] = subject
        self._smtp.sendmail(
            from_addr=self._from_email, to_addrs=[to_email], msg=message.as_string()
        )

    def __enter__(self) -> Self:
        self._smtp.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._smtp.__exit__(exc_type, exc_value, tb)


def send_email_notification(
    mailer: Mailer,
    alert_user_to_email: dict[str, str],
    trace_id: str,
    resource_spans_list: list[ResourceSpans],
) -> None:
    user_id: str | None = None
    health_check_name: str | None = None
    for resource_spans in resource_spans_list:
        resource_attributes: dict[str, Any] = dict(
            (attr.key, attr.value) for attr in resource_spans.resource.attributes
        )
        cur_user_id = resource_attributes.get("user.id", None)
        if user_id is None and cur_user_id is not None:
            user_id = cur_user_id
        elif user_id != cur_user_id:
            logger.error(
                f"Trace {trace_id} specifies distinct user ids '{user_id}' and '{cur_user_id}'"
            )

        cur_health_check_name = resource_attributes.get("health_check.name", None)
        if health_check_name is None and cur_health_check_name is not None:
            health_check_name = cur_health_check_name
        elif health_check_name != cur_health_check_name:
            logger.error(
                f"Trace {trace_id} specifies distinct health check names '{health_check_name}' and '{cur_health_check_name}'"
            )

    if user_id is None:
        logger.warning(
            f"Trace {trace_id} has errors but doesn't have an associated user id, so no notification was sent"
        )
        return
    print(type(user_id))
    if user_id not in alert_user_to_email:
        logger.info(
            f"User id {user_id} doesn't have an associated email for notifications, so no notification was sent for failed check run {trace_id}",
        )
        return
    to_email = alert_user_to_email[user_id]

    # based on https://stackoverflow.com/a/6270987 and https://stackoverflow.com/a/32873143
    # Would like to generate a link to the appropriate health check run in the website,
    # but currently the trace doesn't store health check id
    message_text = (
        f"Health check run (from an unspecified check) {trace_id} failed"
        if health_check_name is None
        else f"Health check {health_check_name} run {trace_id} failed"
    )
    mailer.send_email(
        to_email=to_email, subject="Health Check Failed", message=MIMEText(message_text)
    )
    logger.info(
        f"Email notification for failed check run {trace_id} was successfully sent to user {user_id}",
    )


def process_trace(
    mailer: Mailer,
    trace_to_resource_spans: MutableMappingBytes,
    trace_to_info: MutableMappingBytes,
    alert_user_to_email: dict[str, str],
    send_notif_time: timedelta,
    remove_trace_time: timedelta,
    trace_id: str,
) -> None:
    trace_info = get_trace_info(trace_to_info, trace_id)
    assert trace_info is not None
    now = datetime.now(timezone.utc)
    if (
        trace_info.status == TraceInfoStatusCode.PROCESSED
        and trace_info.last_seen + remove_trace_time < now
    ):
        del trace_to_info[trace_id]
        if trace_id in trace_to_resource_spans:
            logger.warning(
                f"Trace {trace_id} is processed, and still present in the database after {remove_trace_time} from receiving it"
            )
            del trace_to_resource_spans[trace_id]
        return
    if (
        trace_info.status == TraceInfoStatusCode.RECEIVING
        and trace_info.last_seen + send_notif_time < now
    ):
        trace_to_info[trace_id] = bytes(
            TraceInfo(
                last_seen=trace_info.last_seen,
                status=TRACE_INFO_STATUS_CODE_PROCESSING,
            )
        )
        resource_spans_list = get_resource_spans_list(trace_to_resource_spans, trace_id)
        assert resource_spans_list is not None
        send_email_notification(
            mailer,
            alert_user_to_email,
            trace_id,
            resource_spans_list,
        )
        trace_to_info[trace_id] = bytes(
            TraceInfo(
                last_seen=trace_info.last_seen,
                status=TRACE_INFO_STATUS_CODE_PROCESSED,
            )
        )
        del trace_to_resource_spans[trace_id]


def main() -> None:
    from_email = get_env_var_or_throw("FROM_EMAIL")
    from_email_password = get_env_var_or_throw("FROM_EMAIL_PASSWORD")
    execute_period_secs = int(get_env_var_or_throw("EXECUTE_PERIOD_SECS"))
    with open(get_env_var_or_throw("ALERT_USER_EMAILS"), "r") as f:
        alert_user_to_email: dict[str, str] = json.load(f)
    send_notif_time = timedelta(seconds=int(get_env_var_or_throw("SEND_NOTIF_SECS")))
    remove_trace_time = timedelta(
        seconds=int(get_env_var_or_throw("REMOVE_TRACE_SECS"))
    )
    with (
        Mailer(
            from_email=from_email, from_email_password=from_email_password
        ) as mailer,
        dbm.open(ERROR_TRACES_FILE, flag="c") as trace_to_resource_spans,
        dbm.open(TRACE_INFOS_FILE, flag="c") as trace_to_info,
    ):
        while True:
            trace_ids = trace_to_resource_spans.keys()
            logger.debug(
                f"Checking if any notifications need sending. There are {len(trace_ids)} traces stored"
            )
            for trace_id_bytes in trace_ids:
                trace_id = (
                    trace_id_bytes.decode()
                    if isinstance(trace_id_bytes, bytes)
                    else trace_id_bytes
                )
                try:
                    process_trace(
                        mailer,
                        trace_to_resource_spans,
                        trace_to_info,
                        alert_user_to_email,
                        send_notif_time,
                        remove_trace_time,
                        trace_id,
                    )
                except BaseException:
                    logger.exception(
                        f"Exception occurred while trying to process trace {trace_id}"
                    )

            sleep(execute_period_secs)


if __name__ == "__main__":
    main()
