"""C020 read-only rights triage boundary; never interpret review as approval."""
from __future__ import annotations

from .models import MediaCandidate
from .rights import RightsDecision, license_triage


class RightsReview:
    def triage(self, candidate: MediaCandidate) -> RightsDecision:
        """Return conservative URL-based decision, not commercial clearance."""
        return license_triage(candidate.license_url, candidate.provider)
