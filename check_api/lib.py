from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Iterable, NewType, Self
import uuid
from jsonschema import validate
from pydantic import BaseModel
from referencing.jsonschema import Schema

AuthenticationObject = NewType("AuthenticationObject", str)
CronExpression = NewType("CronExpression", str)
CheckTemplateId = NewType("CheckTemplateId", str)
CheckId = NewType("CheckId", str)
type Json = dict[str, "Json"] | list["Json"] | str | int | float | bool | None
# type JsonSchema = dict[str, "JsonSchema"] | list["JsonSchema"] | str


class NotFoundException(Exception):
    pass


class CheckTemplate(BaseModel):
    id: CheckTemplateId
    # SHOULD contain { 'label' : str, 'description' : str }
    metadata: dict[str, Json]
    arguments: Schema


class Check(BaseModel):
    id: CheckId
    # SHOULD contain { 'label' : str, 'description' : str }, MAY contain { 'template': CheckTemplate, 'template_args': Json }
    metadata: dict[str, Json]
    schedule: CronExpression

    # Conditions to determine which spans belong to this check outcome
    outcome_filter: Json
    ## NOTE: For now the above can just be a set of equality conditions on Span/Resource attributes


# Inherit from this class and implement the abstract methods for each new backend
class CheckBackend(ABC):
    def __init__(self: Self, check_templates: list[CheckTemplate]) -> None:
        self.check_template_id_to_template: dict[CheckTemplateId, CheckTemplate] = {
            template.id: template for template in check_templates
        }

    def _get_check_template(self: Self, template_id: CheckTemplateId) -> CheckTemplate:
        if template_id not in self.check_template_id_to_template:
            raise NotFoundException(f"Template id {template_id} not found")
        return self.check_template_id_to_template[template_id]

    def list_check_templates(
        self: Self,
        ids: list[CheckTemplateId] | None = None,
    ) -> Iterable[CheckTemplate]:
        if ids is None:
            return self.check_template_id_to_template.values()
        return [self._get_check_template(id) for id in ids]

    @abstractmethod
    def new_check(
        self: Self,
        auth_obj: AuthenticationObject,
        template_id: CheckTemplateId,
        template_args: Json,
        schedule: CronExpression,
    ) -> CheckId:
        pass

    @abstractmethod
    def update_check(
        self: Self,
        auth_obj: AuthenticationObject,
        check_id: CheckId,
        template_id: CheckTemplateId | None = None,
        template_args: Json = None,
        schedule: CronExpression | None = None,
    ) -> None:
        pass

    @abstractmethod
    def remove_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> None:
        pass

    @abstractmethod
    def list_checks(self: Self, auth_obj: AuthenticationObject) -> Iterable[Check]:
        pass


class MockBackend(CheckBackend):
    def __init__(self: Self) -> None:
        super().__init__(
            [
                CheckTemplate(
                    id=CheckTemplateId("check_template1"),
                    metadata={
                        "label": "Dummy check template",
                        "description": "Dummy check template description",
                    },
                    arguments={
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "title": "Bla",
                        "description": "Bla bla",
                        # TODO: continue this
                        # "type": "object",
                        # "properties": "",
                    },
                )
            ]
        )
        self._auth_to_id_to_check: defaultdict[
            AuthenticationObject, dict[CheckId, Check]
        ] = defaultdict(dict)

    def _get_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> Check:
        id_to_check = self._auth_to_id_to_check[auth_obj]
        if check_id not in id_to_check:
            raise NotFoundException(f"Check id {check_id} not found")
        return id_to_check[check_id]

    def new_check(
        self: Self,
        auth_obj: AuthenticationObject,
        template_id: CheckTemplateId,
        template_args: Json,
        schedule: CronExpression,
    ) -> CheckId:
        check_template = self._get_check_template(template_id)
        validate(template_args, check_template.arguments)
        check_id = CheckId(str(uuid.uuid4()))
        self._auth_to_id_to_check[auth_obj][check_id] = Check(
            id=check_id,
            metadata={"template_id": template_id, "template_args": template_args},
            schedule=schedule,
            outcome_filter={"test.id": check_id},
        )
        return check_id

    def update_check(
        self: Self,
        auth_obj: AuthenticationObject,
        check_id: CheckId,
        template_id: CheckTemplateId | None = None,
        template_args: Json = None,
        schedule: CronExpression | None = None,
    ) -> None:
        check = self._get_check(auth_obj, check_id)
        if template_id is not None:
            check.metadata["template_id"] = template_id
        if template_args is not None:
            check.metadata["template_args"] = template_args
        # TODO: check check if template_args and check_template are compatible
        if schedule is not None:
            check.schedule = schedule

    def remove_check(
        self: Self, auth_obj: AuthenticationObject, check_id: CheckId
    ) -> None:
        id_to_check = self._auth_to_id_to_check[auth_obj]
        if check_id not in id_to_check:
            raise NotFoundException(f"Check id {check_id} not found")
        id_to_check.pop(check_id)

    def list_checks(self: Self, auth_obj: AuthenticationObject) -> Iterable[Check]:
        return self._auth_to_id_to_check[auth_obj].values()
