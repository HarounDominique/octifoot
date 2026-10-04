"""Local control panel: authorised domains and the maximum time of an analysis.

The page controls the authorisation boundary, so it is built to be hard to misuse: it needs a secret token, it is meant to be published on
127.0.0.1 only, it refuses any ``Host`` that is not localhost (DNS rebinding), every change needs a session, a CSRF token and (for a domain)
an explicit ownership confirmation, failed logins are throttled, responses carry restrictive security headers, and every change is audited.
Only the standard library is used, so there is nothing extra to audit.
"""

import hmac
import html
import http.cookies
import http.server
import secrets
import threading
import time
import urllib.parse
from collections.abc import Callable, Mapping
from typing import Any

from spiderfoot_connector.runtime import (
    MAX_TIMEOUT,
    MAX_TOTAL,
    MIN_TIMEOUT,
    MIN_TOTAL,
    RuntimeStore,
)

SESSION_TTL = 8 * 3600
MAX_BODY = 4096
MAX_FAILURES = 5
FAILURE_WINDOW = 300
LOCKOUT = 300
COOKIE = "octifoot_session"
LOCAL_HOSTNAMES = frozenset({"localhost", "127.0.0.1", "[::1]"})
AUDIT_LINES_SHOWN = 15

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "title": "octifoot control panel",
        "login": "Sign in",
        "token": "Access token",
        "bad_token": "That token is not correct.",
        "locked": "Too many failed attempts. Try again in a few minutes.",
        "logout": "Sign out",
        "domains": "Authorized domains",
        "domains_help": "Octifoot analyses only these domains and their subdomains. Add a domain only if you own it or have written permission to investigate it.",
        "from_env": "From the configuration file (read-only)",
        "from_panel": "Added here",
        "none": "none",
        "remove": "Remove",
        "add": "Add domain",
        "domain": "Domain (for example example.com)",
        "confirm": "I own this domain or have written permission to investigate it",
        "need_confirm": "You must confirm that you own the domain or have written permission to investigate it.",
        "timeout": "Maximum time of an analysis",
        "timeout_help": "Applies to the next analysis, not to ones already running. Leave empty to use the default.",
        "timeout_default": "Default (configuration file)",
        "timeout_current": "In use now",
        "seconds": "seconds",
        "save": "Save",
        "audit": "Recent changes",
        "added": "Domain added.",
        "removed": "Domain removed.",
        "saved": "Maximum time saved.",
        "total": "Maximum total time of one analysis",
        "total_help": "All the scans of one analysis together (an analysis can scan the subdomains it finds). Applies to the next analysis. Leave empty to use the default.",
        "bad_csrf": "The form expired or is not valid. Reload the page and try again.",
        "forbidden": "Forbidden",
    },
    "es": {
        "title": "Panel de control de octifoot",
        "login": "Entrar",
        "token": "Token de acceso",
        "bad_token": "Ese token no es correcto.",
        "locked": "Demasiados intentos fallidos. Prueba de nuevo en unos minutos.",
        "logout": "Salir",
        "domains": "Dominios autorizados",
        "domains_help": "Octifoot solo analiza estos dominios y sus subdominios. Añade un dominio solo si es tuyo o tienes permiso por escrito para investigarlo.",
        "from_env": "Del fichero de configuración (solo lectura)",
        "from_panel": "Añadidos aquí",
        "none": "ninguno",
        "remove": "Quitar",
        "add": "Añadir dominio",
        "domain": "Dominio (por ejemplo example.com)",
        "confirm": "Soy titular de este dominio o tengo permiso por escrito para investigarlo",
        "need_confirm": "Debes confirmar que eres titular del dominio o que tienes permiso por escrito para investigarlo.",
        "timeout": "Tiempo máximo de un análisis",
        "timeout_help": "Se aplica al siguiente análisis, no a los que ya están en marcha. Déjalo vacío para usar el valor por defecto.",
        "timeout_default": "Por defecto (fichero de configuración)",
        "timeout_current": "En uso ahora",
        "seconds": "segundos",
        "save": "Guardar",
        "audit": "Cambios recientes",
        "added": "Dominio añadido.",
        "removed": "Dominio quitado.",
        "saved": "Tiempo máximo guardado.",
        "total": "Tiempo total máximo de un análisis",
        "total_help": "Todos los escaneos de un análisis juntos (un análisis puede escanear los subdominios que encuentra). Se aplica al siguiente análisis. Déjalo vacío para usar el valor por defecto.",
        "bad_csrf": "El formulario caducó o no es válido. Recarga la página e inténtalo de nuevo.",
        "forbidden": "Prohibido",
    },
}

