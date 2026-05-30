from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SCREENING_TERMINAL_STATUSES = {"APPROVED", "REVIEW_REQUIRED", "REJECTED", "FAILED"}
SCREENING_ACTIVE_STATUSES = {"SCREENING_PENDING", "SCREENING_IN_PROGRESS"}

SCREENING_JOB_NAMES = [
    "sanctions",
    "pep",
    "adverse_media",
    "internal_watchlist",
    "exit_list",
    "ip_risk",
]


@dataclass
class ProviderResult:
    screening_type: str
    provider_name: str
    outcome: str
    confidence_score: float
    list_name: str | None = None
    matched_fields: dict[str, Any] | None = None
    risk_factors: list[str] | None = None
    evidence_summary: str | None = None
    raw_payload: dict[str, Any] | None = None

    def as_payload(self) -> dict[str, Any]:
        return {
            "screening_type": self.screening_type,
            "provider_name": self.provider_name,
            "list_name": self.list_name,
            "outcome": self.outcome,
            "confidence_score": self.confidence_score,
            "matched_fields": self.matched_fields or {},
            "risk_factors": self.risk_factors or [],
            "evidence_summary": self.evidence_summary,
            "raw_payload": self.raw_payload or {},
        }


def _normalized_name(subject: dict[str, Any]) -> str:
    fields = subject.get("fields") or {}
    name = (
        fields.get("name")
        or fields.get("full_name")
        or fields.get("fullName")
        or fields.get("englishName")
        or fields.get("bnName")
        or subject.get("username")
        or ""
    )
    return str(name).strip().lower()


def _normalized_country(subject: dict[str, Any]) -> str:
    fields = subject.get("fields") or {}
    country = (
        fields.get("country")
        or fields.get("nationality")
        or fields.get("presentAddressCountry")
        or fields.get("permanentAddressCountry")
        or ""
    )
    return str(country).strip().lower()


def mock_sanctions_provider(subject: dict[str, Any]) -> ProviderResult:
    name = _normalized_name(subject)
    high_risk_name = any(token in name for token in ["sanction", "blocked", "ofac"])
    outcome = "MATCH_FOUND" if high_risk_name else "NO_MATCH"
    return ProviderResult(
        screening_type="sanctions",
        provider_name="mock_sanctions_provider",
        list_name="OFAC/UN/EU mock lists",
        outcome=outcome,
        confidence_score=0.99 if high_risk_name else 0.0,
        matched_fields={"name": name} if high_risk_name else {},
        risk_factors=["exact_sanctions_match"] if high_risk_name else [],
        evidence_summary="Mock sanctions exact match." if high_risk_name else "No sanctions indicators.",
        raw_payload={"name": name, "matched": high_risk_name},
    )


def mock_pep_provider(subject: dict[str, Any]) -> ProviderResult:
    name = _normalized_name(subject)
    is_pep = any(token in name for token in ["minister", "senator", "mp", "politician"])
    outcome = "HIGH_CONFIDENCE_MATCH" if is_pep else "NO_MATCH"
    return ProviderResult(
        screening_type="pep",
        provider_name="mock_pep_provider",
        list_name="Global PEP mock list",
        outcome=outcome,
        confidence_score=0.84 if is_pep else 0.0,
        matched_fields={"name": name} if is_pep else {},
        risk_factors=["high_confidence_pep"] if is_pep else [],
        evidence_summary="Mock PEP role match." if is_pep else "No PEP indicators.",
        raw_payload={"name": name, "matched": is_pep},
    )


def mock_adverse_media_provider(subject: dict[str, Any]) -> ProviderResult:
    name = _normalized_name(subject)
    has_media_hit = any(token in name for token in ["fraud", "corrupt", "launder"])
    outcome = "MATCH_FOUND" if has_media_hit else "NO_MATCH"
    return ProviderResult(
        screening_type="adverse_media",
        provider_name="mock_adverse_media_provider",
        list_name="Adverse media mock corpus",
        outcome=outcome,
        confidence_score=0.72 if has_media_hit else 0.0,
        matched_fields={"name": name} if has_media_hit else {},
        risk_factors=["adverse_media_match"] if has_media_hit else [],
        evidence_summary="Mock adverse media match." if has_media_hit else "No negative media indicators.",
        raw_payload={"name": name, "matched": has_media_hit},
    )


def mock_internal_watchlist_provider(subject: dict[str, Any]) -> ProviderResult:
    name = _normalized_name(subject)
    listed = any(token in name for token in ["blacklist", "rejected", "suspicious"])
    outcome = "MATCH_FOUND" if listed else "NO_MATCH"
    return ProviderResult(
        screening_type="internal_watchlist",
        provider_name="mock_internal_watchlist_provider",
        list_name="Internal watchlist",
        outcome=outcome,
        confidence_score=1.0 if listed else 0.0,
        matched_fields={"name": name} if listed else {},
        risk_factors=["internal_blacklist_match"] if listed else [],
        evidence_summary="Mock internal watchlist match." if listed else "No internal watchlist indicators.",
        raw_payload={"name": name, "matched": listed},
    )


