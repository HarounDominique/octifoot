"""OpenCTI INTERNAL_ENRICHMENT wiring: Domain-Name -> SpiderFoot scan -> STIX bundle."""

import importlib.metadata
import os
import sys
import threading
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import stix2
from pycti import Note, OpenCTIConnectorHelper

from spiderfoot_connector.allowlist import is_allowed
from spiderfoot_connector.apikeys import KeyRing, apply_keys, load_keyring
from spiderfoot_connector.changes import (
    Snapshot,
    latest_snapshot,
    render_changes,
    snapshot_from,
    summarize,
)
from spiderfoot_connector.client import SpiderFootClient, SpiderFootError
from spiderfoot_connector.config import ConfigError, Settings, load_settings
from spiderfoot_connector.dnschecks import DnsFacts, check_domain
from spiderfoot_connector.expansion import plan_next
from spiderfoot_connector.knowledge import Known, query_known, render_knowledge
from spiderfoot_connector.mapper import map_events
from spiderfoot_connector.panel import PanelServer
from spiderfoot_connector.profiles import SUBDOMAIN_SOURCES, lean_modules_with, load_snapshot
from spiderfoot_connector.provenance import coverage_line, provenance_line
from spiderfoot_connector.runtime import RuntimeStore
from spiderfoot_connector.watch import Watcher, ask_enrichment, query_watched, snapshot_time

SUPPORTED_ENTITY = "Domain-Name"


class TargetNotAllowed(ValueError):
    """The requested target is not on the operator's authorization allowlist."""


try:
    OCTIFOOT_VERSION = importlib.metadata.version("spiderfoot-connector")
except importlib.metadata.PackageNotFoundError:  # running from a checkout that is not installed
    OCTIFOOT_VERSION = "unknown"
MIN_SCAN_SECONDS = 60  # never start a scan with less time than this left


