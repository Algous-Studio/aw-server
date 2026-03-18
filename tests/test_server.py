import base64
import random
from datetime import datetime, timedelta

import pytest
from aw_server.auth import configure_basic_auth
from aw_server.server import AWFlask


def _basic_auth_headers(username: str, password: str):
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


@pytest.fixture()
def bucket(flask_client):
    "Context manager for creating and deleting a testing bucket"
    try:
        bucket_id = "test"
        r = flask_client.post(
            f"/api/0/buckets/{bucket_id}",
            json={"client": "test", "type": "test", "hostname": "test"},
        )
        assert r.status_code == 200
        yield bucket_id
    finally:
        r = flask_client.delete(f"/api/0/buckets/{bucket_id}")
        assert r.status_code == 200


def test_info(flask_client):
    r = flask_client.get("/api/0/info")
    assert r.status_code == 200
    assert r.json["testing"]


def test_basic_auth_protects_ui_and_mutating_api(monkeypatch):
    monkeypatch.setenv("AW_AUTH_USERNAME", "admin")
    monkeypatch.setenv("AW_AUTH_PASSWORD", "secret")

    app = AWFlask("127.0.0.1", testing=True)
    configure_basic_auth(app)
    client = app.test_client()
    bucket_id = "test-auth-bucket"

    r = client.get("/")
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"] == 'Basic realm="ActivityWatch"'

    r = client.get("/api/")
    assert r.status_code == 401

    r = client.post(
        f"/api/0/buckets/{bucket_id}",
        json={"client": "test", "type": "test", "hostname": "test"},
    )
    assert r.status_code == 200

    r = client.delete(f"/api/0/buckets/{bucket_id}")
    assert r.status_code == 401

    r = client.delete(
        f"/api/0/buckets/{bucket_id}",
        headers=_basic_auth_headers("admin", "secret"),
    )
    assert r.status_code == 200


def test_basic_auth_keeps_read_api_and_watcher_ingest_public(monkeypatch):
    monkeypatch.setenv("AW_AUTH_USERNAME", "admin")
    monkeypatch.setenv("AW_AUTH_PASSWORD", "secret")

    app = AWFlask("127.0.0.1", testing=True)
    configure_basic_auth(app)
    client = app.test_client()
    bucket_id = "test-auth-public"

    r = client.get("/api/0/info")
    assert r.status_code == 200

    r = client.post(
        f"/api/0/buckets/{bucket_id}",
        json={"client": "test", "type": "test", "hostname": "test"},
    )
    assert r.status_code == 200

    r = client.post(
        f"/api/0/buckets/{bucket_id}/heartbeat?pulsetime=1",
        json={"timestamp": datetime.now(), "duration": 0, "data": {"random": 1}},
    )
    assert r.status_code == 200

    r = client.get("/api/0/buckets/")
    assert r.status_code == 200

    r = client.get(f"/api/0/buckets/{bucket_id}/events")
    assert r.status_code == 200

    r = client.delete(
        f"/api/0/buckets/{bucket_id}",
        headers=_basic_auth_headers("admin", "secret"),
    )
    assert r.status_code == 200


def test_buckets(flask_client, bucket, benchmark):
    @benchmark
    def list_buckets():
        r = flask_client.get("/api/0/buckets/")
        print(r.json)
        assert r.status_code == 200
        assert len(r.json) == 1


def test_heartbeats(flask_client, bucket, benchmark):
    # FIXME: Currently tests using the memory storage method
    # TODO: Test with a longer data section and see if there's a significant difference
    # TODO: Test with a larger bucket and see if there's a significant difference
    @benchmark
    def heartbeat():
        now = datetime.now()
        r = flask_client.post(
            f"/api/0/buckets/{bucket}/heartbeat?pulsetime=1",
            json={"timestamp": now, "duration": 0, "data": {"random": random.random()}},
        )
        assert r.status_code == 200


def test_get_events(flask_client, bucket, benchmark):
    n_events = 100
    start_time = datetime.now() - timedelta(days=100)
    for i in range(n_events):
        now = start_time + timedelta(hours=i)
        r = flask_client.post(
            f"/api/0/buckets/{bucket}/heartbeat?pulsetime=0",
            json={"timestamp": now, "duration": 0, "data": {"random": random.random()}},
        )
        assert r.status_code == 200

    @benchmark
    def get_events():
        r = flask_client.get(f"/api/0/buckets/{bucket}/events")
        assert r.status_code == 200
        assert r.json
        assert len(r.json) == n_events

        r = flask_client.get(f"/api/0/buckets/{bucket}/events?limit=-1")
        assert r.status_code == 200
        assert r.json
        assert len(r.json) == n_events

        r = flask_client.get(f"/api/0/buckets/{bucket}/events?limit=10")
        assert r.status_code == 200
        assert r.json
        assert len(r.json) == 10

        r = flask_client.get(f"/api/0/buckets/{bucket}/events?limit=100")
        assert r.status_code == 200
        assert r.json
        assert len(r.json) == n_events

        r = flask_client.get(f"/api/0/buckets/{bucket}/events?limit=1000")
        assert r.status_code == 200
        assert r.json
        assert len(r.json) == n_events


# TODO: Add benchmark for basic AFK-filtering query