def mock_exit_list_provider(subject: dict[str, Any]) -> ProviderResult:
    country = _normalized_country(subject)
    listed = country in {"iran", "north korea", "syria"}
    outcome = "MATCH_FOUND" if listed else "NO_MATCH"
    return ProviderResult(
        screening_type="exit_list",
        provider_name="mock_exit_list_provider",
        list_name="External exit list mock",
        outcome=outcome,
        confidence_score=0.91 if listed else 0.0,
        matched_fields={"country": country} if listed else {},
        risk_factors=["confirmed_exit_list_match"] if listed else [],
        evidence_summary="Mock exit list country match." if listed else "No exit list indicators.",
        raw_payload={"country": country, "matched": listed},
    )


def mock_ip_risk_provider(subject: dict[str, Any]) -> ProviderResult:
    metadata = subject.get("metadata") or {}
    network = metadata.get("network") or {}
    country = str(network.get("country") or _normalized_country(subject)).strip().lower()
    is_high_risk = country in {"iran", "north korea", "syria"} or bool(network.get("vpn"))
    factors: list[str] = []
    if country in {"iran", "north korea", "syria"}:
        factors.append("high_risk_country")
    if network.get("vpn"):
        factors.append("vpn_detected")
    if network.get("tor"):
        factors.append("tor_detected")
    outcome = "MATCH_FOUND" if is_high_risk else "NO_MATCH"
    return ProviderResult(
        screening_type="ip_risk",
        provider_name="mock_ip_risk_provider",
        list_name="IP intelligence mock feed",
        outcome=outcome,
        confidence_score=0.67 if is_high_risk else 0.0,
        matched_fields={"country": country, "network": network} if is_high_risk else {},
        risk_factors=factors,
        evidence_summary="Mock IP/network risk indicators." if is_high_risk else "No IP risk indicators.",
        raw_payload={"country": country, "network": network, "matched": is_high_risk},
    )


PROVIDER_REGISTRY = {
    "sanctions": mock_sanctions_provider,
    "pep": mock_pep_provider,
    "adverse_media": mock_adverse_media_provider,
    "internal_watchlist": mock_internal_watchlist_provider,
    "exit_list": mock_exit_list_provider,
    "ip_risk": mock_ip_risk_provider,
}


def run_provider(screening_type: str, subject: dict[str, Any]) -> dict[str, Any]:
    provider = PROVIDER_REGISTRY[screening_type]
    return provider(subject).as_payload()


def calculate_risk(results: list[dict[str, Any]]) -> dict[str, Any]:
    score = 0
    factors: list[dict[str, Any]] = []
    outcomes = {result["screening_type"]: result for result in results}

    for result in results:
        if result["outcome"] == "NO_MATCH":
            continue

        if "exact_sanctions_match" in result["risk_factors"]:
            factors.append({"rule": "exact_sanctions_match", "severity": "high"})
            return {
                "risk_score": 100,
                "risk_category": "HIGH",
                "decision": "REJECTED",
                "review_required": False,
                "factors": factors,
                "rules_snapshot": {"version": "v1"},
            }
        if "internal_blacklist_match" in result["risk_factors"]:
            factors.append({"rule": "internal_blacklist_match", "severity": "high"})
            return {
                "risk_score": 100,
                "risk_category": "HIGH",
                "decision": "REJECTED",
                "review_required": False,
                "factors": factors,
                "rules_snapshot": {"version": "v1"},
            }
        if "confirmed_exit_list_match" in result["risk_factors"]:
            factors.append({"rule": "confirmed_exit_list_match", "severity": "high"})
            return {
                "risk_score": 95,
                "risk_category": "HIGH",
                "decision": "REJECTED",
                "review_required": False,
                "factors": factors,
                "rules_snapshot": {"version": "v1"},
            }

        if "high_confidence_pep" in result["risk_factors"]:
            score += 45
            factors.append({"rule": "high_confidence_pep", "severity": "medium"})
        if "adverse_media_match" in result["risk_factors"]:
            score += 35
            factors.append({"rule": "adverse_media_match", "severity": "medium"})
        if "high_risk_country" in result["risk_factors"] or "vpn_detected" in result["risk_factors"]:
            score += 20
            factors.append({"rule": "ip_network_risk", "severity": "medium"})

    if outcomes.get("pep", {}).get("outcome") != "NO_MATCH" and outcomes.get("ip_risk", {}).get("outcome") != "NO_MATCH":
        score = max(score, 70)
        factors.append({"rule": "high_risk_ip_plus_pep", "severity": "high"})

    if score >= 80:
        decision = "REJECTED"
        category = "HIGH"
    elif score >= 35:
        decision = "REVIEW_REQUIRED"
        category = "MEDIUM"
    else:
        decision = "APPROVED"
        category = "LOW"

    return {
        "risk_score": score,
        "risk_category": category,
        "decision": decision,
        "review_required": decision == "REVIEW_REQUIRED",
        "factors": factors,
        "rules_snapshot": {"version": "v1"},
    }

