"""UI smoke tests: real missing-key API path, then explicit mocked responses.
Run servers first; install playwright and chromium as documented in README.
This checks browser behavior, not Gemini answer quality.
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1280, 'height': 900})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:5173')
    expect(page.get_by_role('heading', name='Every deal has a story. Get the full picture.')).to_be_visible()
    page.screenshot(path='/tmp/katalyst-chat.png', full_page=True)
    # Real backend health and request behavior in the no-key environment.
    health = page.request.get('http://127.0.0.1:8000/health').json()
    if not health['gemini_configured']:
        page.get_by_label('Message', exact=True).fill('Top 5 deals by amount in prospect')
        page.get_by_role('button', name='Send ↑').click()
        expect(page.get_by_role('alert')).to_contain_text('GOOGLE_API_KEY')
        expect(page.get_by_label('Message', exact=True)).to_have_value('Top 5 deals by amount in prospect')
    page.get_by_role('button', name='New conversation').click()
    requests = []
    answers = [
        {'reply': 'Which did you mean?\n1. Acme Cloud (org-acme-cloud)\n2. Acme Labs (org-acme-labs)',
         'tool_calls': [{'name': 'resolve_entity', 'args': {'query': 'Acme', 'entity_type': 'organization'}, 'result': {'status': 'ambiguous'}}]},
        {'reply': 'Acme Labs lost the $48,000 Research CRM deal because it had no executive sponsor [lead-6].',
         'tool_calls': [{'name': 'get_org_context', 'args': {'org_id': 'org-acme-labs'}, 'result': {'leads': [{'id': 'lead-6', 'amount': 48000}]}}]},
    ]
    def chat(route):
        requests.append(route.request.post_data_json)
        route.fulfill(status=200, content_type='application/json', body=json.dumps(answers.pop(0)))
    page.route('**/api/chat', chat)
    page.get_by_label('Message', exact=True).fill("What's happening with Acme?")
    page.get_by_role('button', name='Send ↑').click()
    expect(page.locator('.assistant .bubble')).to_contain_text('Acme Cloud')
    page.get_by_label('Message', exact=True).fill('the second one')
    page.get_by_role('button', name='Send ↑').click()
    expect(page.locator('.assistant .bubble').last).to_contain_text('$48,000')
    assert requests[0]['session_id'] == requests[1]['session_id']
    assert requests[1]['message'] == 'the second one'
    page.locator('summary').last.click()
    expect(page.locator('.trace').last).to_contain_text('get_org_context')
    expect(page.locator('.trace').last).to_contain_text('48000')
    old_session = requests[-1]['session_id']
    page.get_by_role('button', name='New conversation').click()
    assert page.evaluate("sessionStorage.getItem('katalyst-session')") != old_session
    expect(page.locator('.message')).to_have_count(0)
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not errors, errors
    browser.close()
    print('Browser smoke passed: real API setup error, mocked chat, clarification, session continuity, traces, reset, narrow viewport.')
