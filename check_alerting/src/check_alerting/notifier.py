import ast
import dbm
import json
import logging
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import Message
from email.mime.text import MIMEText
from time import sleep

from opentelemetry_betterproto.opentelemetry.proto.common.v1 import AnyValue
from opentelemetry_betterproto.opentelemetry.proto.trace.v1 import ResourceSpans

from check_alerting.common import (
    ERROR_TRACES_FILE,
    TRACE_INFO_STATUS_CODE_ERROR,
    TRACE_INFO_STATUS_CODE_PROCESSED,
    TRACE_INFO_STATUS_CODE_PROCESSING,
    TRACE_INFOS_FILE,
    MutableMappingBytes,
    get_int_env_var_or_default,
    get_int_env_var_or_throw,
    get_resource_spans_list,
    get_str_env_var_or_default,
    get_str_env_var_or_throw,
    get_trace_info,
)
from check_alerting.proto import TraceInfo, TraceInfoStatusCode

logger = logging.getLogger(name="notifier")
# based on https://stackoverflow.com/a/76026506
logging.basicConfig(
    level=get_str_env_var_or_default("NOTIFIER_LOG_LEVEL", "INFO").upper()
)


class Mailer:
    def __init__(
        self,
        email_counters: MutableMappingBytes,
        max_emails_per_day: int,
        host: str,
        port: int,
        from_email: str,
        from_email_password: str,
    ) -> None:
        self._email_counters = email_counters
        self._max_emails_per_day = max_emails_per_day
        self._host = host
        self._port = port
        self._from_email = from_email
        self._from_email_password = from_email_password

    def send_email(self, to_email: str, subject: str, message: Message) -> bool:
        # For now create a new connection for sending every email
        # to avoid connection timeout problem like here
        # https://stackoverflow.com/questions/49203706/is-there-a-way-to-prevent-smtp-connection-timeout-smtplib-python
        with smtplib.SMTP_SSL(
            host=self._host, port=self._port, context=ssl.create_default_context()
        ) as smtp:
            smtp.login(user=self._from_email, password=self._from_email_password)
            """returns if the email was sent successfully"""
            message["From"] = self._from_email
            message["To"] = to_email
            message["Subject"] = subject

            today = str(datetime.now().date())
            day_count_bytes = self._email_counters.get("day_count")
            day_count: tuple[str, int] = (
                (today, 0)
                if day_count_bytes is None
                else ast.literal_eval(day_count_bytes.decode())
            )
            (day, count) = day_count
            if day == today and count >= self._max_emails_per_day:
                logger.warning(
                    f"Not sending email as daily limit of {self._max_emails_per_day} is reached"
                )
                return False
            next_count = count + 1 if day == today else 1
            self._email_counters["day_count"] = bytes(
                str((today, next_count)), encoding="utf-8"
            )
            smtp.sendmail(
                from_addr=self._from_email, to_addrs=[to_email], msg=message.as_string()
            )
            return True

    # def __enter__(self) -> Self:
    #     self._smtp.__enter__()
    #     return self

    # def __exit__(
    #     self,
    #     exc_type: type[BaseException] | None,
    #     exc_value: BaseException | None,
    #     tb: TracebackType | None,
    # ) -> None:
    #     self._smtp.__exit__(exc_type, exc_value, tb)


def get_string_attribute_value(attributes: dict[str, AnyValue], key: str) -> str | None:
    value_any = attributes.get(key, None)
    return None if value_any is None else value_any.string_value


def send_email_notification(
    mailer: Mailer,
    alert_user_to_email: dict[str, str],
    trace_id: str,
    resource_spans_list: list[ResourceSpans],
) -> None:
    user_id: str | None = None
    health_check_name: str | None = None
    for resource_spans in resource_spans_list:
        resource_attributes: dict[str, AnyValue] = dict(
            (attr.key, attr.value) for attr in resource_spans.resource.attributes
        )
        cur_user_id = get_string_attribute_value(resource_attributes, "user.id")
        if user_id is None and cur_user_id is not None:
            user_id = cur_user_id
        elif user_id != cur_user_id:
            logger.error(
                f"Trace {trace_id} specifies distinct user ids '{user_id}' and '{cur_user_id}'"
            )

        cur_health_check_name = get_string_attribute_value(
            resource_attributes, "health_check.name"
        )
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

    if mailer.send_email(
        to_email=to_email,
        subject="Health Check Failed",
        message=MIMEText(message_text),
    ):
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
        trace_info.status == TraceInfoStatusCode.RECEIVING
        and trace_info.last_seen + send_notif_time < now
    ):
        try:
            trace_to_info[trace_id] = bytes(
                TraceInfo(
                    last_seen=trace_info.last_seen,
                    status=TRACE_INFO_STATUS_CODE_PROCESSING,
                )
            )
            resource_spans_list = get_resource_spans_list(
                trace_to_resource_spans, trace_id
            )
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
        except:
            trace_to_info[trace_id] = bytes(
                TraceInfo(
                    last_seen=trace_info.last_seen,
                    status=TRACE_INFO_STATUS_CODE_ERROR,
                )
            )
            raise
        finally:
            del trace_to_resource_spans[trace_id]
        return
    if trace_info.last_seen + remove_trace_time < now:
        del trace_to_info[trace_id]
        if trace_id in trace_to_resource_spans:
            logger.warning(
                f"Trace {trace_id} is still present in the database after {remove_trace_time} from receiving it. It has status {trace_info.status.name}."
            )
            del trace_to_resource_spans[trace_id]
        return


def main() -> None:
    logger.info("starting")
    email_counters_file = get_str_env_var_or_default(
        "EMAIL_COUNTERS", "email_counters.sqlite3"
    )
    max_emails_per_day = get_int_env_var_or_throw("MAX_EMAILS_PER_DAY")
    smtp_mailer_host = get_str_env_var_or_throw("SMTP_MAILER_HOST")
    smtp_mailer_port = get_int_env_var_or_default("SMTP_MAILER_PORT", 465)
    from_email = get_str_env_var_or_throw("FROM_EMAIL")
    from_email_password = get_str_env_var_or_throw("FROM_EMAIL_PASSWORD")
    execute_period_secs = get_int_env_var_or_default("EXECUTE_PERIOD_SECS", 10)
    alert_user_emails_file = get_str_env_var_or_default(
        "ALERT_USER_EMAILS", "alert_user_emails.json"
    )
    with open(alert_user_emails_file, "r") as f:
        alert_user_to_email: dict[str, str] = json.load(f)
    send_notif_time = timedelta(
        seconds=get_int_env_var_or_default("SEND_NOTIF_SECS", 60)
    )
    remove_trace_time = timedelta(
        seconds=get_int_env_var_or_default("REMOVE_TRACE_SECS", 600)
    )
    with (
        dbm.open(email_counters_file, flag="c") as email_counters,
        dbm.open(ERROR_TRACES_FILE, flag="c") as trace_to_resource_spans,
        dbm.open(TRACE_INFOS_FILE, flag="c") as trace_to_info,
    ):
        mailer = Mailer(
            email_counters=email_counters,
            max_emails_per_day=max_emails_per_day,
            host=smtp_mailer_host,
            port=smtp_mailer_port,
            from_email=from_email,
            from_email_password=from_email_password,
        )
        logger.info("initialization done")
        while True:
            trace_ids = trace_to_info.keys()
            logger.debug(
                f"Checking if any notifications need sending. There are {len(trace_to_resource_spans)} traces stored, and {len(trace_to_info)} trace infos stored"
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
