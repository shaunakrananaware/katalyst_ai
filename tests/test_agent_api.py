import pytest
from google.genai import types
from fastapi.testclient import TestClient
from backend.agent import Agent, ProviderError, tool_declarations
from backend import main


def calls(*items):
    return types.Content(role='model', parts=[types.Part(function_call=types.FunctionCall(name=name, args=args, id=str(i))) for i, (name, args) in enumerate(items)])

def answer(text):
    return types.Content(role='model', parts=[types.Part.from_text(text=text)])

class ScriptedModel:
    """Protocol test double; never used by the production app or live eval."""
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.histories = []
    def generate(self, history):
        self.histories.append(list(history))
        result = next(self.responses)
        if isinstance(result, Exception): raise result
        return result


def test_all_tools_have_serializable_schemas():
    declarations = tool_declarations()
    assert len(declarations) == 9
    assert all(d.parameters_json_schema['type'] == 'object' for d in declarations)


def test_ambiguity_stops_batch_then_resumes_ordinal():
    model = ScriptedModel(
        calls(('resolve_entity', {'query': 'Acme', 'entity_type': 'organization'}),
              ('get_lead_details', {'lead_id': 'lead-5'})),
        calls(('get_org_context', {'org_id': 'org-acme-labs'})),
        answer('Acme Labs lost its Research CRM deal [lead-6].'))
    agent = Agent(model)
    first = agent.chat('one', "What's happening with Acme?")
    assert 'Acme Cloud' in first['reply'] and 'Acme Labs' in first['reply']
    assert first['tool_calls'][1]['result']['status'] == 'skipped'
    assert len(model.histories) == 1
    result = agent.chat('one', 'the second one')
    assert 'Acme Labs' in result['reply']
    assert 'org-acme-labs' in model.histories[1][-1].parts[0].text
    assert "What's happening with Acme?" in model.histories[1][-1].parts[0].text
    assert agent.sessions['one'].pending is None


def test_sessions_are_isolated():
    model = ScriptedModel(answer('One'), answer('Two'))
    agent = Agent(model)
    agent.chat('one', 'private context A')
    agent.chat('two', 'context B')
    assert len(model.histories[1]) == 1
    assert model.histories[1][0].parts[0].text == 'context B'


def test_error_does_not_commit_partial_history():
    agent = Agent(ScriptedModel(ProviderError('quota')))
    with pytest.raises(ProviderError): agent.chat('one', 'query')
    assert agent.sessions['one'].history == []


def test_unknown_tool_and_iteration_limit():
    agent = Agent(ScriptedModel(calls(('bad_tool', {}))), max_iterations=1)
    result = agent.chat('one', 'query')
    assert result['tool_calls'][0]['result']['status'] == 'invalid_input'
    assert 'limit' in result['reply']


def test_api_chat_trace_validation_and_cors(monkeypatch):
    model = ScriptedModel(calls(('rank_leads', {'stage': 'prospect'})), answer('Vercel $110,000; Figma $64,000.'))
    monkeypatch.setattr(main, 'agent', Agent(model))
    client = TestClient(main.app)
    response = client.post('/chat', json={'session_id': 'test', 'message': 'Top prospects'})
    assert response.status_code == 200
    assert response.json()['tool_calls'][0]['result'][0]['amount'] == 110000
    assert client.post('/chat', json={'session_id': 'test', 'message': ' '}).status_code == 422
    assert client.post('/chat', json={'session_id': '../', 'message': 'Hi'}).status_code == 422
    cors = client.options('/chat', headers={'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'POST'})
    assert cors.headers['access-control-allow-origin'] == 'http://localhost:5173'


def test_missing_key_is_actionable(monkeypatch):
    monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
    monkeypatch.setattr(main, 'agent', Agent())
    response = TestClient(main.app).post('/chat', json={'session_id': 'test', 'message': 'Hi'})
    assert response.status_code == 503
    assert 'GOOGLE_API_KEY' in response.json()['detail']


def test_unclear_followup_cannot_resume_tools():
    model = ScriptedModel(calls(('resolve_entity', {'query': 'Alex', 'entity_type': 'person'})))
    agent = Agent(model)
    agent.chat('one', 'Who is Alex?')
    result = agent.chat('one', 'whichever you think')
    assert 'Alex Chen' in result['reply'] and 'Alex Cheng' in result['reply']
    assert result['tool_calls'] == []
    assert len(model.histories) == 1


def test_provider_retries_transient_errors_and_sanitizes_failures(monkeypatch):
    from types import SimpleNamespace
    from google.genai.errors import ClientError
    from backend.agent import GeminiModel
    import backend.agent as module
    sleeps = []
    monkeypatch.setattr(module.time, 'sleep', sleeps.append)
    model = GeminiModel.__new__(GeminiModel)
    model.model, model.config = 'test-model', None
    results = iter([ClientError(429, {'error': {'message': 'secret-bearing upstream URL'}}),
                    SimpleNamespace(candidates=[SimpleNamespace(content=answer('Recovered'))])])
    def generate(**kwargs):
        result = next(results)
        if isinstance(result, Exception): raise result
        return result
    model.client = SimpleNamespace(models=SimpleNamespace(generate_content=generate))
    assert model.generate([]).parts[0].text == 'Recovered'
    assert sleeps == [30]
    def fail(**kwargs):
        raise ClientError(404, {'error': {'message': 'secret-bearing upstream URL'}})
    model.client.models.generate_content = fail
    with pytest.raises(ProviderError, match='GEMINI_MODEL') as error:
        model.generate([])
    assert 'secret' not in str(error.value)


def test_daily_quota_is_not_retried(monkeypatch):
    from types import SimpleNamespace
    from google.genai.errors import ClientError
    from backend.agent import GeminiModel
    import backend.agent as module
    sleeps = []
    monkeypatch.setattr(module.time, 'sleep', sleeps.append)
    model = GeminiModel.__new__(GeminiModel)
    model.model, model.config = 'test-model', None
    def fail(**kwargs):
        raise ClientError(429, {'error': {'details': [{'violations': [{'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier'}]}]}})
    model.client = SimpleNamespace(models=SimpleNamespace(generate_content=fail))
    with pytest.raises(ProviderError, match='daily quota'): model.generate([])
    assert not sleeps
