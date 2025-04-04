from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.api_client import ApiClient
from kubernetes_asyncio.client.rest import ApiException
from kubernetes_asyncio.client.configuration import Configuration

NAMESPACE: str = "resource-health"


def get_username(tokens):
    username = None
    if tokens is None:
        return username
    if "preferred_username" in tokens["id"].decoded:
        username = tokens["id"].decoded["preferred_username"]
    return username


async def get_userinfo(tokens, configuration):
    userinfo = {}
    if tokens is None:
        return userinfo
    if "preferred_username" in tokens["id"].decoded:
        username = tokens["id"].decoded["preferred_username"]
        userinfo["username"] = username

        async with ApiClient(configuration) as api_client:
            api_instance = client.CoreV1Api(api_client)
            api_response = None
            try:
                api_response = await api_instance.read_namespaced_secret(
                    namespace=NAMESPACE,
                    name=f"resource-health-{username}-offline-secret",
                )
            except ApiException:
                print("Could not find secret.")
            except Exception as e:
                raise e
            # if api_response is None:
            #     try:
            #         api_response = await api_instance.create_namespaced_secret(
            #             namespace=NAMESPACE,
            #             name=f"resource-health-{username}-offline-secret",
            #         )
            #     except Exception as e:
            #         raise e

    return userinfo


# def on_auth(auth_obj):


async def default_configuration(auth):
    await config.load_config()
    configuration = Configuration.get_default_copy()
    return configuration


def get_namespace(auth):
    return NAMESPACE


def template_access(auth, template_id):
    # username = get_username(auth)
    # if username == "bob" and template_id == "default_k8s_template":
    #     return False
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
