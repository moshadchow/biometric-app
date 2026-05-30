from __future__ import annotations

import unittest

from core.compliance import calculate_risk, run_provider


class ComplianceEngineTest(unittest.TestCase):
    def test_sanctions_match_rejects(self) -> None:
        subject = {"fields": {"name": "Blocked OFAC Person"}}
        result = run_provider("sanctions", subject)
        risk = calculate_risk([result])

        self.assertEqual(result["outcome"], "MATCH_FOUND")
        self.assertEqual(risk["decision"], "REJECTED")
        self.assertEqual(risk["risk_category"], "HIGH")

    def test_pep_plus_ip_risk_requires_review(self) -> None:
        subject = {
            "fields": {"name": "Senior Minister Example", "country": "Bangladesh"},
            "metadata": {"network": {"vpn": True, "country": "Bangladesh"}},
        }
        pep_result = run_provider("pep", subject)
        ip_result = run_provider("ip_risk", subject)
        risk = calculate_risk([pep_result, ip_result])

        self.assertEqual(pep_result["outcome"], "HIGH_CONFIDENCE_MATCH")
        self.assertEqual(ip_result["outcome"], "MATCH_FOUND")
        self.assertEqual(risk["decision"], "REVIEW_REQUIRED")
        self.assertEqual(risk["risk_category"], "MEDIUM")

    def test_clear_results_approve(self) -> None:
        subject = {"fields": {"name": "Normal Customer", "country": "Bangladesh"}}
        results = [
            run_provider("sanctions", subject),
            run_provider("pep", subject),
            run_provider("adverse_media", subject),
            run_provider("internal_watchlist", subject),
            run_provider("exit_list", subject),
            run_provider("ip_risk", subject),
        ]
        risk = calculate_risk(results)

        self.assertEqual(risk["decision"], "APPROVED")
        self.assertEqual(risk["risk_category"], "LOW")
        self.assertEqual(risk["risk_score"], 0)


if __name__ == "__main__":
    unittest.main()
