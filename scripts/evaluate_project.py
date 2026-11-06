"""Local benchmarks, opt-in live routing/retrieval, and answer review artifacts."""

import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone
from io import StringIO
import json
from math import ceil
from pathlib import Path
import platform
from statistics import median
from time import perf_counter

from finnie.config import get_settings
from finnie.embeddings import embed_texts
from finnie.goals import project_goal
from finnie.knowledge import category_of, load_sources
from finnie.portfolio import analyze_portfolio
from finnie.rag import answer_with_sources, load_knowledge_base
from finnie.routing import resolve_request
from finnie.vector_store import VectorStore

ROOT = Path(__file__).resolve().parents[1]


def benchmark(function, iterations=100):
    """Warm up and measure sequential local operations; not a load test."""
    for _ in range(5):
        function()
    timings = []
    for _ in range(iterations):
        start = perf_counter()
        function()
        timings.append((perf_counter()-start)*1000)
    ordered = sorted(timings)
    return dict(iterations=iterations, p50_ms=median(timings),
                p95_ms=ordered[ceil(.95*iterations)-1], min_ms=ordered[0])


def score_retrieval(matches, relevant_files, catalog):
    """Recall counts distinct gold documents, not duplicate chunks of one source."""
    gold = {source['url'] for source in catalog if source['file'] in relevant_files}
    if len(gold) != len(relevant_files) or not gold:
        raise ValueError('Every gold file must map to a distinct captured source')
    found = {match['url'] for match in matches}
    return dict(hit_at_3=bool(gold & found), recall_at_3=len(gold & found)/len(gold),
                top_1_relevant=bool(matches and matches[0]['url'] in gold))


def payload_matches(actual, expected):
    """Require supplied numerical/holding inputs to survive the router unchanged."""
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and payload_matches(actual[k], v) for k,v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(payload_matches(a,e) for a,e in zip(actual,expected))
    return actual == expected


def evaluate_live(store, cases, catalog, include_answers=False):
    # Batch the query embeddings so source indexing and query API time stay separate.
    start = perf_counter()
    vectors = embed_texts([case['question'] for case in cases['retrieval']])
    batch_ms = (perf_counter()-start)*1000
    if len(vectors) != len(cases['retrieval']):
        raise ValueError('Query embedding count differs from evaluation cases')
    retrieval = []
    for case, vector in zip(cases['retrieval'], vectors):
        selected = [chunk for chunk in store if not case['category'] or category_of(chunk['topic']) == case['category']]
        subset = VectorStore(selected)
        start = perf_counter()
        matches = subset.search(vector, 3)
        retrieval.append(dict(id=case['id'], question=case['question'], category=case['category'],
                              relevant_files=case['relevant_files'], **score_retrieval(matches,case['relevant_files'],catalog),
                              local_search_ms=(perf_counter()-start)*1000,
                              matches=[dict(title=m['title'],url=m['url'],score=m['score']) for m in matches]))
    routing = []
    for case in cases['routing']:
        start = perf_counter()
        decision = resolve_request(case['question'],case.get('history',[]))
        route_ok = decision['intent'] == case['expected_intent']
        data_ok = payload_matches(decision,case.get('expected_payload',{}))
        tasks_ok = (not case.get('expected_tasks') or sorted(t['intent'] for t in decision.get('tasks',[])) == sorted(case['expected_tasks']))
        routing.append(dict(id=case['id'], question=case['question'], expected=case['expected_intent'],
                            actual=decision, intent_pass=route_ok, payload_pass=data_ok, task_pass=tasks_ok,
                            passed=bool(route_ok and data_ok and tasks_ok), latency_ms=(perf_counter()-start)*1000))
    answers=[]
    if include_answers:
        for case in cases['answers']:
            start=perf_counter()
            answer=answer_with_sources(case['question'],store,tax_education=case['tax_education'])
            answers.append(dict(**case,answer=answer,latency_ms=(perf_counter()-start)*1000,
                                review_status='pending human/source review; not automatically graded'))
    return dict(query_embedding_batch_ms=batch_ms, retrieval=retrieval,routing=routing,answers=answers,
                summary=dict(retrieval_cases=len(retrieval),hit_at_3=sum(r['hit_at_3'] for r in retrieval)/len(retrieval),
                             mean_recall_at_3=sum(r['recall_at_3'] for r in retrieval)/len(retrieval),
                             top_1_rate=sum(r['top_1_relevant'] for r in retrieval)/len(retrieval),
                             routing_cases=len(routing),routing_passes=sum(r['passed'] for r in routing)))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true',help='Use configured embedding/router APIs for the curated cases')
    parser.add_argument('--answers',action='store_true',help='With --live, generate three answers for source review')
    args=parser.parse_args()
    if args.answers and not args.live:
        parser.error('--answers requires --live')
    cases=json.loads((ROOT/'evaluation/cases.json').read_text())
    report=dict(created_at_utc=datetime.now(timezone.utc).isoformat(),
                environment=dict(python=platform.python_version(),platform=platform.platform()),
                scope='Sequential local microbenchmarks; external APIs are excluded unless labeled live. No load/throughput or deployment SLA claim.',
                dataset_note=cases['description'],benchmarks={})
    portfolio=[dict(symbol='VTI',quantity=5,price=250,asset_type='ETF'),dict(symbol='BND',quantity=3,price=72,asset_type='Bond ETF')]
    goal=dict(target_amount=20000,current_savings=5000,years=5,annual_return=.05)
    report['benchmarks']['portfolio_2_rows']=benchmark(lambda:analyze_portfolio(portfolio))
    report['benchmarks']['goal_61_monthly_rows']=benchmark(lambda:project_goal(goal))
    with redirect_stdout(StringIO()):
        try:
            store=load_knowledge_base(allow_rebuild=args.live)
        except ValueError:
            if args.live:
                raise
            store=None
    if store:
        vector=store[0]['embedding']
        report['corpus']=dict(sources=len(load_sources()),chunks=len(store),dimensions=store.index.d)
        report['benchmarks']['faiss_top3_precomputed_vector']=benchmark(lambda:store.search(vector,3))
        def restore():
            with redirect_stdout(StringIO()):
                load_knowledge_base(allow_rebuild=False)
        report['benchmarks']['saved_index_load_and_fingerprint']=benchmark(restore,20)
    else:
        report['corpus']='No current saved index; offline FAISS measurements unavailable. Run --live to rebuild.'
    if args.live:
        report['models']=get_settings()
        report['live']=evaluate_live(store,cases,load_sources(),args.answers)
    out=ROOT/'reports'
    out.mkdir(exist_ok=True)
    (out/'evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
    lines=['# Finnie evaluation run','',f"Created: {report['created_at_utc']}",'',report['scope'],'',
           '| Local operation | Iterations | p50 ms | p95 ms |','| --- | ---: | ---: | ---: |']
    for name,values in report['benchmarks'].items():
        lines.append(f"| {name} | {values['iterations']} | {values['p50_ms']:.4f} | {values['p95_ms']:.4f} |")
    if args.live:
        lines.extend(['','## Curated live checks','',json.dumps(report['live']['summary'],indent=2),
                      '', 'Source/route case results and answer-review criteria are in evaluation.json. This is a small development set, not a held-out accuracy estimate.'])
    (out/'evaluation.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))
    print('\nDetailed report: reports/evaluation.json')
    if args.live and (report['live']['summary']['hit_at_3'] < .8 or report['live']['summary']['routing_passes'] < .8*len(cases['routing'])):
        raise SystemExit('Evaluation below the 80% development-set check; inspect failures before submission.')


if __name__=='__main__':
    main()
