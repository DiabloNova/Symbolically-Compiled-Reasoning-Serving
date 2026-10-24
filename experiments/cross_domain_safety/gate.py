"""Executable reference model for the SCRS cross-domain acceptance contract.

This is a specification oracle for conformance tests, not production SCRS code.
The caller must supply already-authenticated validation results; this module
cannot establish that upstream domain extraction or provenance verification is correct.

Fail-closed semantics (per docs/section-5-cross-domain-safety.md Section 2):
  * every validation/currency status is compared with `is not True` — any
    non-affirmative value (False, None, or a truthy non-boolean such as the
    string "unknown") is rejected, never accepted;
  * contract versions must be equal AND each explicitly marked current and
    supported by the version registry; two matching stale versions fail;
  * the canonicalization mapping must be a certified injective, versioned
    mapping, and any reported collision/ambiguity fails closed.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Candidate:
    request_domain: Optional[str]
    capsule_domain: Optional[str]
    request_contract_version: Optional[str]
    capsule_contract_version: Optional[str]
    request_contract_current: Optional[bool]
    capsule_contract_current: Optional[bool]
    canonical_mapping_version: Optional[str]
    canonical_mapping_supported: Optional[bool]
    canonicalization_ambiguous: Optional[bool]
    preconditions_compatible: Optional[bool]
    exceptions_compatible: Optional[bool]
    request_validated: bool
    capsule_validated: bool
    provenance_valid: bool


@dataclass(frozen=True)
class Decision:
    accepted: bool
    reason: str


SUPPORTED_CANONICAL_MAPPING_VERSIONS = frozenset({"cm-1"})


def decide(candidate: Candidate) -> Decision:
    """Fail closed for missing, unknown, invalid, or incompatible inputs.

    Every boolean status uses explicit-affirmative comparison (`is not True`),
    so truthy non-boolean values such as "unknown" can never pass.
    """
    # -- explicit-affirmative validation statuses (fail closed on any
    #    non-boolean truthy value, e.g. the string "unknown")
    if candidate.request_validated is not True:
        return Decision(False, "REQUEST_NOT_VALIDATED")
    if candidate.capsule_validated is not True:
        return Decision(False, "CAPSULE_NOT_VALIDATED")
    if candidate.provenance_valid is not True:
        return Decision(False, "PROVENANCE_INVALID")

    # -- canonicalization precondition: certified injective, versioned mapping
    if candidate.canonical_mapping_version not in SUPPORTED_CANONICAL_MAPPING_VERSIONS:
        return Decision(False, "CANONICALIZATION_MAPPING_UNSUPPORTED")
    if candidate.canonical_mapping_supported is not True:
        return Decision(False, "CANONICALIZATION_MAPPING_UNCERTIFIED")
    if candidate.canonicalization_ambiguous is not False:
        return Decision(False, "CANONICALIZATION_AMBIGUOUS")

    # -- domain identity (only meaningful under the certified mapping above)
    if not candidate.request_domain or not candidate.capsule_domain:
        return Decision(False, "DOMAIN_MISSING")
    if candidate.request_domain != candidate.capsule_domain:
        return Decision(False, "DOMAIN_MISMATCH")

    # -- contract version equality
    if not candidate.request_contract_version or not candidate.capsule_contract_version:
        return Decision(False, "CONTRACT_VERSION_MISSING")
    if candidate.request_contract_version != candidate.capsule_contract_version:
        return Decision(False, "CONTRACT_VERSION_MISMATCH")

    # -- version currency: equality is not enough; each side must be
    #    explicitly marked current and supported by the version registry
    if candidate.request_contract_current is not True:
        return Decision(False, "REQUEST_CONTRACT_NOT_CURRENT")
    if candidate.capsule_contract_current is not True:
        return Decision(False, "CAPSULE_CONTRACT_NOT_CURRENT")

    # -- policy compatibility, explicit affirmative only
    if candidate.preconditions_compatible is not True:
        return Decision(False, "PRECONDITIONS_NOT_CONFIRMED_COMPATIBLE")
    if candidate.exceptions_compatible is not True:
        return Decision(False, "EXCEPTIONS_NOT_CONFIRMED_COMPATIBLE")

    return Decision(True, "ACCEPTED")
