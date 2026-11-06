"""Evaluation scoring must not count duplicate chunks as multiple gold sources."""

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from finnie.knowledge import load_sources
from scripts.evaluate_project import benchmark, payload_matches, score_retrieval


class EvaluationToolTests(unittest.TestCase):
    def test_dataset_has_unique_cases_and_existing_gold_sources(self):
        cases=json.loads((Path(__file__).resolve().parents[1]/'evaluation/cases.json').read_text())
        files={s['file'] for s in load_sources()}
        for section in ('retrieval','routing','answers'):
            self.assertEqual(len({c['id'] for c in cases[section]}),len(cases[section]))
        for case in cases['retrieval']:
            self.assertTrue(set(case['relevant_files']) <= files)

    def test_recall_uses_distinct_urls_and_all_comparison_sources(self):
        catalog=[dict(file='a.md',url='https://example.org/a'),dict(file='b.md',url='https://example.org/b')]
        matches=[dict(url='https://example.org/a')]*3
        scores=score_retrieval(matches,['a.md','b.md'],catalog)
        self.assertTrue(scores['hit_at_3'])
        self.assertEqual(scores['recall_at_3'],.5)
        with self.assertRaises(ValueError):
            score_retrieval(matches,['missing.md'],catalog)

    def test_payload_checks_preserve_numbers_and_list_length(self):
        expected={'goal':{'annual_return':.05,'years':5}}
        self.assertTrue(payload_matches(dict(goal=dict(annual_return=.05,years=5,extra=True)),expected))
        self.assertFalse(payload_matches(dict(goal=dict(annual_return=5,years=5)),expected))
        self.assertFalse(payload_matches([1,2],[1]))
        self.assertFalse(payload_matches(None,expected))

    def test_microbenchmark_counts_warmup_separately(self):
        calls=[]
        result=benchmark(lambda:calls.append(1),10)
        self.assertEqual(len(calls),15)
        self.assertEqual(result['iterations'],10)
        self.assertGreaterEqual(result['p95_ms'],result['p50_ms'])


if __name__=='__main__':
    unittest.main()
