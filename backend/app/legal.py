"""
Legal/Ethical acceptance gating (Phase 5 + NFR-9).

Before a user can launch their first scan they must accept the platform's
legal & ethical terms. Acceptance is recorded with a version string so
future term changes can require re-acceptance.
"""
from __future__ import annotations

from app.models import LegalAcceptance


# Bump this when the terms change to force re-acceptance.
CURRENT_TERMS_VERSION = "v1.0"


TERMS_TEXT = """
RASID — Reconnaissance Automation System
Legal and Ethical Use Terms (v1.0)

By using RASID you agree:

  1. You will only scan targets you OWN or have EXPLICIT WRITTEN PERMISSION
     to scan. Unauthorised scanning is prohibited and may be illegal in your
     jurisdiction.

  2. You accept full responsibility for the scans you launch. RASID and its
     authors are not liable for misuse, abuse or any consequence arising
     from your use of the platform.

  3. You will not use RASID to bypass access controls, exploit
     vulnerabilities, exfiltrate data, or facilitate any unlawful activity.

  4. You will respect rate limits and avoid causing denial of service to
     scanned systems.

  5. You acknowledge that some tools (e.g. masscan, nuclei) generate
     network traffic that may trigger intrusion-detection systems on the
     target's side.

  6. You will comply with all applicable laws (CFAA, GDPR, your local
     computer-misuse statutes) when using this platform.

This is an academic and educational tool. Use it responsibly.
"""


def has_accepted_terms(db, user_id: int) -> bool:
    if user_id is None:
        return False
    row = (
        db.query(LegalAcceptance)
        .filter(
            LegalAcceptance.user_id == user_id,
            LegalAcceptance.terms_version == CURRENT_TERMS_VERSION,
        )
        .one_or_none()
    )
    return row is not None