_CSS = (
    "body{font:16px/1.5 system-ui,sans-serif;max-width:46rem;margin:2rem auto;padding:0 1rem;color:#1c1c1c;background:#fafafa}"
    "h1{font-size:1.4rem}h2{font-size:1.1rem;margin-top:2rem}section{background:#fff;border:1px solid #ddd;border-radius:8px;padding:1rem 1.25rem;margin:1rem 0}"
    "input[type=text],input[type=password],input[type=number]{width:100%;padding:.5rem;border:1px solid #888;border-radius:6px;box-sizing:border-box}"
    "button{padding:.5rem 1rem;border-radius:6px;border:1px solid #444;background:#222;color:#fff;cursor:pointer}"
    "button.link{background:none;color:#a00;border:none;text-decoration:underline;padding:0}"
    ".err{background:#fde8e8;border:1px solid #c33;padding:.6rem .9rem;border-radius:6px}.ok{background:#e6f4ea;border:1px solid #2e7d32;padding:.6rem .9rem;border-radius:6px}"
    "small,.hint{color:#555}pre{background:#f0f0f0;padding:.6rem;overflow:auto;border-radius:6px;font-size:.85rem}"
    "li{margin:.25rem 0}label{display:block;margin:.5rem 0}"
)

ROUTES: Mapping[str, frozenset[str]] = {
    "/": frozenset({"GET"}),
    "/login": frozenset({"GET", "POST"}),
    "/logout": frozenset({"POST"}),
    "/domains/add": frozenset({"POST"}),
    "/domains/remove": frozenset({"POST"}),
    "/timeout": frozenset({"POST"}),
    "/total": frozenset({"POST"}),
}


