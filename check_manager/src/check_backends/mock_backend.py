from collections import defaultdict
import re
from typing import AsyncIterable, Self, override, TypeVar, Callable
import uuid
import os
from jsonschema import ValidationError, validate

from plugin_utils.runner import call_hooks_until_not_none
from check_backends.check_backend import (
    CheckIdError,
    CheckTemplate,
    CheckTemplateIdError,
    CheckTemplateMetadata,
    CronExpression,
    CheckBackend,
    CheckId,
    InCheckAttributes,
    OutCheck,
    OutCheckMetadata,
    OutCheckAttributes,
    CheckTemplateId,
    CheckTemplateAttributes,
    OutcomeFilter,
)
from exceptions import CronExpressionValidationError, JsonValidationError

AuthenticationObject = TypeVar("AuthenticationObject")

MOCK_USERNAME = os.environ.get("RH_CHECK_MOCK_USERNAME") or "eric"
GET_MOCK_USERNAME_HOOK_NAME = (
    os.environ.get("RH_CHECK_GET_MOCK_USERNAME_HOOK_NAME") or "get_mock_username"
)

# copied from K8s_backend
# this is not moved to a common location, as at least in principle different backend could
# support (slightly) different cron expressions
minute_pattern = r"(\*|[0-5]?\d)(/\d+)?([-,][0-5]?\d)*"
hour_pattern = r"(\*|[01]?\d|2[0-3])(/\d+)?([-,]([01]?\d|2[0-3]))*"
day_of_month_pattern = r"(\*|[1-9]|[12]\d|3[01])(/\d+)?([-,]([1-9]|[12]\d|3[01]))*"
month_pattern = r"(\*|1[0-2]|0?[1-9])(/\d+)?([-,](1[0-2]|0?[1-9]))*"
day_of_week_pattern = r"(\*|[0-7])(/\d+)?([-,][0-7])*"

cron_pattern = " ".join(
    [
        minute_pattern,
        hour_pattern,
        day_of_month_pattern,
        month_pattern,
        day_of_week_pattern,
    ]
)


def validate_kubernetes_cron(cron_expr: str) -> None:
    if not re.match(cron_pattern, cron_expr):
        raise CronExpressionValidationError("Invalid cron expression")


