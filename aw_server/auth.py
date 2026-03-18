import base64
import binascii
import hmac
import os
import re
from dataclasses import dataclass

from flask import Flask, Response, Request, request


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


@dataclass(frozen=True)
class BasicAuthConfig:
    username: str
    password: str
    realm: str = "ActivityWatch"
    allow_unauthenticated_watcher_ingest: bool = True


_PUBLIC_API_ROUTES = (
    ("GET", re.compile(r"^/api/0(?:/.*)?$")),
    ("HEAD", re.compile(r"^/api/0(?:/.*)?$")),
    ("POST", re.compile(r"^/api/0/buckets/[^/]+/?$")),
    ("POST", re.compile(r"^/api/0/buckets/[^/]+/heartbeat/?$")),
)


def load_basic_auth_config() -> BasicAuthConfig | None:
    username = (os.getenv("AW_AUTH_USERNAME") or "").strip()
    password = os.getenv("AW_AUTH_PASSWORD") or ""
    if not username or not password:
        return None

    return BasicAuthConfig(
        username=username,
        password=password,
        realm=(os.getenv("AW_AUTH_REALM") or "ActivityWatch").strip()
        or "ActivityWatch",
        allow_unauthenticated_watcher_ingest=_env_flag(
            "AW_AUTH_ALLOW_WATCHER_INGEST", True
        ),
    )


def register_basic_auth(app: Flask, config: BasicAuthConfig) -> None:
    @app.before_request
    def _require_basic_auth():
        if _is_request_exempt(request, config):
            return None
        if _has_valid_basic_auth(request, config):
            return None
        return _build_auth_challenge(config)


def _is_request_exempt(req: Request, config: BasicAuthConfig) -> bool:
    if req.method == "OPTIONS":
        return True

    if not config.allow_unauthenticated_watcher_ingest:
        return False

    for method, pattern in _PUBLIC_API_ROUTES:
        if req.method == method and pattern.match(req.path):
            return True
    return False


def _has_valid_basic_auth(req: Request, config: BasicAuthConfig) -> bool:
    authorization = req.headers.get("Authorization", "")
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


def _build_auth_challenge(config: BasicAuthConfig) -> Response:
    response = Response("Authentication required", 401)
    response.headers["WWW-Authenticate"] = f'Basic realm="{config.realm}"'
    return response
