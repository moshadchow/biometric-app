from __future__ import annotations

import unittest

from core.risk_assessment import _business_scores, calculate_assessment_payload, classify_score, form_type_for_category
from model.models import CustomerIdentityProfile, RiskBusinessCategory, RiskRuleVersion, ScreeningResult


class RiskAssessmentEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rule = RiskRuleVersion(
            version="v1",
            thresholds={"low_max": 9, "medium_max": 14},
            rules_snapshot={"version": "v1"},
        )

    def test_threshold_classification(self) -> None:
        self.assertEqual(classify_score(9, self.rule.thresholds), "LOW")
        self.assertEqual(classify_score(10, self.rule.thresholds), "MEDIUM")
        self.assertEqual(classify_score(14, self.rule.thresholds), "MEDIUM")
        self.assertEqual(classify_score(15, self.rule.thresholds), "HIGH")

    def test_preliminary_low_routes_to_simplified(self) -> None:
        payload = calculate_assessment_payload(
            assessment_type="preliminary",
            rule_version=self.rule,
            identity_profile=None,
            addresses=[],
            nominee=None,
            ocr=None,
            screening_results=[],
            business_scores={"default": 3, "individual_investor": 2},
            profession_scores={"default": 3},
        )

        self.assertEqual(payload["risk_category"], "LOW")
        self.assertEqual(form_type_for_category(payload["risk_category"]), "simplified")
        self.assertFalse(payload["edd_required"])

    def test_pep_and_unverified_source_of_funds_trigger_edd(self) -> None:
        identity = CustomerIdentityProfile(
            session_id=1,
            form_type="regular",
            risk_category="MEDIUM",
            applicant_name="Senior Minister Example",
            profession="business",
            source_of_funds="Cash",
        )
        pep_result = ScreeningResult(
            screening_request_id=1,
            screening_type="pep",
            provider_name="mock",
            outcome="HIGH_CONFIDENCE_MATCH",
            confidence_score=0.9,
        )

        payload = calculate_assessment_payload(
            assessment_type="final",
            rule_version=self.rule,
            identity_profile=identity,
            addresses=[],
            nominee=None,
            ocr=None,
            screening_results=[pep_result],
            business_scores={"default": 3, "individual_investor": 2},
            profession_scores={"default": 3, "business": 3},
        )

        self.assertTrue(payload["edd_required"])
        self.assertIn("pep_match_found", payload["edd_reasons"])
        self.assertIn("source_of_funds_not_verified", payload["edd_reasons"])
        self.assertEqual(payload["decision"], "REVIEW_REQUIRED")

    def test_business_category_snapshot_preserves_dynamic_score(self) -> None:
        identity = CustomerIdentityProfile(
            session_id=1,
            form_type="regular",
            risk_category="MEDIUM",
            applicant_name="Gold Trader Example",
            profession="student",
            payload_metadata={"business_category": "Jeweler / Gold / Valuable Metals Business"},
        )
        business = RiskBusinessCategory(
            id=10,
            category_code="JEWELER_GOLD_VALUABLE_METALS",
            category_name="Jeweler / Gold / Valuable Metals Business",
            risk_score=5,
            is_active=True,
        )

        payload = calculate_assessment_payload(
            assessment_type="final",
            rule_version=self.rule,
            identity_profile=identity,
            addresses=[],
            nominee=None,
            ocr=None,
            screening_results=[],
            business_scores=_business_scores([business]),
            profession_scores={"student": 2, "default": 3},
        )

        business_factor = next(item for item in payload["factors"] if item.name == "business_activity_risk")
        self.assertEqual(business_factor.score, 5)
        self.assertEqual(business_factor.value["category_id"], 10)
        self.assertEqual(business_factor.value["risk_score"], 5)


if __name__ == "__main__":
    unittest.main()
