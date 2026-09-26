"""Composition root for the WhyYou H-03 adapter set."""

from __future__ import annotations

from collections.abc import Mapping

from engine.adapters.base import AdapterSet, CapabilityProbeResult
from engine.adapters.whyyou.browser import WhyYouBrowserAdapter
from engine.adapters.whyyou.capability import WhyYouCapabilityProbe
from engine.adapters.whyyou.client import WhyYouClient
from engine.adapters.whyyou.fault import WhyYouFaultAdapter
from engine.adapters.whyyou.seed import WhyYouSeedAdapter
from engine.adapters.whyyou.state import WhyYouStateAdapter
from engine.config import Settings
from engine.models import TargetSnapshot


class WhyYouTargetAdapter:
    def __init__(self, client: WhyYouClient, capability: WhyYouCapabilityProbe) -> None:
        self.client = client
        self.capability = capability

    @property
    def registrations(self) -> Mapping[str, str]:
        return self.capability.registrations

    def capture_target_snapshot(self) -> TargetSnapshot:
        return self.client.capture_target_snapshot()

    def target_feature_exists(self) -> bool:
        return self.capability.target_feature_exists()

    def probe(self, capability: str) -> CapabilityProbeResult:
        return self.capability.probe(capability)


def create_whyyou_adapter(settings: Settings) -> tuple[AdapterSet, WhyYouClient]:
    client = WhyYouClient(settings)
    capability = WhyYouCapabilityProbe(settings, client)
    target = WhyYouTargetAdapter(client, capability)
    adapters = AdapterSet(
        target=target,
        capability=target,
        seed=WhyYouSeedAdapter(settings),
        state=WhyYouStateAdapter(settings, client),
        fault=WhyYouFaultAdapter(settings, client),
        browser=WhyYouBrowserAdapter(settings),
    )
    return adapters, client
