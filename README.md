# Katalyst · Sales memory

A working prototype connecting a React chat to a read-only CRM memory layer: a typed NetworkX graph, lazy local semantic retrieval, and an explicit Gemini function-calling loop. Eight fictional deals across six prospect organizations provide three wins, three losses, and two prospects, with two meetings, notes, and emails per deal. The snapshot is dated September 8, 2026; amounts are integer USD.

```text
React chat → POST /chat → Gemini tool loop → validated Python tools
                              ↕                      ↓
                       per-session history    NetworkX MultiDiGraph
                                                     ↓
                                        lazy local ONNX embeddings
```

## Core decisions

- **Structured facts:** Python filters and sorts stages, amounts, and dates. Comparisons calculate group counts and totals in code. Asking for five prospects returns the two available. Open deals are excluded from close-date queries.
- **Graph memory:** Organization, Person, Lead, Meeting, Note, and Email nodes connect through `WORKS_AT`, `BELONGS_TO`, `OWNED_BY`, `FOR_LEAD`, `ATTENDED_BY`, `NOTE_OF`, `ABOUT_LEAD`, `SENT_BY`, and `SENT_TO`. Tools traverse typed adjacency, including lead ← meeting ← note and org ← person ← meeting → lead.
- **Semantic retrieval:** FastEmbed runs `sentence-transformers/all-MiniLM-L6-v2` locally through ONNX. Model loading and document embedding happen only on the first semantic request. Normalized document vectors are cached per lead for the process lifetime; queries are embedded at request time. The first use downloads free model weights, so it needs network access. Comparisons bundle all evidence directly because the dataset is small.
- **LLM reasoning:** Gemini chooses among nine tools, interprets retrieved notes/emails, and phrases answers with record IDs as citations. The loop preserves native function-call content, including thought signatures, and stops after six model turns. Provider requests retry transient errors up to three times (30 seconds between rate-limit retries); explicit daily quota exhaustion fails immediately. Source text is treated as data, not instructions. No hardcoded query router or simulated production answers.
- **Clarification:** Fuzzy name collisions and tied selection boundaries return candidates. The backend immediately stops the tool batch, asks the user to choose, and retains the original question. Reply with a numbered choice, exact name, or ID; “the second one” works. An unclear selection cannot resume tool execution.

## Run

Requires Python 3.10+ and Node 22.12+ (Node 24 also works).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set GOOGLE_API_KEY in .env; optionally change GEMINI_MODEL.
uvicorn backend.main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:5173**. The UI proxies `/api` to FastAPI on port 8000. API docs: http://127.0.0.1:8000/docs. The default model is `gemini-3.1-flash-lite`, which was available on the account’s free tier during validation. The key stays on the backend. `/health` reports whether a key is configured; a missing key produces an actionable 503 response. Use one backend worker because graph caches and sessions are in memory.

Try:

- “What's happening with the Figma - Enterprise Plan deal?”
- “Did we close the last deal, and what was the final amount?”
- “What happened in the last meeting for Figma - Enterprise Plan, and why did it fail?”
- “Top 5 deals by amount in prospect”
- “Compare the last 5 closed-won vs closed-lost deals. What can we learn?”
- “What's happening with Acme?” → “the second one”

“Figma” alone also deliberately requires clarification because it has two deals. Expand each assistant message's tool trace to inspect the actual arguments and retrieved evidence.

## Verify

```bash
python -m pytest -q                  # deterministic tools, cache, agent protocol, API
npm run build --prefix frontend     # production bundle
python -m backend.eval.run_eval     # 10 real Gemini cases; requires GOOGLE_API_KEY
```

The eval checks key facts, ranking order, and ambiguity traces; it writes `eval-results.json` and exits nonzero on failure. These are smoke checks, not a factuality proof. Protocol tests use an explicitly scripted model and do not establish Gemini answer quality.

Optional browser smoke (with both servers running):

```bash
pip install playwright
playwright install --with-deps chromium
python tests/browser_smoke.py
# Optional live browser acceptance: 8 cases, real Gemini calls
PYTHONPATH=. python tests/browser_live.py
```

It checks the real missing-key error path and uses explicitly mocked chat responses for UI clarification, session continuity, traces, and reset.

**Validation in the build environment:** 29 backend tests passed; frontend build passed; real local embedding retrieval and per-lead cache reuse passed. All 10 live Gemini eval cases and 8 live browser cases passed on `gemini-3.1-flash-lite` (comparison rerun after strengthening the numeric-fact check). The generated `eval-results.json` and `browser-live-results.json` contain the answers and results.

## Limits

Sessions disappear on restart and have a 500-session cap; chat history is not compacted. New conversation creates a fresh session. No authentication or source writes are implemented. Model phrasing remains probabilistic despite deterministic tool results; there is no formal final-answer verifier. Production would need authorization, persistent sessions, context limits, quota-aware request scheduling, source synchronization, and stronger citation/factuality evaluation. First-use embedding downloads add latency; the local model and cosine scores are relevance signals, not truth guarantees.

Gemini integration follows the [official Python SDK's manual function-calling interface](https://github.com/googleapis/python-genai). Model availability and [free-tier quotas](https://ai.google.dev/gemini-api/docs/rate-limits) depend on the Google account; `GEMINI_MODEL` is configurable. The initial `gemini-3.6-flash` run hit a 20-request daily limit, so the demo uses Flash-Lite. One chat may consume several model requests.