class PanelServer:
    def __init__(
        self,
        store: RuntimeStore,
        token: str,
        *,
        base_domains: frozenset[str],
        base_timeout: int,
        base_total: int = 3600,
        host: str = "127.0.0.1",
        port: int = 8099,
        lang: str = "en",
        clock: Callable[[], float] = time.monotonic,
        log: Callable[[str, str, dict[str, Any]], None] | None = None,
    ) -> None:
        self._store = store
        self._token = token.encode("utf-8")
        self._base_domains = frozenset(base_domains)
        self._base_timeout = base_timeout
        self._base_total = base_total
        self._host, self._port = host, port
        self._t = STRINGS.get(lang, STRINGS["en"])
        self._clock = clock
        self._log = log or (lambda level, message, meta: None)
        self._sessions: dict[str, dict[str, Any]] = {}
        self._failures: dict[str, list[float]] = {}
        self._locked_until: dict[str, float] = {}
        self._lock = threading.Lock()
        self._httpd: http.server.ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    # --- lifecycle ---

    def start(self) -> int:
        panel = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(
                self, fmt: str, *args: Any
            ) -> None:  # no request lines in logs: keep tokens out
                return

            def _go(self) -> None:
                panel._handle(self)

            do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = do_HEAD = do_OPTIONS = _go

        self._httpd = http.server.ThreadingHTTPServer((self._host, self._port), Handler)
        self._httpd.daemon_threads = True
        self._port = self._httpd.server_address[1]
        self._thread = threading.Thread(
            target=lambda: self._httpd.serve_forever(poll_interval=0.05),
            name="octifoot-panel",
            daemon=True,
        )
        self._thread.start()
        return self._port

    def stop(self) -> None:
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()

    # --- plumbing ---

    def _send(
        self,
        h: http.server.BaseHTTPRequestHandler,
        status: int,
        body: str = "",
        *,
        location: str | None = None,
        cookie: str | None = None,
    ) -> None:
        data = body.encode("utf-8")
        h.send_response(status)
        h.send_header("Content-Type", "text/html; charset=utf-8")
        h.send_header("Content-Length", str(len(data)))
        h.send_header(
            "Content-Security-Policy",
            "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
        )
        h.send_header("X-Frame-Options", "DENY")
        h.send_header("X-Content-Type-Options", "nosniff")
        h.send_header("Referrer-Policy", "no-referrer")
        h.send_header("Cache-Control", "no-store")
        if location:
            h.send_header("Location", location)
        if cookie:
            h.send_header("Set-Cookie", cookie)
        h.end_headers()
        if h.command != "HEAD":
            h.wfile.write(data)

    @staticmethod
    def _hostname(value: str) -> str:
        value = value.strip().lower()
        if value.startswith("["):  # [::1]:8099
            return value.split("]")[0] + "]"
        return value.split(":")[0]

    def _session(self, h: http.server.BaseHTTPRequestHandler) -> tuple[str, dict[str, Any]] | None:
        raw = h.headers.get("Cookie", "")
        try:
            jar = http.cookies.SimpleCookie(raw)
        except http.cookies.CookieError:
            return None
        morsel = jar.get(COOKIE)
        if morsel is None:
            return None
        with self._lock:
            session = self._sessions.get(morsel.value)
            if session is None or session["expires"] < self._clock():
                self._sessions.pop(morsel.value, None)
                return None
            return morsel.value, session

    def _form(self, h: http.server.BaseHTTPRequestHandler) -> dict[str, str] | None:
        length = int(h.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return None
        body = h.rfile.read(length).decode("utf-8", "replace") if length else ""
        return {k: v[0] for k, v in urllib.parse.parse_qs(body, keep_blank_values=True).items()}

    # --- routing ---

    def _handle(self, h: http.server.BaseHTTPRequestHandler) -> None:
        # DNS rebinding: only localhost names are served, on every route.
        if self._hostname(h.headers.get("Host", "")) not in LOCAL_HOSTNAMES:
            return self._send(h, 403, self._t["forbidden"])
        path = urllib.parse.urlsplit(h.path).path
        allowed = ROUTES.get(path)
        if allowed is None:
            return self._send(h, 404, "Not found")
        if h.command not in allowed:
            return self._send(h, 405, "Method not allowed")
        client = h.client_address[0]

        form: dict[str, str] = {}
        if h.command == "POST":
            if int(h.headers.get("Content-Length") or 0) > MAX_BODY:
                return self._send(h, 413, "Payload too large")
            origin = h.headers.get("Origin")
            if (
                origin
                and self._hostname(urllib.parse.urlsplit(origin).netloc) not in LOCAL_HOSTNAMES
            ):
                return self._send(h, 403, self._t["forbidden"])
            form = self._form(h) or {}

        if path == "/login":
            return (
                self._login(h, form, client)
                if h.command == "POST"
                else self._send(h, 200, self._login_page())
            )

        found = self._session(h)
        if found is None:
            return self._send(h, 303, location="/login")
        sid, session = found
        if h.command == "GET":
            return self._send(h, 200, self._dashboard(session))
        if not hmac.compare_digest(form.get("csrf", "").encode(), session["csrf"].encode()):
            return self._send(h, 403, self._t["bad_csrf"])

        if path == "/logout":
            with self._lock:
                self._sessions.pop(sid, None)
            return self._send(
                h,
                303,
                location="/login",
                cookie=f"{COOKIE}=; Max-Age=0; Path=/; HttpOnly; SameSite=Strict",
            )
        return self._change(h, path, form, session, client)

    # --- login ---

    def _login(
        self, h: http.server.BaseHTTPRequestHandler, form: dict[str, str], client: str
    ) -> None:
        now = self._clock()
        with self._lock:
            if self._locked_until.get(client, 0) > now:
                return self._send(h, 429, self._login_page(self._t["locked"]))
        if hmac.compare_digest(form.get("token", "").encode("utf-8"), self._token):
            sid, csrf = secrets.token_hex(32), secrets.token_hex(16)
            with self._lock:
                self._sessions[sid] = {"csrf": csrf, "expires": now + SESSION_TTL, "flash": None}
                self._failures.pop(client, None)
            cookie = f"{COOKIE}={sid}; Path=/; HttpOnly; SameSite=Strict; Max-Age={SESSION_TTL}"
            return self._send(h, 303, location="/", cookie=cookie)
        with self._lock:
            recent = [t for t in self._failures.get(client, []) if now - t < FAILURE_WINDOW] + [now]
            self._failures[client] = recent
            if len(recent) >= MAX_FAILURES:
                self._locked_until[client] = now + LOCKOUT
                self._failures.pop(client, None)
        self._log("warning", "Control panel: failed sign-in", {"client": client})
        return self._send(h, 401, self._login_page(self._t["bad_token"]))

    # --- changes ---

    def _change(
        self,
        h: http.server.BaseHTTPRequestHandler,
        path: str,
        form: dict[str, str],
        session: dict[str, Any],
        client: str,
    ) -> None:
        try:
            if path == "/domains/add":
                if form.get("confirm") != "yes":
                    raise ValueError(self._t["need_confirm"])
                self._store.add_domain(form.get("domain", ""), by=client)
                session["flash"] = ("ok", self._t["added"])
            elif path == "/domains/remove":
                self._store.remove_domain(form.get("domain", ""), by=client)
                session["flash"] = ("ok", self._t["removed"])
            elif path == "/total":
                raw = form.get("seconds", "").strip()
                self._store.set_total_timeout(raw if raw else None, by=client)
                session["flash"] = ("ok", self._t["saved"])
            else:  # /timeout
                raw = form.get("seconds", "").strip()
                self._store.set_timeout(raw if raw else None, by=client)
                session["flash"] = ("ok", self._t["saved"])
        except ValueError as exc:
            return self._send(h, 400, self._dashboard(session, error=str(exc)))
        return self._send(h, 303, location="/")

    # --- pages ---

    def _page(self, body: str) -> str:
        t = self._t
        return (
            f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{html.escape(t['title'])}</title><style>{_CSS}</style></head><body>{body}</body></html>"
        )

    def _login_page(self, error: str = "") -> str:
        t = self._t
        err = f'<p class="err">{html.escape(error)}</p>' if error else ""
        return self._page(
            f'<h1>{html.escape(t["title"])}</h1>{err}<section><form method="post" action="/login">'
            f'<label>{html.escape(t["token"])}<input type="password" name="token" autocomplete="current-password" autofocus></label>'
            f'<button type="submit">{html.escape(t["login"])}</button></form></section>'
        )

    def _dashboard(self, session: dict[str, Any], error: str = "") -> str:
        t, csrf = self._t, session["csrf"]
        e = html.escape
        hidden = f'<input type="hidden" name="csrf" value="{csrf}">'
        flash = session.pop("flash", None)
        notice = (
            f'<p class="err">{e(error)}</p>'
            if error
            else (f'<p class="ok">{e(flash[1])}</p>' if flash else "")
        )
        self._store.domains()  # refresh from disk first: `problem` describes the latest read
        problem = self._store.problem
        warn = f'<p class="err">{e(problem)}</p>' if problem else ""

        env_items = (
            "".join(f"<li>{e(d)}</li>" for d in sorted(self._base_domains))
            or f"<li>{e(t['none'])}</li>"
        )
        added = self._store.domains()
        added_items = (
            "".join(
                f"<li>{e(d['value'])} <small>({e(d['added_at'])})</small> "
                f'<form method="post" action="/domains/remove" style="display:inline">{hidden}'
                f'<input type="hidden" name="domain" value="{e(d["value"])}"><button class="link" type="submit">{e(t["remove"])}</button></form></li>'
                for d in added
            )
            or f"<li>{e(t['none'])}</li>"
        )
        override = self._store.timeout_override()
        current = override if override is not None else self._base_timeout
        total_override = self._store.total_timeout_override()
        total_now = total_override if total_override is not None else self._base_total
        audit_path = self._store.directory / "audit.log"
        try:
            lines = (
                audit_path.read_text(encoding="utf-8").splitlines()[-AUDIT_LINES_SHOWN:]
                if audit_path.exists()
                else []
            )
        except OSError:
            lines = []
        audit = e("\n".join(lines)) or e(t["none"])

        body = (
            f'<h1>{e(t["title"])}</h1><form method="post" action="/logout" style="float:right">{hidden}'
            f'<button type="submit">{e(t["logout"])}</button></form>{notice}{warn}'
            f'<section><h2>{e(t["domains"])}</h2><p class="hint">{e(t["domains_help"])}</p>'
            f"<h3>{e(t['from_env'])}</h3><ul>{env_items}</ul><h3>{e(t['from_panel'])}</h3><ul>{added_items}</ul>"
            f'<form method="post" action="/domains/add">{hidden}<label>{e(t["domain"])}'
            f'<input type="text" name="domain" maxlength="253" autocomplete="off" required></label>'
            f'<label><input type="checkbox" name="confirm" value="yes"> {e(t["confirm"])}</label>'
            f'<button type="submit">{e(t["add"])}</button></form></section>'
            f'<section><h2>{e(t["timeout"])}</h2><p class="hint">{e(t["timeout_help"])}</p>'
            f"<p>{e(t['timeout_default'])}: <b>{self._base_timeout}</b> {e(t['seconds'])}<br>{e(t['timeout_current'])}: <b>{current}</b> {e(t['seconds'])}</p>"
            f'<form method="post" action="/timeout">{hidden}<label>{e(t["seconds"])} ({MIN_TIMEOUT}-{MAX_TIMEOUT})'
            f'<input type="number" name="seconds" min="{MIN_TIMEOUT}" max="{MAX_TIMEOUT}" step="1" value="{override if override is not None else ""}"></label>'
            f'<button type="submit">{e(t["save"])}</button></form></section>'
            f'<section><h2>{e(t["total"])}</h2><p class="hint">{e(t["total_help"])}</p>'
            f"<p>{e(t['timeout_default'])}: <b>{self._base_total}</b> {e(t['seconds'])}<br>{e(t['timeout_current'])}: <b>{total_now}</b> {e(t['seconds'])}</p>"
            f'<form method="post" action="/total">{hidden}<label>{e(t["seconds"])} ({MIN_TOTAL}-{MAX_TOTAL})'
            f'<input type="number" name="seconds" min="{MIN_TOTAL}" max="{MAX_TOTAL}" step="1" value="{total_override if total_override is not None else ""}"></label>'
            f'<button type="submit">{e(t["save"])}</button></form></section>'
            f"<section><h2>{e(t['audit'])}</h2><pre>{audit}</pre></section>"
        )
        return self._page(body)
