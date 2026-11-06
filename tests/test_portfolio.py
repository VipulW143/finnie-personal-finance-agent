"""Portfolio arithmetic, duplicate positions, malformed inputs, and CSV parity."""

import math
from pathlib import Path
import unittest

from finnie.portfolio import analyze_portfolio, summarize_portfolio
from finnie.portfolio_import import CSV_TEMPLATE, parse_holdings_csv
from finnie.workflow import build_workflow


def holding(symbol="AAA", quantity=1, price=100, **fields):
    return dict(symbol=symbol, quantity=quantity, price=price, asset_type="ETF", **fields)


class PortfolioTests(unittest.TestCase):
    def test_sample_values_fees_and_asset_classes(self):
        rows = parse_holdings_csv(CSV_TEMPLATE.encode())
        report = analyze_portfolio(rows)
        self.assertEqual(report["total_value"], 1466)
        self.assertEqual(report["value_by_asset_class"], {"STOCKS": 1250, "BONDS": 216})
        self.assertAlmostEqual(report["annual_fees"], .4398)
        self.assertAlmostEqual(report["weighted_expense_ratio"], .0003)
        self.assertAlmostEqual(sum(p["weight"] for p in report["positions"]), 1)
        self.assertIn("$0.44", summarize_portfolio(rows))

    def test_duplicate_lots_do_not_inflate_diversification(self):
        rows = [holding(" aaa ", price=50), holding("AAA", price=50), holding("BBB", price=100)]
        report = analyze_portfolio(rows)
        self.assertEqual(report["input_rows"], 3)
        self.assertEqual(len(report["positions"]), 2)
        self.assertAlmostEqual(report["concentration"], .5)
        self.assertAlmostEqual(report["effective_positions"], 2)
        self.assertEqual(report["positions"][0]["market_value"], 100)

    def test_concentrated_and_equal_weight_portfolios(self):
        self.assertEqual(analyze_portfolio([holding()])["effective_positions"], 1)
        balanced = analyze_portfolio([holding(str(i)) for i in range(4)])
        self.assertEqual(balanced["concentration"], .25)
        self.assertEqual(balanced["effective_positions"], 4)
        concentrated = analyze_portfolio([holding("A", price=900), holding("B", price=100)])
        self.assertAlmostEqual(concentrated["concentration"], .82)
        self.assertLess(concentrated["effective_positions"], balanced["effective_positions"])

    def test_partial_fee_coverage_and_zero_are_different_from_missing(self):
        report = analyze_portfolio([holding("A", expense_ratio=0), holding("B")])
        self.assertEqual(report["known_fee_value"], 100)
        self.assertEqual(report["weighted_expense_ratio"], 0)
        self.assertIsNone(analyze_portfolio([holding()])["weighted_expense_ratio"])
        self.assertIn("$100.00 of $200.00", summarize_portfolio([holding("A", expense_ratio=0), holding("B")]))

    def test_missing_asset_class_remains_unknown(self):
        self.assertEqual(analyze_portfolio([holding("VTI")])["value_by_asset_class"], {"UNKNOWN": 100})

    def test_duplicate_conflicting_labels_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "conflicting"):
            analyze_portfolio([holding(asset_class="STOCKS"), holding(asset_class="BONDS")])

    def test_invalid_and_nonfinite_inputs(self):
        invalid = [None, [], [None], [holding(symbol=" ")], [holding(asset_class="Equities")]]
        for field in ("quantity", "price"):
            invalid.extend([[holding(**{field: value})] for value in (True, "2", 0, -1, math.nan, math.inf, 10**400)])
        invalid.extend([[holding(expense_ratio=value)] for value in (True, "0.1", -1, 1.01, math.nan, math.inf, 10**400)])
        invalid.extend([[holding(quantity=1e308, price=10)], [holding("A", price=1e308), holding("B", price=1e308)]])
        for rows in invalid:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                analyze_portfolio(rows)

    def test_csv_template_and_cli_share_workflow(self):
        rows = parse_holdings_csv(CSV_TEMPLATE.encode())
        result = build_workflow().invoke({"question": "Portfolio", "portfolio": rows})
        self.assertEqual(result["intent"], "portfolio_analysis")
        self.assertEqual(result["answer"], summarize_portfolio(rows))
        sample = Path(__file__).resolve().parents[1] / "samples/portfolio.csv"
        self.assertEqual(parse_holdings_csv(sample.read_bytes()), rows)

    def test_csv_bom_blank_optional_fields_and_blank_rows(self):
        data = '\ufeffsymbol,quantity,price,asset_type,asset_class,expense_ratio\nAAA,2,50,ETF,,\n,,,,,\n'
        rows = parse_holdings_csv(data.encode())
        self.assertEqual(rows, [holding(quantity=2., price=50.)])
        self.assertEqual(analyze_portfolio(rows)["total_value"], 100)

    def test_csv_rejects_structure_numbers_and_limits(self):
        invalid = [b'', b'\xff', b'symbol,quantity\nA,2',
                   b'symbol,quantity,price,asset_type,price\nA,1,2,ETF,2',
                   b'symbol,quantity,price,asset_type,expense_ratios\nA,1,2,ETF,0',
                   b'symbol,quantity,price,asset_type\nA,1,2,ETF,extra',
                   b'symbol,quantity,price,asset_type\nA,no,2,ETF',
                   b'symbol,quantity,price,asset_type\n"unclosed,1,2,ETF',
                   b'x' * 1_000_001,
                   ('symbol,quantity,price,asset_type\n' + 'A,1,2,ETF\n'*1001).encode()]
        for data in invalid:
            with self.subTest(prefix=data[:80]), self.assertRaises(ValueError):
                parse_holdings_csv(data)
        with self.assertRaises(ValueError):
            analyze_portfolio(parse_holdings_csv(b'symbol,quantity,price,asset_type\nA,nan,2,ETF'))


if __name__ == "__main__":
    unittest.main()