class MockBackend(CheckBackend[AuthenticationObject]):
    def __init__(
        self: Self,
        template_id_prefix: str = "",
        *,
        hooks: dict[str, list[Callable]],
    ) -> None:
        self._hooks = hooks

        check_templates = [
            (
                CheckTemplateId(template_id_prefix + "check_template1"),
                CheckTemplateAttributes(
                    metadata=CheckTemplateMetadata(
                        label="Dummy check template",
                        description="Dummy check template description",
                    ),
                    arguments={
                        "$schema": "http://json-schema.org/draft-07/schema",
                        "type": "object",
                        "properties": {
                            "script": {"type": "string", "format": "textarea"},
                            "requirements": {"type": "string", "format": "textarea"},
                        },
                        "required": ["script"],
                    },
                ),
            )
        ]
        self._check_template_id_to_attributes: dict[
            CheckTemplateId, CheckTemplateAttributes
        ] = {template_id: attributes for template_id, attributes in check_templates}
        # metadata={
        #     "template": "remote_check_template1",
        #     "template_args": {
        #         "health_check.name": "Simple Health Check",
        #         "script": "Dummy Script",
        #     },
        # },
        checks = [
            (
                CheckId("check_id_1_iuhwqed7"),
                OutCheckAttributes(
                    metadata=OutCheckMetadata(
                        name="Simple Health Check",
                        template_id=CheckTemplateId("remote_check_template1"),
                        template_args={"script": "Dummy Script"},
                    ),
                    schedule=CronExpression("* * * * *"),
                    outcome_filter=OutcomeFilter(
                        resource_attributes={"resource.foo": ["bar"]}
                    ),
                ),
            )
        ]
        self._auth_to_check_id_to_attributes: defaultdict[
            str, dict[CheckId, OutCheckAttributes]
        ] = defaultdict(dict)
        self._auth_to_check_id_to_attributes[MOCK_USERNAME] = dict(checks)
        # self._auth_to_check_id_to_attributes["unauthorized_user"] = dict(checks)

    @override
    async def aclose(self: Self) -> None:
        pass

    def _get_check_template_attributes(
        self: Self,
        template_id: CheckTemplateId,
    ) -> CheckTemplateAttributes | None:
        if template_id not in self._check_template_id_to_attributes:
            return None
        return self._check_template_id_to_attributes[template_id]

    async def _get_check_attributes(
        self: Self,
        auth_obj: AuthenticationObject,
        check_id: CheckId,
    ) -> OutCheckAttributes | None:
        if GET_MOCK_USERNAME_HOOK_NAME not in self._hooks:
            raise ValueError(
                f"Must set hook {GET_MOCK_USERNAME_HOOK_NAME} ($GET_MOCK_USERNAME_HOOK_NAME) when using the mock backend"
            )

        username = await call_hooks_until_not_none(
            self._hooks[GET_MOCK_USERNAME_HOOK_NAME], auth_obj
        )

        check_id_to_attributes = self._auth_to_check_id_to_attributes[username]
        if check_id not in check_id_to_attributes:
            return None
        return check_id_to_attributes[check_id]

    @override
    async def get_check_templates(
        self: Self,
        auth_obj: AuthenticationObject,
        ids: list[CheckTemplateId] | None = None,
    ) -> AsyncIterable[CheckTemplate]:
        if ids is None:
            for (
                template_id,
                attributes,
            ) in self._check_template_id_to_attributes.items():
                yield CheckTemplate(id=template_id, attributes=attributes)
        else:
            for template_id in ids:
                template_attributes = self._get_check_template_attributes(template_id)
                if template_attributes is not None:
                    yield CheckTemplate(id=template_id, attributes=template_attributes)

    @override
    async def create_check(
        self: Self, auth_obj: AuthenticationObject, attributes: InCheckAttributes
    ) -> OutCheck:
        if GET_MOCK_USERNAME_HOOK_NAME not in self._hooks:
            raise ValueError(
                f"Must set hook {GET_MOCK_USERNAME_HOOK_NAME} ($GET_MOCK_USERNAME_HOOK_NAME) when using the mock backend"
            )

        username = await call_hooks_until_not_none(
            self._hooks[GET_MOCK_USERNAME_HOOK_NAME], auth_obj
        )

        validate_kubernetes_cron(attributes.schedule)

        check_template_attributes = self._get_check_template_attributes(
            attributes.metadata.template_id
        )
        if check_template_attributes is None:
            raise CheckTemplateIdError(attributes.metadata.template_id)
        try:
            validate(
                attributes.metadata.template_args, check_template_attributes.arguments
            )
        except ValidationError as e:
            raise JsonValidationError("/data/attributes/metadata/template_args/", e)

        check_id = CheckId(str(uuid.uuid4()))
        out_attributes = OutCheckAttributes(
            metadata=OutCheckMetadata(
                name=attributes.metadata.name,
                description=attributes.metadata.description,
                template_id=attributes.metadata.template_id,
                template_args=attributes.metadata.template_args,
            ),
            schedule=attributes.schedule,
            # Just return some filter which I know will have some results
            outcome_filter=OutcomeFilter(
                resource_attributes={
                    "k8s.cronjob.name": ["resource-health-healthchecks-cronjob-3"]
                }
            ),
        )
        self._auth_to_check_id_to_attributes[username][check_id] = out_attributes
        return OutCheck(id=check_id, attributes=out_attributes)

    # @override
    # async def update_check(
    #     self: Self,
    #     auth_obj: AuthenticationObject,
    #     check_id: CheckId,
    #     template_id: CheckTemplateId | None = None,
    #     template_args: Json | None = None,
    #     schedule: CronExpression | None = None,
    # ) -> Check:
    #     check = self._get_check(auth_obj, check_id)
    #     if template_id is not None:
    #         check.metadata["template_id"] = template_id
    #     if template_args is not None:
    #         check.metadata["template_args"] = template_args
    #     # TODO: check check if template_args and check_template are compatible
    #     if schedule is not None:
    #         check.schedule = schedule
    #     return check

    @override
    async def remove_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> None:
        username = await call_hooks_until_not_none(
            self._hooks[GET_MOCK_USERNAME_HOOK_NAME], auth_obj
        )
        id_to_check = self._auth_to_check_id_to_attributes[username]
        if check_id not in id_to_check:
            raise CheckIdError(check_id)
        id_to_check.pop(check_id)

    @override
    async def get_checks(
        self: Self,
        auth_obj: AuthenticationObject,
        ids: list[CheckId] | None = None,
    ) -> AsyncIterable[OutCheck]:
        if GET_MOCK_USERNAME_HOOK_NAME not in self._hooks:
            raise ValueError(
                f"Must set hook {GET_MOCK_USERNAME_HOOK_NAME} ($GET_MOCK_USERNAME_HOOK_NAME) when using the mock backend"
            )

        username = await call_hooks_until_not_none(
            self._hooks[GET_MOCK_USERNAME_HOOK_NAME], auth_obj
        )

        if ids is None:
            for check_id, attributes in self._auth_to_check_id_to_attributes[
                username
            ].items():
                yield OutCheck(id=check_id, attributes=attributes)
        else:
            for id in ids:
                check_attributes = await self._get_check_attributes(auth_obj, id)
                if check_attributes is not None:
                    yield OutCheck(id=id, attributes=check_attributes)

    @override
    async def run_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> None:
        if GET_MOCK_USERNAME_HOOK_NAME not in self._hooks:
            raise ValueError(
                f"Must set hook {GET_MOCK_USERNAME_HOOK_NAME} ($GET_MOCK_USERNAME_HOOK_NAME) when using the mock backend"
            )

        username = await call_hooks_until_not_none(
            self._hooks[GET_MOCK_USERNAME_HOOK_NAME], auth_obj
        )

        id_to_check = self._auth_to_check_id_to_attributes[username]
        if check_id not in id_to_check:
            raise CheckIdError(check_id)
