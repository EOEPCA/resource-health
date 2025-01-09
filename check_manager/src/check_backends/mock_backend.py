from collections import defaultdict
from typing import (
    Any,
    AsyncIterable,
    Final,
    Literal,
    NewType,
    Self,
    Type,
    assert_never,
    override,
)
import uuid
from jsonschema import validate

from api_interface import Json
from check_backends.check_backend import (
    AuthenticationObject,
    CronExpression,
    CheckBackend,
    Check,
    CheckId,
    CheckTemplate,
    CheckTemplateId,
)
from exceptions import (
    CheckException,
    CheckInternalError,
    CheckTemplateIdError,
    CheckIdError,
    CheckIdNonUniqueError,
)


class MockBackend(CheckBackend):
    def __init__(self: Self, template_id_prefix: str = "") -> None:
        check_templates = [
            CheckTemplate(
                id=CheckTemplateId(template_id_prefix + "check_template1"),
                metadata={
                    "label": "Dummy check template",
                    "description": "Dummy check template description",
                },
                arguments={
                    "$schema": "http://json-schema.org/draft-07/schema",
                    "type": "object",
                    "properties": {
                        "health_check.name": {"type": "string"},
                        "script": {"type": "string", "format": "textarea"},
                        "requirements": {
                            "type": "string",
                            "format": "textarea"
                        },
                    },
                    "required": ["health_check.name", "script"],
                },
            )
        ]
        self._check_template_id_to_template: dict[CheckTemplateId, CheckTemplate] = {
            template.id: template for template in check_templates
        }
        self._auth_to_id_to_check: defaultdict[
            AuthenticationObject, dict[CheckId, Check]
        ] = defaultdict(dict)

    @override
    async def aclose(self: Self) -> None:
        pass

    def _get_check_template(self: Self, template_id: CheckTemplateId) -> CheckTemplate:
        if template_id not in self._check_template_id_to_template:
            raise CheckTemplateIdError(template_id)
        return self._check_template_id_to_template[template_id]

    def _get_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> Check:
        id_to_check = self._auth_to_id_to_check[auth_obj]
        if check_id not in id_to_check:
            raise CheckIdError(f"Check id {check_id} not found")
        return id_to_check[check_id]

    @override
    async def list_check_templates(
        self: Self,
        ids: list[CheckTemplateId] | None = None,
    ) -> AsyncIterable[CheckTemplate]:
        if ids is None:
            for template in self._check_template_id_to_template.values():
                yield template
        else:
            for id in ids:
                if id in self._check_template_id_to_template:
                    yield self._check_template_id_to_template[id]

    @override
    async def new_check(
        self: Self,
        auth_obj: AuthenticationObject,
        template_id: CheckTemplateId,
        template_args: Json,
        schedule: CronExpression,
    ) -> Check:
        check_template = self._get_check_template(template_id)
        validate(template_args, check_template.arguments)
        check_id = CheckId(str(uuid.uuid4()))
        check = Check(
            id=check_id,
            metadata={"template_id": template_id, "template_args": template_args},
            schedule=schedule,
            # Just return some filter which I know will have some results
            outcome_filter={"resource_attributes": {"k8s.cronjob.name": "resource-health-healthchecks-cronjob-3"}},
        )
        self._auth_to_id_to_check[auth_obj][check_id] = check
        return check

    @override
    async def update_check(
        self: Self,
        auth_obj: AuthenticationObject,
        check_id: CheckId,
        template_id: CheckTemplateId | None = None,
        template_args: Json | None = None,
        schedule: CronExpression | None = None,
    ) -> Check:
        check = self._get_check(auth_obj, check_id)
        if template_id is not None:
            check.metadata["template_id"] = template_id
        if template_args is not None:
            check.metadata["template_args"] = template_args
        # TODO: check check if template_args and check_template are compatible
        if schedule is not None:
            check.schedule = schedule
        return check

    @override
    async def remove_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> None:
        id_to_check = self._auth_to_id_to_check[auth_obj]
        if check_id not in id_to_check:
            raise CheckIdError(f"Check id {check_id} not found")
        id_to_check.pop(check_id)

    @override
    async def list_checks(
        self: Self,
        auth_obj: AuthenticationObject,
        ids: list[CheckId] | None = None,
    ) -> AsyncIterable[Check]:
        if ids is None:
            for check in self._auth_to_id_to_check[auth_obj].values():
                yield check
        else:
            for id in ids:
                yield self._get_check(auth_obj, id)
