import base64
import binascii
import hmac
import os
import re
from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional, Tuple

from flask import Flask

StartResponse = Callable[
    [str, List[Tuple[str, str]], Optional[tuple]],
    Callable,
]
WSGIApp = Callable[[dict, StartResponse], Iterable[bytes]]


@dataclass(frozen=True)
class BasicAuthConfig:
    username: str
    password: str
    realm: str = "ActivityWatch"


_PUBLIC_ROUTES = (
    ("GET", re.compile(r"^/api/0(?:/.*)?$")),
    ("HEAD", re.compile(r"^/api/0(?:/.*)?$")),
    ("POST", re.compile(r"^/api/0/buckets/[^/]+/?$")),
    ("POST", re.compile(r"^/api/0/buckets/[^/]+/heartbeat/?$")),
)


def load_basic_auth_config() -> Optional[BasicAuthConfig]:
    username = (os.getenv("AW_AUTH_USERNAME") or "").strip()
    password = os.getenv("AW_AUTH_PASSWORD") or ""
    if not username or not password:
        return None

    realm = (os.getenv("AW_AUTH_REALM") or "ActivityWatch").strip()
    return BasicAuthConfig(
        username=username,
        password=password,
        realm=realm or "ActivityWatch",
    )


def configure_basic_auth(app: Flask) -> Optional[BasicAuthConfig]:
    config = load_basic_auth_config()
    if config is not None:
        app.wsgi_app = BasicAuthMiddleware(app.wsgi_app, config)  # type: ignore[assignment]
    return config


class BasicAuthMiddleware:
    def __init__(self, app: WSGIApp, config: BasicAuthConfig) -> None:
        self.app = app
        self.config = config

    def __call__(self, environ: dict, start_response: StartResponse) -> Iterable[bytes]:
        method = (environ.get("REQUEST_METHOD") or "GET").upper()
        path = environ.get("PATH_INFO") or "/"
        authorization = environ.get("HTTP_AUTHORIZATION") or ""

        if _is_public_request(method, path) or _has_valid_basic_auth(
            authorization, self.config
        ):
            return self.app(environ, start_response)

        headers = [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("WWW-Authenticate", f'Basic realm="{self.config.realm}"'),
        ]
        start_response("401 Unauthorized", headers)
        return [b"Authentication required"]


def _is_public_request(method: str, path: str) -> bool:
    if method == "OPTIONS":
        return True

    for allowed_method, pattern in _PUBLIC_ROUTES:
        if method == allowed_method and pattern.match(path):
            return True
    return False


def _has_valid_basic_auth(authorization: str, config: BasicAuthConfig) -> bool:
    if not authorization.startswith("Basic "):
        return False

    try:
        decoded = base64.b64decode(authorization[6:].strip()).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return False

    username, separator, password = decoded.partition(":")
    if not separator:
        return False

    return hmac.compare_digest(username, config.username) and hmac.compare_digest(
        password, config.password
    )
