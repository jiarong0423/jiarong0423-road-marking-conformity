"""The access gate in aws/handler.py (2026-09-23)."""
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "aws"))


def _handler(monkeypatch, token):
    if token is None:
        monkeypatch.delenv("ACCESS_TOKEN", raising=False)
    else:
        monkeypatch.setenv("ACCESS_TOKEN", token)
    import handler
    return importlib.reload(handler).handler


def _post(h, headers):
    return h({"requestContext": {"http": {"method": "POST"}}, "headers": headers, "body": "not json"}, None)


def test_open_when_no_token_is_configured(monkeypatch):
    h = _handler(monkeypatch, None)
    assert _post(h, {})["statusCode"] == 400          # reaches the body parser


def test_refused_without_the_header(monkeypatch):
    h = _handler(monkeypatch, "s3cret")
    r = _post(h, {})
    assert r["statusCode"] == 401 and json.loads(r["body"])["state"] == "UNAUTHORISED"


def test_refused_with_the_wrong_token(monkeypatch):
    h = _handler(monkeypatch, "s3cret")
    assert _post(h, {"x-access-token": "nope"})["statusCode"] == 401


def test_header_name_is_case_insensitive_and_right_token_passes(monkeypatch):
    h = _handler(monkeypatch, "s3cret")
    assert _post(h, {"X-Access-Token": "s3cret"})["statusCode"] == 400   # past the gate


def test_get_stays_open_and_says_a_token_is_needed(monkeypatch):
    h = _handler(monkeypatch, "s3cret")
    r = h({"requestContext": {"http": {"method": "GET"}}}, None)
    assert r["statusCode"] == 200 and "x-access-token" in json.loads(r["body"])["access"]
