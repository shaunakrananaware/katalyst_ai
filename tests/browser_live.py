"""Live UI acceptance: both servers and a valid Gemini key required.
Run from root: PYTHONPATH=. python tests/browser_live.py
No response mocks; requests go through Vite -> FastAPI -> Gemini -> graph tools.
"""

import json
import argparse
from playwright.sync_api import sync_playwright, expect
from backend.eval.queries import CASES
from backend.eval.run_eval import normalize, fact_present

selected = [CASES[i] for i in [0, 1, 2, 3, 4, 6, 7, 9]]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--only", help="Run one named case")
args = parser.parse_args()
if args.only:
    selected = [case for case in selected if case["name"] == args.only]
    if not selected:
        parser.error("Unknown case name")
results = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto("http://127.0.0.1:5173")
    for case in selected:
        page.get_by_role("button", name="New conversation").click()
        for question in case["turns"]:
            page.get_by_label("Message", exact=True).fill(question)
            with page.expect_response(
                lambda response: response.url.endswith("/api/chat"), timeout=360000
            ) as pending:
                page.get_by_role("button", name="Send ↑").click()
            response = pending.value
            assert response.status == 200, f'{case["name"]}: {response.status}'
            expect(page.get_by_label("Message", exact=True)).to_be_enabled(timeout=5000)
            expect(page.locator(".assistant .bubble").last).to_be_visible()
        reply = page.locator(".assistant .bubble").last.inner_text()
        text = normalize(reply)
        missing = [
            facts
            for facts in case["facts"]
            if not any(fact_present(f, reply) for f in facts)
        ]
        order = [text.find(normalize(f)) for f in case.get("ordered", [])]
        passed = not missing and all(i >= 0 for i in order) and order == sorted(order)
        results.append(
            {"name": case["name"], "passed": passed, "missing": missing, "reply": reply}
        )
        print(
            f"{'PASS' if passed else 'FAIL'} UI {case['name']} {missing if missing else ''}",
            flush=True,
        )
    page.screenshot(path="/tmp/katalyst-live-chat.png", full_page=True)
    browser.close()
path = "browser-live-results-single.json" if args.only else "browser-live-results.json"
with open(path, "w") as out:
    json.dump(results, out, indent=2)
assert all(
    r["passed"] for r in results
), "Some UI acceptance cases failed; see browser-live-results.json"
print(f"{len(results)}/{len(results)} live UI cases passed")
