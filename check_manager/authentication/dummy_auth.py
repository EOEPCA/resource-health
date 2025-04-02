from kubernetes_asyncio import config
from kubernetes_asyncio.client.api_client import ApiClient

NAMESPACE: str = "resource-health"


def get_username(tokens):
    if tokens is None:
        username = "unauthorised person"
    elif "preferred_username" in tokens["id"].decoded:
        username = tokens["id"].decoded["preferred_username"]
    else:
        username = "mysterious stranger"
    return username


# def on_auth(auth_obj):


async def default_client(auth):
    await config.load_config()
    return ApiClient


def get_namespace(auth):
    return NAMESPACE


def template_access(auth, template_id):
    username = get_username(auth)
    if username == "bob" and template_id == "default_k8s_template":
        return False
    return True


def cronjob_access(auth, cronjob):
    username = get_username(auth)
    if cronjob.metadata.annotations.get("owner") == username:
        return True
    return False


def tag_cronjob(auth, cronjob):
    username = get_username(auth)
    cronjob.metadata.annotations["owner"] = username
    return cronjob


# def get_check_templates_client(auth):


# def create_check_client(auth):


# def remove_check_client(auth):


# def run_check_client(auth):


# def get_checks_client(auth):
