import http.client
import re
import urllib.parse

import pytest

from spiderfoot_connector.panel import PanelServer
from spiderfoot_connector.runtime import RuntimeStore

TOKEN = "correct-horse-battery-staple-0123"


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class Browser:
    """A tiny cookie-keeping client that speaks to the real server."""

    def __init__(self, port, host=None):
        self.port = port
        self.host = host or f"localhost:{port}"
        self.cookie = None

    def request(self, method, path, fields=None, headers=None, raw_body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        hdrs = {"Host": self.host, **(headers or {})}
        if self.cookie:
            hdrs["Cookie"] = self.cookie
        body = raw_body
        if fields is not None:
            body = urllib.parse.urlencode(fields)
            hdrs["Content-Type"] = "application/x-www-form-urlencoded"
        conn.request(method, path, body=body, headers=hdrs)
        resp = conn.getresponse()
        data = resp.read().decode("utf-8", "replace")
        set_cookie = resp.getheader("Set-Cookie")
        if set_cookie:
            self.cookie = set_cookie.split(";")[0]
        result = (resp.status, dict(resp.getheaders()), data)
        conn.close()
        return result

    def login(self, token=TOKEN):
        return self.request("POST", "/login", {"token": token})

    def csrf(self):
        _, _, page = self.request("GET", "/")
        return re.search(r'name="csrf" value="([0-9a-f]+)"', page).group(1)


@pytest.fixture
def env(tmp_path):
    clock = Clock()
    store = RuntimeStore(tmp_path / "state")
    server = PanelServer(
        store,
        TOKEN,
        base_domains=frozenset({"env.example.com"}),
        base_timeout=900,
        host="127.0.0.1",
        port=0,
        clock=clock,
    )
    port = server.start()
    yield server, store, clock, port
    server.stop()


@pytest.fixture
def logged_in(env):
    _, store, clock, port = env
    b = Browser(port)
    assert b.login()[0] == 303
    return b, store, clock, port


# --- access ---


def test_every_page_needs_a_session(env):
    _, _, _, port = env
    b = Browser(port)
    for method, path in (
        ("GET", "/"),
        ("POST", "/domains/add"),
        ("POST", "/timeout"),
        ("POST", "/domains/remove"),
    ):
        status, headers, _ = b.request(method, path, {} if method == "POST" else None)
        assert status == 303 and headers["Location"] == "/login", (method, path)


def test_the_login_page_is_served_without_a_session_and_holds_no_secret(env):
    _, _, _, port = env
    status, _, page = Browser(port).request("GET", "/login")
    assert status == 200 and 'type="password"' in page and TOKEN not in page


def test_a_wrong_token_is_refused_and_sets_no_cookie(env):
    _, _, _, port = env
    b = Browser(port)
    status, headers, _ = b.login("wrong-token-wrong-token")
    assert status == 401 and "Set-Cookie" not in headers and b.cookie is None


def test_the_right_token_sets_an_httponly_samesite_strict_cookie_and_opens_the_panel(env):
    _, _, _, port = env
    b = Browser(port)
    status, headers, _ = b.login()
    cookie = headers["Set-Cookie"]
    assert (
        status == 303
        and "HttpOnly" in cookie
        and "SameSite=Strict" in cookie
        and "Path=/" in cookie
    )
    assert b.request("GET", "/")[0] == 200


def test_logout_ends_the_session(logged_in):
    b, _, _, _ = logged_in
    csrf = b.csrf()
    assert b.request("POST", "/logout", {"csrf": csrf})[0] == 303
    assert b.request("GET", "/")[0] == 303


def test_a_session_expires(logged_in):
    b, _, clock, _ = logged_in
    clock.now += 9 * 3600
    assert b.request("GET", "/")[0] == 303


def test_repeated_failures_lock_the_client_out_even_for_the_right_token(env):
    _, _, clock, port = env
    b = Browser(port)
    for _ in range(5):
        assert b.login("wrong-token-wrong-token")[0] == 401
    assert b.login()[0] == 429
    clock.now += 301
    assert b.login()[0] == 303


# --- the panel page ---


def test_the_page_lists_env_domains_read_only_and_offers_the_add_and_timeout_forms(logged_in):
    b, _, _, _ = logged_in
    _, _, page = b.request("GET", "/")
    assert "env.example.com" in page and "read-only" in page.lower()
    assert (
        'action="/domains/add"' in page and 'name="confirm"' in page and 'action="/timeout"' in page
    )
    assert 'action="/domains/remove"' not in page  # nothing added from the panel yet
    assert TOKEN not in page


def test_the_page_shows_the_default_and_effective_time(logged_in):
    b, store, _, _ = logged_in
    assert "900" in b.request("GET", "/")[2]
    store.set_timeout(1800, by="test")
    assert "1800" in b.request("GET", "/")[2]


# --- changes need csrf and confirmation ---


def test_a_change_without_the_csrf_token_is_refused(logged_in):
    b, store, _, _ = logged_in
    status, _, _ = b.request(
        "POST", "/domains/add", {"domain": "new.example.com", "confirm": "yes"}
    )
    assert status == 403 and store.domains() == []


def test_a_change_with_a_wrong_csrf_token_is_refused(logged_in):
    b, store, _, _ = logged_in
    status, _, _ = b.request(
        "POST", "/domains/add", {"domain": "new.example.com", "confirm": "yes", "csrf": "0" * 32}
    )
    assert status == 403 and store.domains() == []


def test_a_foreign_origin_is_refused_even_with_a_valid_session_and_csrf(logged_in):
    b, store, _, _ = logged_in
    csrf = b.csrf()
    status, _, _ = b.request(
        "POST",
        "/domains/add",
        {"domain": "new.example.com", "confirm": "yes", "csrf": csrf},
        headers={"Origin": "http://evil.example.org"},
    )
    assert status == 403 and store.domains() == []


def test_adding_a_domain_requires_the_ownership_confirmation(logged_in):
    b, store, _, _ = logged_in
    status, _, page = b.request(
        "POST", "/domains/add", {"domain": "new.example.com", "csrf": b.csrf()}
    )
    assert status == 400 and "permission" in page and store.domains() == []


@pytest.mark.parametrize(
    "bad", ["com", "co.uk", "192.168.0.1", "http://example.com", "*.example.com", "example.com/x"]
)
def test_an_unsafe_domain_is_refused_with_a_reason(logged_in, bad):
    b, store, _, _ = logged_in
    status, _, _ = b.request(
        "POST", "/domains/add", {"domain": bad, "confirm": "yes", "csrf": b.csrf()}
    )
    assert status == 400 and store.domains() == []


def test_a_valid_domain_is_added_audited_and_shown_with_a_remove_button(logged_in):
    b, store, _, _ = logged_in
    status, headers, _ = b.request(
        "POST", "/domains/add", {"domain": " New.Example.COM ", "confirm": "yes", "csrf": b.csrf()}
    )
    assert status == 303 and headers["Location"] == "/"
    assert [d["value"] for d in store.domains()] == ["new.example.com"]
    assert "add domain=new.example.com by=127.0.0.1" in (store.directory / "audit.log").read_text()
    _, _, page = b.request("GET", "/")
    assert "new.example.com" in page and 'action="/domains/remove"' in page


def test_a_duplicate_domain_is_reported(logged_in):
    b, store, _, _ = logged_in
    store.add_domain("new.example.com", by="test")
    status, _, page = b.request(
        "POST", "/domains/add", {"domain": "new.example.com", "confirm": "yes", "csrf": b.csrf()}
    )
    assert status == 400 and "already" in page


def test_a_domain_added_from_the_panel_can_be_removed(logged_in):
    b, store, _, _ = logged_in
    store.add_domain("new.example.com", by="test")
    status, _, _ = b.request(
        "POST", "/domains/remove", {"domain": "new.example.com", "csrf": b.csrf()}
    )
    assert status == 303 and store.domains() == []
    assert "remove domain=new.example.com" in (store.directory / "audit.log").read_text()


def test_an_env_domain_cannot_be_removed_from_the_panel(logged_in):
    b, _, _, _ = logged_in
    status, _, page = b.request(
        "POST", "/domains/remove", {"domain": "env.example.com", "csrf": b.csrf()}
    )
    assert status == 400 and "not in the list" in page


# --- maximum time ---


def test_the_maximum_time_can_be_changed_within_bounds(logged_in):
    b, store, _, _ = logged_in
    assert b.request("POST", "/timeout", {"seconds": "1800", "csrf": b.csrf()})[0] == 303
    assert store.timeout_override() == 1800


@pytest.mark.parametrize("bad", ["59", "7201", "abc", "-5", "12.5"])
def test_an_out_of_range_time_is_refused(logged_in, bad):
    b, store, _, _ = logged_in
    status, _, page = b.request("POST", "/timeout", {"seconds": bad, "csrf": b.csrf()})
    assert status == 400 and "between 60 and 7200" in page and store.timeout_override() is None


def test_a_blank_time_returns_to_the_default(logged_in):
    b, store, _, _ = logged_in
    store.set_timeout(1800, by="test")
    assert b.request("POST", "/timeout", {"seconds": "", "csrf": b.csrf()})[0] == 303
    assert store.timeout_override() is None


# --- hardening ---


@pytest.mark.parametrize("path", ["/", "/login"])
def test_a_foreign_host_header_is_refused_on_every_page(env, path):
    _, _, _, port = env
    status, _, _ = Browser(port, host="evil.example.org").request("GET", path)
    assert status == 403


@pytest.mark.parametrize(
    "host", ["localhost", "127.0.0.1", "localhost:8099", "127.0.0.1:1234", "[::1]:8099"]
)
def test_localhost_host_headers_are_accepted(env, host):
    _, _, _, port = env
    assert Browser(port, host=host).request("GET", "/login")[0] == 200


def test_security_headers_are_on_every_response(env):
    _, _, _, port = env
    for path in ("/login", "/", "/nope"):
        _, headers, _ = Browser(port).request("GET", path)
        assert "default-src 'none'" in headers["Content-Security-Policy"]
        assert headers["X-Frame-Options"] == "DENY" and headers["Cache-Control"] == "no-store"
        assert headers["X-Content-Type-Options"] == "nosniff"


def test_unknown_paths_are_404_and_wrong_methods_405(logged_in):
    b, _, _, _ = logged_in
    assert b.request("GET", "/admin")[0] == 404
    assert b.request("GET", "/domains/add")[0] == 405
    assert b.request("DELETE", "/")[0] == 405


def test_an_oversized_body_is_refused(env):
    _, _, _, port = env
    status, _, _ = Browser(port).request(
        "POST",
        "/login",
        raw_body="token=" + "a" * 20000,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert status == 413


def test_the_token_never_appears_in_any_response_or_stored_file(logged_in):
    b, store, _, _ = logged_in
    seen = []
    seen.append(b.request("GET", "/")[2])
    seen.append(
        b.request(
            "POST",
            "/domains/add",
            {"domain": "new.example.com", "confirm": "yes", "csrf": b.csrf()},
        )[2]
    )
    seen.append(b.request("GET", "/")[2])
    seen.append(Browser(b.port).login("wrong-token-wrong-token")[2])
    for path in store.directory.iterdir():
        seen.append(path.read_text())
    assert not any(TOKEN in text for text in seen)


def test_echoed_input_is_html_escaped(logged_in):
    b, _, _, _ = logged_in
    _, _, page = b.request(
        "POST",
        "/domains/add",
        {"domain": "<script>alert(1)</script>.com", "confirm": "yes", "csrf": b.csrf()},
    )
    assert "<script>alert(1)</script>" not in page


def test_the_page_can_be_shown_in_spanish(tmp_path):
    store = RuntimeStore(tmp_path / "state")
    server = PanelServer(
        store,
        TOKEN,
        base_domains=frozenset({"env.example.com"}),
        base_timeout=900,
        port=0,
        lang="es",
    )
    port = server.start()
    try:
        b = Browser(port)
        b.login()
        page = b.request("GET", "/")[2]
        assert "Dominios autorizados" in page and "permiso" in page
    finally:
        server.stop()


def test_a_corrupt_state_file_is_reported_on_the_page_not_raised(logged_in):
    b, store, _, _ = logged_in
    (store.directory / "settings.json").write_text("{broken")
    status, _, page = b.request("GET", "/")
    assert status == 200 and "could not be read" in page
