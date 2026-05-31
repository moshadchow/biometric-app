from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from core.risk_assessment import (
    _business_scores,
    _profession_scores,
    _sync_active_rule_version,
    calculate_assessment_payload,
    classify_score,
    form_type_for_category,
    stale_preliminary_assessment_session_ids_sync,
)
from scripts.seed_step3_risk_options import seed_step3_risk_options
from model.models import (
    CustomerIdentityProfile,
    CustomerRiskAssessment,
    RiskBusinessCategory,
    RiskFactorDefinition,
    RiskFactorRule,
    RiskProfessionCategory,
    RiskRuleVersion,
    OnboardingSession,
    User,
    ScreeningResult,
)
from sqlmodel import Session, SQLModel, create_engine, select


def definition(code: str, source_key: str, order: int) -> dict:
    return {
        "id": order,
        "factor_code": code,
        "factor_name": code,
        "factor_group": "customer",
        "source_key": source_key,
        "aggregation_mode": "max",
        "is_active": True,
        "display_order": order,
    }


def rule(rule_id: int, code: str, rule_type: str, score: int, **kwargs) -> dict:
    return {
        "id": rule_id,
        "rule_code": code,
        "rule_type": rule_type,
        "risk_score": score,
        "is_active": True,
        **kwargs,
    }


class RiskAssessmentEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rule = RiskRuleVersion(
            id=1,
            version="v1",
            thresholds={"low_max": 9, "medium_max": 14},
            rules_snapshot={"version": "v1"},
        )
        self.model = {
            "factor_definitions": [
                definition("profession_risk", "profession", 1),
                definition("business_activity_risk", "business_category", 2),
                definition("product_risk", "product_type", 3),
                definition("transactional_risk", "expected_transaction_range", 4),
                definition("source_of_funds_verification", "source_of_funds", 5),
                definition("type_of_onboarding", "onboarding_channel", 6),
                definition("pep", "pep_match", 7),
                definition("adverse_media_risk", "adverse_media_match", 8),
            ],
            "factor_rules": {
                "transactional_risk": [
                    rule(10, "TXN_LT_1M", "normalized_match", 1, match_value="LT_1M"),
                    rule(11, "TXN_GT_50M", "normalized_match", 5, match_value="GT_50M"),
                ],
                "source_of_funds_verification": [
                    rule(16, "SALARY", "normalized_match", 1, match_value="salary"),
                    rule(17, "CASH", "normalized_match", 5, match_value="cash"),
                ],
                "type_of_onboarding": [
                    rule(18, "BRANCH", "normalized_match", 2, match_value="branch"),
                    rule(19, "WALK_IN", "normalized_match", 3, match_value="walk_in"),
                ],
                "pep": [
                    rule(12, "PEP_MATCH", "boolean", 5, boolean_value=True),
                    rule(13, "PEP_NO_MATCH", "boolean", 0, boolean_value=False),
                ],
                "adverse_media_risk": [
                    rule(14, "ADVERSE_MEDIA_MATCH", "boolean", 4, boolean_value=True),
                    rule(15, "ADVERSE_MEDIA_NO_MATCH", "boolean", 0, boolean_value=False),
                ],
            },
            "product_scores": {
                "savings": {
                    "id": 20,
                    "code": "SAVINGS",
                    "name": "Savings Account",
                    "risk_score": 1,
                    "source_table": "risk_product_categories",
                }
            },
            "threshold_bands": [],
        }
        self.business_scores = _business_scores(
            [
                RiskBusinessCategory(
                    id=30,
                    category_code="EXPORT_IMPORT",
                    category_name="Export/Import",
                    risk_score=4,
                    is_active=True,
                ),
                RiskBusinessCategory(
                    id=31,
                    category_code="SMALL_BUSINESS",
                    category_name="Small Business",
                    risk_score=2,
                    is_active=True,
                ),
            ]
        )
        self.profession_scores = _profession_scores(
            [
                RiskProfessionCategory(
                    id=40,
                    profession_code="TEACHER",
                    profession_name="Teacher",
                    risk_score=1,
                    is_active=True,
                ),
                RiskProfessionCategory(
                    id=41,
                    profession_code="PILOT",
                    profession_name="Pilot",
                    risk_score=3,
                    is_active=True,
                ),
            ]
        )

    def _payload(self, identity: CustomerIdentityProfile, results: list[ScreeningResult] | None = None) -> dict:
        return calculate_assessment_payload(
            assessment_type="final",
            rule_version=self.rule,
            identity_profile=identity,
            addresses=[],
            nominee=None,
            ocr=None,
            screening_results=results or [],
            business_scores=self.business_scores,
            profession_scores=self.profession_scores,
            configured_model=self.model,
        )

    def _identity(self, **overrides) -> CustomerIdentityProfile:
        values = {
            "session_id": 1,
            "form_type": "regular",
            "risk_category": "MEDIUM",
            "applicant_name": "Configured Risk Example",
            "profession": "TEACHER",
            "business_category": "SMALL_BUSINESS",
            "product_type": "SAVINGS",
            "expected_transaction_range": "LT_1M",
            "source_of_funds": "salary",
            "onboarding_channel": "branch",
        }
        values.update(overrides)
        return CustomerIdentityProfile(**values)

    def test_threshold_classification(self) -> None:
        self.assertEqual(classify_score(9, self.rule.thresholds), "LOW")
        self.assertEqual(classify_score(10, self.rule.thresholds), "MEDIUM")
        self.assertEqual(classify_score(14, self.rule.thresholds), "MEDIUM")
        self.assertEqual(classify_score(15, self.rule.thresholds), "HIGH")

    def test_preliminary_low_routes_to_simplified_when_no_configured_factors(self) -> None:
        payload = calculate_assessment_payload(
            assessment_type="preliminary",
            rule_version=self.rule,
            identity_profile=None,
            addresses=[],
            nominee=None,
            ocr=None,
            screening_results=[],
            business_scores={},
            profession_scores={},
            configured_model={"factor_definitions": [], "factor_rules": {}, "threshold_bands": []},
        )

        self.assertEqual(payload["risk_category"], "LOW")
        self.assertEqual(form_type_for_category(payload["risk_category"]), "simplified")
        self.assertFalse(payload["edd_required"])

    def test_profession_and_business_scores_come_from_master_categories(self) -> None:
        payload = self._payload(self._identity(profession="PILOT", business_category="EXPORT_IMPORT"))

        factors = {factor.code: factor for factor in payload["factors"]}
        self.assertEqual(factors["profession_risk"].score, 3)
        self.assertEqual(factors["profession_risk"].source_table, "risk_profession_categories")
        self.assertEqual(factors["profession_risk"].rule_id, 41)
        self.assertEqual(factors["business_activity_risk"].score, 4)
        self.assertEqual(factors["business_activity_risk"].source_table, "risk_business_categories")
        self.assertEqual(factors["business_activity_risk"].rule_id, 30)

    def test_transaction_range_scores_come_from_factor_rules(self) -> None:
        low_payload = self._payload(self._identity(expected_transaction_range="LT_1M"))
        high_payload = self._payload(self._identity(expected_transaction_range="GT_50M"))

        low_factor = next(factor for factor in low_payload["factors"] if factor.code == "transactional_risk")
        high_factor = next(factor for factor in high_payload["factors"] if factor.code == "transactional_risk")
        self.assertEqual(low_factor.score, 1)
        self.assertEqual(low_factor.rule_id, 10)
        self.assertEqual(high_factor.score, 5)
        self.assertEqual(high_factor.rule_id, 11)

    def test_source_of_funds_scores_transparency_risk_from_factor_rules(self) -> None:
        low_payload = self._payload(self._identity(source_of_funds="salary"))
        high_payload = self._payload(self._identity(source_of_funds="cash"))

        low_factor = next(factor for factor in low_payload["factors"] if factor.code == "source_of_funds_verification")
        high_factor = next(factor for factor in high_payload["factors"] if factor.code == "source_of_funds_verification")
        self.assertEqual(low_factor.score, 1)
        self.assertEqual(low_factor.source_table, "risk_factor_rules")
        self.assertEqual(low_factor.selected_value, "salary")
        self.assertEqual(low_factor.rule_id, 16)
        self.assertEqual(high_factor.score, 5)
        self.assertEqual(high_factor.rule_id, 17)

    def test_onboarding_channel_scores_onboarding_type_from_factor_rules(self) -> None:
        branch_payload = self._payload(self._identity(onboarding_channel="branch"))
        walk_in_payload = self._payload(self._identity(onboarding_channel="walk_in"))

        branch_factor = next(factor for factor in branch_payload["factors"] if factor.code == "type_of_onboarding")
        walk_in_factor = next(factor for factor in walk_in_payload["factors"] if factor.code == "type_of_onboarding")
        self.assertEqual(branch_factor.score, 2)
        self.assertEqual(branch_factor.source_table, "risk_factor_rules")
        self.assertEqual(branch_factor.selected_value, "branch")
        self.assertEqual(branch_factor.rule_id, 18)
        self.assertEqual(walk_in_factor.score, 3)
        self.assertEqual(walk_in_factor.rule_id, 19)

    def test_screening_results_apply_configured_scores(self) -> None:
        pep = ScreeningResult(
            screening_request_id=1,
            screening_type="pep",
            provider_name="mock",
            outcome="HIGH_CONFIDENCE_MATCH",
            confidence_score=0.9,
        )
        adverse = ScreeningResult(
            screening_request_id=1,
            screening_type="adverse_media",
            provider_name="mock",
            outcome="MATCH",
            confidence_score=0.8,
        )

        payload = self._payload(self._identity(), [pep, adverse])

        factors = {factor.code: factor for factor in payload["factors"]}
        self.assertEqual(factors["pep"].score, 5)
        self.assertEqual(factors["pep"].source_table, "risk_factor_rules")
        self.assertEqual(factors["adverse_media_risk"].score, 4)
        self.assertTrue(payload["edd_required"])
        self.assertIn("pep_match_found", payload["edd_reasons"])
        self.assertIn("adverse_media_match_found", payload["edd_reasons"])

    def test_missing_configuration_scores_zero_and_remains_auditable(self) -> None:
        payload = self._payload(self._identity(profession="UNKNOWN"))

        factor = next(item for item in payload["factors"] if item.code == "profession_risk")
        self.assertEqual(factor.score, 0)
        self.assertEqual(factor.match_status, "missing_config")
        self.assertEqual(factor.selected_value, "UNKNOWN")
        self.assertEqual(factor.source_table, "risk_profession_categories")

    def test_active_rule_version_does_not_seed_step3_options_at_runtime(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            active = _sync_active_rule_version(session)
            definitions = {
                item.factor_code: item
                for item in session.exec(
                    select(RiskFactorDefinition).where(
                        RiskFactorDefinition.factor_code.in_(
                            [
                                "type_of_onboarding",
                                "transactional_risk",
                                "source_of_funds_verification",
                            ]
                        )
                    )
                ).all()
            }
            rules = list(
                session.exec(
                    select(RiskFactorRule).where(RiskFactorRule.rule_version_id == active.id)
                ).all()
            )

        self.assertEqual(active.status, "ACTIVE")
        self.assertEqual(definitions, {})
        self.assertEqual(rules, [])

    def test_step3_seed_script_creates_missing_options_without_overwriting_existing_rules(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            version = RiskRuleVersion(
                version="v1",
                status="ACTIVE",
                thresholds={"low_max": 9, "medium_max": 14},
                rules_snapshot={},
            )
            existing_definition = RiskFactorDefinition(
                factor_code="source_of_funds_verification",
                factor_name="Source of Funds",
                factor_group="transparency",
                source_key="source_of_funds",
                aggregation_mode="first",
                is_active=True,
                display_order=110,
            )
            session.add(version)
            session.add(existing_definition)
            session.flush()
            existing_rule = RiskFactorRule(
                rule_version_id=version.id,
                factor_definition_id=existing_definition.id,
                rule_code="SALARY",
                rule_type="normalized_match",
                match_value="salary",
                risk_score=9,
                description="Admin Salary",
                is_active=True,
            )
            session.add(existing_rule)
            session.commit()

            counts = seed_step3_risk_options(session)
            definitions = {
                row.factor_code: row
                for row in session.exec(select(RiskFactorDefinition)).all()
            }
            rules = list(session.exec(select(RiskFactorRule)).all())
            salary = session.exec(
                select(RiskFactorRule).where(RiskFactorRule.rule_code == "SALARY")
            ).one()

        self.assertEqual(counts["definitions_created"], 2)
        self.assertGreaterEqual(counts["rules_created"], 13)
        self.assertEqual(counts["rules_repaired"], 0)
        self.assertIn("type_of_onboarding", definitions)
        self.assertIn("transactional_risk", definitions)
        self.assertIn("source_of_funds_verification", definitions)
        self.assertEqual(salary.risk_score, 9)
        self.assertEqual(salary.description, "Admin Salary")
        self.assertGreaterEqual(len(rules), 14)

    def test_step3_seed_script_repairs_legacy_source_keys_without_overwriting_scores(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            version = RiskRuleVersion(
                version="v1",
                status="ACTIVE",
                thresholds={"low_max": 9, "medium_max": 14},
                rules_snapshot={},
            )
            definition_row = RiskFactorDefinition(
                factor_code="type_of_onboarding",
                factor_name="Legacy Onboarding",
                factor_group="legacy",
                source_key="onboarding_type",
                aggregation_mode="max",
                is_active=True,
                display_order=999,
            )
            session.add(version)
            session.add(definition_row)
            session.flush()
            existing_rule = RiskFactorRule(
                rule_version_id=version.id,
                factor_definition_id=definition_row.id,
                rule_code="BRANCH",
                rule_type="normalized_match",
                match_value="branch",
                risk_score=7,
                description="Admin Branch",
                is_active=True,
            )
            session.add(existing_rule)
            session.commit()

            counts = seed_step3_risk_options(session)
            repaired = session.exec(
                select(RiskFactorDefinition).where(RiskFactorDefinition.factor_code == "type_of_onboarding")
            ).one()
            branch = session.exec(
                select(RiskFactorRule).where(RiskFactorRule.rule_code == "BRANCH")
            ).one()

        self.assertEqual(counts["definitions_repaired"], 1)
        self.assertEqual(repaired.factor_name, "Onboarding Channel")
        self.assertEqual(repaired.factor_group, "onboarding")
        self.assertEqual(repaired.source_key, "onboarding_channel")
        self.assertEqual(repaired.aggregation_mode, "first")
        self.assertEqual(repaired.display_order, 10)
        self.assertEqual(branch.risk_score, 7)
        self.assertEqual(branch.description, "Admin Branch")

    def test_step3_seed_script_repairs_known_rule_shape_without_overwriting_scores(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            version = RiskRuleVersion(
                version="v1",
                status="ACTIVE",
                thresholds={"low_max": 9, "medium_max": 14},
                rules_snapshot={},
            )
            definition_row = RiskFactorDefinition(
                factor_code="transactional_risk",
                factor_name="Expected Annual Transaction Volume",
                factor_group="transactional",
                source_key="expected_transaction_range",
                aggregation_mode="first",
                is_active=True,
                display_order=100,
            )
            session.add(version)
            session.add(definition_row)
            session.flush()
            existing_rule = RiskFactorRule(
                rule_version_id=version.id,
                factor_definition_id=definition_row.id,
                rule_code="BELOW_BDT_1M",
                rule_type="range",
                match_value=None,
                risk_score=8,
                description=None,
                is_active=True,
            )
            session.add(existing_rule)
            session.commit()

            counts = seed_step3_risk_options(session)
            repaired = session.exec(
                select(RiskFactorRule).where(RiskFactorRule.rule_code == "BELOW_BDT_1M")
            ).one()

        self.assertEqual(counts["rules_repaired"], 1)
        self.assertEqual(repaired.rule_type, "normalized_match")
        self.assertEqual(repaired.match_value, "below_bdt_1m")
        self.assertEqual(repaired.description, "< BDT 1 Million")
        self.assertEqual(repaired.risk_score, 8)

    def test_stale_preliminary_assessment_session_ids_detects_completed_stale_rows(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)
        now = datetime.utcnow()

        with Session(engine) as session:
            session.add_all(
                [
                    User(id=1, username="customer1", password="hashed", role="customer"),
                    User(id=2, username="customer2", password="hashed", role="customer"),
                    OnboardingSession(
                        id=1,
                        user_id=1,
                        status="in_progress",
                        current_step="identity_form",
                        workflow_state="IDENTITY_FORM_PENDING",
                        completed_steps=["face_verification", "ocr_extraction"],
                        activation_status="blocked",
                        started_at=now,
                        updated_at=now,
                    ),
                    OnboardingSession(
                        id=2,
                        user_id=2,
                        status="in_progress",
                        current_step="identity_form",
                        workflow_state="IDENTITY_FORM_PENDING",
                        completed_steps=["face_verification", "ocr_extraction"],
                        activation_status="blocked",
                        started_at=now,
                        updated_at=now,
                    ),
                ]
            )
            session.add_all(
                [
                    CustomerIdentityProfile(
                        session_id=1,
                        form_type="regular",
                        risk_category="LOW",
                        status="IDENTITY_FORM_COMPLETED",
                        applicant_name="Stale Example",
                        source_of_funds="cash",
                        expected_transaction_range="bdt_1m_5m",
                        onboarding_channel="walk_in",
                        submitted_at=now,
                        created_at=now - timedelta(hours=2),
                        updated_at=now - timedelta(hours=2),
                    ),
                    CustomerIdentityProfile(
                        session_id=2,
                        form_type="regular",
                        risk_category="LOW",
                        status="IDENTITY_FORM_COMPLETED",
                        applicant_name="Fresh Example",
                        source_of_funds="salary",
                        expected_transaction_range="below_bdt_1m",
                        onboarding_channel="branch",
                        submitted_at=now - timedelta(hours=2),
                        created_at=now - timedelta(hours=3),
                        updated_at=now - timedelta(hours=1),
                    ),
                ]
            )
            session.add_all(
                [
                    CustomerRiskAssessment(
                        session_id=1,
                        assessment_type="preliminary",
                        status="RISK_COMPLETED",
                        total_score=0,
                        risk_category="LOW",
                        rule_version="v1",
                        calculated_at=now - timedelta(hours=3),
                        created_at=now - timedelta(hours=3),
                        updated_at=now - timedelta(hours=3),
                    ),
                    CustomerRiskAssessment(
                        session_id=2,
                        assessment_type="preliminary",
                        status="RISK_COMPLETED",
                        total_score=5,
                        risk_category="LOW",
                        rule_version="v1",
                        calculated_at=now - timedelta(minutes=30),
                        created_at=now - timedelta(minutes=30),
                        updated_at=now - timedelta(minutes=30),
                    ),
                ]
            )
            session.commit()

            stale_ids = stale_preliminary_assessment_session_ids_sync(session)

        self.assertEqual(stale_ids, [1])


if __name__ == "__main__":
    unittest.main()
