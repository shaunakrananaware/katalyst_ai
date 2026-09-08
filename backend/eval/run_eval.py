"""Run from repo root: python -m backend.eval.run_eval. Requires a real API key."""
import json
import argparse
import re
import sys
from uuid import uuid4
from backend.agent import Agent, ConfigurationError, ProviderError
from backend.eval.queries import CASES


def normalize(text):
    return re.sub(r'[,\s]+', ' ', text.casefold()).replace('$', '').replace(' ', '')

def fact_present(fact, text):
    # Citation IDs are evidence pointers, not asserted counts/amounts.
    expected = normalize(fact)
    if expected.isdigit():
        cleaned = normalize(re.sub(r'\[[^\]]+\]', '', text))
        return re.search(r'(?<!\d)' + re.escape(expected) + r'(?!\d)', cleaned) is not None
    return expected in normalize(text)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', help='Run one named case')
    args = parser.parse_args()
    cases = [case for case in CASES if not args.only or case['name'] == args.only]
    if not cases: parser.error('Unknown case name')
    agent = Agent()
    results = []
    for case in cases:
        session = str(uuid4())
        try:
            traces = []
            for question in case['turns']:
                response = agent.chat(session, question)
                traces.extend(response['tool_calls'])
            reply = normalize(response['reply'])
            missing = [alternatives for alternatives in case['facts'] if not any(fact_present(fact, response['reply']) for fact in alternatives)]
            ordered = [reply.find(normalize(s)) for s in case.get('ordered', [])]
            order_ok = all(i >= 0 for i in ordered) and ordered == sorted(ordered)
            ambiguity_ok = not case.get('ambiguous') or any(isinstance(t['result'], dict) and t['result'].get('status') == 'ambiguous' for t in traces)
            passed = not missing and order_ok and ambiguity_ok and bool(traces)
            results.append({'name': case['name'], 'passed': passed, 'missing': missing, **response})
            print(f"{'PASS' if passed else 'FAIL'} {case['name']}" + (f' missing={missing}' if missing else ''))
        except ConfigurationError as exc:
            print(f'BLOCKED: {exc}', file=sys.stderr)
            return 2
        except ProviderError as exc:
            results.append({'name': case['name'], 'passed': False, 'error': str(exc)})
            print(f"FAIL {case['name']}: {exc}")
    print(f"\n{sum(r['passed'] for r in results)}/{len(results)} passed")
    path = 'eval-results-single.json' if args.only else 'eval-results.json'
    with open(path, 'w') as out: json.dump(results, out, indent=2)
    return 0 if all(r['passed'] for r in results) else 1

if __name__ == '__main__': sys.exit(main())
