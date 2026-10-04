from urllib.parse import parse_qs

import pytest
import responses

from spiderfoot_connector.client import SpiderFootClient, SpiderFootError

BASE = "http://sf:5001"


@pytest.fixture
def client():
    return SpiderFootClient(BASE, sleep=lambda s: None)


@responses.activate
def test_get_options_returns_the_token_and_the_option_map(client):
    responses.add(
        responses.GET,
        f"{BASE}/optsraw",
        json=[
            "SUCCESS",
            {"token": 4711, "data": {"module.sfp_x.api_key": "", "global.debug": False}},
        ],
    )
    token, data = client.get_options()
    assert token == "4711"
    assert data["module.sfp_x.api_key"] == "" and data["global.debug"] is False


@responses.activate
def test_get_options_rejects_an_unexpected_answer(client):
    responses.add(responses.GET, f"{BASE}/optsraw", json=["ERROR", "nope"])
    with pytest.raises(SpiderFootError):
        client.get_options()


@responses.activate
def test_save_options_posts_json_options_and_the_token_as_a_form(client):
    responses.add(responses.POST, f"{BASE}/savesettingsraw", json=["SUCCESS", ""])
    client.save_options({"sfp_x:api_key": "VALUE"}, "4711")
    body = parse_qs(responses.calls[0].request.body)
    assert body["token"] == ["4711"]
    assert body["allopts"] == ['{"sfp_x:api_key": "VALUE"}']


@responses.activate
def test_save_options_raises_on_an_error_answer_without_echoing_values(client):
    responses.add(responses.POST, f"{BASE}/savesettingsraw", json=["ERROR", "Invalid token (1)."])
    with pytest.raises(SpiderFootError) as err:
        client.save_options({"sfp_x:api_key": "SENTINEL-KEY-VALUE-123"}, "1")
    assert "SENTINEL-KEY-VALUE-123" not in str(err.value)


@responses.activate
def test_save_options_is_never_retried_after_a_connection_error(client):
    import requests

    responses.add(
        responses.POST, f"{BASE}/savesettingsraw", body=requests.exceptions.ConnectionError("down")
    )
    responses.add(responses.POST, f"{BASE}/savesettingsraw", json=["SUCCESS", ""])
    with pytest.raises(SpiderFootError):
        client.save_options({"sfp_x:api_key": "v"}, "1")
    assert len(responses.calls) == 1
