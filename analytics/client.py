"""Read the analytics API, either over HTTP or in-process.

``train_models --api-url http://host:8000 --token ...`` reads a running
server over HTTP. Without ``--api-url`` the same API views are called
in-process, so training still goes through the API layer.
"""

import json
import urllib.parse
import urllib.request

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import resolve


class APIError(Exception):
    pass


def fetch(path, params=None, api_url=None, token=None):
    params = params or {}
    if api_url:
        url = api_url.rstrip("/") + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Token {token}"
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode())
        except Exception as exc:
            raise APIError(f"GET {url} failed: {exc}") from exc

    request = RequestFactory().get(path, params)
    request.user = AnonymousUser()
    request._analytics_internal = True
    match = resolve(path)
    response = match.func(request, *match.args, **match.kwargs)
    if response.status_code != 200:
        raise APIError(f"GET {path} returned {response.status_code}: {response.content[:200]!r}")
    return json.loads(response.content)