class SpiderFootEnrichment:
    def __init__(
        self,
        helper: Any,
        settings: Settings,
        client: SpiderFootClient,
        dns_check: Callable[[str], DnsFacts] | None = None,
        knowledge_lookup: Callable[[list[str]], list[Known]] | None = None,
        snapshot_lookup: Callable[[str], Snapshot | None] | None = None,
        key_ring: KeyRing | None = None,
        runtime: RuntimeStore | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._helper = helper
        self._settings = settings
        self._client = client
        self._dns_check = dns_check
        self._knowledge_lookup = knowledge_lookup
        self._snapshot_lookup = snapshot_lookup
        self._key_ring = key_ring
        self._runtime = runtime
        self._clock = clock

    def process_message(self, data: dict) -> str:
        entity = data["enrichment_entity"]
        if entity.get("entity_type") != SUPPORTED_ENTITY:
            raise ValueError(f"only {SUPPORTED_ENTITY} observables are supported")

        root = entity["observable_value"]
        log = self._helper.connector_logger
        # Authorization gate: must run before any SpiderFoot call.
        if not self._authorized(root):
            log.warning("Refusing scan: target not in SPIDERFOOT_ALLOWED_DOMAINS", {"target": root})
            raise TargetNotAllowed(f"{root} is not in SPIDERFOOT_ALLOWED_DOMAINS")

        cfg = self._settings
        timeout = (
            self._timeout()
        )  # fixed for this analysis; a change in the panel applies to the next one
        total = self._total_timeout()
        started = self._clock()
        # `full` keeps SpiderFoot's whole Passive group; `lean` sends an explicit module list.
        # Keyed modules join `lean` only once their key is stored and verified in SpiderFoot.
        keyed = self._apply_keys()
        spiderfoot_version = self._spiderfoot_version()
        scan_options = {"modules": lean_modules_with(keyed)} if cfg.profile == "lean" else {}
        objects: dict[str, Any] = {}
        queue: list[tuple[str, int]] = [(root, 0)]
        known = {_norm(root)}  # scanned or queued: never scan twice
        attempts = 0
        scans_ok = 0
        depth_reached = 0
        failed: list[str] = []
        out_of_scope: list[str] = []
        budget_skipped: list[str] = []
        deadline_skipped: list[str] = []
        sent: set[str] = set()
        timed_out = False
        root_outcome = None
        unmapped: Counter = Counter()

        while queue:
            target, depth = queue.pop(0)
            attempts += 1
            # Every scan, including expansions, passes the allowlist gate.
            if not self._authorized(target):
                out_of_scope.append(target)
                continue
            remaining = total - (self._clock() - started)
            if remaining < MIN_SCAN_SECONDS:
                deadline_skipped.append(target)
                continue
            scan_timeout = int(min(timeout, remaining))
            log.info("Starting SpiderFoot scan", {"target": target, "depth": depth})
            try:
                outcome = self._client.run_scan(
                    target,
                    cfg.usecase,
                    timeout_seconds=scan_timeout,
                    poll_seconds=cfg.poll_seconds,
                    **scan_options,
                )
                if outcome.status == "ERROR-FAILED":
                    raise SpiderFootError(f"scan {outcome.scan_id} ended with ERROR-FAILED")
            except SpiderFootError as exc:
                if depth == 0:
                    raise
                log.warning("Sub-scan failed, continuing", {"target": target, "error": str(exc)})
                failed.append(target)
                continue

            root_outcome = root_outcome or outcome
            timed_out = timed_out or outcome.timed_out
            scans_ok += 1
            depth_reached = max(depth_reached, depth)
            dns_facts = None
            source_errors = []
            if depth == 0 and self._dns_check is not None:  # the root target only, never expansions
                try:
                    dns_facts = self._dns_check(target)
                except Exception as exc:  # noqa: BLE001  a diagnostic must never fail the enrichment
                    log.warning("DNS checks failed", {"target": target, "error": str(exc)})
            try:
                source_errors = self._client.fetch_errors(outcome.scan_id)
            except SpiderFootError as exc:  # a diagnostic must never fail the enrichment
                log.warning("Could not read scan log", {"scan": outcome.scan_id, "error": str(exc)})
                source_errors = []
            mapped = map_events(
                outcome.events,
                target=target,
                scan_id=outcome.scan_id,
                score=cfg.score,
                now=datetime.now(UTC),
                source_errors=source_errors,
                subdomain_sources=SUBDOMAIN_SOURCES,
                dns_facts=dns_facts,
                scan_status=outcome.status,
                timeout_seconds=scan_timeout,
                timed_out=outcome.timed_out,
                ui_url=cfg.ui_url,
                extra_lines=[
                    provenance_line(
                        octifoot_version=OCTIFOOT_VERSION,
                        spiderfoot_version=spiderfoot_version,
                        profile=cfg.profile,
                        usecase=cfg.usecase,
                        modules=scan_options.get("modules"),
                        seconds=scan_timeout,
                        events=outcome.events,
                    ),
                    coverage_line(outcome.events, source_errors, keyed),
                ],
            )
            if depth == 0:
                root_mapped, root_dns, root_errors = mapped, dns_facts, source_errors
            unmapped.update(mapped.unmapped)
            for obj in mapped.objects:
                objects.setdefault(obj.id, obj)

            if depth < cfg.max_depth:
                plan = plan_next(
                    mapped.discovered_domains,
                    scanned=known,
                    allowlist=self._allowlist(),
                    remaining_budget=cfg.max_scans - attempts - len(queue),
                )
                known.update(plan.targets)
                known.update(plan.out_of_scope)
                known.update(plan.budget_skipped)
                out_of_scope += plan.out_of_scope
                budget_skipped += plan.budget_skipped
                queue += [(t, depth + 1) for t in plan.targets]

            if queue:  # more scans to come: keep what this one found even if the run stops
                self._send_new(objects, sent)

        if unmapped:
            log.info("Unmapped SpiderFoot event types", dict(unmapped))

        expanding = cfg.max_depth > 0
        if expanding:
            note = self._expansion_note(
                objects,
                root,
                scans_ok,
                depth_reached,
                failed,
                out_of_scope,
                budget_skipped,
                deadline_skipped,
                total,
            )
            objects[note.id] = note

        snapshot_note = self._snapshot_note(
            objects,
            root,
            root_outcome,
            root_mapped,
            root_dns,
            root_errors,
            complete=not timed_out
            and not failed
            and not deadline_skipped
            and root_outcome.status == "FINISHED",
        )
        if snapshot_note is not None:
            objects[snapshot_note.id] = snapshot_note

        knowledge_note = self._knowledge_note(objects, root)
        if knowledge_note is not None:
            objects[knowledge_note.id] = knowledge_note

        bundle = stix2.Bundle(objects=list(objects.values()), allow_custom=True).serialize()
        self._helper.send_stix2_bundle(bundle)

        partial = " (partial results: scan timed out and was stopped)" if timed_out else ""
        message = (
            f"SpiderFoot scan {root_outcome.scan_id} {root_outcome.status}: "
            f"sent {len(objects)} STIX objects{partial}"
        )
        if expanding:
            message += (
                f". Expansion: scans={scans_ok} depth={depth_reached} "
                f"failed={len(failed)} out_of_scope={len(out_of_scope)} "
                f"budget_skipped={len(budget_skipped)} deadline_skipped={len(deadline_skipped)}"
            )
        return message

    def _allowlist(self) -> frozenset[str]:
        """The .env list plus the domains added from the control panel, read at each use."""
        base = self._settings.allowed_domains
        return self._runtime.effective_allowlist(base) if self._runtime else base

    def _timeout(self) -> int:
        base = self._settings.timeout_seconds
        return self._runtime.effective_timeout(base) if self._runtime else base

    def _spiderfoot_version(self) -> str:
        try:
            return str(self._client.version() or "")
        except Exception as exc:  # noqa: BLE001  a diagnostic must never fail the enrichment
            self._helper.connector_logger.warning(
                "Could not read SpiderFoot version", {"error": str(exc)}
            )
            return ""

    def _total_timeout(self) -> int:
        base = self._settings.max_total_seconds
        return self._runtime.effective_total_timeout(base) if self._runtime else base

    def _send_new(self, objects: dict[str, Any], sent: set[str]) -> None:
        """Send the objects not yet sent (ids are deterministic, so the final bundle may repeat them)."""
        fresh = [o for o in objects.values() if o.id not in sent]
        if not fresh:
            return
        self._helper.send_stix2_bundle(stix2.Bundle(objects=fresh, allow_custom=True).serialize())
        sent.update(o.id for o in fresh)

    def _authorized(self, target: str) -> bool:
        return is_allowed(target, self._allowlist())

    def _apply_keys(self) -> frozenset[str]:
        """Store the owner's free API keys in SpiderFoot; returns the modules whose key is verified. Never logs values."""
        if self._key_ring is None or not self._key_ring.entries:
            return frozenset()
        log = self._helper.connector_logger
        result = apply_keys(self._key_ring, self._client)
        if result.failed:
            log.warning(
                "API keys not applied (option missing or not stored)", {"options": result.failed}
            )
        if result.applied:
            log.info("API keys applied", {"modules": sorted(result.applied)})
        return result.applied

    def _snapshot_note(
        self, objects, root, root_outcome, root_mapped, root_dns, root_errors, complete
    ):
        """Compare with the previous snapshot kept in OpenCTI and write the new one (never fatal)."""
        if self._snapshot_lookup is None:
            return None
        log = self._helper.connector_logger
        target = _norm(root)
        now = datetime.now(UTC)
        try:
            current = snapshot_from(
                target=target,
                scan=root_outcome.scan_id,
                at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                complete=complete,
                objects=list(objects.values()),
                infra=root_mapped.infra,
                dns=root_dns,
                source_gaps=bool({m for m, _ in root_errors} & SUBDOMAIN_SOURCES),
            )
            unreadable = False
            try:
                previous = self._snapshot_lookup(target)
            except Exception as exc:  # noqa: BLE001  the comparison is a diagnostic, never fatal
                log.warning("Could not read the previous snapshot", {"error": str(exc)})
                previous, unreadable = None, True
            failed_sources = bool({m for m, _ in root_errors} & SUBDOMAIN_SOURCES)
            content = render_changes(target, previous, current, failed_sources, unreadable)
            abstract = f"octifoot snapshot for {target}: " + (
                "previous snapshot unreadable"
                if unreadable
                else summarize(previous, current, failed_sources)
            )
            identity_id = next(o.id for o in objects.values() if o.type == "identity")
            return stix2.Note(
                id=Note.generate_id(now.isoformat(), content),
                created=now,
                modified=now,
                content=content,
                abstract=abstract,
                object_refs=[stix2.DomainName(value=target).id],
                created_by_ref=identity_id,
                allow_custom=True,
            )
        except Exception as exc:  # noqa: BLE001  never fail the enrichment for a diagnostic
            log.warning("Snapshot note failed", {"error": str(exc)})
            return None

    def _knowledge_note(self, objects, root):
        """Read what OpenCTI already holds about the imported observables (read-only, never fatal)."""
        if self._knowledge_lookup is None:
            return None
        values = sorted(
            {
                o.value
                for o in objects.values()
                if o.type in ("domain-name", "ipv4-addr", "ipv6-addr", "email-addr")
            }
        )
        try:
            known = self._knowledge_lookup(values)
        except Exception as exc:  # noqa: BLE001  a lookup must never fail the enrichment
            self._helper.connector_logger.warning(
                "OpenCTI knowledge lookup failed", {"error": str(exc)}
            )
            return None
        abstract, content = render_knowledge(known, len(values))
        identity_id = next(o.id for o in objects.values() if o.type == "identity")
        now = datetime.now(UTC)
        return stix2.Note(
            id=Note.generate_id(now.isoformat(), content),
            created=now,
            modified=now,
            content=content,
            abstract=abstract,
            object_refs=[stix2.DomainName(value=_norm(root)).id],
            created_by_ref=identity_id,
            allow_custom=True,
        )

    @staticmethod
    def _expansion_note(
        objects,
        root,
        scans_ok,
        depth,
        failed,
        out_of_scope,
        budget_skipped,
        deadline_skipped,
        total,
    ):
        identity_id = next(o.id for o in objects.values() if o.type == "identity")
        lines = [
            f"Expansion from {root}: scans run: {scans_ok}, max depth reached: {depth}.",
            f"Failed sub-scans: {', '.join(failed) or 'none'}.",
            f"Skipped, outside the allowlist (never scanned): {', '.join(out_of_scope) or 'none'}.",
            f"Skipped, over the scan budget: {', '.join(budget_skipped) or 'none'}.",
        ]
        if deadline_skipped:
            lines.append(
                f"Skipped, total time limit reached ({total} s): {', '.join(deadline_skipped)}."
            )
        content = "\n".join(lines)
        now = datetime.now(UTC)
        return stix2.Note(
            id=Note.generate_id(now.isoformat(), content),
            created=now,
            modified=now,
            content=content,
            abstract=f"SpiderFoot expansion summary for {root}",
            object_refs=[stix2.DomainName(value=_norm(root)).id],
            created_by_ref=identity_id,
            allow_custom=True,
        )


def _norm(domain: str) -> str:
    return domain.strip().lower().rstrip(".")


def _start_watcher(helper: Any, settings: Settings, runtime: RuntimeStore | None = None) -> None:
    """Re-analyse domains labelled octifoot:watch every interval (off unless configured)."""
    log = helper.connector_logger
    interval = settings.watch_interval_minutes * 60
    watcher = Watcher(
        interval_seconds=interval,
        max_per_cycle=settings.watch_max_per_cycle,
        allowlist=(
            (lambda: runtime.effective_allowlist(settings.allowed_domains))
            if runtime
            else settings.allowed_domains
        ),
        list_watched=lambda: query_watched(helper.api.query),
        last_scan=lambda value: snapshot_time(helper.api.query, value),
        ask=lambda object_id: ask_enrichment(helper.api.query, object_id, helper.connect_id),
        log=lambda level, message, meta: getattr(log, level)(message, meta),
    )
    cycle = min(900.0, max(60.0, interval / 4))
    threading.Thread(
        target=watcher.serve, args=(threading.Event(), cycle), name="octifoot-watch", daemon=True
    ).start()
    log.info(
        "Automatic re-analysis on",
        {"every_minutes": settings.watch_interval_minutes, "cycle_s": cycle},
    )


def _load_configuration() -> tuple[Settings, KeyRing | None, RuntimeStore | None]:
    """Read and validate every setting before the connector registers; a bad one exits with a readable message."""
    try:
        settings = load_settings(os.environ)
        ring = (
            load_keyring(settings.api_keys_file, load_snapshot())
            if settings.api_keys_file
            else None
        )
        runtime = RuntimeStore(settings.state_dir) if settings.state_dir else None
    except (ConfigError, OSError) as exc:
        print(f"octifoot: configuration error: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(2) from exc
    return settings, ring, runtime


def _start_panel(helper: Any, settings: Settings, runtime: RuntimeStore) -> None:
    """Serve the local control panel (domains and maximum time). The token is never logged."""
    log = helper.connector_logger
    panel = PanelServer(
        runtime,
        settings.ui_token,
        base_domains=settings.allowed_domains,
        base_timeout=settings.timeout_seconds,
        base_total=settings.max_total_seconds,
        host=settings.ui_bind,
        port=settings.ui_port,
        lang=settings.ui_lang,
        log=lambda level, message, meta: getattr(log, level)(message, meta),
    )
    port = panel.start()
    log.info("Control panel listening", {"bind": settings.ui_bind, "port": port})
    if settings.ui_bind not in ("127.0.0.1", "::1"):
        log.warning(
            "Control panel bound beyond loopback: it is safe only if the port is published on 127.0.0.1",
            {"bind": settings.ui_bind},
        )


def main() -> None:
    settings, key_ring, runtime = _load_configuration()
    helper = OpenCTIConnectorHelper({})
    enrichment = SpiderFootEnrichment(
        helper,
        settings,
        SpiderFootClient(settings.base_url),
        dns_check=check_domain,
        knowledge_lookup=lambda values: query_known(helper.api.query, values),
        snapshot_lookup=lambda target: latest_snapshot(helper.api.query, target),
        key_ring=key_ring,
        runtime=runtime,
    )
    if key_ring is not None:  # names only, never values
        helper.connector_logger.info("API keys loaded", {"modules": sorted(key_ring.modules)})
    if settings.ui_token and runtime is not None:
        _start_panel(helper, settings, runtime)
    if settings.watch_interval_minutes:
        _start_watcher(helper, settings, runtime)
    helper.listen(message_callback=enrichment.process_message)
