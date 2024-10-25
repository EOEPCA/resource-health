from collections import defaultdict
from typing import Annotated, Iterable, NewType
import uuid
from fastapi import FastAPI, HTTPException, Query
from jsonschema import validate
from referencing.jsonschema import Schema
from pydantic import BaseModel

AuthenticationObject = NewType("AuthenticationObject", str)
CronExpression = NewType("CronExpression", str)
CheckTemplateId = NewType("CheckTemplateId", str)
CheckId = NewType("CheckId", str)
type Json = dict[str, "Json"] | list["Json"] | str | int | float | bool | None
type JsonSchema = dict[str, "JsonSchema"] | list["JsonSchema"] | str


app = FastAPI()


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


def _get_check_templates() -> list[CheckTemplate]:
    return [
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


def _get_check_template(template_id: CheckTemplateId) -> CheckTemplate:
    if template_id not in check_template_id_to_template:
        raise HTTPException(
            status_code=404, detail=f"Template id {template_id} not found"
        )
    return check_template_id_to_template[template_id]


def _get_check(auth_obj: AuthenticationObject, check_id: CheckId) -> Check:
    id_to_check = auth_to_id_to_check[auth_obj]
    if check_id not in id_to_check:
        raise HTTPException(status_code=404, detail=f"Check id {check_id} not found")
    return id_to_check[check_id]


check_template_id_to_template: dict[CheckTemplateId, CheckTemplate] = {
    template.id: template for template in _get_check_templates()
}

auth_to_id_to_check: defaultdict[AuthenticationObject, dict[CheckId, Check]] = (
    defaultdict(dict)
)


@app.get("/check_templates/")
## filter: conditions to filter on Metadata
def list_check_templates(
    ids: Annotated[
        list[CheckTemplateId] | None, Query(description="restrict IDs to include")
    ] = None,
) -> Iterable[CheckTemplate]:
    if ids is None:
        return check_template_id_to_template.values()
    return [check_template_id_to_template[id] for id in ids]


@app.post("/checks")
def new_check(
    auth_obj: AuthenticationObject,
    template_id: CheckTemplateId,
    template_args: Json,
    schedule: CronExpression,
) -> CheckId:  # Optional? or raise exception?
    check_template = _get_check_template(template_id)
    validate(template_args, check_template.arguments)
    check_id = CheckId(str(uuid.uuid4()))
    auth_to_id_to_check[auth_obj][check_id] = Check(
        id=check_id,
        metadata={"template_id": template_id, "template_args": template_args},
        schedule=schedule,
        outcome_filter={"test.id": check_id},
    )
    return check_id


@app.patch("/checks/{check_id}")
def update_check(
    auth_obj: AuthenticationObject,
    check_id: CheckId,
    template_id: CheckTemplateId | None = None,
    template_args: Json = None,
    schedule: CronExpression | None = None,
) -> None:
    check = _get_check(auth_obj, check_id)
    if template_id is not None:
        check.metadata["template_id"] = template_id
    if template_args is not None:
        check.metadata["template_args"] = template_args
    # TODO: check check if template_args and check_template are compatible
    if schedule is not None:
        check.schedule = schedule


@app.delete("/checks/{check_id}")
def remove_check(auth_obj: AuthenticationObject, check_id: CheckId) -> None:
    id_to_check = auth_to_id_to_check[auth_obj]
    if check_id not in id_to_check:
        raise HTTPException(status_code=404, detail=f"Check id {check_id} not found")
    id_to_check.pop(check_id)


@app.get("/checks/")
def list_checks(auth_obj: AuthenticationObject) -> Iterable[Check]:
    return auth_to_id_to_check[auth_obj].values()
