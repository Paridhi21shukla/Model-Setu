import os
import requests


RENDER_API_BASE = "https://api.render.com/v1"


class RenderAPIError(Exception):
    pass


def _get_config():
    api_key = os.getenv("RENDER_API_KEY")
    service_id = os.getenv("RENDER_SERVICE_ID")

    if not api_key or not service_id:
        raise RenderAPIError(
            "Render API credentials are not configured"
        )

    return api_key, service_id


def _request(method, path, **kwargs):
    api_key, _ = _get_config()

    headers = kwargs.pop("headers", {})
    headers.update({
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    })

    try:
        response = requests.request(
            method,
            f"{RENDER_API_BASE}{path}",
            headers=headers,
            timeout=20,
            **kwargs
        )
    except requests.RequestException as exc:
        raise RenderAPIError(
            f"Could not connect to Render: {exc}"
        ) from exc

    if not response.ok:
        raise RenderAPIError(
            f"Render API returned HTTP {response.status_code}"
        )

    return response.json() if response.content else {}


def list_service_deploys(limit=100):
    _, service_id = _get_config()

    result = _request(
        "GET",
        f"/services/{service_id}/deploys",
        params={"limit": limit}
    )

    return [
        item.get("deploy", item)
        for item in result
    ]


def get_service_deploy(deploy_id):
    _, service_id = _get_config()

    return _request(
        "GET",
        f"/services/{service_id}/deploys/{deploy_id}"
    )


def rollback_render_deploy(deploy_id):
    _, service_id = _get_config()

    return _request(
        "POST",
        f"/services/{service_id}/rollback",
        json={"deployId": deploy_id}
    )
