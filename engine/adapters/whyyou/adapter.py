"""Composition root for the WhyYou adapter set (H-03, E-03, N-02, Spec 004 E-01 citation path)."""

from __future__ import annotations

from collections.abc import Mapping

from engine.adapters.base import AdapterSet, CapabilityProbeResult
from engine.adapters.whyyou.browser import WhyYouBrowserAdapter
from engine.adapters.whyyou.capability import WhyYouCapabilityProbe
from engine.adapters.whyyou.causality import WhyYouCausalityAdapter
from engine.adapters.whyyou.client import WhyYouClient
from engine.adapters.whyyou.consent import WhyYouConsentAdapter
from engine.adapters.whyyou.consent_fault import WhyYouConsentFaultAdapter
from engine.adapters.whyyou.criteria_versions import (
    WhyYouCriteriaVersionAdapter,
    WhyYouScoringSourceAdapter,
)
from engine.adapters.whyyou.decisions import WhyYouDecisionAdapter
from engine.adapters.whyyou.effects import WhyYouEffectAdapter
from engine.adapters.whyyou.environment import WhyYouEnvironmentAdapter
from engine.adapters.whyyou.evidence_mutation import WhyYouEvidenceMutationAdapter
from engine.adapters.whyyou.fault import WhyYouFaultAdapter
from engine.adapters.whyyou.model_emission import WhyYouModelEmissionAdapter
from engine.adapters.whyyou.n02_seed import N02CredentialStore, WhyYouN02SeedAdapter
from engine.adapters.whyyou.protected_processing import WhyYouProtectedProcessingAdapter
from engine.adapters.whyyou.queue import WhyYouQueueAdapter
from engine.adapters.whyyou.report_records import WhyYouSpec004ReportAdapter
from engine.adapters.whyyou.seed import WhyYouSeedAdapter
from engine.adapters.whyyou.spec004_seed import WhyYouSpec004SeedAdapter
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
    queue = WhyYouQueueAdapter(settings)
    environment = WhyYouEnvironmentAdapter(settings, client)
    fault = WhyYouFaultAdapter(settings, client)
    decision = WhyYouDecisionAdapter(settings, client)
    effects = WhyYouEffectAdapter(settings)
    n02_credentials = N02CredentialStore()
    n02_seed = WhyYouN02SeedAdapter(settings, credentials=n02_credentials)
    n02_processing = WhyYouProtectedProcessingAdapter(
        settings,
        credentials=n02_credentials,
    )
    n02_consent = WhyYouConsentAdapter(
        settings,
        credentials=n02_credentials,
    )
    n02_causality = WhyYouCausalityAdapter()
    n02_fault = WhyYouConsentFaultAdapter(
        settings,
        consent_adapter=n02_consent,
        processing_adapter=n02_processing,
    )
    # Spec 004 lanes keep their own applicant credentials; consent reuses the N-02 protocol.
    spec004_credentials = N02CredentialStore()
    spec004_seed = WhyYouSpec004SeedAdapter(settings, credentials=spec004_credentials)
    spec004_consent = WhyYouConsentAdapter(settings, credentials=spec004_credentials)
    spec004_reports = WhyYouSpec004ReportAdapter(settings)
    spec004_emissions = WhyYouModelEmissionAdapter(settings)
    spec004_mutation = WhyYouEvidenceMutationAdapter(settings)
    spec004_versions = WhyYouCriteriaVersionAdapter(settings)
    spec004_scoring_source = WhyYouScoringSourceAdapter(settings)
    capability = WhyYouCapabilityProbe(
        settings,
        client,
        queue=queue,
        environment=environment,
        decision=decision,
        effects=effects,
        n02_processing=n02_processing,
        n02_consent=n02_consent,
        n02_fault=n02_fault,
        spec004={
            "spec004_seed": spec004_seed,
            "spec004_reports": spec004_reports,
            "spec004_emissions": spec004_emissions,
            "spec004_mutation": spec004_mutation,
            "spec004_versions": spec004_versions,
            "spec004_scoring_source": spec004_scoring_source,
        },
    )
    target = WhyYouTargetAdapter(client, capability)
    adapters = AdapterSet(
        target=target,
        capability=target,
        seed=WhyYouSeedAdapter(settings),
        state=WhyYouStateAdapter(settings, client),
        fault=fault,
        browser=WhyYouBrowserAdapter(settings),
        environment=environment,
        queue=queue,
        decision=decision,
        effects=effects,
        boundary_receipts=fault,
        duplicate_acks=fault,
        safe_redrive=queue,
        n02_seed=n02_seed,
        n02_consent=n02_consent,
        n02_processing=n02_processing,
        n02_causality=n02_causality,
        n02_fault=n02_fault,
        n02_observer=n02_processing,
        spec004_seed=spec004_seed,
        spec004_consent=spec004_consent,
        spec004_requests=spec004_reports,
        spec004_records=spec004_reports,
        spec004_emissions=spec004_emissions,
        spec004_mutation=spec004_mutation,
        spec004_versions=spec004_versions,
        spec004_scoring_source=spec004_scoring_source,
    )
    return adapters, client
