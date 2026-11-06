"""Goal formulas, stable arithmetic, chart paths, context, and workflow parity."""

from math import isfinite
import unittest

from finnie.goals import calculate_monthly_contribution, project_goal
from finnie.workflow import build_workflow


def goal(**changes):
    return dict(target_amount=20000, current_savings=5000, years=5, annual_return=.05, **changes)


class GoalTests(unittest.TestCase):
    def test_existing_sample_and_zero_return_comparison(self):
        report = project_goal(goal())
        self.assertEqual(report["monthly_contribution"], 199.74)
        self.assertAlmostEqual(report["projected_balance"], 20000.33, places=2)
        self.assertAlmostEqual(report["zero_return_balance"], 16984.40)
        self.assertAlmostEqual(report["zero_return_gap"], -3015.60)
        self.assertEqual(len(report["rows"]), 61)
        self.assertEqual(report["rows"][0]["balance"], 5000)
        self.assertEqual(report["rows"][-1]["balance"], report["projected_balance"])
        self.assertTrue(all(row["target"] == 20000 for row in report["rows"]))

    def test_path_matches_independent_month_end_recurrence(self):
        for annual in (.05, -.05, 0, 1e-10):
            data = goal()
            data["annual_return"] = annual
            report = project_goal(data)
            balance = 5000.
            for row in report["rows"][1:]:
                balance = balance * (1 + annual / 12) + report["monthly_contribution"]
                self.assertAlmostEqual(row["balance"], balance, places=6)
                self.assertAlmostEqual(row["modeled_growth"], row["balance"] - row["zero_return_balance"])

    def test_zero_rate_paths_overlap_and_round_up(self):
        data = goal()
        data.update(current_savings=0, target_amount=100, years=1, annual_return=0)
        report = project_goal(data)
        self.assertEqual(report["monthly_contribution"], 8.34)
        self.assertAlmostEqual(report["projected_balance"], 100.08)
        self.assertTrue(all(row["balance"] == row["zero_return_balance"] for row in report["rows"]))

    def test_nominal_rate_convention_preserved(self):
        data = goal()
        data.update(target_amount=25000, years=10, annual_return=.12)
        report = project_goal(data)
        self.assertEqual(report["monthly_rate"], .01)
        self.assertEqual(report["monthly_contribution"], 36.95)
        self.assertAlmostEqual(report["projected_balance"], 25001.86, places=2)

    def test_risk_context_does_not_change_math(self):
        reports = [project_goal(goal(risk_tolerance=risk)) for risk in ("low", "moderate", "high", "not_specified")]
        self.assertTrue(all(r["monthly_contribution"] == reports[0]["monthly_contribution"] for r in reports))
        self.assertTrue(all(r["rows"] == reports[0]["rows"] for r in reports))
        self.assertEqual(len({r["risk_note"] for r in reports}), 4)

    def test_already_funded_and_negative_return(self):
        data = goal()
        data.update(current_savings=25000, annual_return=0)
        report = project_goal(data)
        self.assertEqual(report["monthly_contribution"], 0)
        self.assertEqual(report["projected_balance"], 25000)
        data.update(current_savings=20000, annual_return=-.05)
        negative = project_goal(data)
        self.assertGreater(negative["monthly_contribution"], 0)
        self.assertGreaterEqual(negative["projected_balance"], 20000)
        self.assertGreater(negative["zero_return_balance"], negative["projected_balance"])

    def test_near_zero_and_extreme_inputs_do_not_crash(self):
        for rate in (1e-15, -1e-15, 1e-300):
            data = goal()
            data["annual_return"] = rate
            report = project_goal(data)
            self.assertTrue(isfinite(report["monthly_contribution"]))
            self.assertAlmostEqual(report["monthly_contribution"], 250, delta=.011)
        data = goal()
        data.update(current_savings=1e308, years=100, annual_return=1)
        with self.assertRaisesRegex(ValueError, "numeric limits"):
            project_goal(data)

    def test_invalid_inputs(self):
        cases = [None, [], {}]
        for key, values in {
            "target_amount": (0, -1, True, "20000", float("nan"), float("inf"), 10**400),
            "current_savings": (-1, False), "annual_return": (-.99, 1.01),
            "years": (0, 101, 1.5, True), "risk_tolerance": (None, [], "aggressive"),
        }.items():
            for value in values:
                data = goal()
                data[key] = value
                cases.append(data)
        for data in cases:
            with self.subTest(data=data), self.assertRaises(ValueError):
                project_goal(data)

    def test_workflow_summary_parity_and_educational_limits(self):
        data = goal(risk_tolerance="low")
        result = build_workflow().invoke({"question": "Goal", "goal": data})
        self.assertEqual(result["intent"], "goal_planning")
        self.assertEqual(result["answer"], calculate_monthly_contribution(data))
        self.assertIn("$199.74", result["answer"])
        self.assertIn("$3,015.60 below", result["answer"])
        self.assertIn("not a guaranteed minimum", result["answer"])
        self.assertIn("investor.gov", result["answer"])


if __name__ == "__main__":
    unittest.main()
