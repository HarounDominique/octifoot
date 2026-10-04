"""OpenCTI INTERNAL_ENRICHMENT wiring: Domain-Name -> SpiderFoot scan -> STIX bundle."""

import os
from datetime import UTC, datetime
from typing import Any

import stix2
from pycti import OpenCTIConnectorHelper

from spiderfoot_connector.allowlist import is_allowed
from spiderfoot_connector.client import SpiderFootClient, SpiderFootError
from spiderfoot_connector.config import Settings, load_settings
from spiderfoot_connector.mapper import map_events

SUPPORTED_ENTITY = "Domain-Name"


class TargetNotAllowed(ValueError):
    """The requested target is not on the operator's authorization allowlist."""


class SpiderFootEnrichment:
    def __init__(self, helper: Any, settings: Settings, client: SpiderFootClient) -> None:
        self._helper = helper
        self._settings = settings
        self._client = client

    def process_message(self, data: dict) -> str:
        entity = data["enrichment_entity"]
        if entity.get("entity_type") != SUPPORTED_ENTITY:
            raise ValueError(f"only {SUPPORTED_ENTITY} observables are supported")

        target = entity["observable_value"]
        log = self._helper.connector_logger
        # Authorization gate: must run before any SpiderFoot call.
        if not is_allowed(target, self._settings.allowed_domains):
            log.warning(
                "Refusing scan: target not in SPIDERFOOT_ALLOWED_DOMAINS", {"target": target}
            )
            raise TargetNotAllowed(f"{target} is not in SPIDERFOOT_ALLOWED_DOMAINS")

        log.info("Starting SpiderFoot scan", {"target": target, "usecase": self._settings.usecase})
        outcome = self._client.run_scan(
            target,
            self._settings.usecase,
            timeout_seconds=self._settings.timeout_seconds,
            poll_seconds=self._settings.poll_seconds,
        )
        if outcome.status == "ERROR-FAILED":
            raise SpiderFootError(f"scan {outcome.scan_id} ended with ERROR-FAILED")

        mapped = map_events(
            outcome.events,
            target=target,
            scan_id=outcome.scan_id,
            score=self._settings.score,
            now=datetime.now(UTC),
        )
        if mapped.unmapped:
            log.info("Unmapped SpiderFoot event types", dict(mapped.unmapped))

        bundle = stix2.Bundle(objects=mapped.objects, allow_custom=True).serialize()
        self._helper.send_stix2_bundle(bundle)

        partial = " (partial results: scan timed out and was stopped)" if outcome.timed_out else ""
        return (
            f"SpiderFoot scan {outcome.scan_id} {outcome.status}: "
            f"sent {len(mapped.objects)} STIX objects{partial}"
        )


def main() -> None:
    settings = load_settings(os.environ)
    helper = OpenCTIConnectorHelper({})
    enrichment = SpiderFootEnrichment(helper, settings, SpiderFootClient(settings.base_url))
    helper.listen(message_callback=enrichment.process_message)
