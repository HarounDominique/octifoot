"""OpenCTI INTERNAL_ENRICHMENT wiring: Domain-Name -> SpiderFoot scan -> STIX bundle."""

import os
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import stix2
from pycti import Note, OpenCTIConnectorHelper

from spiderfoot_connector.allowlist import is_allowed
from spiderfoot_connector.client import SpiderFootClient, SpiderFootError
from spiderfoot_connector.config import Settings, load_settings
from spiderfoot_connector.dnschecks import DnsFacts, check_domain
from spiderfoot_connector.expansion import plan_next
from spiderfoot_connector.knowledge import Known, query_known, render_knowledge
from spiderfoot_connector.mapper import map_events
from spiderfoot_connector.profiles import SUBDOMAIN_SOURCES, lean_modules

SUPPORTED_ENTITY = "Domain-Name"


class TargetNotAllowed(ValueError):
    """The requested target is not on the operator's authorization allowlist."""


class SpiderFootEnrichment:
    def __init__(
        self,
        helper: Any,
        settings: Settings,
        client: SpiderFootClient,
        dns_check: Callable[[str], DnsFacts] | None = None,
        knowledge_lookup: Callable[[list[str]], list[Known]] | None = None,
    ) -> None:
        self._helper = helper
        self._settings = settings
        self._client = client
        self._dns_check = dns_check
        self._knowledge_lookup = knowledge_lookup

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
        # `full` keeps SpiderFoot's whole Passive group; `lean` sends an explicit module list.
        scan_options = {"modules": lean_modules()} if cfg.profile == "lean" else {}
        objects: dict[str, Any] = {}
        queue: list[tuple[str, int]] = [(root, 0)]
        known = {_norm(root)}  # scanned or queued: never scan twice
        attempts = 0
        scans_ok = 0
        depth_reached = 0
        failed: list[str] = []
        out_of_scope: list[str] = []
        budget_skipped: list[str] = []
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
            log.info("Starting SpiderFoot scan", {"target": target, "depth": depth})
            try:
                outcome = self._client.run_scan(
                    target,
                    cfg.usecase,
                    timeout_seconds=cfg.timeout_seconds,
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
                timeout_seconds=cfg.timeout_seconds,
                timed_out=outcome.timed_out,
            )
            unmapped.update(mapped.unmapped)
            for obj in mapped.objects:
                objects.setdefault(obj.id, obj)

            if depth < cfg.max_depth:
                plan = plan_next(
                    mapped.discovered_domains,
                    scanned=known,
                    allowlist=cfg.allowed_domains,
                    remaining_budget=cfg.max_scans - attempts - len(queue),
                )
                known.update(plan.targets)
                known.update(plan.out_of_scope)
                known.update(plan.budget_skipped)
                out_of_scope += plan.out_of_scope
                budget_skipped += plan.budget_skipped
                queue += [(t, depth + 1) for t in plan.targets]

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
            )
            objects[note.id] = note

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
                f"budget_skipped={len(budget_skipped)}"
            )
        return message

    def _authorized(self, target: str) -> bool:
        return is_allowed(target, self._settings.allowed_domains)

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
    def _expansion_note(objects, root, scans_ok, depth, failed, out_of_scope, budget_skipped):
        identity_id = next(o.id for o in objects.values() if o.type == "identity")
        lines = [
            f"Expansion from {root}: scans run: {scans_ok}, max depth reached: {depth}.",
            f"Failed sub-scans: {', '.join(failed) or 'none'}.",
            f"Skipped, outside the allowlist (never scanned): {', '.join(out_of_scope) or 'none'}.",
            f"Skipped, over the scan budget: {', '.join(budget_skipped) or 'none'}.",
        ]
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


def main() -> None:
    settings = load_settings(os.environ)
    helper = OpenCTIConnectorHelper({})
    enrichment = SpiderFootEnrichment(
        helper,
        settings,
        SpiderFootClient(settings.base_url),
        dns_check=check_domain,
        knowledge_lookup=lambda values: query_known(helper.api.query, values),
    )
    helper.listen(message_callback=enrichment.process_message)
